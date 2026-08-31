from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str
    error_code: str
    request_id: str | None = None
    errors: list[dict[str, Any]] | None = None


class ItemListMeta(BaseModel):
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1)
    returned: int = Field(ge=0)
    has_next: bool = False
    has_previous: bool = False
