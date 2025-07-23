from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict

class ParsedFields(BaseModel):
    full_name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    custom_fields: Optional[Dict[str, str]] = Field(default_factory=dict)

    model_config = {
        "extra": "allow"  
    }

class OcrResult(BaseModel):
    lead_id: str
    status: str
    emails: List[EmailStr]
    phones: List[str]
    parsed_fields: ParsedFields
    tag: str