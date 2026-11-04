from datetime import date, datetime, time, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models.application_activity import ApplicationActivity
from app.models.job_application import JobApplication
from app.schemas.job_application import (
    ApplicationActivityResponse,
    JobApplicationCreate,
    JobApplicationResponse,
    JobApplicationUpdate,
)

router = APIRouter(
    prefix="/applications",
    tags=["Job Applications"],
)

_STATUS_LABELS = {
    "PENDING": "Pending",
    "INTERVIEW": "Interview",
    "INTERVIEW_CONFIRMED": "Interview Confirmed",
    "REJECTED": "Rejected",
    "OFFER_RECEIVED": "Offer Received",
    "UNKNOWN": "Unknown",
}

_EMAIL_CATEGORY_TITLES = {
    "APPLICATION_RECEIVED": "Application received",
    "INTERVIEW_INVITATION": "Interview invitation received",
    "INTERVIEW_CONFIRMED": "Interview confirmed",
    "REJECTION": "Rejection received",
    "OFFER_RECEIVED": "Offer received",
    "OTHER": "Application update received",
    "UNKNOWN": "Email processed",
}

_EMAIL_CATEGORY_TO_STATUS = {
    "APPLICATION_RECEIVED": "PENDING",
    "INTERVIEW_INVITATION": "INTERVIEW",
    "INTERVIEW_CONFIRMED": "INTERVIEW_CONFIRMED",
    "REJECTION": "REJECTED",
    "OFFER_RECEIVED": "OFFER_RECEIVED",
}


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _format_date(d: date | None) -> str:
    if d is None:
        return "Not specified"
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def _format_time(t: time | None) -> str:
    if t is None:
        return "Not specified"
    return t.strftime("%H:%M")


def _status_label(status_value: str | None) -> str:
    if not status_value:
        return "Unknown"
    return _STATUS_LABELS.get(status_value, status_value)


def _record_creation_activities(
    db: Session,
    application: JobApplication,
    source: str,
    event_time: datetime,
) -> None:
    category = application.email_category
    status_label = _status_label(application.status)

    if source == "sync" and category in _EMAIL_CATEGORY_TITLES:
        title = f"{_EMAIL_CATEGORY_TITLES[category]} → {status_label}"
    else:
        title = f"Application created → {status_label}"

    description_parts = [f"{application.company} — {application.position}"]
    if application.summary:
        description_parts.append(application.summary)

    db.add(
        ApplicationActivity(
            application_id=application.id,
            event_type="CREATED",
            title=title,
            description=" · ".join(description_parts),
            old_value=None,
            new_value=application.status,
            event_at=event_time,
        )
    )

    if application.interview_date or application.interview_time:
        schedule_str = f"{_format_date(application.interview_date)} at {_format_time(application.interview_time)}"
        db.add(
            ApplicationActivity(
                application_id=application.id,
                event_type="INTERVIEW_SCHEDULED",
                title=f"Interview scheduled → {schedule_str}",
                description=f"Date: {_format_date(application.interview_date)} · Time: {_format_time(application.interview_time)}",
                old_value=None,
                new_value=schedule_str,
                event_at=event_time,
            )
        )


