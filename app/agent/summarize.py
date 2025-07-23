from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=settings.gemini_api_key,
    temperature=0.3,
)

prompt = ChatPromptTemplate.from_template(
    """
    Summarize the following conversation in a single paragraph focusing on the user's interest in the product:

    {transcript}
    """
)

parser = StrOutputParser()
summarize_chain = prompt | llm | parser


async def summarize_interest(transcript: str) -> str:
    try:
        return await summarize_chain.ainvoke({"transcript": transcript})
    except Exception as e:
        return f"Summary unavailable: {str(e)}"
