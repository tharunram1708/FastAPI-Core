from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator


def _clean(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ValueError("value cannot be blank")
    return normalized


def _email(value: str) -> str:
    normalized = value.strip().casefold()
    if "@" not in normalized or any(character.isspace() for character in normalized):
        raise ValueError("email must be valid")
    return normalized


class EmployeeBase(BaseModel):
    employee_code: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    department: str = Field(default="operations", min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=120)
    salary: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    status: Literal["active", "inactive", "terminated"] = "active"
    user_id: UUID | None = None

    @field_validator("employee_code", "first_name", "last_name", "department", "title")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _clean(value)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _email(value)

    @field_validator("phone")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    phone: str | None = Field(default=None, max_length=40)
    department: str | None = Field(default=None, min_length=1, max_length=80)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    salary: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    status: Literal["active", "inactive", "terminated"] | None = None
    user_id: UUID | None = None

    @field_validator("first_name", "last_name", "phone", "department", "title")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None


class EmployeeRead(EmployeeBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CustomerBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    billing_address: str | None = Field(default=None, max_length=1000)
    status: Literal["active", "inactive", "blocked"] = "active"

    @field_validator("name", "phone", "billing_address")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _email(value)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    billing_address: str | None = Field(default=None, max_length=1000)
    status: Literal["active", "inactive", "blocked"] | None = None

    @field_validator("name", "phone", "billing_address")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None


class CustomerRead(CustomerBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    sku: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    category: str = Field(default="general", min_length=1, max_length=80)
    unit_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    stock_quantity: int = Field(default=0, ge=0)
    status: Literal["active", "inactive", "discontinued"] = "active"

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return _clean(value).upper()

    @field_validator("name", "description", "category")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    stock_quantity: int | None = Field(default=None, ge=0)
    status: Literal["active", "inactive", "discontinued"] | None = None

    @field_validator("name", "description", "category")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None


class ProductRead(ProductBase):
    id: UUID
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_price", when_used="json")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OrderLineCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0, le=100000)


class OrderLineRead(BaseModel):
    id: UUID
    order_id: UUID
    product_id: UUID | None
    sku: str
    name: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("unit_price", "line_total", when_used="json")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class OrderCreate(BaseModel):
    customer_id: UUID
    order_number: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=1000)
    line_items: list[OrderLineCreate] = Field(min_length=1, max_length=100)

    @field_validator("order_number", "notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None


class OrderUpdate(BaseModel):
    status: Literal["draft", "confirmed", "paid", "fulfilled", "cancelled"] | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None


class OrderRead(BaseModel):
    id: UUID
    order_number: str
    customer_id: UUID
    status: str
    total_amount: Decimal
    notes: str | None
    created_at: datetime
    updated_at: datetime | None
    line_items: list[OrderLineRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("total_amount", when_used="json")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class PaymentCreate(BaseModel):
    order_id: UUID
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: Literal["cash", "card", "bank_transfer", "wallet"]
    transaction_reference: str | None = Field(default=None, max_length=160)

    @field_validator("transaction_reference")
    @classmethod
    def normalize_reference(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None


class PaymentUpdate(BaseModel):
    status: Literal["pending", "completed", "failed", "refunded"]


class PaymentRead(BaseModel):
    id: UUID
    order_id: UUID
    customer_id: UUID
    amount: Decimal
    method: str
    status: str
    transaction_reference: str | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("amount", when_used="json")
    def serialize_money(self, value: Decimal) -> str:
        return f"{value:.2f}"


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    assigned_to_user_id: UUID | None = None
    employee_id: UUID | None = None
    customer_id: UUID | None = None
    order_id: UUID | None = None
    status: Literal["open", "in_progress", "blocked", "completed"] = "open"
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    due_at: datetime | None = None

    @field_validator("title", "description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    description: str | None = Field(default=None, max_length=2000)
    assigned_to_user_id: UUID | None = None
    employee_id: UUID | None = None
    customer_id: UUID | None = None
    order_id: UUID | None = None
    status: Literal["open", "in_progress", "blocked", "completed"] | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    due_at: datetime | None = None

    @field_validator("title", "description")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        return _clean(value) if value is not None else None


class TaskRead(TaskCreate):
    id: UUID
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class ReportCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    report_type: Literal["sales_summary", "customer_summary", "task_summary", "inventory_summary"]
    filters: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return _clean(value)


class ReportRead(BaseModel):
    id: UUID
    name: str
    report_type: str
    filters: dict[str, Any]
    generated_by_id: UUID | None
    status: str
    result: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
