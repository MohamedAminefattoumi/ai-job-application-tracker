
from app.database import Base, engine
from app.models.job_application import JobApplication

Base.metadata.create_all(bind=engine)

print("Database tables created successfully!")
