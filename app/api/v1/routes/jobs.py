from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select

from app.api.dependencies import CurrentUserDep, DatabaseSessionDep, require_roles
from app.core.authorization import Role
from app.schemas.enterprise import JobRunResponse


router = APIRouter()


@router.post("/cleanup", response_model=JobRunResponse, summary="Run cleanup job")
async def run_cleanup_job(
    background_tasks: BackgroundTasks,
    db: DatabaseSessionDep,
    current_user: CurrentUserDep,
    _role: Annotated[object, Depends(require_roles(Role.ADMIN, Role.MANAGER))],
) -> JobRunResponse:
    result = db.enterprise.cleanup_expired_security_records()
    model = db.enterprise.scheduled_jobs.model
    existing = db.enterprise.session.scalar(select(model).where(model.name == "cleanup"))
    if existing is None:
        db.enterprise.scheduled_jobs.create(
            {
                "name": "cleanup",
                "last_run_at": datetime.now(timezone.utc),
                "next_run_at": datetime.now(timezone.utc) + timedelta(days=1),
                "result": result,
            }
        )
    else:
        existing.last_run_at = datetime.now(timezone.utc)
        existing.next_run_at = datetime.now(timezone.utc) + timedelta(days=1)
        existing.result = result
    db.enterprise.create_audit_log(
        actor_id=current_user.id,
        action="RUN_CLEANUP_JOB",
        resource_type="scheduled_job",
        resource_id="cleanup",
    )
    background_tasks.add_task(lambda: None)
    return JobRunResponse(name="cleanup", result=result, ran_at=datetime.now(timezone.utc))


@router.get("", response_model=list[JobRunResponse], summary="List scheduled jobs")
async def list_jobs(
    db: DatabaseSessionDep,
    _role: Annotated[object, Depends(require_roles(Role.ADMIN, Role.MANAGER))],
) -> list[JobRunResponse]:
    jobs = db.enterprise.scheduled_jobs.list(limit=100)
    return [
        JobRunResponse(
            name=job.name,
            result=job.result,
            ran_at=job.last_run_at or job.created_at,
        )
        for job in jobs
    ]
