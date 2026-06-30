import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class TestResult(Base):
    __tablename__ = "test_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    test_la = Column(Float, default=0.0)
    test_code = Column(Float, default=0.0)
    combined_score = Column(Float, default=0.0)
    uploaded_at = Column(DateTime, server_default=func.now())

    candidate = relationship("Candidate", back_populates="test_results")
