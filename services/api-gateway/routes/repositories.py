"""Repository CRUD routes."""

from typing import Optional

from celery import Celery
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from common.config import get_settings
from common.models import (
    Job,
    JobCreate,
    JobPayload,
    JobResponse,
    JobStatus,
    Repository,
    RepositoryCreate,
    RepositoryResponse,
    RepositoryUpdate,
    TriggerType,
    get_db,
)
from ..auth.dependencies import verify_api_key

router = APIRouter(prefix="/api/repos", tags=["repositories"])

settings = get_settings()
celery_app = Celery(broker=settings.celery_broker_url)


@router.get("/", response_model=list[RepositoryResponse])
def list_repositories(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """List all registered repositories with pagination."""
    repos = db.query(Repository).offset(skip).limit(limit).all()
    return repos


@router.post("/", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
def create_repository(
    body: RepositoryCreate,
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """Register a new repository for documentation generation."""
    existing = db.query(Repository).filter(Repository.github_url == body.github_url).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository with URL '{body.github_url}' already exists",
        )
    repo = Repository(
        github_url=body.github_url,
        default_branch=body.default_branch,
        confluence_space_key=body.confluence_space_key,
        config_json=body.config_json,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


@router.get("/{repo_id}", response_model=RepositoryResponse)
def get_repository(
    repo_id: int,
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """Get a single repository by ID."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return repo


@router.put("/{repo_id}", response_model=RepositoryResponse)
def update_repository(
    repo_id: int,
    body: RepositoryUpdate,
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """Update an existing repository."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(repo, field, value)

    db.commit()
    db.refresh(repo)
    return repo


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_repository(
    repo_id: int,
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """Delete a repository and all associated data."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    db.delete(repo)
    db.commit()


@router.post("/{repo_id}/trigger", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_documentation(
    repo_id: int,
    trigger_type: TriggerType = TriggerType.manual,
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """Trigger documentation generation for a repository.

    Creates a new Job in 'pending' state and enqueues a Celery task.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    job = Job(repo_id=repo.id, trigger_type=trigger_type, status=JobStatus.pending)
    db.add(job)
    db.commit()
    db.refresh(job)

    payload = JobPayload(
        job_id=job.id,
        repo_id=repo.id,
        github_url=repo.github_url,
        branch=repo.default_branch,
        trigger_type=trigger_type,
        confluence_space_key=repo.confluence_space_key,
    )

    celery_app.send_task("process_documentation", args=[payload.model_dump_json()])

    return job
