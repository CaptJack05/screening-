import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.database import Base

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id = Column(String, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False)
    email_type = Column(String, nullable=False)  # TEST_LINK, INTERVIEW_INVITE
    recipient_email = Column(String, nullable=False)
    subject = Column(String, nullable=True)
    body_preview = Column(String, nullable=True)
    status = Column(String, default="SENT")  # SENT, FAILED
    sent_at = Column(DateTime, server_default=func.now())

    candidate = relationship("Candidate", back_populates="email_logs")