def _record_change_activities(
    db: Session,
    application: JobApplication,
    old_snapshot: dict[str, Any],
    source: str,
    event_time: datetime,
) -> None:
    events_added = 0

    old_status = old_snapshot.get("status")
    new_status = application.status
    if new_status != old_status:
        category = application.email_category
        if source == "sync" and category in _EMAIL_CATEGORY_TITLES:
            title = f"{_EMAIL_CATEGORY_TITLES[category]} → {_status_label(new_status)}"
        else:
            title = f"Status updated: {_status_label(old_status)} → {_status_label(new_status)}"

        db.add(
            ApplicationActivity(
                application_id=application.id,
                event_type="STATUS_CHANGED",
                title=title,
                description=application.summary if source == "sync" and application.summary != old_snapshot.get("summary") else None,
                old_value=old_status,
                new_value=new_status,
                event_at=event_time,
            )
        )
        events_added += 1

    old_date = old_snapshot.get("interview_date")
    new_date = application.interview_date
    if new_date != old_date:
        old_str = _format_date(old_date)
        new_str = _format_date(new_date)
        title = (
            f"Interview date scheduled → {new_str}"
            if old_date is None
            else f"Interview date updated → {new_str}"
        )
        db.add(
            ApplicationActivity(
                application_id=application.id,
                event_type="INTERVIEW_DATE_UPDATED",
                title=title,
                description=f"Previous: {old_str}" if old_date is not None else None,
                old_value=old_date.isoformat() if old_date else None,
                new_value=new_date.isoformat() if new_date else None,
                event_at=event_time,
            )
        )
        events_added += 1

    old_time = old_snapshot.get("interview_time")
    new_time = application.interview_time
    if new_time != old_time:
        old_str = _format_time(old_time)
        new_str = _format_time(new_time)
        title = (
            f"Interview time scheduled → {new_str}"
            if old_time is None
            else f"Interview time updated → {new_str}"
        )
        db.add(
            ApplicationActivity(
                application_id=application.id,
                event_type="INTERVIEW_TIME_UPDATED",
                title=title,
                description=f"Previous: {old_str}" if old_time is not None else None,
                old_value=old_str if old_time else None,
                new_value=new_str if new_time else None,
                event_at=event_time,
            )
        )
        events_added += 1

    # Record summary or metadata updates when no status/interview change already captured it
    if events_added == 0:
        changed_fields = [
            field
            for field in ("company", "position", "summary", "email_category", "confidence")
            if getattr(application, field) != old_snapshot.get(field)
        ]
        if changed_fields:
            if source == "sync":
                category = application.email_category
                title = _EMAIL_CATEGORY_TITLES.get(category, "Synchronization update received")
            else:
                title = f"Application details updated ({', '.join(changed_fields)})"
            db.add(
                ApplicationActivity(
                    application_id=application.id,
                    event_type="UPDATED",
                    title=title,
                    description=application.summary if "summary" in changed_fields else None,
                    old_value=None,
                    new_value=", ".join(changed_fields),
                    event_at=event_time,
                )
            )


def _snapshot(application: JobApplication) -> dict[str, Any]:
    return {
        "company": application.company,
        "position": application.position,
        "summary": application.summary,
        "status": application.status,
        "email_category": application.email_category,
        "confidence": application.confidence,
        "interview_date": application.interview_date,
        "interview_time": application.interview_time,
    }


def _normalize_sync_status(incoming_data: dict[str, Any]) -> None:
    """Derive status from email_category or interview fields when status was left as default."""
    category = incoming_data.get("email_category")
    status_val = incoming_data.get("status")

    if category in _EMAIL_CATEGORY_TO_STATUS and status_val in (None, "PENDING", "UNKNOWN"):
        incoming_data["status"] = _EMAIL_CATEGORY_TO_STATUS[category]
    elif (
        (incoming_data.get("interview_date") is not None or incoming_data.get("interview_time") is not None)
        and status_val in (None, "PENDING", "UNKNOWN")
    ):
        incoming_data["status"] = "INTERVIEW"


# CREATE
@router.post(
    "/",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_application(
    application_data: JobApplicationCreate,
    db: Session = Depends(get_db),
):
    payload = application_data.model_dump()
    payload["last_email_at"] = _ensure_utc(payload.get("last_email_at"))
    application = JobApplication(**payload)

    db.add(application)

    try:
        db.flush()
        event_time = application.last_email_at or datetime.now(timezone.utc)
        _record_creation_activities(db, application, source="manual", event_time=event_time)
        db.commit()
        db.refresh(application)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An application with this application_key already exists.",
        )

    return application


# READ ALL
@router.get("/", response_model=list[JobApplicationResponse])
def get_applications(db: Session = Depends(get_db)):
    statement = (
        select(JobApplication)
        .options(selectinload(JobApplication.activities))
        .order_by(JobApplication.created_at.desc())
    )
    applications = db.scalars(statement).all()

    return applications


