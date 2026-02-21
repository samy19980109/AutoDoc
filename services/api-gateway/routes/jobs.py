"""Job management routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from common.models import (
    Job,
    JobResponse,
    JobStatus,
    ProcessingLog,
    ProcessingLogResponse,
    get_db,
)
from ..auth.dependencies import verify_api_key

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/", response_model=list[JobResponse])
def list_jobs(
    repo_id: Optional[int] = Query(None, description="Filter by repository ID"),
    status_filter: Optional[JobStatus] = Query(None, alias="status", description="Filter by job status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """List jobs with optional filtering by repo_id and status."""
    query = db.query(Job)

    if repo_id is not None:
        query = query.filter(Job.repo_id == repo_id)
    if status_filter is not None:
        query = query.filter(Job.status == status_filter)

    query = query.order_by(Job.id.desc())
    jobs = query.offset(skip).limit(limit).all()
    return jobs


@router.get("/{job_id}", response_model=JobResponse)
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """Get details of a single job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/{job_id}/logs", response_model=list[ProcessingLogResponse])
def get_job_logs(
    job_id: int,
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """Get processing logs for a specific job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    logs = (
        db.query(ProcessingLog)
        .filter(ProcessingLog.job_id == job_id)
        .order_by(ProcessingLog.created_at.asc())
        .all()
    )
    return logs
