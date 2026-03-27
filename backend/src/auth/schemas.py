"""
Pydantic schemas for auth control plane identity responses.
"""
from pydantic import BaseModel, ConfigDict


class CurrentUserResponse(BaseModel):
    """Current authenticated user metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    auth_mode: str
    connected_account_count: int
