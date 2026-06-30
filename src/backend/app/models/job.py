import uuid
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.orm import relationship
from app.database import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    candidates = relationship("Candidate", back_populates="job", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="job", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="job", cascade="all, delete-orphan")
