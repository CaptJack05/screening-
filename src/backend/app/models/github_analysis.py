import uuid
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class GitHubAnalysis(Base):
    __tablename__ = "github_analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    github_username = Column(String, nullable=True)
    total_repos = Column(Integer, default=0)
    languages = Column(String, nullable=True)  # Store JSON as string: {lang: bytes}
    total_stars = Column(Integer, default=0)
    total_forks = Column(Integer, default=0)
    recent_commit_count = Column(Integer, default=0)
    has_readme_ratio = Column(Float, default=0.0)
    has_tests_ratio = Column(Float, default=0.0)
    has_ci_ratio = Column(Float, default=0.0)
    top_repos = Column(String, nullable=True)  # Store JSON as string: list of repo info
    raw_api_response = Column(String, nullable=True)  # Cached full response
    score = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    candidate = relationship("Candidate", back_populates="github_analyses")
