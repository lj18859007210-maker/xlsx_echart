# Day 11 Header Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add stable multi-row header parsing to the existing review payload so confirmed structures can produce column paths and rough dimension/measure groupings.

**Architecture:** Reuse the aligned review grid as the input to header parsing and keep the output inside each sheet snapshot returned by `GET /api/tasks/{task_id}/review`. Prefer deterministic rules over semantic guessing: identify header row span, build per-column path arrays, and classify columns as `dimension`, `measure`, or `unknown`.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, React, Vitest

---

### Task 1: Backend review contract

**Files:**
- Modify: `backend/tests/unit/test_task_review.py`
- Modify: `backend/app/schemas/review_schema.py`
- Modify: `backend/app/services/review_service.py`

- [ ] Add failing backend tests for header row span, column path arrays, and measure/dimension summaries in review payload.
- [ ] Extend review schemas with deterministic header parsing fields.
- [ ] Implement minimal parsing inside review service and make targeted tests pass.

### Task 2: Frontend summary display

**Files:**
- Modify: `frontend/tests/draftEditing.test.ts`
- Modify: `frontend/src/types/review.ts`
- Modify: `frontend/src/pages/TaskReviewPage.tsx`

- [ ] Add focused frontend tests around the new review payload fields.
- [ ] Extend frontend types for header parsing results.
- [ ] Add a lightweight summary panel that shows header span and column role counts.

### Task 3: Verification

**Files:**
- Modify: `backend/tests/unit/test_task_review.py`
- Modify: `frontend/tests/draftEditing.test.ts`

- [ ] Run backend tests.
- [ ] Run frontend tests and production build.
- [ ] Review the diff for scope and consistency.
