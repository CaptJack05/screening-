# System Architecture

This document tracks database DDL schemas, core system constraints, and the approved libraries/dependencies list.

## 1. Database DDL Schemas

Below are the active database table schemas used in the platform (SQLite dialect):

```sql
-- Jobs Description Context
CREATE TABLE jobs (
  id VARCHAR PRIMARY KEY,
  title VARCHAR NOT NULL,
  description VARCHAR NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Candidates Ingested Info
CREATE TABLE candidates (
  id VARCHAR PRIMARY KEY,
  job_id VARCHAR REFERENCES jobs(id) ON DELETE CASCADE,
  s_no INTEGER NOT NULL,
  name VARCHAR NOT NULL,
  email VARCHAR NOT NULL,
  college VARCHAR,
  branch VARCHAR,
  cgpa FLOAT,
  best_ai_project VARCHAR,
  research_work VARCHAR,
  github_url VARCHAR,
  resume_drive_link VARCHAR,
  resume_text VARCHAR,
  resume_status VARCHAR DEFAULT 'PENDING',
  status VARCHAR DEFAULT 'UPLOADED',
  composite_score FLOAT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AI Evaluations and Composite Scores
CREATE TABLE evaluations (
  id VARCHAR PRIMARY KEY,
  candidate_id VARCHAR REFERENCES candidates(id) ON DELETE CASCADE,
  job_id VARCHAR REFERENCES jobs(id) ON DELETE CASCADE,
  jd_relevance_score FLOAT,
  jd_relevance_rationale VARCHAR,
  jd_matched_skills VARCHAR, -- Serialized JSON
  jd_missing_skills VARCHAR, -- Serialized JSON
  project_quality_score FLOAT,
  project_quality_rationale VARCHAR,
  github_technical_score FLOAT,
  github_technical_rationale VARCHAR,
  academic_score FLOAT,
  test_performance_score FLOAT,
  composite_score FLOAT,
  llm_prompt VARCHAR,
  llm_response VARCHAR,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- GitHub Profile Deep Analyses
CREATE TABLE github_analyses (
  id VARCHAR PRIMARY KEY,
  candidate_id VARCHAR REFERENCES candidates(id) ON DELETE CASCADE,
  github_username VARCHAR,
  total_repos INTEGER DEFAULT 0,
  languages VARCHAR, -- Serialized JSON
  total_stars INTEGER DEFAULT 0,
  total_forks INTEGER DEFAULT 0,
  recent_commit_count INTEGER DEFAULT 0,
  has_readme_ratio FLOAT DEFAULT 0.0,
  has_tests_ratio FLOAT DEFAULT 0.0,
  has_ci_ratio FLOAT DEFAULT 0.0,
  top_repos VARCHAR, -- Serialized JSON
  raw_api_response VARCHAR, -- Serialized JSON
  score FLOAT DEFAULT 0.0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Assessment Test Results
CREATE TABLE test_results (
  id VARCHAR PRIMARY KEY,
  candidate_id VARCHAR REFERENCES candidates(id) ON DELETE CASCADE,
  test_la FLOAT DEFAULT 0.0,
  test_code FLOAT DEFAULT 0.0,
  combined_score FLOAT DEFAULT 0.0,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Scheduled Interviews and Meet Links
CREATE TABLE interviews (
  id VARCHAR PRIMARY KEY,
  candidate_id VARCHAR REFERENCES candidates(id) ON DELETE CASCADE,
  job_id VARCHAR REFERENCES jobs(id) ON DELETE CASCADE,
  scheduled_at TIMESTAMP NOT NULL,
  google_event_id VARCHAR,
  meet_link VARCHAR,
  status VARCHAR DEFAULT 'SCHEDULED',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Recruiter Email Outbox Audits
CREATE TABLE email_logs (
  id VARCHAR PRIMARY KEY,
  candidate_id VARCHAR REFERENCES candidates(id) ON DELETE CASCADE,
  email_type VARCHAR NOT NULL,
  recipient_email VARCHAR NOT NULL,
  subject VARCHAR,
  body_preview VARCHAR,
  status VARCHAR DEFAULT 'SENT',
  sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Encrypted SMTP and Google Credentials
CREATE TABLE system_settings (
  key VARCHAR PRIMARY KEY,
  value VARCHAR NOT NULL
);
```

## 2. Core System Constraints
*   **Security & Encryption**: Password hashing using bcrypt or argon2. Sensitive configurations must be loaded via environment variables (`.env`).
*   **Data Integrity**: Cascade delete rules must be explicitly defined. All tables must have audit timestamps (`created_at`, `updated_at`).
*   **Performance Constraints**:
    *   No single query should run longer than 200ms.
    *   Appropriate database indices must be defined for foreign keys and frequent lookup columns.

## 3. Approved Libraries and Tech Stack
*To be populated once the technology stack is selected by the user. Below are typical options:*

### Backend
*   **Runtime**: Node.js or Python
*   **Framework**: Express (Node.js) or FastAPI (Python)
*   **Database Client / ORM**: Prisma (TypeScript) or SQLAlchemy (Python)

### Frontend
*   **Runtime/Build Tool**: Vite or Next.js
*   **UI Library**: React / HTML5 / Vanilla CSS
*   **State Management**: React Context or Zustand
