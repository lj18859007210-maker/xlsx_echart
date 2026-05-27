from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
def review_ping() -> dict[str, str]:
    return {"module": "review", "status": "ready"}
