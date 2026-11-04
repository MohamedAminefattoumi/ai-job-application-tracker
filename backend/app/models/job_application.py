from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Time,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.application_activity import ApplicationActivity


class JobApplication(Base):
    __tablename__ = "job_applications"

    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="check_confidence_range",
        ),
    )

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    # Application information
    company: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    position: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # AI classification
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PENDING",
    )

    email_category: Mapped[str | None] = mapped_column(
        String(40),
        nullable=True,
    )

    confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    # Interview information
    interview_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    interview_time: Mapped[time | None] = mapped_column(
        Time,
        nullable=True,
    )

    # Deduplication
    application_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    # Email chronology
    last_email_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Automatic timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Activity history (ordered chronologically, oldest to newest)
    activities: Mapped[list["ApplicationActivity"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationActivity.event_at.asc(), ApplicationActivity.id.asc()",
    )
