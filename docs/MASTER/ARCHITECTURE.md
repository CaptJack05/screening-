# System Architecture

This document tracks database DDL schemas, core system constraints, and the approved libraries/dependencies list.

## 1. Database DDL Schemas
*To be filled during active database design. Below is a template schema entry format:*

```sql
-- Example Schema definition (PostgreSQL / SQLite dialect)
-- CREATE TABLE users (
--   id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--   email VARCHAR(255) UNIQUE NOT NULL,
--   password_hash VARCHAR(255) NOT NULL,
--   created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
--   updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
-- );
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
