# Finding 001: Dataset & Assignment Validation

**Date**: 2026-06-30
**Author**: Lead Architect

## Files Inspected
- `info/DOC-20260630-WA0002.pdf` — 4-page assignment brief from Visl AI Labs
- `info/candidate_dataset.xlsx` — Sample dataset with 2 sheets

## Dataset Schema Validation

### Sheet "Response" (10 rows)
**Columns**: `s_no, name, email, college, branch, cgpa, best_ai_project, research_work, github, resume, test_la, test_code`
- ✅ **Exact match** with our MASTER_PLAN §4.1 schema
- All 10 rows use the **same email** (`rishabh.choudhary+hatif@mynachiketa.com`) — confirms duplicate email handling is critical
- `github` is NaN for some rows (e.g., Student 3) — must handle as optional
- `research_work` is NaN for some rows — confirmed optional
- `resume` links use both `?usp=sharing` and `?usp=drive_link` suffixes — parser must handle both
- CGPA values: 7.00, 6.60, 8.22 — float normalization confirmed needed
- `test_la` and `test_code` are pre-filled with values (49-75, 57-97 range) — treat as placeholders per plan

### Sheet "Test Result" (8 rows)
**Columns**: `s_no, name, email, college, branch, cgpa, test_la, test_code`
- ✅ **Exact match** with our MASTER_PLAN §4.2 schema
- Only 8 of 10 candidates have test results — parser must handle partial matches

## Assignment PDF Requirements Cross-Check
| # | Requirement | Plan Coverage | Status |
|---|---|---|---|
| 4.1 | CSV upload | Upload pipeline Phase 2 | ✅ |
| 4.2 | Resume download + extract | Resume service Phase 3 | ✅ |
| 4.3 | AI evaluation vs JD | LLM evaluator Phase 3 | ✅ |
| 4.4 | GitHub repo-level analysis | GitHub analyzer Phase 3 | ✅ |
| 4.5 | Scoring & ranking | Scorer module Phase 3 | ✅ |
| 4.6 | Automated emailing (own SMTP) | Email service Phase 5 | ✅ |
| 4.7 | Test result upload | Parser (auto-detect) Phase 2 | ✅ |
| 4.8 | Google Calendar + Meet | Calendar service Phase 6 | ✅ |
| §5 | Publicly hosted | Vercel + Render | ✅ |
| §6 | Architecture doc + demo video | docs/ + recording | ✅ |
| §8 | Explainable AI, dashboard, ranking | Phases 3-4 | ✅ |

## Conclusion
**Plan is fully validated.** No schema mismatches or missing requirements found. Proceeding to execution.
