from pydantic import BaseModel, Field
from typing import Optional

class ComplaintCreate(BaseModel):
    name: str = Field(..., description="Short title for the complaint")
    description: Optional[str] = Field(None, description="Detailed description")
    reporter_name: Optional[str] = Field(None)
    reporter_email: Optional[str] = Field(None)

class ComplaintResponse(BaseModel):
    id: int
    board_id: int
    list_id: int
    name: str
    description: Optional[str]
    created_at: Optional[str]
