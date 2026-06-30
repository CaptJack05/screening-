import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=True)
    s_no = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    college = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    cgpa = Column(Float, nullable=True)
    best_ai_project = Column(String, nullable=True)
    research_work = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    resume_drive_link = Column(String, nullable=True)
    resume_text = Column(String, nullable=True)
    resume_status = Column(String, default="PENDING")  # PENDING, DOWNLOADED, EXTRACTED, UNAVAILABLE
    status = Column(String, default="UPLOADED")  # UPLOADED, RESUME_PROCESSED, GITHUB_ANALYZED, AI_SCORED, SHORTLISTED, TEST_SENT, TEST_SCORED, INTERVIEW_SCHEDULED
    composite_score = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    job = relationship("Job", back_populates="candidates")
    evaluations = relationship("Evaluation", back_populates="candidate", cascade="all, delete-orphan")
    github_analyses = relationship("GitHubAnalysis", back_populates="candidate", cascade="all, delete-orphan")
    test_results = relationship("TestResult", back_populates="candidate", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")
    email_logs = relationship("EmailLog", back_populates="candidate", cascade="all, delete-orphan")
