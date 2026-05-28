from pydantic import BaseModel, ConfigDict


class ParsedSheetSummary(BaseModel):
    sheet_id: int
    sheet_name: str
    row_count: int
    col_count: int


class TaskParseResponse(BaseModel):
    task_id: int
    status: str
    sheets: list[ParsedSheetSummary]


class TaskInferFormulaRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

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
