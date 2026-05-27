from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.file_schema import FileUploadResponse
from app.services.file_upload_service import create_upload_records

router = APIRouter()


@router.get("/ping")
def files_ping() -> dict[str, str]:
    return {"module": "files", "status": "ready"}


@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> FileUploadResponse:
    payload = await create_upload_records(db, file)
    return FileUploadResponse(**payload)