# READ ONE
@router.get("/{application_id}", response_model=JobApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
):
    statement = (
        select(JobApplication)
        .options(selectinload(JobApplication.activities))
        .where(JobApplication.id == application_id)
    )
    application = db.scalar(statement)

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )

    return application


# READ ACTIVITIES
@router.get(
    "/{application_id}/activities",
    response_model=list[ApplicationActivityResponse],
)
def get_application_activities(
    application_id: int,
    db: Session = Depends(get_db),
):
    application = db.get(JobApplication, application_id)
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )
    return application.activities


# UPDATE
@router.patch(
    "/{application_id}",
    response_model=JobApplicationResponse,
)
def update_application(
    application_id: int,
    application_data: JobApplicationUpdate,
    db: Session = Depends(get_db),
):
    application = db.get(JobApplication, application_id)

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )

    updates = application_data.model_dump(exclude_unset=True)

    # Prevent NULL values for required database columns.
    for field in ("company", "position", "status"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field} cannot be null.",
            )

    if "last_email_at" in updates:
        updates["last_email_at"] = _ensure_utc(updates["last_email_at"])

    old_snapshot = _snapshot(application)

    for field, value in updates.items():
        setattr(application, field, value)

    _record_change_activities(
        db,
        application,
        old_snapshot=old_snapshot,
        source="manual",
        event_time=datetime.now(timezone.utc),
    )

    db.commit()
    db.refresh(application)

    return application


# DELETE
@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
):
    application = db.get(JobApplication, application_id)

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )

    db.delete(application)
    db.commit()

    return None


# SYNC
@router.post(
    "/sync",
    response_model=JobApplicationResponse,
)
def sync_application(
    application_data: JobApplicationCreate,
    db: Session = Depends(get_db),
):
    incoming_data = application_data.model_dump()
    incoming_date = _ensure_utc(incoming_data["last_email_at"])
    incoming_data["last_email_at"] = incoming_date

    # Require an email timestamp for chronological synchronization.
    if incoming_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="last_email_at is required for synchronization.",
        )

    _normalize_sync_status(incoming_data)
    application_key = incoming_data["application_key"]

    # Lock existing row if present to serialize concurrent updates.
    statement = (
        select(JobApplication)
        .where(JobApplication.application_key == application_key)
        .with_for_update()
    )
    application = db.scalar(statement)

    # Create a new application if it does not exist.
    if application is None:
        try:
            with db.begin_nested():
                application = JobApplication(**incoming_data)
                db.add(application)
                db.flush()
                _record_creation_activities(
                    db,
                    application,
                    source="sync",
                    event_time=incoming_date,
                )
            db.commit()
            db.refresh(application)
            return application
        except IntegrityError:
            # Another concurrent request inserted the same application_key first.
            # Fall through and lock the newly created row to apply chronological update rules.
            application = db.scalar(
                select(JobApplication)
                .where(JobApplication.application_key == application_key)
                .with_for_update()
            )
            if application is None:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A concurrent synchronization created this application.",
                )

    # Ignore emails older than the latest processed email.
    current_last_email = _ensure_utc(application.last_email_at)
    if current_last_email is not None and incoming_date < current_last_email:
        return application

    old_snapshot = _snapshot(application)

    # Do not let a generic PENDING/UNKNOWN status overwrite a more specific status
    # when the incoming email has the exact same timestamp or lacks a stronger status.
    incoming_status = incoming_data.get("status")
    if (
        incoming_status in ("PENDING", "UNKNOWN")
        and application.status not in ("PENDING", "UNKNOWN")
        and incoming_data.get("email_category") in (None, "OTHER", "UNKNOWN")
    ):
        incoming_data["status"] = application.status

    # Update only fields containing a value.
    for field, value in incoming_data.items():
        if value is not None and field != "application_key":
            setattr(application, field, value)

    _record_change_activities(
        db,
        application,
        old_snapshot=old_snapshot,
        source="sync",
        event_time=incoming_date,
    )

    db.commit()
    db.refresh(application)

    return application
