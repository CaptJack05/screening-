# Architecture & Schema Change Log

This document lists a chronological audit trail of all schema modifications, architectural adjustments, and library updates.

## [2026-06-30] Initial Workspace & Multi-Agent Framework Setup
*   **Author**: Lead Architect
*   **Description**: Setup the workspace document structure under `docs/` and root level `HANDOFF.md`.
*   **Approved Plan**: Sprint v1.0
*   **Details**:
    *   Setup agent governance rules and context directories.
    *   Set strict scopes for Backend and Frontend agents to prevent codebase corruption.

## [2026-06-30] Codebase Upload to GitHub
*   **Author**: Lead Architect / AI Assistant
*   **Description**: Uploaded the entire project codebase to a remote GitHub repository.
*   **Details**:
    *   Created root-level `.gitignore` file to ignore environment configurations, local database files, and caches.
    *   Uploaded all 40 core project files to the `CaptJack05/screening-` repository.

## [2026-06-30] Google Calendar & SMTP Email Scheduling Integration
*   **Author**: Lead Architect / AI Assistant
*   **Description**: Implemented recruiter calendar authorization and automated candidate assessment link emailing.
*   **Details**:
    *   Created `app/services/calendar.py` and `app/api/calendar.py` to handle Google Calendar OAuth2 consent, decryption of database credentials, and dynamic Meet link generation.
    *   Added candidate mail and schedule endpoints (`/send-test`, `/schedule`) in `app/api/candidates.py`.
    *   Updated `src/frontend/index.html` React app with settings forms, drawer mail controls, and interview booking widgets.
    *   Created unit tests suite `app/tests/test_endpoints.py` to mock calendar Meet links and verify status code flows.
