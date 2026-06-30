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
