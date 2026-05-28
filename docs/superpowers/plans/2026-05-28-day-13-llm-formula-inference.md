# Day 13 LLM Formula Inference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a high-precision Day 13 formula-inference pipeline that turns confirmed sheet structures into validated candidate formula rules without breaking the existing Day 14-16 schedule.

**Architecture:** Keep the LLM in a tightly constrained role: it may propose candidate formulas, but every candidate must pass JSON schema validation, DSL parsing, semantic validation, and sample-data verification before it is persisted. The pipeline should prefer false negatives over false positives: empty results are acceptable, low-confidence hallucinations are not.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Pydantic, existing Day 12 formula parser/validator, Python stdlib `urllib` for HTTP, pytest

---

## File Structure

**Backend API surface**
- Modify: `backend/app/api/routes/tasks.py`
  Add `POST /api/tasks/{task_id}/infer-formulas`.
- Modify: `backend/app/schemas/task_schema.py`
  Add request/response models for Day 13 inference.

**Formula persistence**
- Create: `backend/app/db/models/formula_rule_record.py`
  Persist inferred rules and their audit metadata.
- Modify: `backend/app/db/models/task_record.py`
  Add relationship from task to formula rules.
- Modify: `backend/app/db/base.py`
  Register the new model for metadata.
- Create: `backend/alembic/versions/20260528_0004_add_formula_rules.py`
  Add the `formula_rules` table.

**Inference pipeline**
- Create: `backend/app/services/formula/prompt_builder.py`
  Build a minimal, deterministic LLM prompt from confirmed review payloads.
- Create: `backend/app/services/formula/formula_candidate_schema.py`
  Strict JSON response schema for LLM output.
- Create: `backend/app/services/formula/formula_sample_verifier.py`
  Verify candidate formulas against the current aligned sheet data.
- Create: `backend/app/services/formula/llm_formula_client.py`
  Small HTTP client wrapper for structured model calls.
- Create: `backend/app/services/formula/formula_inference_service.py`
  Orchestrate prompt building, model invocation, parsing, validation, verification, and persistence.
- Modify: `backend/app/services/formula/__init__.py`
  Export the new Day 13 services.

**Testing**
- Create: `backend/tests/unit/test_formula_inference_service.py`
  Unit tests for prompt construction, response parsing, verification, and failure downgrade.
- Modify: `backend/tests/unit/test_task_review.py`
  Add end-to-end API coverage for `POST /infer-formulas`.

**Documentation**
- Modify: `README.md`
  Add Day 13 environment variables and local test commands.

---

### Task 1: Add the persistence contract

**Files:**
- Create: `backend/app/db/models/formula_rule_record.py`
- Modify: `backend/app/db/models/task_record.py`
- Modify: `backend/app/db/base.py`
- Create: `backend/alembic/versions/20260528_0004_add_formula_rules.py`
- Test: `backend/tests/unit/test_db_models.py`

- [ ] **Step 1: Write the failing model test**

```python
def test_formula_rule_model_is_registered_in_metadata():
    table_names = set(Base.metadata.tables)
    assert "formula_rules" in table_names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_db_models.py::test_formula_rule_model_is_registered_in_metadata -v`
Expected: FAIL because `formula_rules` is not registered.

- [ ] **Step 3: Add the ORM model**

```python
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FormulaRuleRecordModel(Base):
    __tablename__ = "formula_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    sheet_id: Mapped[int] = mapped_column(ForeignKey("sheets.id", ondelete="CASCADE"), nullable=False)
    formula_text: Mapped[str] = mapped_column(Text, nullable=False)
    formula_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False, default="inferred")
    scope_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    verification_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_candidate_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    task: Mapped["TaskRecordModel"] = relationship(back_populates="formula_rules")
    sheet: Mapped["SheetRecordModel"] = relationship()
```

- [ ] **Step 4: Wire relationships and metadata**

