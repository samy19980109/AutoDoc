"""Page mapping routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from common.models import PageMapping, PageMappingResponse, get_db
from ..auth.dependencies import verify_api_key

router = APIRouter(prefix="/api/mappings", tags=["mappings"])


@router.get("/", response_model=list[PageMappingResponse])
def list_mappings(
    repo_id: Optional[int] = Query(None, description="Filter by repository ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """List page mappings with optional filtering by repo_id."""
    query = db.query(PageMapping)

    if repo_id is not None:
        query = query.filter(PageMapping.repo_id == repo_id)

    mappings = query.offset(skip).limit(limit).all()
    return mappings


@router.get("/{mapping_id}", response_model=PageMappingResponse)
def get_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """Get a single page mapping by ID."""
    mapping = db.query(PageMapping).filter(PageMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page mapping not found")
    return mapping


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mapping(
    mapping_id: int,
    db: Session = Depends(get_db),
    _identity: str = Depends(verify_api_key),
):
    """Delete a page mapping."""
    mapping = db.query(PageMapping).filter(PageMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Page mapping not found")

    db.delete(mapping)
    db.commit()
