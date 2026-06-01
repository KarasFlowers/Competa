from fastapi import APIRouter

from app.api.sse import router as sse_router
from app.api.tasks import router as tasks_router
from app.api.reports import router as reports_router
from app.api.traces import router as traces_router
from app.demo.routes import router as demo_router

api_router = APIRouter()


@api_router.get("/health")
async def health():
    return {"status": "ok"}


api_router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
api_router.include_router(reports_router, prefix="/tasks", tags=["reports"])
api_router.include_router(traces_router, prefix="/tasks", tags=["traces"])
api_router.include_router(sse_router, prefix="/tasks", tags=["sse"])
api_router.include_router(demo_router, prefix="/demos", tags=["demos"])
