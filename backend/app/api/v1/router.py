from fastapi import APIRouter

from app.api.v1.endpoints import generate, jobs, auth, webhook, projects, segments, licenses, bgm, audit, retention, music_mixer, overlays

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(generate.router, prefix="/generate", tags=["generate"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(segments.router, prefix="/segments", tags=["segments"])
router.include_router(licenses.router, prefix="/licenses", tags=["licenses"])
router.include_router(bgm.router, prefix="/bgm", tags=["bgm"])
router.include_router(audit.router, prefix="/audit", tags=["audit"])
router.include_router(retention.router, prefix="/admin/retention", tags=["retention"])
router.include_router(music_mixer.router, prefix="/music-mixer", tags=["music-mixer"])
router.include_router(overlays.router, prefix="/projects/{project_id}/segments/{segment_id}/overlays", tags=["overlays"])
