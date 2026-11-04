from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Allowed values for AI classification
ApplicationStatus = Literal[
    "PENDING",
    "INTERVIEW",
    "INTERVIEW_CONFIRMED",
    "REJECTED",
    "OFFER_RECEIVED",
    "UNKNOWN",
]

EmailCategory = Literal[
    "APPLICATION_RECEIVED",
    "INTERVIEW_INVITATION",
    "INTERVIEW_CONFIRMED",
    "REJECTION",
    "OFFER_RECEIVED",
    "OTHER",
    "UNKNOWN",
]


def _normalize_optional_value(value: Any) -> Any:
    """Convert empty strings or 'null'/'none' strings from LLM/n8n outputs into None."""
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped or stripped.lower() in {"null", "none", "n/a", "unspecified"}:
            return None
        return stripped
    return value


def _normalize_interview_date(value: Any) -> Any:
    value = _normalize_optional_value(value)
    if value is None or isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Accept full ISO datetime strings like '2026-11-12T10:30:00Z' and extract the date part
        if "T" in value:
            value = value.split("T", 1)[0]
        elif " " in value and len(value) > 10:
            value = value.split(" ", 1)[0]
        for fmt in ("%d.%m.%Y", "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return value


def _normalize_interview_time(value: Any) -> Any:
    value = _normalize_optional_value(value)
    if value is None or isinstance(value, time):
        return value
    if isinstance(value, str):
        cleaned = value.upper().replace("UHR", "").strip()
        for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M%p", "%I %p"):
            try:
                return datetime.strptime(cleaned, fmt).time()
            except ValueError:
                continue
    return value


# 0. Schema for application activity history items
class ApplicationActivityResponse(BaseModel):
    id: int
    application_id: int
    event_type: str
    title: str
    description: str | None
    old_value: str | None
    new_value: str | None
    event_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# 1. Schema for creating an application
class JobApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=150)
    position: str = Field(min_length=1, max_length=200)

    summary: str | None = None

    status: ApplicationStatus = "PENDING"
    email_category: EmailCategory | None = None

    interview_date: date | None = None
    interview_time: time | None = None

    confidence: float | None = Field(default=None, ge=0, le=1)

    application_key: str = Field(min_length=1, max_length=255)
    last_email_at: datetime | None = None

    @field_validator("summary", "email_category", "confidence", "last_email_at", mode="before")
    @classmethod
    def normalize_nullable_fields(cls, value: Any) -> Any:
        return _normalize_optional_value(value)

    @field_validator("interview_date", mode="before")
    @classmethod
    def normalize_date_field(cls, value: Any) -> Any:
        return _normalize_interview_date(value)

    @field_validator("interview_time", mode="before")
    @classmethod
    def normalize_time_field(cls, value: Any) -> Any:
        return _normalize_interview_time(value)


# 2. Schema for updating an application
class JobApplicationUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=150)
    position: str | None = Field(default=None, min_length=1, max_length=200)

    summary: str | None = None

    status: ApplicationStatus | None = None
    email_category: EmailCategory | None = None

    interview_date: date | None = None
    interview_time: time | None = None

    confidence: float | None = Field(default=None, ge=0, le=1)

    last_email_at: datetime | None = None

    @field_validator("summary", "email_category", "confidence", "last_email_at", mode="before")
    @classmethod
    def normalize_nullable_fields(cls, value: Any) -> Any:
        return _normalize_optional_value(value)

    @field_validator("interview_date", mode="before")
    @classmethod
    def normalize_date_field(cls, value: Any) -> Any:
        return _normalize_interview_date(value)

    @field_validator("interview_time", mode="before")
    @classmethod
    def normalize_time_field(cls, value: Any) -> Any:
        return _normalize_interview_time(value)


# 3. Schema for returning an application
class JobApplicationResponse(BaseModel):
    id: int

    company: str
    position: str
    summary: str | None

    status: ApplicationStatus
    email_category: EmailCategory | None

    interview_date: date | None
    interview_time: time | None

    confidence: float | None
    application_key: str
    last_email_at: datetime | None

    created_at: datetime
    updated_at: datetime

    activities: list[ApplicationActivityResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
