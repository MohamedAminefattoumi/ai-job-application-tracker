
from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# Allowed values for AI classification
ApplicationStatus = Literal[
    "PENDING",
    "INTERVIEW",
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

    model_config = ConfigDict(from_attributes=True)