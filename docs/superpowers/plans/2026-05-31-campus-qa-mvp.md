# Campus QA MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a runnable MVP for a university campus service intelligent Q&A system with RAG, knowledge management, QA records, feedback, model-provider switching, React UI, Docker, and documentation.

**Architecture:** The backend is a FastAPI service split into config/database, SQLAlchemy models, Pydantic schemas, API routes, and services for knowledge CRUD, embeddings, LLM calls, and RAG orchestration. PostgreSQL with pgvector stores knowledge embeddings and records; deterministic mock embedding and fallback model behavior keep the MVP runnable without external model services. The frontend is a Vite React TypeScript app using Ant Design, with pages for chat, knowledge management, and feedback status.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy, pgvector, PostgreSQL, Pydantic, httpx, React, Vite, TypeScript, Axios, Ant Design, Docker Compose.

---

## File Structure

- `backend/app/main.py`: FastAPI app setup, CORS, health route, API router registration.
- `backend/app/core/config.py`: environment-driven settings.
- `backend/app/core/database.py`: SQLAlchemy engine/session/Base helpers.
- `backend/app/models/*.py`: `knowledge_base`, `qa_records`, and `feedback` tables.
- `backend/app/schemas/*.py`: request/response contracts.
- `backend/app/services/embedding/*.py`: embedding interface plus local, SiliconFlow, and deterministic mock implementations.
- `backend/app/services/llm/*.py`: LLM interface plus local, SiliconFlow, and fallback implementations.
- `backend/app/services/rag_service.py`: question embedding, vector retrieval, prompt building, model call, QA record persistence.
- `backend/app/services/knowledge_service.py`: knowledge CRUD and vector search.
- `backend/app/services/qa_service.py`: QA record persistence and listing.
- `backend/app/api/routes/*.py`: FastAPI routes for knowledge, QA, and feedback.
- `backend/app/scripts/init_db.py`: create pgvector extension and SQLAlchemy tables.
- `backend/app/scripts/seed_knowledge.py`: import campus service example knowledge.
- `backend/tests/*.py`: focused tests for deterministic embedding and prompt construction.
- `frontend/src/api/*.ts`: Axios client and API helpers.
- `frontend/src/components/*.tsx`: chat and knowledge UI components.
- `frontend/src/pages/*.tsx`: chat, knowledge, and feedback pages.
- `frontend/src/App.tsx`, `frontend/src/main.tsx`, `frontend/src/styles.css`: app shell and styling.
- `docker-compose.yml`: pgvector PostgreSQL service.
- `README.md`: setup, configuration, API, and manual test instructions.

## Tasks

### Task 1: Core Tests

**Files:**
- Create: `backend/tests/test_embedding.py`
- Create: `backend/tests/test_rag_prompt.py`

- [x] **Step 1: Write failing tests**

Tests assert deterministic mock embeddings have the configured dimension and that the RAG prompt contains the campus-service guardrails, context, and user question.

- [x] **Step 2: Run tests and verify they fail**

Run: `py -3.13 -m pytest backend/tests -q`
Expected: FAIL because backend package and service modules do not exist.

### Task 2: Backend Foundation

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: backend package `__init__.py` files
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`

- [ ] **Step 1: Implement settings and database session wiring**
- [ ] **Step 2: Implement FastAPI app, health check, CORS, and route registration**
- [ ] **Step 3: Run import/compile checks**

### Task 3: Data Model and Schemas

**Files:**
- Create: `backend/app/models/knowledge.py`
- Create: `backend/app/models/qa_record.py`
- Create: `backend/app/models/feedback.py`
- Create: `backend/app/schemas/knowledge.py`
- Create: `backend/app/schemas/qa.py`
- Create: `backend/app/schemas/feedback.py`

- [ ] **Step 1: Implement SQLAlchemy tables required by the spec**
- [ ] **Step 2: Implement Pydantic request/response models**
- [ ] **Step 3: Run import/compile checks**

### Task 4: Embedding, LLM, RAG, and CRUD Services

**Files:**
- Create: `backend/app/services/embedding/*.py`
- Create: `backend/app/services/llm/*.py`
- Create: `backend/app/services/knowledge_service.py`
- Create: `backend/app/services/qa_service.py`
- Create: `backend/app/services/rag_service.py`

- [ ] **Step 1: Implement deterministic mock embedding**
- [ ] **Step 2: Implement local and SiliconFlow embedding clients with mock fallback**
- [ ] **Step 3: Implement local and SiliconFlow LLM clients with evidence-based fallback**
- [ ] **Step 4: Implement knowledge CRUD and pgvector top-k retrieval**
- [ ] **Step 5: Implement prompt building and RAG ask flow**
- [ ] **Step 6: Run backend tests**

### Task 5: Backend API Routes and Scripts

**Files:**
- Create: `backend/app/api/routes/knowledge.py`
- Create: `backend/app/api/routes/qa.py`
- Create: `backend/app/api/routes/feedback.py`
- Create: `backend/app/scripts/init_db.py`
- Create: `backend/app/scripts/seed_knowledge.py`

- [ ] **Step 1: Implement `/api/knowledge` CRUD routes**
- [ ] **Step 2: Implement `/api/qa/ask` and QA listing route**
- [ ] **Step 3: Implement feedback creation/listing route**
- [ ] **Step 4: Implement DB initialization and seed scripts**

### Task 6: React Frontend

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig*.json`
- Create: `frontend/index.html`
- Create: `frontend/src/**/*`

- [ ] **Step 1: Implement Axios API helpers**
- [ ] **Step 2: Implement ChatPage with answer, citations, loading state, and feedback**
- [ ] **Step 3: Implement KnowledgePage CRUD with category filtering**
- [ ] **Step 4: Implement FeedbackPage and polished Ant Design shell**
- [ ] **Step 5: Run TypeScript build**

### Task 7: Docker, README, and Verification

**Files:**
- Create: `docker-compose.yml`
- Create: `README.md`

- [ ] **Step 1: Add pgvector Docker Compose service**
- [ ] **Step 2: Document setup, model switching, seeding, APIs, and manual tests**
- [ ] **Step 3: Run backend tests and frontend build**
- [ ] **Step 4: Audit requirements from the original document against files and command output**