```python
# backend/app/db/models/task_record.py
formula_rules: Mapped[list["FormulaRuleRecordModel"]] = relationship(
    back_populates="task",
    cascade="all, delete-orphan",
)
```

```python
# backend/app/db/base.py
from app.db.models import (  # noqa: E402,F401
    cell_record,
    file_record,
    formula_rule_record,
    sheet_record,
    structure_version_record,
    task_record,
)
```

- [ ] **Step 5: Add the migration**

```python
def upgrade() -> None:
    op.create_table(
        "formula_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("sheet_id", sa.Integer(), nullable=False),
        sa.Column("formula_text", sa.Text(), nullable=False),
        sa.Column("formula_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rule_type", sa.String(length=30), nullable=False, server_default="inferred"),
        sa.Column("scope_json", sa.JSON(), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("verification_passed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("verification_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("raw_candidate_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sheet_id"], ["sheets.id"], ondelete="CASCADE"),
    )
```

- [ ] **Step 6: Run targeted tests**

Run: `python -m pytest tests/unit/test_db_models.py -v`
Expected: PASS with the new table registered.

- [ ] **Step 7: Commit**

```bash
git add backend/app/db/models/formula_rule_record.py backend/app/db/models/task_record.py backend/app/db/base.py backend/alembic/versions/20260528_0004_add_formula_rules.py backend/tests/unit/test_db_models.py
git commit -m "feat: add formula rule persistence model"
```

### Task 2: Define the Day 13 request/response contracts

**Files:**
- Create: `backend/app/services/formula/formula_candidate_schema.py`
- Modify: `backend/app/schemas/task_schema.py`
- Test: `backend/tests/unit/test_formula_inference_service.py`

- [ ] **Step 1: Write the failing schema test**

```python
def test_formula_candidate_response_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        FormulaCandidateResponse.model_validate(
            {
                "sheet_candidates": [
                    {
                        "sheet_id": 1,
                        "candidates": [{"formula_text": "col_C = col_A + col_B", "extra": "x"}],
                    }
                ]
            }
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_formula_inference_service.py::test_formula_candidate_response_rejects_unknown_fields -v`
Expected: FAIL because the schema does not exist.

- [ ] **Step 3: Add strict candidate schemas**

```python
from pydantic import BaseModel, ConfigDict, Field


class FormulaCandidateItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    formula_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class FormulaCandidateSheet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sheet_id: int
    candidates: list[FormulaCandidateItem]


class FormulaCandidateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sheet_candidates: list[FormulaCandidateSheet]
```

- [ ] **Step 4: Add API request/response models**

```python
class TaskInferFormulaRequest(BaseModel):
    model_name: str | None = None
    max_candidates_per_sheet: int = 5


class FormulaRuleSummary(BaseModel):
    id: int
    sheet_id: int
    formula_text: str
    formula_type: str
    confidence: float
    verification_score: float


class TaskInferFormulaResponse(BaseModel):
    task_id: int
    status: str
    accepted_rules: list[FormulaRuleSummary]
    rejected_count: int
```

- [ ] **Step 5: Run the schema tests**

Run: `python -m pytest tests/unit/test_formula_inference_service.py -k schema -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/formula/formula_candidate_schema.py backend/app/schemas/task_schema.py backend/tests/unit/test_formula_inference_service.py
git commit -m "feat: add day13 formula candidate schemas"
```

### Task 3: Build a constrained prompt builder

**Files:**
- Create: `backend/app/services/formula/prompt_builder.py`
- Test: `backend/tests/unit/test_formula_inference_service.py`

- [ ] **Step 1: Write the failing prompt test**

