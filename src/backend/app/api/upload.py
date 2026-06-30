import uuid
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.parser import parse_upload_file
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.test_result import TestResult

router = APIRouter(prefix="/api/upload", tags=["Upload"])

@router.post("/candidates")
async def upload_candidates(
    file: UploadFile = File(...),
    job_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Ingests the candidate dataset. Creates a default Job context if job_id is not provided.
    """
    content = await file.read()
    try:
        detected_type, records = parse_upload_file(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if detected_type != "candidate_response":
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file looks like '{detected_type}' but candidate dataset was expected."
        )

    # Ensure a Job context exists
    if not job_id:
        # Create a default job if none exists or is provided
        default_job = db.query(Job).filter(Job.title == "Founding AI Engineer").first()
        if not default_job:
            default_job = Job(
                title="Founding AI Engineer",
                description="Default Founding AI Engineer role to evaluate candidates against."
            )
            db.add(default_job)
            db.commit()
            db.refresh(default_job)
        job_id = default_job.id
    else:
        # Verify job exists
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Specified Job ID not found.")

    candidates_added = 0
    for record in records:
        # Since duplicate emails can exist, we generate a fresh UUID for every candidate row on ingestion.
        # This aligns with the requirements.
        candidate = Candidate(
            id=str(uuid.uuid4()),
            job_id=job_id,
            s_no=record.get("s_no"),
            name=record.get("name"),
            email=record.get("email"),
            college=record.get("college"),
            branch=record.get("branch"),
            cgpa=record.get("cgpa"),
            best_ai_project=record.get("best_ai_project"),
            research_work=record.get("research_work"),
            github_url=record.get("github"),
            resume_drive_link=record.get("resume"),
            status="UPLOADED",
            resume_status="PENDING"
        )
        db.add(candidate)
        candidates_added += 1

    db.commit()
    return {
        "message": f"Successfully imported {candidates_added} candidates.",
        "job_id": job_id,
        "count": candidates_added
    }

@router.post("/test-results")
async def upload_test_results(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Ingests test results CSV/XLSX and merges them with existing candidates by email,
    using s_no and name fallback validations for duplicate email rows.
    """
    content = await file.read()
    try:
        detected_type, records = parse_upload_file(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if detected_type != "test_result":
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file looks like '{detected_type}' but test results dataset was expected."
        )

    matched_count = 0
    unmatched_count = 0

    for record in records:
        email = record.get("email")
        s_no = record.get("s_no")
        name = record.get("name")
        test_la = record.get("test_la", 0.0)
        test_code = record.get("test_code", 0.0)
        combined_score = 0.4 * test_la + 0.6 * test_code

        # Attempt to match by:
        # 1. Email AND s_no (Strongest alignment for sheet exports)
        candidate = db.query(Candidate).filter(
            Candidate.email == email,
            Candidate.s_no == s_no
        ).first()

        # 2. Fallback: Email AND name
        if not candidate and name:
            candidate = db.query(Candidate).filter(
                Candidate.email == email,
                Candidate.name.ilike(name)
            ).first()

        # 3. Fallback: Email only
        if not candidate:
            candidate = db.query(Candidate).filter(
                Candidate.email == email
            ).first()

        if candidate:
            # Delete old test result for idempotency
            db.query(TestResult).filter(TestResult.candidate_id == candidate.id).delete()

            # Create new test result
            test_res = TestResult(
                id=str(uuid.uuid4()),
                candidate_id=candidate.id,
                test_la=test_la,
                test_code=test_code,
                combined_score=combined_score
            )
            db.add(test_res)

            # Update candidate pipeline state and scores
            candidate.status = "TEST_SCORED"
            # Recompute composite score if the candidate was already AI scored
            # Composite Score: 30% JD, 20% Project, 20% GitHub, 10% Academic, 20% Test Performance
            if candidate.composite_score is not None:
                # Get the existing evaluation record to obtain other scores
                from app.models.evaluation import Evaluation
                eval_record = db.query(Evaluation).filter(Evaluation.candidate_id == candidate.id).first()
                if eval_record:
                    eval_record.test_performance_score = combined_score
                    # Composite score recalculation
                    new_composite = (
                        0.30 * (eval_record.jd_relevance_score or 0) +
                        0.20 * (eval_record.project_quality_score or 0) +
                        0.20 * (eval_record.github_technical_score or 0) +
                        0.10 * (eval_record.academic_score or 0) +
                        0.20 * combined_score
                    )
                    eval_record.composite_score = new_composite
                    candidate.composite_score = new_composite

            matched_count += 1
        else:
            unmatched_count += 1

    db.commit()
    return {
        "message": f"Test results processing complete. Matched: {matched_count}, Unmatched: {unmatched_count}.",
        "matched": matched_count,
        "unmatched": unmatched_count
    }
