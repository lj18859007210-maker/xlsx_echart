"""Complex demo: multi-sheet, 35+ rows, mixed anomalies, Chinese headers."""
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
from app.services.validation import validation_service
from app.services.anomaly import anomaly_service
from app.services.summarize import summarize_service

BACKEND_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BACKEND_DIR, "demo_complex.db")
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

engine = create_engine(f"sqlite:///{DB_PATH}", future=True, connect_args={"check_same_thread": False})
@event.listens_for(engine, "connect")
def _pragma(dbapi_conn, _rec):
    dbapi_conn.execute("PRAGMA foreign_keys=ON")
Base.metadata.create_all(bind=engine)
SF = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def p(title, data, max_str=1500):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    if len(text) > max_str:
        print(text[:max_str] + f"\n... ({len(text)} chars)")

# ── BUILD COMPLEX DATA ──
with SF() as s:
    f = FileRecordModel(file_name="complex.xlsx", file_path="complex.xlsx", file_type=".xlsx")
    s.add(f); s.flush()
    t = TaskRecordModel(file_id=f.id, status="confirmed")
    s.add(t); s.flush()

    # Sheet 1: 销售明细 (35 rows of data)
    sheet1 = SheetRecordModel(task_id=t.id, sheet_name="销售明细", sheet_index=0, row_count=37, col_count=6, is_hidden=False)
    s.add(sheet1); s.flush()

    # Header: 月份, 销售额, 成本, 利润, 费用, 净利润
    g1 = [["月份", "销售额", "成本", "利润", "费用", "净利润"]]
    # 30 rows of normal data with slight variation
    for m in range(1, 32):
        rev = 5000 + m * 120 + (m % 7) * 50   # 5000-9000 range
        cost = int(rev * 0.55 + (m % 5) * 30)  # ~55% of revenue
        exp = 800 + m * 10
        profit = rev - cost                     # should match
        net = profit - exp
        g1.append([f"{m}月", str(rev), str(cost), str(profit), str(exp), str(net)])

    # Row 32: negative profit (anomaly!)
    g1.append(["32月", "8500", "7800", "700", "900", "-200"])  # net = 700-900 = -200 (negative!)
    # Row 33: formula mismatch (profit should be 9000-5000=4000 but we put 3500)
    g1.append(["33月", "9000", "5000", "3500", "950", "2550"])  # profit mismatch!
    # Row 34: huge revenue spike (IQR outlier!)
    g1.append(["34月", "50000", "25000", "25000", "1200", "23800"])  # massive outlier
    # Row 35: division by zero edge case (cost=0)
    g1.append(["35月", "6000", "0", "6000", "850", "5150"])
    # Row 36: another mismatch
    g1.append(["36月", "7200", "4000", "3000", "900", "2100"])  # profit should be 3200

    cp1 = [["月份"], ["销售额"], ["成本"], ["利润"], ["费用"], ["净利润"]]
    ck1 = ["dimension", "measure", "measure", "measure", "measure", "measure"]

    # Sheet 2: 成本分析 (smaller, different structure)
    sheet2 = SheetRecordModel(task_id=t.id, sheet_name="成本分析", sheet_index=1, row_count=6, col_count=4, is_hidden=False)
    s.add(sheet2); s.flush()

    g2 = [
        ["类别", "Q1", "Q2", "Q3"],
        ["原材料", "15000", "14000", "13000",],   # 3 consecutive declines!
        ["人工", "8000", "8200", "8100"],
        ["运输", "3000", "3100", "3200"],
        ["其他", "2000", "2100", "2200"],
    ]
    cp2 = [["类别"], ["Q1"], ["Q2"], ["Q3"]]
    ck2 = ["dimension", "measure", "measure", "measure"]

    sv = StructureVersionRecordModel(
        task_id=t.id, version_number=1,
        snapshot_json={
            "sheets": [
                {"sheet_id": sheet1.id, "sheet_name": "销售明细", "sheet_index": 0,
                 "row_count": 37, "col_count": 6, "is_hidden": False,
                 "merge_ranges": [], "aligned_grid": g1,
                 "aligned_cell_roles": [ck1[:] for _ in g1],
                 "aligned_source_map": [], "cell_tags": [],
                 "column_paths": cp1, "column_kinds": ck1},
                {"sheet_id": sheet2.id, "sheet_name": "成本分析", "sheet_index": 1,
                 "row_count": 6, "col_count": 4, "is_hidden": False,
                 "merge_ranges": [], "aligned_grid": g2,
                 "aligned_cell_roles": [ck2[:] for _ in g2],
                 "aligned_source_map": [], "cell_tags": [],
                 "column_paths": cp2, "column_kinds": ck2},
            ]
        },
        patch_summary_json={}, is_confirmed=True,
    )
    s.add(sv); s.flush()

    # Formulas for sheet 1
    s.add(FormulaRuleRecordModel(
        task_id=t.id, sheet_id=sheet1.id,
        formula_text="col_利润 = col_销售额 - col_成本",
        formula_type="column_arithmetic",
        description="利润 = 销售额 - 成本",
        confidence=0.95, verification_passed=True, verification_score=0.95,
        prompt_version="demo", model_name="mock/complex",
    ))
    s.add(FormulaRuleRecordModel(
        task_id=t.id, sheet_id=sheet1.id,
        formula_text="col_净利润 = col_利润 - col_费用",
        formula_type="column_arithmetic",
        description="净利润 = 利润 - 费用",
        confidence=0.93, verification_passed=True, verification_score=0.93,
        prompt_version="demo", model_name="mock/complex",
    ))
    # Formula for sheet 2
    s.add(FormulaRuleRecordModel(
        task_id=t.id, sheet_id=sheet2.id,
        formula_text="row_Q1 = sum(row_1:row_4)",
        formula_type="row_aggregation",
        description="Q1合计 = 原材料+人工+运输+其他",
        confidence=0.80, verification_passed=True, verification_score=0.80,
        prompt_version="demo", model_name="mock/complex",
    ))

    s.commit()
    task_id = t.id

