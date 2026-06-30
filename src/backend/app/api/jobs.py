from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.database import get_db
from app.models.job import Job

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

class JobCreate(BaseModel):
    title: str
    description: str

@router.post("")
def create_job(job_in: JobCreate, db: Session = Depends(get_db)):
    """
    Submits a new Job Description (JD).
    """
    job = Job(
        title=job_in.title,
        description=job_in.description
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job

@router.get("")
def list_jobs(db: Session = Depends(get_db)):
    """
    Lists all submitted job descriptions.
    """
    return db.query(Job).order_by(Job.created_at.desc()).all()

@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    """
    Retrieves a single Job Description.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found.")
    return job
