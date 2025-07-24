import json
import logging
from functools import lru_cache
from typing import Optional

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

# === Scoring Result Schema ===

class InterestScoreResult(BaseModel):
    interest_score: float
    reason: str

# === LLM + Parser Factories ===

@lru_cache()
def get_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.gemini_api_key,
    )

@lru_cache()
def get_interest_score_output_parser() -> OutputFixingParser:
    llm = get_llm()
    base_parser = PydanticOutputParser(pydantic_object=InterestScoreResult)
    return OutputFixingParser.from_llm(parser=base_parser, llm=llm)

# === Prompt ===

def build_prompt_for_interest_score(lead_data: dict) -> str:
    return f"""
You are an AI assistant for DelightLoop, a B2B growth-marketing company that blends AI automation with human curation to scale personalized physical gifting across the customer journey. DelightLoop's core product is an AI-powered gifting platform called 'Gifty' that analyzes CRM data, psychographic signals, and purchase intent to identify high-value prospects or at-risk customers. Gifty selects personalized gifts, orchestrates handwritten notes, handles procurement and international logistics from warehouses across Asia, the US, and Europe, and triggers follow-ups tied to buyer actions—all fully integrated into existing CRM and GTM tools. The goal is to amplify pipeline growth, accelerate deal closures, and reduce churn by turning gifting into a measurable, automated campaign rather than a one-off gesture.

Here's the lead card information in JSON:
{json.dumps(lead_data, ensure_ascii=False, indent=2)}

Using this data, return a JSON object with:
- "interest_score": float from 0.0 (no fit) to 1.0 (perfect fit)
- "reason": short, clear justification for the score (1-2 sentences max)

Respond with only JSON in this format:
{{
  "interest_score": 0.85,
  "reason": "CTO at a SaaS company – strong fit for AI-powered gifting platform."
}}

Do not add explanations or extra output.
"""

# === Main Agent Function ===

async def score_lead_interest_with_ai(
    lead_data: dict,
    llm: Optional[BaseChatModel] = None,
    parser: Optional[BaseOutputParser] = None,
) -> dict:
    prompt = build_prompt_for_interest_score(lead_data)

    llm = llm or get_llm()
    parser = parser or get_interest_score_output_parser()

    try:
        result = await llm.ainvoke([HumanMessage(content=prompt)])
        structured_output = await parser.ainvoke(result.content)
        return structured_output.dict()
    except Exception as e:
        logger.exception("Error scoring lead interest")
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Lead interest scoring failed",
                "error": str(e),
                "raw_output": getattr(result, "content", None),
            },
        )
