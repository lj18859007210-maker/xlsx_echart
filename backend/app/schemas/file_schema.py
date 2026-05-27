from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    file_id: int
    task_id: int
    status: str
