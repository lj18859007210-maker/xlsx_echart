from pydantic import BaseModel


class ParsedSheetSummary(BaseModel):
    sheet_id: int
    sheet_name: str
    row_count: int
    col_count: int


class TaskParseResponse(BaseModel):
    task_id: int
    status: str
    sheets: list[ParsedSheetSummary]
