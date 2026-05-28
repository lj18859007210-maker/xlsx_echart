import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models.cell_record import CellRecordModel
from app.db.models.file_record import FileRecordModel
from app.db.models.formula_rule_record import FormulaRuleRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.task_record import TaskRecordModel
from app.services.formula import formula_inference_service
from app.services.formula.formula_candidate_schema import FormulaCandidateResponse
from app.services.formula.formula_sample_verifier import verify_formula_candidate
from app.services.formula.llm_formula_client import build_formula_inference_request_payload
from app.services.formula.prompt_builder import PROMPT_VERSION, build_formula_inference_prompt


def _override_db_session(database_url: str) -> sessionmaker[Session]:
    engine = create_engine(
        database_url,
        future=True,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def _create_confirmed_formula_task(session_factory: sessionmaker[Session]) -> int:
    with session_factory() as session:
        file_record = FileRecordModel(
            file_name="formula.xlsx",
            file_path="formula.xlsx",
            file_type=".xlsx",
        )
        session.add(file_record)
        session.flush()

        task_record = TaskRecordModel(file_id=file_record.id, status="confirmed")
        session.add(task_record)
        session.flush()

        sheet_record = SheetRecordModel(
            task_id=task_record.id,
            sheet_name="P&L",
            sheet_index=0,
            row_count=3,
            col_count=4,
            is_hidden=False,
        )
        session.add(sheet_record)
        session.flush()

        values = [
            ["Region", "Revenue", "Cost", "Profit"],
            ["East", "100", "80", "20"],
            ["West", "90", "70", "20"],
        ]
        cell_records: list[CellRecordModel] = []
        for row_index, row in enumerate(values, start=1):
            for col_index, value in enumerate(row, start=1):
                address = f"{chr(64 + col_index)}{row_index}"
                cell_records.append(
                    CellRecordModel(
                        sheet_id=sheet_record.id,
                        row_index=row_index,
                        col_index=col_index,
                        address=address,
                        raw_value=value,
                        normalized_value=value,
                        value_type="n" if row_index > 1 and col_index > 1 else "s",
                        is_merged=False,
                        merge_range=None,
                    )
                )
        session.add_all(cell_records)
        session.commit()
        session.refresh(task_record)
        return task_record.id


def test_formula_candidate_response_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        FormulaCandidateResponse.model_validate(
            {
                "sheet_candidates": [
                    {
                        "sheet_id": 1,
                        "candidates": [
                            {
                                "formula_text": "col_C = col_A + col_B",
                                "confidence": 0.91,
                                "rationale": "C equals A plus B",
                                "extra": "x",
                            }
                        ],
                    }
                ]
            }
        )


def test_formula_candidate_response_accepts_strict_candidate_payload() -> None:
    payload = FormulaCandidateResponse.model_validate(
        {
            "sheet_candidates": [
                {
                    "sheet_id": 1,
                    "candidates": [
                        {
                            "formula_text": "col_C = col_A + col_B",
                            "confidence": 0.91,
                            "rationale": "C equals A plus B",
                        }
                    ],
                }
            ]
        }
    )

    assert payload.sheet_candidates[0].sheet_id == 1
    assert payload.sheet_candidates[0].candidates[0].confidence == 0.91


def test_prompt_builder_uses_confirmed_structure_fields_only() -> None:
    prompt = build_formula_inference_prompt(
        task_id=11,
        sheets=[
            {
                "sheet_id": 7,
                "sheet_name": "P&L",
                "column_paths": [["Region"], ["Revenue"], ["Cost"], ["Profit"]],
                "column_kinds": ["dimension", "measure", "measure", "measure"],
                "aligned_grid": [
                    ["Region", "Revenue", "Cost", "Profit"],
                    ["East", "100", "80", "20"],
                    ["West", "90", "70", "20"],
                    ["North", "50", "25", "25"],
                    ["South", "30", "10", "20"],
                    ["Central", "20", "5", "15"],
                    ["Overflow", "999", "1", "998"],
                ],
                "raw_cells": [{"address": "A1", "raw_value": "should not be included"}],
            }
        ],
        max_candidates_per_sheet=3,
    )

    assert PROMPT_VERSION == "day13_v1"
    assert "Only use the provided columns" in prompt
    assert "Return JSON only" in prompt
    assert "prefer_empty_over_guessing" in prompt
    assert "column_paths" in prompt
    assert "Overflow" not in prompt
    assert "raw_cells" not in prompt


def test_sample_verifier_accepts_exact_subtraction_match() -> None:
    sheet_payload = {
        "column_paths": [["Region"], ["Revenue"], ["Cost"], ["Profit"]],
        "aligned_grid": [
            ["Region", "Revenue", "Cost", "Profit"],
            ["East", "100", "80", "20"],
            ["West", "90", "70", "20"],
        ],
    }

    score = verify_formula_candidate(sheet_payload, "col_Profit = col_Revenue - col_Cost")

    assert score == 1.0


def test_sample_verifier_rejects_wrong_math() -> None:
    sheet_payload = {
        "column_paths": [["Region"], ["Revenue"], ["Cost"], ["Profit"]],
        "aligned_grid": [["Region", "Revenue", "Cost", "Profit"], ["East", "100", "80", "20"]],
    }

    score = verify_formula_candidate(sheet_payload, "col_Profit = col_Revenue + col_Cost")

    assert score == 0.0


def test_sample_verifier_scores_partial_matches() -> None:
    sheet_payload = {
        "column_paths": [["Revenue"], ["Cost"], ["Profit"]],
        "aligned_grid": [
            ["Revenue", "Cost", "Profit"],
            ["100", "80", "20"],
            ["90", "70", "21"],
        ],
    }

    score = verify_formula_candidate(sheet_payload, "col_Profit = col_Revenue - col_Cost")

    assert score == 0.5


def test_llm_client_builds_json_request_payload() -> None:
    payload = build_formula_inference_request_payload(
        prompt="infer formulas",
        model_name="mock/day13",
    )

    assert payload == {
        "model": "mock/day13",
        "prompt": "infer formulas",
        "response_format": {"type": "json_object"},
    }


def test_inference_service_persists_only_verified_rules(tmp_path, monkeypatch) -> None:
    session_factory = _override_db_session(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    task_id = _create_confirmed_formula_task(session_factory)

    monkeypatch.setattr(
        formula_inference_service.llm_formula_client,
        "run_formula_inference",
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
                            "rationale": "wrong sign",
                        },
                    ],
                }
            ]
        },
    )

    with session_factory() as session:
        payload = formula_inference_service.infer_task_formulas(
            task_id,
            session,
            model_name="mock/day13",
        )

    assert [item["formula_text"] for item in payload["accepted_rules"]] == [
        "col_Profit = col_Revenue - col_Cost"
    ]
    assert payload["rejected_count"] == 1

    with session_factory() as session:
        records = session.scalars(select(FormulaRuleRecordModel)).all()

    assert len(records) == 1
    assert records[0].verification_passed is True
    assert records[0].verification_score == 1.0


