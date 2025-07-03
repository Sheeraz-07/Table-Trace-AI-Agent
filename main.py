import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_community.utilities.sql_database import SQLDatabase
from sqlalchemy import create_engine, text
# import pdf_report
from pdf_report import generate_pdf_report
import re
sys.stdout.reconfigure(encoding='utf-8')
# Load environment variables 
load_dotenv()


os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")  
llm = ChatOpenAI(model="gpt-4", temperature=0, openai_api_key=os.environ["OPENAI_API_KEY"])

# Configure Database
try:
    engine = create_engine(
        f"mssql+pyodbc://{os.getenv('DB_USER')}:{os.getenv('DB_USER_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}?driver=ODBC+Driver+18+for+SQL+Server&timeout=30&TrustServerCertificate=Yes" #For Windows
        # f"{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}?driver=ODBC+Driver+17+for+SQL+Server&timeout=30&TrustServerCertificate=Yes" # For Linux
    )
    with engine.connect() as connection:
        print("✅ Database connection successful!")
        print(f"Connected to: {os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}")
except Exception as e:
    print("❌ Database connection failed!")
    print(f"Error: {str(e)}")
    exit(1)

db = SQLDatabase(engine)

# Schema Configuration
SCHEMA_INFO = """
Tables:
- Attendance (
    empId: integer,
    empName: varchar(200),
    depart: integer,
    departName: varchar(150),
    vrdate: date,
    staff_status_id: integer,
    status: varchar(30)
  )
  Primary Key: (empId, vrdate)
  Constraints: 
    - status must match staff_status_id:
      * status='Present' when staff_status_id=5
      * status='Absent' when staff_status_id=1
      * status='Rest Day' when staff_status_id=6
"""



sql_prompt = PromptTemplate(
    input_variables=["schema", "dates", "question"],
    template="""
You are a world-class AI assistant that converts human language into correct, efficient SQL Server (T-SQL) queries — no matter how vague, typo-filled, or informal the input is.

Schema:
{schema}

Time context (optional): {dates}

RULES:
1. 📊 ALWAYS return a valid T-SQL query that ONLY uses the schema above.
2. 🧠 Guess user intent from messy, incomplete, or slang input.
   - Examples: "get all hr", "show resting", "everyone absent", "who there last week"
3. 🔍 If the user wants names, IDs, or departments (e.g. "list all employees"), return columns like `empId`, `empName`, `departName`.
4. 🧾 For any column like `empName`, `departName`, or `status`, use `LIKE '%value%'` for text matching.
5. 📅 If the query mentions a date range like "from 2024-05-01 to 2024-05-31", use it. If not, fall back to this date context: `{dates}`
6. 📉 If nothing date-related is needed (e.g. “list all employees”), do NOT add date filters.
7. 🧮 If the question asks "how many", "count", or "total", return aggregate queries using COUNT(*).
8. 🛑 No explanations, comments, markdown, or non-SQL text.
9. Don't execute query that will delete database or modify because we only want to read data .s
Just output a clean, ready-to-run SQL query. Nothing else.

User’s question:
{question}

SQL:
"""
)


# Create the SQL chain using the prompt and LLM
sql_chain = RunnableSequence(sql_prompt | llm)

def get_previous_month_dates():
    return "2024-07-01 to 2024-07-31"

def generate_report(user_query, specific_dates=None):
    try:
        # Use specific dates if provided, else use previous month
        dates = specific_dates or get_previous_month_dates()
        sql_query = sql_chain.invoke({
            "schema": SCHEMA_INFO,
            "dates": dates,
            "question": user_query
        }).content.strip()
        
        # Clean SQL output
        sql_query = sql_query.replace("sql", "").replace("```", "").strip()
                
        # Execute Query
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            columns = list(result.keys())
            result_data = [dict(row) for row in result.mappings()]
        
        # Format console report
        if not result_data:
            return "No data found", []
        
        report = f"Report for: {user_query}\nDates: {dates}\n\n"
        report += "| " + " | ".join(col.title() for col in columns) + " |\n"
        report += "|-" + "-|-".join("-" * len(col) for col in columns) + "-|\n"
        for row in result_data:
            report += "| " + " | ".join(str(row[col]) for col in columns) + " |\n"
        
        return report, result_data
    
    except Exception as e:
        return f"Error generating report: {str(e)}", []



# Example Usage
def extract_date_range_from_query(query):
    # Match patterns like "2024-07-01 to 2024-07-31"
    match = re.search(r'(\d{4}-\d{2}-\d{2})\s*to\s*(\d{4}-\d{2}-\d{2})', query)
    if match:
        start_date, end_date = match.groups()
        date_range = f"{start_date} to {end_date}"
        # Remove the date range from the query string
        cleaned_query = re.sub(r'\s*from\s*' + re.escape(match.group(0)), '', query, flags=re.IGNORECASE).strip()
        return cleaned_query, date_range
    else:
        return query, None  # fallback to default date range if not found

