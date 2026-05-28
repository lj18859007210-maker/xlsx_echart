"""Day 21 tests — chart recommendation with rule engine."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.db.models.chart_spec_record import ChartSpecRecordModel
from app.db.models.file_record import FileRecordModel
from app.db.models.insight_record import InsightRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.structure_version_record import StructureVersionRecordModel
from app.db.models.summary_record import SummaryRecordModel
from app.db.models.task_record import TaskRecordModel
from app.services.chart_recommendation import chart_service
from app.services.chart_recommendation.chart_rule_selector import select_chart_types
from app.services.chart_recommendation.chart_spec_builder import build_chart_spec
from app.services.chart_recommendation.echarts_adapter import (
    to_echarts_option,
    supports_chart_type,
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

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


def _create_task_with_data(
    session_factory: sessionmaker[Session],
    *,
    status: str = "analyzed",
    grid: list[list[object]] | None = None,
    kinds: list[str] | None = None,
    paths: list[list[str]] | None = None,
    chart_hints: list[dict[str, object]] | None = None,
) -> int:
    if grid is None:
        grid = [
            ["Region", "Revenue", "Cost", "Profit"],
            ["East", "100", "80", "20"],
            ["West", "90", "70", "25"],
            ["North", "120", "95", "25"],
            ["South", "80", "60", "15"],
            ["Total", "390", "305", "85"],
        ]
    if kinds is None:
        kinds = ["dimension", "measure", "measure", "measure"]
    if paths is None:
        paths = [["Region"], ["Revenue"], ["Cost"], ["Profit"]]

    with session_factory() as session:
        f = FileRecordModel(file_name="t.xlsx", file_path="t.xlsx", file_type=".xlsx")
        session.add(f); session.flush()

        t = TaskRecordModel(file_id=f.id, status=status)
        session.add(t); session.flush()

        sheet = SheetRecordModel(
            task_id=t.id, sheet_name="Sheet1", sheet_index=0,
            row_count=len(grid), col_count=len(grid[0]) if grid else 0,
            is_hidden=False,
        )
        session.add(sheet); session.flush()

        sv = StructureVersionRecordModel(
            task_id=t.id, version_number=1,
            snapshot_json={"sheets": [{
                "sheet_id": sheet.id, "sheet_name": "Sheet1",
                "aligned_grid": grid,
                "column_paths": paths,
                "column_kinds": kinds,
            }]},
            patch_summary_json={},
        )
        session.add(sv); session.flush()

        summary = SummaryRecordModel(
            task_id=t.id,
            summary_json={"statistical_summary": [], "semantic_schema": []},
            slice_json=[],
            token_estimate=100,
            token_budget=4000,
            trimmed=False,
        )
        session.add(summary)

        insight = InsightRecordModel(
            task_id=t.id, version_no=1,
            executive_summary="",
            key_findings_json=[],
            risks_json=[],
            recommendations_json=[],
            citations_json=[],
            chart_hints_json=chart_hints or [],
            model_name="mock",
            prompt_version="day20_v1",
        )
        session.add(insight)
        session.commit()
        return t.id


# ---------------------------------------------------------------------------
# rule_engine tests
# ---------------------------------------------------------------------------

class TestRuleEngine:
    def test_bar_selection_dim_plus_multi_measures(self):
        kinds = ["dimension", "measure", "measure", "measure"]
        paths = [["Region"], ["Revenue"], ["Cost"], ["Profit"]]
        grid = [
            ["Region", "Revenue", "Cost", "Profit"],
            ["East", "100", "80", "20"],
            ["West", "90", "70", "25"],
        ]
        results, reason = select_chart_types(kinds, paths, grid)
        assert len(results) >= 1
        assert results[0]["chart_type"] in {"bar", "grouped_bar"}

    def test_line_selection_time_dimension(self):
        kinds = ["dimension", "measure"]
        paths = [["月份"], ["Revenue"]]
        grid = [
            ["月份", "Revenue"],
            ["1月", "100"],
            ["2月", "110"],
            ["3月", "120"],
        ]
        results, reason = select_chart_types(kinds, paths, grid)
        assert len(results) >= 1
        assert results[0]["chart_type"] == "line"

    def test_pie_selection_short_series(self):
        kinds = ["dimension", "measure"]
        paths = [["Category"], ["Share"]]
        grid = [
            ["Category", "Share"],
            ["A", "30"],
            ["B", "45"],
            ["C", "25"],
        ]
        results, reason = select_chart_types(kinds, paths, grid)
        assert len(results) >= 1
        assert results[0]["chart_type"] == "pie"

    def test_scatter_selection_two_measures_no_dim(self):
        kinds = ["measure", "measure"]
        paths = [["Income"], ["Spend"]]
        grid = [
            ["Income", "Spend"],
            ["100", "80"],
            ["200", "150"],
        ]
        results, reason = select_chart_types(kinds, paths, grid)
        assert len(results) >= 1
        assert results[0]["chart_type"] == "scatter"

    def test_no_chart_empty_grid(self):
        results, reason = select_chart_types(["dimension"], [["X"]], [])
        assert results == []
        assert reason != ""

    def test_no_chart_single_measure_no_dim(self):
        kinds = ["measure"]
        paths = [["Value"]]
        grid = [
            ["Value"],
            ["1"],
            ["2"],
        ]
        results, reason = select_chart_types(kinds, paths, grid)
        assert results == []
        assert reason != ""

    def test_chart_hints_validation(self):
        kinds = ["dimension", "measure", "measure"]
        paths = [["Region"], ["Revenue"], ["Cost"]]
        grid = [
            ["Region", "Revenue", "Cost"],
            ["East", "100", "80"],
            ["West", "90", "70"],
        ]
        hints = [{"chart_type": "bar", "title": "Test", "metrics": ["Revenue"], "dimension": "Region"}]
        results, reason = select_chart_types(kinds, paths, grid, chart_hints=hints)
        assert len(results) >= 1
        assert results[0]["chart_type"] == "bar"
        assert results[0]["source"] == "llm_hint"

    def test_stacked_bar_for_composition(self):
        """Composition/structure data should use stacked bar."""
        kinds = ["dimension", "measure", "measure"]
        paths = [["类别"], ["占比A"], ["占比B"]]
        grid = [
            ["类别", "占比A", "占比B"],
            ["产品1", "30", "70"],
            ["产品2", "45", "55"],
            ["产品3", "60", "40"],
        ]
        results, reason = select_chart_types(kinds, paths, grid)
        assert len(results) >= 1
        assert results[0]["chart_type"] == "stacked_bar"

    def test_horizontal_bar_for_ranking(self):
        """Ranking data should use horizontal bar."""
        kinds = ["dimension", "measure"]
        paths = [["名称"], ["排名得分"]]
        grid = [
            ["名称", "排名得分"],
            ["产品A", "95"],
            ["产品B", "88"],
            ["产品C", "76"],
        ]
        results, reason = select_chart_types(kinds, paths, grid)
        assert len(results) >= 1
        assert results[0]["chart_type"] == "horizontal_bar"


# ---------------------------------------------------------------------------
# spec_builder tests
# ---------------------------------------------------------------------------

class TestSpecBuilder:
    def test_build_bar_spec(self):
        rule = {"chart_type": "bar", "source": "auto_infer"}
        grid = [
            ["Region", "Revenue", "Cost"],
            ["East", "100", "80"],
            ["West", "90", "70"],
            ["North", "120", "95"],
        ]
        kinds = ["dimension", "measure", "measure"]
        paths = [["Region"], ["Revenue"], ["Cost"]]
        names = ["Region", "Revenue", "Cost"]

        spec = build_chart_spec(rule, grid, kinds, paths, names, "Sheet1")

        assert spec["chart_type"] == "bar"
        assert "Sheet1" in spec["title"]
        assert spec["x_field"] == "Region"
        assert len(spec["y_fields"]) == 2
        assert len(spec["series"]) == 2
        assert len(spec["source_cells"]) >= 1
        assert "filter_conditions" in spec
        assert spec["filter_conditions"] != ""
        assert len(spec["series"][0]["data"]) == 3

    def test_build_line_spec(self):
        rule = {"chart_type": "line", "source": "auto_infer"}
        grid = [
            ["Month", "Sales"],
            ["Jan", "100"],
            ["Feb", "120"],
            ["Mar", "115"],
            ["Apr", "140"],
            ["May", "135"],
            ["Jun", "160"],
            ["Jul", "155"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Month"], ["Sales"]]
        names = ["Month", "Sales"]

        spec = build_chart_spec(rule, grid, kinds, paths, names, "Trend")

        assert spec["chart_type"] == "line"
        assert len(spec["series"]) == 1
        assert len(spec["series"][0]["data"]) == 7

    def test_build_pie_spec(self):
        rule = {"chart_type": "pie", "source": "auto_infer"}
        grid = [
            ["Category", "Share"],
            ["A", "30"],
            ["B", "45"],
            ["C", "25"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Category"], ["Share"]]
        names = ["Category", "Share"]

        spec = build_chart_spec(rule, grid, kinds, paths, names, "Sheet1")

        assert spec["chart_type"] == "pie"
        assert len(spec["series"]) == 1
        assert len(spec["series"][0]["data"]) == 3

    def test_data_points_correctly_extracted(self):
        rule = {"chart_type": "bar", "source": "auto_infer"}
        grid = [
            ["X", "Y"],
            ["a", "1.5"],
            ["b", "2.7"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["X"], ["Y"]]
        names = ["X", "Y"]

        spec = build_chart_spec(rule, grid, kinds, paths, names, "S")

        assert spec["series"][0]["data"] == [1.5, 2.7]

    def test_series_format_is_echarts_compatible(self):
        rule = {"chart_type": "bar", "source": "auto_infer"}
        grid = [
            ["Region", "Revenue"],
            ["East", "100"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]
        names = ["Region", "Revenue"]

        spec = build_chart_spec(rule, grid, kinds, paths, names, "S")

        for s in spec["series"]:
            assert "name" in s
            assert "data" in s
            assert isinstance(s["data"], list)

    def test_filter_conditions_in_output(self):
        rule = {"chart_type": "bar", "source": "auto_infer"}
        grid = [
            ["Region", "Revenue"],
            ["East", "100"],
            ["West", "200"],
        ]
        kinds = ["dimension", "measure"]
        paths = [["Region"], ["Revenue"]]
        names = ["Region", "Revenue"]

        spec = build_chart_spec(rule, grid, kinds, paths, names, "S")
        assert "filter_conditions" in spec
        assert "Region" in spec["filter_conditions"]
        assert "Revenue" in spec["filter_conditions"]


# ---------------------------------------------------------------------------
# echarts_adapter tests
# ---------------------------------------------------------------------------

class TestEchartsAdapter:
    def test_bar_to_echarts_option(self):
        spec = {
            "chart_type": "bar",
            "title": "Test",
            "x_field": "Region",
            "y_fields": ["Revenue"],
            "series": [{"name": "Revenue", "data": [100, 200]}],
            "highlights": [],
            "source_cells": ["A1:B3"],
            "filter_conditions": "维度: Region",
            "reason": "auto_infer",
        }
        option = to_echarts_option(spec)
        assert option["title"]["text"] == "Test"
        assert option["xAxis"]["type"] == "category"
        assert option["yAxis"]["type"] == "value"
        assert len(option["series"]) == 1

    def test_pie_to_echarts_option(self):
        spec = {
            "chart_type": "pie",
            "title": "Share",
            "x_field": "Category",
            "y_fields": ["Share"],
            "series": [{"name": "Share", "data": [30, 45, 25]}],
            "highlights": [],
            "source_cells": [],
            "filter_conditions": "",
            "reason": "",
        }
        option = to_echarts_option(spec)
        assert option["series"][0]["type"] == "pie"
        assert "xAxis" not in option

    def test_stacked_bar_option(self):
        spec = {
            "chart_type": "stacked_bar",
            "title": "Stack",
            "x_field": "Region",
            "y_fields": ["A", "B"],
            "series": [
                {"name": "A", "data": [30, 40]},
                {"name": "B", "data": [70, 60]},
            ],
            "highlights": [],
            "source_cells": [],
            "filter_conditions": "",
            "reason": "",
        }
        option = to_echarts_option(spec)
        assert option["series"][0].get("stack") == "total"

    def test_horizontal_bar_option(self):
        spec = {
            "chart_type": "horizontal_bar",
            "title": "Rank",
            "x_field": "Name",
            "y_fields": ["Score"],
            "series": [{"name": "Score", "data": [95, 88, 76]}],
            "highlights": [],
            "source_cells": [],
            "filter_conditions": "",
            "reason": "",
        }
        option = to_echarts_option(spec)
        # yAxis should be category (swapped)
        assert option["yAxis"]["type"] == "category"
        assert option["xAxis"]["type"] == "value"

    def test_supports_all_chart_types(self):
        for ct in ["bar", "line", "pie", "scatter", "grouped_bar",
                    "stacked_bar", "horizontal_bar"]:
            assert supports_chart_type(ct), f"Should support {ct}"
        assert not supports_chart_type("unknown_type")


# ---------------------------------------------------------------------------
# chart_service tests
# ---------------------------------------------------------------------------

class TestChartService:
    def test_recommend_charts_normal_flow(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_data(session_factory)

        with session_factory() as session:
            result = chart_service.recommend_charts(task_id, session)

        assert result["task_id"] == task_id
        assert result["total"] >= 1
        assert len(result["charts"]) >= 1
        chart = result["charts"][0]
        assert "chart_type" in chart
        assert "series" in chart

    def test_recommend_charts_idempotent(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_data(session_factory)

        with session_factory() as session:
            r1 = chart_service.recommend_charts(task_id, session)
        with session_factory() as session:
            r2 = chart_service.recommend_charts(task_id, session)

        assert r1["total"] == r2["total"]

    def test_no_chart_single_measure_returns_reason(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_data(
            session_factory,
            kinds=["measure"],
            paths=[["Value"]],
            grid=[
                ["Value"],
                ["1"],
                ["2"],
            ],
        )

        with session_factory() as session:
            result = chart_service.recommend_charts(task_id, session)

        assert result["total"] == 0
        assert len(result["no_chart_reasons"]) >= 1

    def test_charts_are_persisted(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_data(session_factory)

        with session_factory() as session:
            chart_service.recommend_charts(task_id, session)

        with session_factory() as session:
            records = list(
                session.scalars(
                    select(ChartSpecRecordModel).where(
                        ChartSpecRecordModel.task_id == task_id,
                    ),
                ),
            )
            assert len(records) >= 1
            assert records[0].chart_type != ""

    def test_get_chart_specs_returns_persisted(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_data(session_factory)

        with session_factory() as session:
            chart_service.recommend_charts(task_id, session)

        with session_factory() as session:
            result = chart_service.get_chart_specs(task_id, session)

        assert result is not None
        assert result["total"] >= 1
        assert len(result["charts"]) >= 1

    def test_task_status_becomes_chart_ready(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_data(session_factory)

        with session_factory() as session:
            chart_service.recommend_charts(task_id, session)

        with session_factory() as session:
            task = session.scalar(
                select(TaskRecordModel).where(TaskRecordModel.id == task_id),
            )
            assert task is not None
            assert task.status == "chart_ready"

    def test_rejects_non_analyzed_task(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_data(session_factory, status="validated")

        with session_factory() as session:
            with pytest.raises(chart_service.HTTPException, match="409"):
                chart_service.recommend_charts(task_id, session)

    def test_get_chart_specs_returns_none_for_nonexistent(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        with session_factory() as session:
            result = chart_service.get_chart_specs(999, session)
        assert result is None

    def test_with_llm_chart_hints(self, tmp_path):
        session_factory = _override_db_session(
            f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
        )
        task_id = _create_task_with_data(
            session_factory,
            chart_hints=[{
                "chart_type": "bar",
                "title": "Revenue by Region",
                "metrics": ["Revenue", "Cost"],
                "dimension": "Region",
                "reason": "Bar chart best for comparison",
            }],
        )

        with session_factory() as session:
            result = chart_service.recommend_charts(task_id, session)

        assert result["total"] >= 1
        has_bar = any(c["chart_type"] == "bar" for c in result["charts"])
        assert has_bar