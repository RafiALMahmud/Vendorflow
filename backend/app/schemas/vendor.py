from datetime import datetime
import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


PHONE_PATTERN = re.compile(r"^[0-9+().\-\s]{7,40}$")


def normalize_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} cannot be blank")
    return normalized


class VendorProfileFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1, max_length=200)
    registration_number: str = Field(min_length=1, max_length=100)
    contact_email: EmailStr
    phone: str = Field(min_length=7, max_length=40)
    address: str = Field(min_length=1, max_length=500)

    @field_validator("company_name", "registration_number", "phone", "address")
    @classmethod
    def normalize_text(cls, value: str, info) -> str:
        return normalize_required_text(value, info.field_name)

    @field_validator("contact_email", mode="after")
    @classmethod
    def normalize_contact_email(cls, value: EmailStr) -> str:
        return str(value).strip().casefold()

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if not PHONE_PATTERN.fullmatch(value):
            raise ValueError("phone contains unsupported characters")
        return value


class VendorCreate(VendorProfileFields):
    pass


class VendorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str | None = Field(default=None, min_length=1, max_length=200)
    registration_number: str | None = Field(default=None, min_length=1, max_length=100)
    contact_email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=40)
    address: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def require_non_null_update(self) -> "VendorUpdate":
        supplied = self.model_fields_set
        if not supplied:
            raise ValueError("At least one profile field is required")
        if any(getattr(self, field) is None for field in supplied):
            raise ValueError("Profile fields cannot be null")
        return self

    @field_validator("company_name", "registration_number", "phone", "address")
    @classmethod
    def normalize_optional_text(cls, value: str | None, info) -> str | None:
        if value is None:
            return value
        return normalize_required_text(value, info.field_name)

    @field_validator("contact_email", mode="after")
    @classmethod
    def normalize_optional_email(cls, value: EmailStr | None) -> str | None:
        return None if value is None else str(value).strip().casefold()

    @field_validator("phone")
    @classmethod
    def validate_optional_phone(cls, value: str | None) -> str | None:
        if value is not None and not PHONE_PATTERN.fullmatch(value):
            raise ValueError("phone contains unsupported characters")
        return value


class VendorResponse(VendorProfileFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_user_id: UUID
    created_at: datetime
    updated_at: datetime