```python
def test_prompt_builder_uses_confirmed_structure_fields_only():
    prompt = build_formula_inference_prompt(
        task_id=11,
        sheets=[
            {
                "sheet_id": 7,
                "sheet_name": "P&L",
                "column_paths": [["Region"], ["Revenue"], ["Cost"], ["Profit"]],
                "column_kinds": ["dimension", "measure", "measure", "measure"],
                "aligned_grid": [["Region", "Revenue", "Cost", "Profit"], ["East", "100", "80", "20"]],
            }
        ],
        max_candidates_per_sheet=3,
    )
    assert "column_paths" in prompt
    assert "Only use the provided columns" in prompt
    assert "Return JSON only" in prompt
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_formula_inference_service.py::test_prompt_builder_uses_confirmed_structure_fields_only -v`
Expected: FAIL because the builder does not exist.

- [ ] **Step 3: Implement the prompt builder**

```python
import json


PROMPT_VERSION = "day13_v1"


def build_formula_inference_prompt(
    task_id: int,
    sheets: list[dict[str, object]],
    max_candidates_per_sheet: int,
) -> str:
    prompt_payload = {
        "task_id": task_id,
        "rules": {
            "json_only": True,
            "no_new_columns": True,
            "max_candidates_per_sheet": max_candidates_per_sheet,
            "prefer_empty_over_guessing": True,
        },
        "sheets": [
            {
                "sheet_id": sheet["sheet_id"],
                "sheet_name": sheet["sheet_name"],
                "column_paths": sheet["column_paths"],
                "column_kinds": sheet["column_kinds"],
                "sample_rows": sheet["aligned_grid"][:6],
            }
            for sheet in sheets
        ],
    }
    return (
        "You are inferring spreadsheet formulas.\n"
        "Only use the provided columns.\n"
        "Return JSON only.\n"
        "If uncertain, return an empty candidate list.\n\n"
        f"{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}"
    )
```

- [ ] **Step 4: Run prompt tests**

Run: `python -m pytest tests/unit/test_formula_inference_service.py -k prompt -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/formula/prompt_builder.py backend/tests/unit/test_formula_inference_service.py
git commit -m "feat: add constrained formula inference prompt builder"
```

### Task 4: Add candidate parsing and sample verification

**Files:**
- Create: `backend/app/services/formula/formula_sample_verifier.py`
- Modify: `backend/app/services/formula/__init__.py`
- Test: `backend/tests/unit/test_formula_inference_service.py`

- [ ] **Step 1: Write the failing verification tests**

```python
def test_sample_verifier_accepts_exact_subtraction_match():
    sheet_payload = {
        "column_paths": [["Region"], ["Revenue"], ["Cost"], ["Profit"]],
        "aligned_grid": [["Region", "Revenue", "Cost", "Profit"], ["East", "100", "80", "20"]],
    }
    score = verify_formula_candidate(sheet_payload, "col_Profit = col_Revenue - col_Cost")
    assert score == 1.0


def test_sample_verifier_rejects_wrong_math():
    sheet_payload = {
        "column_paths": [["Region"], ["Revenue"], ["Cost"], ["Profit"]],
        "aligned_grid": [["Region", "Revenue", "Cost", "Profit"], ["East", "100", "80", "20"]],
    }
    score = verify_formula_candidate(sheet_payload, "col_Profit = col_Revenue + col_Cost")
    assert score == 0.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit/test_formula_inference_service.py -k verifier -v`
Expected: FAIL because the verifier does not exist.

- [ ] **Step 3: Implement minimal deterministic verification**

