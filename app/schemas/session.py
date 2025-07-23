from pydantic import BaseModel, Field

class SessionResponse(BaseModel):
    session_id: str = Field(..., description="Client-facing session ID")

