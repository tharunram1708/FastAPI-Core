from fastapi import APIRouter, Depends

from app.api.dependencies import rate_limit
from app.api.v1.routes import (
    audit,
    auth,
    bulk,
    business,
    csv,
    documents,
    health,
    integrations,
    items,
    jobs,
    notifications,
    search,
    users,
    webhooks,
)


router = APIRouter(dependencies=[Depends(rate_limit)])
router.include_router(auth.router, prefix="/auth", tags=["v1:auth"])
router.include_router(audit.router, prefix="/audit", tags=["v1:audit"])
router.include_router(bulk.router, prefix="/bulk", tags=["v1:bulk"])
router.include_router(business.router, prefix="/business", tags=["v1:business"])
router.include_router(csv.router, prefix="/csv", tags=["v1:csv"])
router.include_router(documents.router, prefix="/documents", tags=["v1:documents"])
router.include_router(health.router, prefix="/health", tags=["v1:health"])
router.include_router(integrations.router, prefix="/integrations", tags=["v1:integrations"])
router.include_router(items.router, prefix="/items", tags=["v1:items"])
router.include_router(jobs.router, prefix="/jobs", tags=["v1:jobs"])
router.include_router(notifications.router, prefix="/notifications", tags=["v1:notifications"])
router.include_router(search.router, prefix="/search", tags=["v1:search"])
router.include_router(users.router, prefix="/users", tags=["v1:users"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["v1:webhooks"])

api_router = router
