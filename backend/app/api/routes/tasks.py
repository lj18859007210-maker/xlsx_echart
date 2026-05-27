from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
def tasks_ping() -> dict[str, str]:
    return {"module": "tasks", "status": "ready"}
