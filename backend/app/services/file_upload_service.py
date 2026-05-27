from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models.file_record import FileRecordModel
from app.db.models.task_record import TaskRecordModel


def _validate_upload(file: UploadFile, content: bytes) -> None:
    suffix = Path(file.filename or "").suffix.lower()

    if suffix != ".xlsx":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .xlsx files are supported",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )


def _build_storage_path(original_filename: str) -> Path:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(original_filename).suffix.lower()

    return upload_dir / f"{uuid4().hex}{suffix}"


async def create_upload_records(db: Session, file: UploadFile) -> dict[str, int | str]:
    contents = await file.read()
    _validate_upload(file, contents)

    storage_path = _build_storage_path(file.filename or "upload.xlsx")
    storage_path.write_bytes(contents)

    file_record = FileRecordModel(
        file_name=file.filename or storage_path.name,
        file_path=str(storage_path),
        file_type=storage_path.suffix.lower(),
    )
    db.add(file_record)
    db.flush()

    task_record = TaskRecordModel(
        file_id=file_record.id,
        status="uploaded",
    )
    db.add(task_record)
    db.commit()
    db.refresh(file_record)
    db.refresh(task_record)

    return {
        "file_id": file_record.id,
        "task_id": task_record.id,
        "status": task_record.status,
    }
