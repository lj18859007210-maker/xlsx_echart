"""Day 20 tests - AI analysis with mock LLM."""

import json
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models.file_record import FileRecordModel
from app.db.models.insight_record import InsightRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.structure_version_record import StructureVersionRecordModel
from app.db.models.summary_record import SummaryRecordModel
from app.db.models.task_record import TaskRecordModel
from app.services.analysis import analysis_service
from app.services.analysis.prompt_builder import build_analysis_prompt


MOCK_LLM_RESPONSE = {
    "executive_summary": "Sales data shows overall growth but two profit calculation errors and one negative net profit anomaly exist. Recommend verifying West and South region profit data.",
    "key_findings": [
        {
            "title": "West profit calculation error",
            "description": "West revenue 90, cost 70, profit should be 20 but actual is 25. Delta 5.",
            "severity": "critical",
            "needs_human_review": False,
            "evidence": [
                {"sheet": "P&L", "metric": "Profit", "row": 2, "col": 3, "value": "25",
                 "context": "Expected 20 (90-70)"}
            ]
        },
        {
            "title": "South profit calculation error",
            "description": "South profit should be 20 but actual is 15.",
            "severity": "warning",
            "needs_human_review": False,
            "evidence": [
                {"sheet": "P&L", "metric": "Profit", "row": 4, "col": 3, "value": "15",
                 "context": "Expected 20 (80-60)"}
            ]
        },
        {
            "title": "Total row large growth",
            "description": "Total row Revenue, Cost, Profit grew over 50% vs previous row",
            "severity": "info",
            "needs_human_review": False,
            "evidence": [
                {"sheet": "P&L", "metric": "Revenue", "row": 5, "col": 1, "value": "390",
                 "context": "Total row summary"}
            ]
        }
    ],
    "risks": [
        {
            "title": "West data quality risk",
            "description": "Profit mismatch may lead to decisions based on wrong data",
            "severity": "critical",
            "mitigation": "Verify West raw data and correct immediately"
        }
    ],
    "recommendations": [
        {
            "title": "Verify profit formulas",
            "description": "Use formulas instead of manual entry for profit calculations",
            "priority": "high",
            "expected_impact": "Eliminate manual entry errors"
        }
    ],
    "chart_hints": [
        {
            "chart_type": "bar",
            "title": "Revenue vs Cost by Region",
            "metrics": ["Revenue", "Cost"],
            "dimension": "Region",
            "reason": "Bar chart best shows revenue/cost comparison"
        }
    ]
}


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


def _create_task_with_summary(
    session_factory: sessionmaker[Session],
) -> int:
    with session_factory() as session:
        f = FileRecordModel(file_name="t.xlsx", file_path="t.xlsx", file_type=".xlsx")
        session.add(f); session.flush()
        t = TaskRecordModel(file_id=f.id, status="validated")
        session.add(t); session.flush()

        sheet = SheetRecordModel(
            task_id=t.id, sheet_name="P&L", sheet_index=0,
            row_count=6, col_count=4, is_hidden=False,
        )
        session.add(sheet); session.flush()

        grid = [
            ["Region", "Revenue", "Cost", "Profit"],
            ["East", "100", "80", "20"],
            ["West", "90", "70", "25"],
            ["North", "120", "95", "25"],
            ["South", "80", "60", "15"],
            ["Total", "390", "305", "85"],
        ]
        kinds = ["dimension", "measure", "measure", "measure"]
        paths = [["Region"], ["Revenue"], ["Cost"], ["Profit"]]

        sv = StructureVersionRecordModel(
            task_id=t.id, version_number=1,
            snapshot_json={"sheets": [{
                "sheet_id": sheet.id, "sheet_name": "P&L",
                "aligned_grid": grid,
                "column_paths": paths, "column_kinds": kinds,
                "aligned_cell_roles": [kinds[:] for _ in grid],
                "aligned_source_map": [], "cell_tags": [],
                "sheet_index": 0, "row_count": 6, "col_count": 4,
                "is_hidden": False, "merge_ranges": [],
            }]},
            patch_summary_json={}, is_confirmed=True,
        )
        session.add(sv); session.flush()

        summary = SummaryRecordModel(
            task_id=t.id,
            summary_json={
                "statistical_summary": [],
                "validation_issues_summary": {"total": 2, "by_severity": {"error": 2}},
                "anomaly_summary": {"total": 3, "rule_hits": 3, "stat_hits": 0},
                "semantic_schema": [],
            },
            slice_json=[],
            token_estimate=500,
        )
        session.add(summary)
        session.commit()
        return t.id


