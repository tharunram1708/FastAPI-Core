from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.schemas.item import ItemCreate, ItemPatch


class MessageResponse(BaseModel):
    message: str


class DocumentRead(BaseModel):
    id: UUID
    owner_id: UUID | None
    filename: str
    content_type: str
    size_bytes: int
    checksum: str
    description: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class DocumentUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=500)


class CSVImportResponse(BaseModel):
    inserted: int
    errors: list[dict[str, Any]] = Field(default_factory=list)


class CSVExportFilter(BaseModel):
    q: str | None = None
    category: str | None = None
    is_active: bool | None = None


class NotificationCreate(BaseModel):
    user_id: UUID | None = None
    title: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=1, max_length=2000)
    category: str = Field(default="general", min_length=1, max_length=80)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationRead(BaseModel):
    id: UUID
    user_id: UUID | None
    title: str
    message: str
    category: str
    read_at: datetime | None
    delivered_at: datetime | None
    metadata: dict[str, Any] = Field(
        validation_alias="notification_metadata",
        serialization_alias="metadata",
    )
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("created_at", "read_at", "delivered_at", when_used="json")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        return value.isoformat() if value is not None else None


class BulkDeleteRequest(BaseModel):
    ids: list[UUID] = Field(min_length=1, max_length=100)


class BulkItemCreateRequest(BaseModel):
    items: list[ItemCreate] = Field(min_length=1, max_length=100)


class BulkItemUpdate(BaseModel):
    id: UUID
    data: ItemPatch


class BulkItemUpdateRequest(BaseModel):
    items: list[BulkItemUpdate] = Field(min_length=1, max_length=100)


class BulkOperationResponse(BaseModel):
    created: int = 0
    updated: int = 0
    deleted: int = 0
    failed: int = 0
    errors: list[dict[str, Any]] = Field(default_factory=list)


class AuditLogRead(BaseModel):
    id: UUID
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    ip_address: str | None
    details: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecordHistoryRead(BaseModel):
    id: UUID
    resource_type: str
    resource_id: str
    version: int
    previous_data: dict[str, Any]
    changed_by_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WebhookEventCreate(BaseModel):
    source: str = Field(min_length=1, max_length=120)
    event_type: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source", "event_type")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return " ".join(value.strip().split())


class WebhookEventRead(BaseModel):
    id: UUID
    source: str
    event_type: str
    payload: dict[str, Any]
    status: str
    attempts: int
    next_retry_at: datetime | None
    last_error: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SearchResponse(BaseModel):
    data: list[Any]
    total: int
    skip: int
    limit: int


class ExternalAPIResponse(BaseModel):
    source: str
    ok: bool
    data: dict[str, Any]


class HealthDetailResponse(BaseModel):
    status: str
    checks: dict[str, str]
    version: str
    environment: str


class JobRunResponse(BaseModel):
    name: str
    result: dict[str, Any]
    ran_at: datetime
