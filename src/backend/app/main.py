import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.database import engine, Base
from app.models import *  # Ensure all models are registered
from app.api.upload import router as upload_router
from app.api.candidates import router as candidates_router
from app.api.jobs import router as jobs_router
from app.api.pipeline import router as pipeline_router
from app.api.settings import router as settings_router
from app.api.calendar import router as calendar_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-create tables for SQLite development environment
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(
    title="AI-Powered Candidate Screening API",
    description="Backend service for automated recruiter screening workflows",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(upload_router)
app.include_router(calendar_router)
app.include_router(candidates_router)
app.include_router(jobs_router)
app.include_router(pipeline_router)
app.include_router(settings_router)

@app.get("/api/health")
def healthcheck():
    return {
        "status": "online",
        "database": "connected",
        "message": "AI-Powered Candidate Screening Platform API is running."
    }

# Serve frontend static files
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    @app.get("/")
    def read_root():
        return {
            "status": "online",
            "message": f"API is online, but static frontend folder not found at {frontend_path}."
        }
