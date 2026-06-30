from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.candidate import Candidate
from app.models.evaluation import Evaluation
from app.models.github_analysis import GitHubAnalysis
from app.models.test_result import TestResult
from app.models.interview import Interview

router = APIRouter(prefix="/api/candidates", tags=["Candidates"])

@router.get("")
def list_candidates(
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lists all candidates. Supports optional filtering by job_id and pipeline status.
    """
    query = db.query(Candidate)
    if job_id:
        query = query.filter(Candidate.job_id == job_id)
    if status:
        query = query.filter(Candidate.status == status)
    
    # Sort candidates by composite score (highest first), then by s_no
    candidates = query.order_by(Candidate.composite_score.desc().nullslast(), Candidate.s_no.asc()).all()
    
    result = []
    for c in candidates:
        # Include basic scores for the summary list
        result.append({
            "id": c.id,
            "s_no": c.s_no,
            "name": c.name,
            "email": c.email,
            "college": c.college,
            "branch": c.branch,
            "cgpa": c.cgpa,
            "status": c.status,
            "resume_status": c.resume_status,
            "composite_score": c.composite_score
        })
    return result

@router.get("/{candidate_id}")
def get_candidate_detail(candidate_id: str, db: Session = Depends(get_db)):
    """
    Returns full details for a single candidate, including resume text,
    AI evaluation scores, GitHub repositories analysis, and test results.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    evaluation = db.query(Evaluation).filter(Evaluation.candidate_id == candidate.id).first()
    github = db.query(GitHubAnalysis).filter(GitHubAnalysis.candidate_id == candidate.id).first()
    test = db.query(TestResult).filter(TestResult.candidate_id == candidate.id).first()
    interview = db.query(Interview).filter(Interview.candidate_id == candidate.id).first()

    # Parse JSON strings back to python structures
    import json
    eval_data = None
    if evaluation:
        eval_data = {
            "jd_relevance_score": evaluation.jd_relevance_score,
            "jd_relevance_rationale": evaluation.jd_relevance_rationale,
            "jd_matched_skills": json.loads(evaluation.jd_matched_skills) if evaluation.jd_matched_skills else [],
            "jd_missing_skills": json.loads(evaluation.jd_missing_skills) if evaluation.jd_missing_skills else [],
            "project_quality_score": evaluation.project_quality_score,
            "project_quality_rationale": evaluation.project_quality_rationale,
            "github_technical_score": evaluation.github_technical_score,
            "github_technical_rationale": evaluation.github_technical_rationale,
            "academic_score": evaluation.academic_score,
            "test_performance_score": evaluation.test_performance_score,
            "composite_score": evaluation.composite_score,
            "llm_prompt": evaluation.llm_prompt,
            "llm_response": evaluation.llm_response
        }

    github_data = None
    if github:
        github_data = {
            "github_username": github.github_username,
            "total_repos": github.total_repos,
            "languages": json.loads(github.languages) if github.languages else {},
            "total_stars": github.total_stars,
            "total_forks": github.total_forks,
            "recent_commit_count": github.recent_commit_count,
            "has_readme_ratio": github.has_readme_ratio,
            "has_tests_ratio": github.has_tests_ratio,
            "has_ci_ratio": github.has_ci_ratio,
            "top_repos": json.loads(github.top_repos) if github.top_repos else [],
            "score": github.score
        }

    test_data = None
    if test:
        test_data = {
            "test_la": test.test_la,
            "test_code": test.test_code,
            "combined_score": test.combined_score
        }

    interview_data = None
    if interview:
        interview_data = {
            "scheduled_at": interview.scheduled_at,
            "meet_link": interview.meet_link,
            "status": interview.status
        }

    return {
        "id": candidate.id,
        "s_no": candidate.s_no,
        "name": candidate.name,
        "email": candidate.email,
        "college": candidate.college,
        "branch": candidate.branch,
        "cgpa": candidate.cgpa,
        "best_ai_project": candidate.best_ai_project,
        "research_work": candidate.research_work,
        "github_url": candidate.github_url,
        "resume_drive_link": candidate.resume_drive_link,
        "resume_text": candidate.resume_text,
        "resume_status": candidate.resume_status,
        "status": candidate.status,
        "composite_score": candidate.composite_score,
        "evaluation": eval_data,
        "github_analysis": github_data,
        "test_result": test_data,
        "interview": interview_data
    }

@router.post("/{candidate_id}/shortlist")
def toggle_shortlist(candidate_id: str, db: Session = Depends(get_db)):
    """
    Toggles the shortlist state of a candidate between AI_SCORED/TEST_SCORED and SHORTLISTED.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    if candidate.status == "SHORTLISTED":
        # Revert back to test scored or AI scored based on whether they have test scores
        test = db.query(TestResult).filter(TestResult.candidate_id == candidate.id).first()
        candidate.status = "TEST_SCORED" if test else "AI_SCORED"
    else:
        candidate.status = "SHORTLISTED"

    db.commit()
    return {"id": candidate.id, "status": candidate.status}

@router.delete("/{candidate_id}")
def delete_candidate(candidate_id: str, db: Session = Depends(get_db)):
    """
    Deletes a candidate record from the database.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    db.delete(candidate)
    db.commit()
    return {"message": "Candidate record successfully deleted."}

from pydantic import BaseModel
from app.services.emailer import send_smtp_email, render_test_link_email, render_interview_invite_email
from app.services.calendar import create_interview_meet_event
from app.models.job import Job

class InterviewSchedule(BaseModel):
    scheduled_at: str  # ISO timestamp

@router.post("/{candidate_id}/send-test")
def send_test_assessment(candidate_id: str, db: Session = Depends(get_db)):
    """
    Generates assessment links, emails them using SMTP configurations,
    and updates candidate status to TEST_SENT.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    test_url = f"http://localhost:8000/test/{candidate.id}"
    body_html = render_test_link_email(candidate.name, test_url)
    
    subject = "Visl AI Labs: Logical Aptitude & Technical Coding Assessment"
    success = send_smtp_email(
        candidate_id=candidate.id,
        recipient_email=candidate.email,
        subject=subject,
        body_html=body_html,
        email_type="TEST_LINK"
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to send assessment email. Please verify SMTP server settings."
        )
        
    candidate.status = "TEST_SENT"
    db.commit()
    
    return {"status": "success", "message": f"Assessment email successfully sent to {candidate.email}."}

@router.post("/{candidate_id}/schedule")
def schedule_interview(candidate_id: str, schedule_in: InterviewSchedule, db: Session = Depends(get_db)):
    """
    Creates Google Calendar interview event, generates Google Meet link,
    emails candidate confirmation, and updates candidate status to INTERVIEW_SCHEDULED.
    """
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
        
    job = db.query(Job).filter(Job.id == candidate.job_id).first()
    job_title = job.title if job else "Founding AI Engineer"
    
    try:
        event_id, meet_link = create_interview_meet_event(
            candidate_name=candidate.name,
            candidate_email=candidate.email,
            job_title=job_title,
            start_time_iso=schedule_in.scheduled_at
        )
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Calendar integration error: {str(e)}")
        
    # Format date/time string for email readability
    try:
        from datetime import datetime
        clean_time = schedule_in.scheduled_at.replace("Z", "+00:00")
        dt_obj = datetime.fromisoformat(clean_time)
        formatted_datetime = dt_obj.strftime("%B %d, %Y at %I:%M %p (UTC)")
    except Exception:
        formatted_datetime = schedule_in.scheduled_at
        
    body_html = render_interview_invite_email(candidate.name, formatted_datetime, meet_link)
    
    email_success = send_smtp_email(
        candidate_id=candidate.id,
        recipient_email=candidate.email,
        subject=f"Technical Interview Confirmation: {job_title} at Visl AI Labs",
        body_html=body_html,
        email_type="INTERVIEW_INVITE"
    )
    
    # Update SQLite Database
    import uuid
    from datetime import datetime as dt
    try:
        clean_time = schedule_in.scheduled_at.replace("Z", "+00:00")
        scheduled_dt = dt.fromisoformat(clean_time)
    except Exception:
        scheduled_dt = dt.utcnow()
        
    # Delete older schedules for idempotency
    db.query(Interview).filter(Interview.candidate_id == candidate.id).delete()
    
    interview = Interview(
        id=str(uuid.uuid4()),
        candidate_id=candidate.id,
        job_id=candidate.job_id,
        scheduled_at=scheduled_dt,
        google_event_id=event_id,
        meet_link=meet_link,
        status="SCHEDULED"
    )
    db.add(interview)
    
    candidate.status = "INTERVIEW_SCHEDULED"
    db.commit()
    
    return {
        "status": "success",
        "google_event_id": event_id,
        "meet_link": meet_link,
        "email_sent": email_success,
        "message": f"Interview scheduled successfully. Meet Link: {meet_link}"
    }
