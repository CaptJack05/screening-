import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
import sys
import os

# Append src/backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.main import app
from app.database import SessionLocal, Base, engine
from app.models.candidate import Candidate
from app.models.job import Job

class TestCandidateEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        Base.metadata.create_all(bind=engine)
        self.db = SessionLocal()
        
        # Clean up database tables
        self.db.query(Candidate).delete()
        self.db.query(Job).delete()
        self.db.commit()
        
        # Seed a dummy Job
        self.job = Job(id="test-job-uuid", title="AI Engineer", description="Test job description context")
        self.db.add(self.job)
        
        # Seed a dummy Candidate
        self.candidate = Candidate(
            id="test-candidate-uuid",
            job_id="test-job-uuid",
            s_no=1,
            name="John Doe",
            email="johndoe@example.com",
            college="Test College",
            branch="CS",
            cgpa=9.5,
            status="SHORTLISTED"
        )
        self.db.add(self.candidate)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    @patch("app.api.candidates.send_smtp_email")
    def test_send_test_assessment_success(self, mock_send_email):
        mock_send_email.return_value = True
        
        response = self.client.post("/api/candidates/test-candidate-uuid/send-test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        
        # Refresh candidate state from DB
        db_candidate = self.db.query(Candidate).filter(Candidate.id == "test-candidate-uuid").first()
        self.assertEqual(db_candidate.status, "TEST_SENT")
        mock_send_email.assert_called_once()

    @patch("app.api.candidates.create_interview_meet_event")
    @patch("app.api.candidates.send_smtp_email")
    def test_schedule_interview_success(self, mock_send_email, mock_create_event):
        mock_create_event.return_value = ("event-12345", "https://meet.google.com/abc-defg-hij")
        mock_send_email.return_value = True
        
        schedule_data = {
            "scheduled_at": "2026-07-05T10:00:00Z"
        }
        
        response = self.client.post(
            "/api/candidates/test-candidate-uuid/schedule",
            json=schedule_data
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["google_event_id"], "event-12345")
        self.assertEqual(response.json()["meet_link"], "https://meet.google.com/abc-defg-hij")
        
        # Refresh candidate state
        db_candidate = self.db.query(Candidate).filter(Candidate.id == "test-candidate-uuid").first()
        self.assertEqual(db_candidate.status, "INTERVIEW_SCHEDULED")
        mock_create_event.assert_called_once()

if __name__ == "__main__":
    unittest.main()
