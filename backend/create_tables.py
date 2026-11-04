from app.database import Base, engine
from app.models.application_activity import ApplicationActivity  # noqa: F401
from app.models.job_application import JobApplication  # noqa: F401

Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")
