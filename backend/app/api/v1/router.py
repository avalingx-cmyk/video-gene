from fastapi import APIRouter

from app.api.v1.endpoints import generate, jobs, auth, webhook

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(generate.router, prefix="/generate", tags=["generate"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
