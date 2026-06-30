import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    
    jd_relevance_score = Column(Float, nullable=True)
    jd_relevance_rationale = Column(String, nullable=True)
    jd_matched_skills = Column(String, nullable=True)  # Store as serialized JSON
    jd_missing_skills = Column(String, nullable=True)  # Store as serialized JSON
    
    project_quality_score = Column(Float, nullable=True)
    project_quality_rationale = Column(String, nullable=True)
    
    github_technical_score = Column(Float, nullable=True)
    github_technical_rationale = Column(String, nullable=True)
    
    academic_score = Column(Float, nullable=True)
    test_performance_score = Column(Float, nullable=True)
    composite_score = Column(Float, nullable=True)
    
    llm_prompt = Column(String, nullable=True)
    llm_response = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    candidate = relationship("Candidate", back_populates="evaluations")
    job = relationship("Job", back_populates="evaluations")
