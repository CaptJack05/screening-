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
    
    # Seed default GTM Intern Job Description if database is empty
    from app.database import SessionLocal
    from app.models.job import Job
    db = SessionLocal()
    try:
        exists = db.query(Job).first()
        if not exists:
            default_jd = Job(
                id="default-gtm-intern-uuid",
                title="GTM (Go-to-Market) Engineering Intern",
                description=(
                    "Internship opportunity for a GTM (Go-to-Market) Engineering Intern role with our team at myNachiketa.\n\n"
                    "myNachiketa is India’s only D2C brand that develops products to bring the knowledge of Gita & Vedas to children. "
                    "We design innovative products in the form of videos, books, games, workshops, etc. and market them through Youtube, Instagram, and Amazon.\n\n"
                    "This internship is ideal for individuals interested in working at the intersection of technology, AI, automation, growth, and business operations. "
                    "It offers hands-on experience in solving real-world challenges and contributing to impactful projects in a fast-paced environment."
                )
            )
            db.add(default_jd)
            db.commit()
            print("Default Job Description for GTM Engineering Intern seeded successfully.")
    except Exception as e:
        print(f"Error seeding default JD: {e}")
    finally:
        db.close()
        
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
