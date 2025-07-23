import json
import logging
from functools import lru_cache
from typing import Literal, Optional

from fastapi import HTTPException
from langchain.output_parsers import OutputFixingParser
from langchain.output_parsers.pydantic import PydanticOutputParser
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers.base import BaseOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger(__name__)


# === Models ===


class LeadTagResult(BaseModel):
    tag: Literal["hot", "warm", "cold"]


# === Prompt Builder ===


def build_prompt_for_lead_tagging(
    lead_data: dict, company_context: str, interactions: list[str], session_count: int
) -> str:
    return f"""
You are an intelligent lead classification agent working for **{company_context}**.

{company_context} is an AI-powered customer engagement platform that helps SaaS and product-led growth companies 
increase user retention, product adoption, and reduce churn using behavior-based workflows, feedback campaigns, 
and activation nudges.

Your task is to analyze the lead's details and assign a tag:
- "hot": strong interest match + prior activity
- "warm": some relevance, limited prior signals
- "cold": weak/no relevance

Lead Details:
- Name: {lead_data.get("full_name", "N/A")}
- Email(s): {lead_data.get("emails", "N/A")}
- Phone(s): {lead_data.get("phones", "N/A")}
- Job title: {lead_data.get("title", "N/A")}
- Company: {lead_data.get("company", "N/A")}
- Website: {lead_data.get("website", "N/A")}

Previous Interactions:
{interactions if interactions else 'None found'}

Session Activity Matches: {session_count}

Return only a valid JSON object in this format:
{{
  "tag": "hot"
}}

Ensure the output is strictly valid JSON with no explanation or extra text.
""".strip()


# === Cached Factories ===


@lru_cache()
def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.gemini_api_key,
    )


@lru_cache()
def get_output_parser() -> OutputFixingParser:
    llm = get_llm()
    base_parser = PydanticOutputParser(pydantic_object=LeadTagResult)
    return OutputFixingParser.from_llm(parser=base_parser, llm=llm)


# === Main Logic ===


async def classify_lead_with_ai(
    lead_data: dict,
    interactions: list[str],
    session_count: int,
    llm: Optional[BaseChatModel] = None,
    parser: Optional[BaseOutputParser] = None,
) -> dict:
    prompt = build_prompt_for_lead_tagging(
        lead_data=lead_data,
        company_context="Delightloop",
        interactions=interactions,
        session_count=session_count,
    )

    logger.info("Prompt sent to LLM:\n%s", prompt)
    print("\n===== Prompt Sent to LLM =====\n")
    print(prompt)
    print("\n==============================\n")

    llm = llm or get_llm()
    parser = parser or get_output_parser()

    try:
        result = await llm.ainvoke([HumanMessage(content=prompt)])

        logger.info("Raw LLM Output:\n%s", result.content)
        print("\n===== Raw LLM Output =====\n")
        print(result.content)
        print("\n==========================\n")

        structured_output = await parser.ainvoke(result.content)

        return structured_output.dict()

    except Exception as e:
        logger.error("Error parsing LLM output: %s", str(e))
        logger.error(
            "LLM Output that caused error:\n%s",
            result.content if result else "No result",
        )
        print(f"Error parsing output: {e}")
        print(
            f"LLM Output that caused error:\n{result.content if result else 'No result'}"
        )

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Lead classification failed",
                "error": str(e),
                "raw_output": result.content if result else None,
            },
        )