p("INPUT: 2 Sheets, 36+5 rows, Chinese headers", {
    "task_id": task_id,
    "sheets": [
        {"name": "销售明细", "rows": 37, "cols": 6, "preview_head": g1[0], "preview_tail": g1[-5:]},
        {"name": "成本分析", "rows": 5, "cols": 4, "data": g2},
    ],
    "formulas": [
        "Sheet1: col_利润 = col_销售额 - col_成本",
        "Sheet1: col_净利润 = col_利润 - col_费用",
        "Sheet2: row_Q1 = sum(row_1:row_4)",
    ]
}, max_str=2000)

# ── VALIDATE ──
with SF() as s:
    r = validation_service.validate_task_formulas(task_id, s)
p("VALIDATE: 逐行数学验算", {
    "total": r["total_issues"],
    "errors": r["error_count"],
    "warnings": r["warning_count"],
    "breakdown": {it: sum(1 for i in r["issues"] if i["issue_type"]==it) for it in set(i["issue_type"] for i in r["issues"])},
    "sample": r["issues"],
}, max_str=2000)

# ── ANOMALIES ──
with SF() as s:
    r = anomaly_service.detect_task_anomalies(task_id, s)
p(f"ANOMALIES: mode={r['detection_mode']} (N>=30 -> IQR enabled)", {
    "total": r["anomaly_issue_count"],
    "rule_hits": r["rule_hits"],
    "stat_hits": r["stat_hits"],
    "by_type": {it: sum(1 for i in r["issues"] if i["issue_type"]==it) for it in sorted(set(i["issue_type"] for i in r["issues"]))},
    "sample": [i for i in r["issues"] if i["issue_type"] != "growth_rate_anomaly"][:8],
    "growth_rate_count": sum(1 for i in r["issues"] if i["issue_type"]=="growth_rate_anomaly"),
}, max_str=2000)

# ── SUMMARIZE ──
with SF() as s:
    r = summarize_service.summarize_task(task_id, s)
p("SUMMARIZE: AI-ready package", {
    "tokens": f"{r['token_estimate']}/{r['token_budget']}",
    "trimmed": r["trimmed"],
    "sheets_summarized": len(r["statistical_summary"]),
    "sheet1_stats": r["statistical_summary"][0]["columns"][1:],  # skip dimension
    "sheet2_stats": r["statistical_summary"][1]["columns"],
    "slices_count": len(r["slices"]),
    "first_slice": r["slices"][0] if r["slices"] else None,
}, max_str=2000)

print(f"\n{'='*60}")
print(f"  COMPLEX DEMO DONE - task_id={task_id}")
print(f"  DB: {DB_PATH}")
print(f"{'='*60}")