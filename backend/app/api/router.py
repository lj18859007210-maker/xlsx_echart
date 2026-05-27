from fastapi import APIRouter

from app.api.routes import files, review, tasks

api_router = APIRouter()
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
api_router.include_router(review.router, prefix="/review", tags=["review"])
