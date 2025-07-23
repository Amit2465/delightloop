import logging
from typing import List, Optional

from beanie.operators import In, Or

from app.db.models.lead_interactions import MockLeadInteraction

logger = logging.getLogger("uvicorn.error")


async def find_mock_interactions(
    emails: Optional[List[str]] = None,
    phones: Optional[List[str]] = None,
    name: Optional[str] = None,
    company: Optional[str] = None,
) -> List[str]:
    """
    Search for mock interactions based on one or more lead identifiers.

    Any of the input fields may be null or empty. Only valid filters will be applied.
    Returns all non-empty interaction summaries found for matching entries.

    Args:
        emails (Optional[List[str]]): One or more lead email addresses.
        phones (Optional[List[str]]): One or more lead phone numbers.
        name (Optional[str]): Full name of the lead.
        company (Optional[str]): Company name associated with the lead.

    Returns:
        List[str]: List of interaction summary strings.
    """
    filters = []

    logger.info("[MATCH-INTERACTION] Starting lookup with the following input:")
    logger.info("  Emails: %s", emails)
    logger.info("  Phones: %s", phones)
    logger.info("  Name: %s", name)
    logger.info("  Company: %s", company)

    if emails:
        valid_emails = [e for e in emails if e]
        if valid_emails:
            filters.append(In(MockLeadInteraction.emails, valid_emails))
            logger.info("  Added email filter")

    if phones:
        valid_phones = [p for p in phones if p]
        if valid_phones:
            filters.append(In(MockLeadInteraction.phones, valid_phones))
            logger.info("  Added phone filter")

    if name and company:
        filters.append(
            Or(MockLeadInteraction.name == name, MockLeadInteraction.company == company)
        )
        logger.info("  Added name or company filter")
    elif name:
        filters.append(MockLeadInteraction.name == name)
        logger.info("  Added name-only filter")
    elif company:
        filters.append(MockLeadInteraction.company == company)
        logger.info("  Added company-only filter")

    if not filters:
        logger.warning(
            "[MATCH-INTERACTION] No valid filters provided. Query will be skipped."
        )
        return []

    logger.info("[MATCH-INTERACTION] Applying %d filters", len(filters))

    try:
        results = await MockLeadInteraction.find(Or(*filters)).to_list()
        logger.info(
            "[MATCH-INTERACTION] Found %d matching interaction(s)", len(results)
        )
        return [doc.interaction_summary for doc in results if doc.interaction_summary]
    except Exception as e:
        logger.exception("Error while querying mock interactions: %s", str(e))
        return []
