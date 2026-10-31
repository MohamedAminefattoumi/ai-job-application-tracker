
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.job_application import JobApplication
from app.schemas.job_application import (
    JobApplicationCreate,
    JobApplicationUpdate,
    JobApplicationResponse,
)

router = APIRouter(
    prefix="/applications",
    tags=["Job Applications"],
)


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
    application = JobApplication(**application_data.model_dump())

    db.add(application)

    try:
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
    statement = select(JobApplication).order_by(
        JobApplication.created_at.desc()
    )
    applications = db.scalars(statement).all()

    return applications


# READ ONE
@router.get("/{application_id}", response_model=JobApplicationResponse)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
):
    application = db.get(JobApplication, application_id)

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )

    return application


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
    for field in ("company", "position"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field} cannot be null.",
            )

    for field, value in updates.items():
        setattr(application, field, value)

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
    incoming_date = incoming_data["last_email_at"]

    # Require an email timestamp for chronological synchronization.
    if incoming_date is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="last_email_at is required for synchronization.",
        )

    # Find an existing application using its unique key.
    statement = select(JobApplication).where(
        JobApplication.application_key == incoming_data["application_key"]
    )
    application = db.scalar(statement)

    # Create a new application if it does not exist.
    if application is None:
        application = JobApplication(**incoming_data)
        db.add(application)

        try:
            db.commit()
            db.refresh(application)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A concurrent synchronization created this application.",
            )

        return application

    # Ignore emails older than the latest processed email.
    if (
        application.last_email_at is not None
        and incoming_date < application.last_email_at
    ):
        return application

    # Update only fields containing a value.
    for field, value in incoming_data.items():
        if value is not None and field != "application_key":
            setattr(application, field, value)

    db.commit()
    db.refresh(application)

    return application


