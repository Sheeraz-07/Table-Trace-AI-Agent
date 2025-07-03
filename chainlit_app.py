
import chainlit as cl
from main import extract_date_range_from_query, generate_report
from pdf_report import generate_pdf_report
from io import BytesIO

# Handle the start of the chat
@cl.on_chat_start
async def on_chat_start():
    await cl.Message(content="👋 Welcome! Please enter your query.").send()

# Handle user queries
@cl.on_message
async def on_message(message: cl.Message):
    raw_query = message.content

    if not raw_query.strip():
        await cl.Message(content="⚠️ Query cannot be empty!").send()
        return

    try:
        # Process the query
        cleaned_query, extracted_date_range = extract_date_range_from_query(raw_query)
        console_report, result_data = generate_report(cleaned_query, specific_dates=extracted_date_range)

        # Show result text
        if console_report:
            await cl.Message(content=console_report).send()
        else:
            await cl.Message(content="No data found for the given query.").send()

        # If there’s data, save it to user session and offer download
        if result_data:
            cl.user_session.set("query_info", {
                "cleaned_query": cleaned_query,
                "extracted_date_range": extracted_date_range,
                "result_data": result_data
            })

            await cl.Message(
                content="✅ Report generated. Click below to download the PDF.",
                actions=[
                    cl.Action(
                        name="download_pdf",
                        label="📄 Download PDF",
                        payload={"download": True}  # Payload can be anything, not needed here
                    )
                ]
            ).send()
        else:
            await cl.Message(content="ℹ️ No data available to generate a PDF report.").send()

    except Exception as e:
        await cl.Message(content=f"❌ An error occurred: {str(e)}").send()

# Handle PDF download button click
@cl.action_callback("download_pdf")
async def handle_download_pdf(action: cl.Action):
    query_info = cl.user_session.get("query_info")

    if not query_info:
        await cl.Message(content="⚠️ No report data found. Please run a query first.").send()
        return

    try:
        # Generate PDF
        pdf_bytes = generate_pdf_report(
            query_info["cleaned_query"],
            query_info["extracted_date_range"],
            query_info["result_data"]
        )
        pdf_bytes.seek(0)

        # Send the file to the user
        await cl.Message(
            content="📄 Here is your PDF report:",
            elements=[
                cl.File(
                    name="attendance_report.pdf",
                    content=pdf_bytes.read(),
                    mime="application/pdf"
                )
            ]
        ).send()
    except Exception as e:
        await cl.Message(content=f"❌ Error generating PDF: {str(e)}").send()

