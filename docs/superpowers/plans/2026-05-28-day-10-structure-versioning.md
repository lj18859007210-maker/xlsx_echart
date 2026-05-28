# Day 10 Structure Versioning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist Gate 1 review drafts as structure versions, expose confirm behavior, and let the frontend save and confirm reviewed structures.

**Architecture:** Keep the existing parsed workbook data as the raw source of truth and add a structure-version snapshot layer on top. The review endpoint should return the latest saved version when present, while save and confirm endpoints create immutable snapshots and advance task status without mutating parsed cell rows.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, Vitest

---

### Task 1: Backend version persistence

**Files:**
- Create: `backend/app/db/models/structure_version_record.py`
- Modify: `backend/app/db/base.py`
- Modify: `backend/app/db/models/__init__.py`
- Modify: `backend/tests/unit/test_task_review.py`

- [ ] Add failing tests for saving a structure version and reading it back through `GET /api/tasks/{task_id}/review`.
- [ ] Add failing tests for confirming a saved structure version through `POST /api/tasks/{task_id}/confirm`.
- [ ] Implement the ORM model and wire metadata imports.
- [ ] Run targeted backend tests and make them pass.

### Task 2: Backend API and services

**Files:**
- Modify: `backend/app/api/routes/tasks.py`
- Modify: `backend/app/schemas/review_schema.py`
- Modify: `backend/app/services/review_service.py`

- [ ] Add request and response schemas for structure version save and confirm.
- [ ] Implement a save service that stores sheet snapshots plus a patch summary.
- [ ] Update review loading to prefer the newest saved structure version.
- [ ] Implement confirm behavior that marks the chosen version confirmed and updates task status to `confirmed`.
- [ ] Run the full backend test suite.

### Task 3: Frontend save and confirm flow

**Files:**
- Modify: `frontend/src/pages/TaskReviewPage.tsx`
- Modify: `frontend/src/types/review.ts`
- Modify: `frontend/tests/draftEditing.test.ts`

- [ ] Add focused frontend tests around payload shaping for save/confirm.
- [ ] Wire `Save draft` and `Confirm structure` actions to the new backend endpoints.
- [ ] Reflect save and confirm results in local page state.
- [ ] Run frontend tests and make them pass.

### Task 4: Verification

**Files:**
- Modify: `backend/tests/unit/test_task_review.py`
- Modify: `frontend/tests/draftEditing.test.ts`

- [ ] Run backend and frontend test suites.
- [ ] Review the diff for scope and consistency.