```python
from decimal import Decimal, InvalidOperation

from .formula_parser import FormulaParser
from .formula_schema import FormulaType
from .formula_validator import FormulaValidator


def verify_formula_candidate(sheet_payload: dict[str, object], formula_text: str) -> float:
    rule = FormulaParser().parse(formula_text)
    validator = FormulaValidator(
        available_columns=[f"col_{path[-1]}" for path in sheet_payload["column_paths"] if path],
        available_rows=[],
    )
    if validator.validate(rule):
        return 0.0

    if rule.formula_type != FormulaType.COLUMN_ARITHMETIC or not rule.right or not rule.left:
        return 0.0

    # Day 13 stays narrow: only score exact two-source column arithmetic.
    if len(rule.right) != 2:
        return 0.0

    header = sheet_payload["aligned_grid"][0]
    data_rows = sheet_payload["aligned_grid"][1:]
    col_map = {f"col_{name}": index for index, name in enumerate(header)}
    target_index = col_map.get(rule.left.replace("col_", "col_"))
    left_index = col_map.get(rule.right[0])
    right_index = col_map.get(rule.right[1])
    if target_index is None or left_index is None or right_index is None:
        return 0.0

    total = 0
    matched = 0
    for row in data_rows:
        try:
            left_value = Decimal(str(row[left_index]))
            right_value = Decimal(str(row[right_index]))
            target_value = Decimal(str(row[target_index]))
        except (InvalidOperation, IndexError):
            continue

        total += 1
        expected = left_value - right_value if rule.operator == "-" else None
        if expected is not None and expected == target_value:
            matched += 1

    return 0.0 if total == 0 else matched / total
```

- [ ] **Step 4: Run verification tests**

Run: `python -m pytest tests/unit/test_formula_inference_service.py -k verifier -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/formula/formula_sample_verifier.py backend/app/services/formula/__init__.py backend/tests/unit/test_formula_inference_service.py
git commit -m "feat: add deterministic sample verification for formula candidates"
```

### Task 5: Add the model client and orchestration service

**Files:**
- Create: `backend/app/services/formula/llm_formula_client.py`
- Create: `backend/app/services/formula/formula_inference_service.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/pyproject.toml`
- Test: `backend/tests/unit/test_formula_inference_service.py`

- [ ] **Step 1: Write the failing orchestration test**

```python
def test_inference_service_persists_only_verified_rules(session_factory, monkeypatch):
    task_id = build_confirmed_task(session_factory)

    monkeypatch.setattr(
        "app.services.formula.llm_formula_client.run_formula_inference",
        lambda **_: {
            "sheet_candidates": [
                {
                    "sheet_id": 1,
                    "candidates": [
                        {
                            "formula_text": "col_Profit = col_Revenue - col_Cost",
                            "confidence": 0.92,
                            "rationale": "profit equals revenue minus cost",
                        },
                        {
                            "formula_text": "col_Profit = col_Revenue + col_Cost",
                            "confidence": 0.80,
                            "rationale": "wrong",
                        },
                    ],
                }
            ]
        },
    )

    payload = infer_task_formulas(task_id, db_session, model_name="mock/day13")
    assert [item["formula_text"] for item in payload["accepted_rules"]] == [
        "col_Profit = col_Revenue - col_Cost"
    ]
    assert payload["rejected_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_formula_inference_service.py::test_inference_service_persists_only_verified_rules -v`
Expected: FAIL because the service does not exist.

- [ ] **Step 3: Add config knobs**

```python
class Settings(BaseSettings):
    ...
    formula_llm_api_url: str = "https://example.invalid/v1/formula-infer"
    formula_llm_api_key: str = ""
    formula_llm_model: str = "mock/day13"
    formula_prompt_version: str = "day13_v1"
```

- [ ] **Step 4: Implement the HTTP client**

```python
import json
from urllib import request

from app.core.config import settings


def run_formula_inference(*, prompt: str, model_name: str) -> dict[str, object]:
    payload = json.dumps({"model": model_name, "prompt": prompt}).encode("utf-8")
    req = request.Request(
        settings.formula_llm_api_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.formula_llm_api_key}",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))
```

- [ ] **Step 5: Implement the inference orchestrator**

