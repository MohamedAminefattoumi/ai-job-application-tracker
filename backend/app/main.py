from fastapi import FastAPI
from app.api.job_applications import router as applications_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="AI Job Application Tracker",
    description="API for managing job applications",
    version="1.0.0"
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
