"""End-to-end demo: full pipeline with real data."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from app.db.base import Base
from app.db.models.file_record import FileRecordModel
from app.db.models.task_record import TaskRecordModel
from app.db.models.sheet_record import SheetRecordModel
from app.db.models.structure_version_record import StructureVersionRecordModel
from app.db.models.formula_rule_record import FormulaRuleRecordModel
from app.services.excel_parse_service import parse_task_workbook
from app.services.review_service import build_task_review
from app.services.validation import validation_service
from app.services.anomaly import anomaly_service
from app.services.summarize import summarize_service

BACKEND_DIR = os.path.dirname(__file__)
EXCEL_PATH = os.path.join(BACKEND_DIR, "demo_data.xlsx")
DB_PATH = os.path.join(BACKEND_DIR, "demo.db")

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

engine = create_engine(f"sqlite:///{DB_PATH}", future=True, connect_args={"check_same_thread": False})
@event.listens_for(engine, "connect")
def _pragma(dbapi_conn, _rec):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")
Base.metadata.create_all(bind=engine)
SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def p(title, data, max_str=1200):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    if len(text) > max_str:
        print(text[:max_str] + f"\n... ({len(text)} chars total, truncated)")
    else:
        print(text)

# ── 1. CREATE TASK + DATA DIRECTLY ──
with SessionFactory() as s:
    f = FileRecordModel(file_name="demo_data.xlsx", file_path=EXCEL_PATH, file_type=".xlsx")
    s.add(f); s.flush()
    t = TaskRecordModel(file_id=f.id, status="confirmed")
    s.add(t); s.flush()

    # Manually create sheet with correct column_kinds
    sheet = SheetRecordModel(
        task_id=t.id, sheet_name="P&L", sheet_index=0,
        row_count=6, col_count=4, is_hidden=False,
    )
    s.add(sheet); s.flush()

    # The actual data grid
    aligned_grid = [
        ["Region",   "Revenue", "Cost", "Profit"],
        ["East",     "100",     "80",   "20"],
        ["West",     "90",      "70",   "25"],
        ["North",    "120",     "95",   "25"],
        ["South",    "80",      "60",   "15"],
        ["Total",    "390",     "305",  "85"],
    ]
    column_paths = [["Region"], ["Revenue"], ["Cost"], ["Profit"]]
    column_kinds = ["dimension", "measure", "measure", "measure"]

    cell_roles = [column_kinds[:] for _ in aligned_grid]

    sv = StructureVersionRecordModel(
        task_id=t.id, version_number=1,
        snapshot_json={
            "sheets": [{
                "sheet_id": sheet.id, "sheet_name": "P&L", "sheet_index": 0,
                "row_count": 6, "col_count": 4, "is_hidden": False,
                "merge_ranges": [], "aligned_grid": aligned_grid,
                "aligned_cell_roles": cell_roles, "aligned_source_map": [],
                "cell_tags": [], "column_paths": column_paths,
                "column_kinds": column_kinds,
            }]
        },
        patch_summary_json={}, is_confirmed=True,
    )
    s.add(sv); s.flush()

    # Formula rules
    s.add(FormulaRuleRecordModel(
        task_id=t.id, sheet_id=sheet.id,
        formula_text="col_Profit = col_Revenue - col_Cost",
        formula_type="column_arithmetic",
        description="Profit = Revenue - Cost",
        confidence=0.92, verification_passed=True, verification_score=0.92,
        prompt_version="demo", model_name="mock/demo",
    ))
    s.add(FormulaRuleRecordModel(
        task_id=t.id, sheet_id=sheet.id,
        formula_text="row_Total = sum(row_1:row_4)",
        formula_type="row_aggregation",
        description="Total = sum of 4 regions",
        confidence=0.85, verification_passed=True, verification_score=0.85,
        prompt_version="demo", model_name="mock/demo",
    ))
    s.commit()
    task_id = t.id

p("1. INPUT DATA", {
    "task_id": task_id,
    "status": "confirmed",
    "grid": aligned_grid,
    "column_kinds": column_kinds,
    "formulas": [
        "col_Profit = col_Revenue - col_Cost (conf=0.92)",
        "row_Total = sum(row_1:row_4) (conf=0.85)",
    ],
})

# ── 2. VALIDATE ──
with SessionFactory() as s:
    result = validation_service.validate_task_formulas(task_id, s)
p("2. VALIDATE - Formula math verification", {
    "total_issues": result["total_issues"],
    "errors": result["error_count"],
    "warnings": result["warning_count"],
    "issues": result["issues"],
})

# ── 3. ANOMALIES ──
with SessionFactory() as s:
    result = anomaly_service.detect_task_anomalies(task_id, s)
p("3. ANOMALIES - Business rule detection", {
    "mode": result["detection_mode"],
    "total": result["anomaly_issue_count"],
    "rule_hits": result["rule_hits"],
    "stat_hits": result["stat_hits"],
    "issues": result["issues"],
})

# ── 4. SUMMARIZE ──
with SessionFactory() as s:
    result = summarize_service.summarize_task(task_id, s)
p("4. SUMMARIZE - AI context package", {
    "token": f"{result['token_estimate']}/{result['token_budget']}",
    "trimmed": result["trimmed"],
    "stats": result["statistical_summary"],
    "val_summary": result["validation_issues_summary"],
    "anom_summary": result["anomaly_summary"],
    "slices": result["slices"],
    "schema": result["semantic_schema"],
}, max_str=2500)

print(f"\n{'='*60}")
print(f"  END-TO-END PIPELINE DONE")
print(f"  task_id = {task_id}  |  DB = demo.db")
print(f"{'='*60}")