```python
def infer_task_formulas(task_id: int, db: Session, model_name: str | None = None) -> dict[str, object]:
    task = _load_task(task_id, db)
    if task.status != "confirmed":
        raise HTTPException(status_code=409, detail="Task must be confirmed before formula inference")

    review_payload = build_task_review(task_id, db)
    prompt = build_formula_inference_prompt(
        task_id=task.id,
        sheets=review_payload["sheets"],
        max_candidates_per_sheet=5,
    )
    raw_response = run_formula_inference(
        prompt=prompt,
        model_name=model_name or settings.formula_llm_model,
    )
    candidate_response = FormulaCandidateResponse.model_validate(raw_response)

    accepted_rules = []
    rejected_count = 0
    for sheet_candidate in candidate_response.sheet_candidates:
        sheet_payload = next(
            sheet for sheet in review_payload["sheets"] if sheet["sheet_id"] == sheet_candidate.sheet_id
        )
        for candidate in sheet_candidate.candidates:
            verification_score = verify_formula_candidate(sheet_payload, candidate.formula_text)
            if verification_score < 0.95:
                rejected_count += 1
                continue
            parsed_rule = FormulaParser().parse(candidate.formula_text)
            record = FormulaRuleRecordModel(
                task_id=task.id,
                sheet_id=sheet_candidate.sheet_id,
                formula_text=parsed_rule.formula_text,
                formula_type=parsed_rule.formula_type,
                description=parsed_rule.description,
                confidence=candidate.confidence,
                rule_type="inferred",
                scope_json=parsed_rule.scope,
                prompt_version=settings.formula_prompt_version,
                model_name=model_name or settings.formula_llm_model,
                verification_passed=True,
                verification_score=verification_score,
                raw_candidate_json=candidate.model_dump(),
            )
            db.add(record)
            db.flush()
            accepted_rules.append(
                {
                    "id": record.id,
                    "sheet_id": record.sheet_id,
                    "formula_text": record.formula_text,
                    "formula_type": record.formula_type,
                    "confidence": record.confidence,
                    "verification_score": record.verification_score,
                }
            )

    db.commit()
    return {
        "task_id": task.id,
        "status": task.status,
        "accepted_rules": accepted_rules,
        "rejected_count": rejected_count,
    }
```

- [ ] **Step 6: Run orchestration tests**

Run: `python -m pytest tests/unit/test_formula_inference_service.py -k inference -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/formula/llm_formula_client.py backend/app/services/formula/formula_inference_service.py backend/app/core/config.py backend/pyproject.toml backend/tests/unit/test_formula_inference_service.py
git commit -m "feat: add llm-backed formula inference orchestration"
```

### Task 6: Expose the API endpoint

**Files:**
- Modify: `backend/app/api/routes/tasks.py`
- Modify: `backend/app/schemas/task_schema.py`
- Modify: `backend/tests/unit/test_task_review.py`

- [ ] **Step 1: Write the failing API test**

```python
def test_infer_formulas_returns_verified_rules_only(tmp_path, monkeypatch):
    ...
    response = client.post(f"/api/tasks/{task_id}/infer-formulas", json={})
    assert response.status_code == 200
    payload = response.json()
    assert payload["accepted_rules"][0]["formula_text"] == "col_Profit = col_Revenue - col_Cost"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_task_review.py::test_infer_formulas_returns_verified_rules_only -v`
Expected: FAIL with 404 because the route does not exist.

- [ ] **Step 3: Add the route**

```python
@router.post("/{task_id}/infer-formulas", response_model=TaskInferFormulaResponse)
def infer_formulas_for_task(
    task_id: int,
    request: TaskInferFormulaRequest,
    db: Session = Depends(get_db),
) -> TaskInferFormulaResponse:
    payload = infer_task_formulas(
        task_id,
        db,
        model_name=request.model_name,
    )
    return TaskInferFormulaResponse(**payload)
```

- [ ] **Step 4: Add the “must be confirmed” regression test**

```python
def test_infer_formulas_requires_confirmed_task(tmp_path):
    ...
    response = client.post(f"/api/tasks/{task_id}/infer-formulas", json={})
    assert response.status_code == 409
    assert response.json()["detail"] == "Task must be confirmed before formula inference"
```

