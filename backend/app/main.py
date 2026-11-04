from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.job_applications import router as applications_router
from app.database import Base, engine
from app.models import ApplicationActivity, JobApplication  # noqa: F401


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Ensure tables (such as application_activities) exist on startup without modifying existing data
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="AI Job Application Tracker",
    description="API for managing job applications",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(applications_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to AI Job Application Tracker API"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }
