from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.database import get_db, SessionLocal
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.evaluation import Evaluation
from app.models.github_analysis import GitHubAnalysis
from app.models.test_result import TestResult

from app.services.resume import process_resume
from app.services.github import analyze_github_profile
from app.services.evaluator import evaluate_candidate_with_llm
from app.services.scorer import calculate_composite_score

import json
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])

def run_async_candidate_pipeline(candidate_id: str, job_id: str):
    """
    Background worker function that processes a single candidate through:
    Resume Extraction -> GitHub Analyzer -> LLM Evaluator -> Score Calculation.
    """
    # Create isolated DB session for background task safety
    db: Session = SessionLocal()
    try:
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        job = db.query(Job).filter(Job.id == job_id).first()
        if not candidate or not job:
            return

        # 1. Resume Downloader & Extractor
        if candidate.resume_drive_link and candidate.resume_status == "PENDING":
            status, text = process_resume(candidate.resume_drive_link)
            candidate.resume_status = status
            candidate.resume_text = text
            candidate.status = "RESUME_PROCESSED"
            db.commit()

        # 2. GitHub Analyzer
        github_score_val = 0.0
        if candidate.github_url:
            status, details = analyze_github_profile(candidate.github_url, job.description)
            if status == "EXTRACTED":
                # Clear existing
                db.query(GitHubAnalysis).filter(GitHubAnalysis.candidate_id == candidate.id).delete()
                
                analysis = GitHubAnalysis(
                    candidate_id=candidate.id,
                    github_username=details.get("github_username"),
                    total_repos=details.get("total_repos", 0),
                    languages=json.dumps(details.get("languages", {})),
                    total_stars=details.get("total_stars", 0),
                    total_forks=details.get("total_forks", 0),
                    recent_commit_count=details.get("recent_commit_count", 0),
                    has_readme_ratio=details.get("has_readme_ratio", 0.0),
                    has_tests_ratio=details.get("has_tests_ratio", 0.0),
                    has_ci_ratio=details.get("has_ci_ratio", 0.0),
                    top_repos=json.dumps(details.get("top_repos", [])),
                    raw_api_response=json.dumps(details),
                    score=details.get("score", 0.0)
                )
                db.add(analysis)
                github_score_val = details.get("score", 0.0)
                candidate.status = "GITHUB_ANALYZED"
                db.commit()

        # 3. LLM Evaluator (Groq / Fallback)
        jd_score_val = 0.0
        proj_score_val = 0.0
        
        # We run evaluation even if resume extraction failed, using their best_ai_project details
        eval_dict, prompt_str, response_str = evaluate_candidate_with_llm(
            candidate.resume_text or "Not Extracted",
            candidate.best_ai_project or "Not Provided",
            candidate.research_work or "Not Provided",
            job.description
        )

        db.query(Evaluation).filter(
            Evaluation.candidate_id == candidate.id,
            Evaluation.job_id == job.id
        ).delete()

        # Calculate academic score component
        from app.services.scorer import normalize_academic_score
        academic_score_val = normalize_academic_score(candidate.cgpa)

        # Retrieve test result if already uploaded
        test_res = db.query(TestResult).filter(TestResult.candidate_id == candidate.id).first()
        test_score_val = test_res.combined_score if test_res else 0.0

        jd_score_val = eval_dict.get("jd_relevance_score", 0.0)
        proj_score_val = eval_dict.get("project_quality_score", 0.0)

        # 4. Score Calculation
        composite_score_val = calculate_composite_score(
            jd_score_val,
            proj_score_val,
            github_score_val,
            candidate.cgpa,
            test_res.test_la if test_res else 0.0,
            test_res.test_code if test_res else 0.0
        )

        evaluation = Evaluation(
            candidate_id=candidate.id,
            job_id=job.id,
            jd_relevance_score=jd_score_val,
            jd_relevance_rationale=eval_dict.get("jd_relevance_rationale"),
            jd_matched_skills=json.dumps(eval_dict.get("jd_matched_skills", [])),
            jd_missing_skills=json.dumps(eval_dict.get("jd_missing_skills", [])),
            project_quality_score=proj_score_val,
            project_quality_rationale=eval_dict.get("project_quality_rationale"),
            github_technical_score=github_score_val,
            github_technical_rationale=details.get("reason") if candidate.github_url else "No GitHub link provided.",
            academic_score=academic_score_val,
            test_performance_score=test_score_val,
            composite_score=composite_score_val,
            llm_prompt=prompt_str,
            llm_response=response_str
        )
        db.add(evaluation)
        
        # Keep candidate status as SHORTLISTED or TEST_SCORED if they were set, otherwise transition to AI_SCORED
        if candidate.status not in ["SHORTLISTED", "TEST_SCORED", "INTERVIEW_SCHEDULED"]:
            candidate.status = "AI_SCORED"
            
        candidate.composite_score = composite_score_val
        db.commit()

    except Exception as e:
        logger.error(f"Error in candidate background pipeline execution: {str(e)}")
    finally:
        db.close()

def run_pipeline_batch(job_id: str):
    """
    Process all candidates registered under a job in batch.
    """
    db = SessionLocal()
    try:
        candidates = db.query(Candidate).filter(Candidate.job_id == job_id).all()
        for candidate in candidates:
            try:
                run_async_candidate_pipeline(candidate.id, job_id)
            except Exception as e:
                logger.error(f"Failed pipeline run for candidate {candidate.id}: {str(e)}")
    finally:
        db.close()

@router.post("/run")
async def run_pipeline(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Triggers the async background processing pipeline for all candidates under a job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description context not found.")

    candidates_count = db.query(Candidate).filter(Candidate.job_id == job_id).count()
    if candidates_count == 0:
        raise HTTPException(status_code=400, detail="No candidates uploaded under this job context.")

    # Queue execution
    background_tasks.add_task(run_pipeline_batch, job_id)
    
    return {
        "message": f"Async candidate screening pipeline triggered in background for {candidates_count} candidates.",
        "job_id": job_id,
        "count": candidates_count
    }
