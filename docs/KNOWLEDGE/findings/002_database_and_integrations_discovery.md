# Finding 002: Database Schemas & Missing Integrations Discovery

**Date**: 2026-06-30
**Author**: Lead Architect / AI Assistant

## 1. Current Database Models

We inspected the SQLAlchemy models in `src/backend/app/models/` and identified the active database tables. Below is the mapping:

### Jobs (`jobs`)
- `id` (VARCHAR, PK, UUID)
- `title` (VARCHAR, NOT NULL)
- `description` (VARCHAR, NOT NULL)
- `created_at` (DATETIME, default now)

### Candidates (`candidates`)
- `id` (VARCHAR, PK, UUID)
- `job_id` (VARCHAR, FK jobs.id, ON DELETE CASCADE)
- `s_no` (INTEGER, NOT NULL)
- `name` (VARCHAR, NOT NULL)
- `email` (VARCHAR, NOT NULL)
- `college` (VARCHAR)
- `branch` (VARCHAR)
- `cgpa` (FLOAT)
- `best_ai_project` (VARCHAR)
- `research_work` (VARCHAR)
- `github_url` (VARCHAR)
- `resume_drive_link` (VARCHAR)
- `resume_text` (VARCHAR)
- `resume_status` (VARCHAR, default "PENDING")
- `status` (VARCHAR, default "UPLOADED")
- `composite_score` (FLOAT)
- `created_at` (DATETIME, default now)
- `updated_at` (DATETIME, default now, onupdate now)

### Evaluations (`evaluations`)
- `id` (VARCHAR, PK, UUID)
- `candidate_id` (VARCHAR, FK candidates.id, ON DELETE CASCADE)
- `job_id` (VARCHAR, FK jobs.id, ON DELETE CASCADE)
- `jd_relevance_score` (FLOAT)
- `jd_relevance_rationale` (VARCHAR)
- `jd_matched_skills` (VARCHAR, JSON string)
- `jd_missing_skills` (VARCHAR, JSON string)
- `project_quality_score` (FLOAT)
- `project_quality_rationale` (VARCHAR)
- `github_technical_score` (FLOAT)
- `github_technical_rationale` (VARCHAR)
- `academic_score` (FLOAT)
- `test_performance_score` (FLOAT)
- `composite_score` (FLOAT)
- `llm_prompt` (VARCHAR)
- `llm_response` (VARCHAR)
- `created_at` (DATETIME, default now)

### GitHub Analyses (`github_analyses`)
- `id` (VARCHAR, PK, UUID)
- `candidate_id` (VARCHAR, FK candidates.id, ON DELETE CASCADE)
- `github_username` (VARCHAR)
- `total_repos` (INTEGER, default 0)
- `languages` (VARCHAR, JSON string)
- `total_stars` (INTEGER, default 0)
- `total_forks` (INTEGER, default 0)
- `recent_commit_count` (INTEGER, default 0)
- `has_readme_ratio` (FLOAT, default 0.0)
- `has_tests_ratio` (FLOAT, default 0.0)
- `has_ci_ratio` (FLOAT, default 0.0)
- `top_repos` (VARCHAR, JSON string)
- `raw_api_response` (VARCHAR, JSON string)
- `score` (FLOAT, default 0.0)
- `created_at` (DATETIME, default now)

### Test Results (`test_results`)
- `id` (VARCHAR, PK, UUID)
- `candidate_id` (VARCHAR, FK candidates.id, ON DELETE CASCADE)
- `test_la` (FLOAT, default 0.0)
- `test_code` (FLOAT, default 0.0)
- `combined_score` (FLOAT, default 0.0)
- `uploaded_at` (DATETIME, default now)

### Interviews (`interviews`)
- `id` (VARCHAR, PK, UUID)
- `candidate_id` (VARCHAR, FK candidates.id, ON DELETE CASCADE)
- `job_id` (VARCHAR, FK jobs.id, ON DELETE CASCADE)
- `scheduled_at` (DATETIME, NOT NULL)
- `google_event_id` (VARCHAR)
- `meet_link` (VARCHAR)
- `status` (VARCHAR, default "SCHEDULED")
- `created_at` (DATETIME, default now)

### Email Logs (`email_logs`)
- `id` (VARCHAR, PK, UUID)
- `candidate_id` (VARCHAR, FK candidates.id, ON DELETE CASCADE)
- `email_type` (VARCHAR, NOT NULL)
- `recipient_email` (VARCHAR, NOT NULL)
- `subject` (VARCHAR)
- `body_preview` (VARCHAR)
- `status` (VARCHAR, default "SENT")
- `sent_at` (DATETIME, default now)

### System Settings (`system_settings`)
- `key` (VARCHAR, PK)
- `value` (VARCHAR, NOT NULL)

---

## 2. Missing Core Backend Integrations & Routes

To complete the candidate screening lifecycle, the following backend integrations must be implemented:

### A. Google Calendar Integration
- Recruiter OAuth link consent endpoint: `/api/calendar/auth`
- OAuth callback exchange and state store endpoint: `/api/calendar/callback`
- Calendar linking state status endpoint: `/api/calendar/status`
- Auto-schedule Google Meet event and update status endpoint: `/api/candidates/{candidate_id}/schedule`

### B. Email Link Actions
- Trigger test invitation link endpoint: `/api/candidates/{candidate_id}/send-test`
- Trigger candidate pipeline execution (trigger manually via frontend) endpoint: `/api/pipeline/run` (already exists, but needs exposure in UI)

---

## 3. Frontend Gaps
- **Recruitment Pipeline Tab**: Add a "Run Pipeline" button in the pipeline board header to trigger async candidate evaluations.
- **Candidate Detail Drawer**: 
  - Add "Send Test Assessment Link" button when status is `AI_SCORED` or `SHORTLISTED`.
  - Add "Schedule Interview" modal/input (picking datetime) when status is `TEST_SCORED` or `SHORTLISTED`.
- **Settings Tab**: Connect "Google Calendar OAuth2" authorization to the actual `/api/calendar/auth` callback redirect flow.