class TestPromptBuilder:
    def test_builds_system_and_user_prompts(self):
        ctx = {"statistical_summary": [], "validation_issues_summary": {}}
        sys_p, usr_p = build_analysis_prompt(ctx)
        assert "senior financial data analyst" in sys_p.lower()
        assert "CRITICAL RULES" in sys_p
        assert "DATA-ONLY" in sys_p
        assert "EVIDENCE REQUIRED" in sys_p
        assert "JSON ONLY" in sys_p
        assert "CONTEXT PACKAGE" in usr_p
        # Context data is embedded (with indent, so check keys exist)
        assert "statistical_summary" in usr_p
        assert "validation_issues_summary" in usr_p

    def test_prompt_includes_required_output_structure(self):
        ctx = {"statistical_summary": []}
        _sys, usr = build_analysis_prompt(ctx)
        assert "executive_summary" in usr
        assert "key_findings" in usr
        assert "risks" in usr
        assert "recommendations" in usr
        assert "chart_hints" in usr


class TestAnalysisService:
    def test_analyze_with_mock_llm(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_summary(session_factory)

        with patch(
            "app.services.analysis.analysis_service.call_analysis_llm",
            return_value=MOCK_LLM_RESPONSE,
        ):
            with session_factory() as session:
                result = analysis_service.analyze_task(task_id, session)

        assert result["task_id"] == task_id
        assert len(result["key_findings"]) == 3
        assert len(result["risks"]) == 1
        assert len(result["recommendations"]) == 1
        assert len(result["chart_hints"]) == 1
        assert len(result["citations"]) > 0

        # Critical finding should have disclaimer attached
        critical = [f for f in result["key_findings"] if f["severity"] == "critical"]
        assert len(critical) > 0
        assert "建议人工复核" in critical[0]["description"]

    def test_analysis_is_persisted(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_summary(session_factory)

        with patch(
            "app.services.analysis.analysis_service.call_analysis_llm",
            return_value=MOCK_LLM_RESPONSE,
        ):
            with session_factory() as session:
                analysis_service.analyze_task(task_id, session)

        with session_factory() as session:
            record = session.scalar(
                select(InsightRecordModel).where(
                    InsightRecordModel.task_id == task_id,
                ),
            )
            assert record is not None
            assert len(record.key_findings_json) == 3
            assert record.model_name != ""

    def test_get_insight_returns_persisted(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_summary(session_factory)

        with patch(
            "app.services.analysis.analysis_service.call_analysis_llm",
            return_value=MOCK_LLM_RESPONSE,
        ):
            with session_factory() as session:
                analysis_service.analyze_task(task_id, session)

        with session_factory() as session:
            result = analysis_service.get_insight(task_id, session)

        assert result is not None
        assert len(result["key_findings"]) == 3
        assert result["key_findings"][0]["title"] == MOCK_LLM_RESPONSE["key_findings"][0]["title"]

    def test_rejects_invalid_llm_json(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_summary(session_factory)

        bad_response = {"executive_summary": 123}

        with patch(
            "app.services.analysis.analysis_service.call_analysis_llm",
            return_value=bad_response,
        ):
            with session_factory() as session:
                with pytest.raises(analysis_service.HTTPException, match="502"):
                    analysis_service.analyze_task(task_id, session)

    def test_rejects_task_without_summary(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        with session_factory() as session:
            f = FileRecordModel(file_name="t.xlsx", file_path="t.xlsx", file_type=".xlsx")
            session.add(f); session.flush()
            t = TaskRecordModel(file_id=f.id, status="validated")
            session.add(t); session.commit()
            task_id = t.id

        with session_factory() as session:
            with pytest.raises(analysis_service.HTTPException, match="400"):
                analysis_service.analyze_task(task_id, session)

    def test_get_insight_returns_none_for_no_data(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        with session_factory() as session:
            result = analysis_service.get_insight(999, session)
        assert result is None