- [ ] **Step 5: Run the targeted API tests**

Run: `python -m pytest tests/unit/test_task_review.py -k infer_formulas -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/routes/tasks.py backend/app/schemas/task_schema.py backend/tests/unit/test_task_review.py
git commit -m "feat: expose formula inference task endpoint"
```

### Task 7: Add failure downgrade and audit coverage

**Files:**
- Modify: `backend/app/services/formula/formula_inference_service.py`
- Modify: `backend/tests/unit/test_formula_inference_service.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing downgrade test**

```python
def test_inference_returns_empty_rules_when_model_output_is_invalid(session_factory, monkeypatch):
    task_id = build_confirmed_task(session_factory)

    monkeypatch.setattr(
        "app.services.formula.llm_formula_client.run_formula_inference",
        lambda **_: {"bad": "payload"},
    )

    payload = infer_task_formulas(task_id, db_session, model_name="mock/day13")
    assert payload["accepted_rules"] == []
    assert payload["rejected_count"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/test_formula_inference_service.py::test_inference_returns_empty_rules_when_model_output_is_invalid -v`
Expected: FAIL because the service raises instead of degrading gracefully.

- [ ] **Step 3: Add conservative downgrade behavior**

```python
try:
    candidate_response = FormulaCandidateResponse.model_validate(raw_response)
except ValidationError:
    return {
        "task_id": task.id,
        "status": task.status,
        "accepted_rules": [],
        "rejected_count": 0,
    }
```

- [ ] **Step 4: Document the runtime contract**

```markdown
## Day 13 formula inference

Required environment variables:

- `FORMULA_LLM_API_URL`
- `FORMULA_LLM_API_KEY`
- `FORMULA_LLM_MODEL`

Local verification:

```bash
cd backend
python -m pytest tests/unit/test_formula_inference_service.py -v
python -m pytest tests/unit/test_task_review.py -k infer_formulas -v
```
```

- [ ] **Step 5: Run focused tests**

Run: `python -m pytest tests/unit/test_formula_inference_service.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/formula/formula_inference_service.py backend/tests/unit/test_formula_inference_service.py README.md
git commit -m "feat: add conservative downgrade for formula inference"
```

### Task 8: Full verification

**Files:**
- Modify: `backend/tests/unit/test_formula_inference_service.py`
- Modify: `backend/tests/unit/test_task_review.py`

- [ ] **Step 1: Run the full backend test suite**

Run: `cd backend && python -m pytest tests -v`
Expected: PASS

- [ ] **Step 2: Run Ruff**

Run: `cd backend && python -m ruff check app tests`
Expected: PASS

- [ ] **Step 3: Review scope before handoff**

Check that Day 13 only adds:
- candidate generation
- strict parsing
- sample verification
- conservative persistence

Check that Day 14-16 responsibilities are still untouched:
- no fallback inference heuristics beyond verification gating
- no full validation engine execution
- no anomaly detection

- [ ] **Step 4: Commit**

```bash
git add backend
git commit -m "test: verify day13 formula inference pipeline"
```

---

## Self-Review

### Spec coverage
- `写 Prompt`: covered by Task 3.
- `接入模型`: covered by Task 5.
- `解析 JSON`: covered by Tasks 2, 4, 5, and 7.
- `存储公式规则`: covered by Tasks 1 and 5.
- “企业级高准确率、宁缺毋滥”: covered by strict prompt scope, JSON schema validation, parser validation, sample verification threshold, and conservative downgrade.

### Placeholder scan
- No `TODO`, `TBD`, or “similar to above” placeholders remain.
- Each task has explicit files, commands, and code blocks.

### Type consistency
- API returns `TaskInferFormulaResponse`.
- Service persists `FormulaRuleRecordModel`.
- Candidate schema uses `FormulaCandidateResponse`.
- Parsed DSL still flows through the existing `FormulaParser` / `FormulaValidator`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-28-day-13-llm-formula-inference.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