def test_inference_service_requires_confirmed_task(tmp_path) -> None:
    session_factory = _override_db_session(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    task_id = _create_confirmed_formula_task(session_factory)
    with session_factory() as session:
        task = session.scalar(select(TaskRecordModel).where(TaskRecordModel.id == task_id))
        assert task is not None
        task.status = "waiting_confirm"
        session.commit()

    with session_factory() as session:
        with pytest.raises(formula_inference_service.HTTPException, match="409"):
            formula_inference_service.infer_task_formulas(task_id, session, model_name="mock/day13")


def test_inference_returns_empty_rules_when_model_output_is_invalid(tmp_path, monkeypatch) -> None:
    session_factory = _override_db_session(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    task_id = _create_confirmed_formula_task(session_factory)

    monkeypatch.setattr(
        formula_inference_service.llm_formula_client,
        "run_formula_inference",
        lambda **_: {"bad": "payload"},
    )

    with session_factory() as session:
        payload = formula_inference_service.infer_task_formulas(
            task_id,
            session,
            model_name="mock/day13",
        )

    assert payload["accepted_rules"] == []
    assert payload["rejected_count"] == 0


def test_audit_logger_emits_start_and_complete(caplog, tmp_path, monkeypatch) -> None:
    import logging

    caplog.set_level(logging.INFO, logger="formula_audit")

    session_factory = _override_db_session(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    task_id = _create_confirmed_formula_task(session_factory)

    monkeypatch.setattr(
        formula_inference_service.llm_formula_client,
        "run_formula_inference",
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
                    ],
                }
            ]
        },
    )

    with session_factory() as session:
        formula_inference_service.infer_task_formulas(
            task_id,
            session,
            model_name="mock/day13",
        )

    start_events = [
        r for r in caplog.records
        if r.name == "formula_audit" and "inference_start" in r.message
    ]
    complete_events = [
        r for r in caplog.records
        if r.name == "formula_audit" and "inference_complete" in r.message
    ]

    assert len(start_events) == 1
    assert len(complete_events) == 1

    import json

    complete_payload = json.loads(complete_events[0].message)
    assert complete_payload["accepted"] == 1
    assert complete_payload["rejected"] == 0
    assert complete_payload["duration_ms"] >= 0
    assert complete_payload["confidence_p50"] == 0.92
    assert "rejection_reasons" in complete_payload


