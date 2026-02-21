from datetime import datetime
from typing import Optional

from pydantic import BaseModel, HttpUrl

from common.models.tables import DocType, JobStatus, TriggerType


# --- Repository ---

class RepositoryCreate(BaseModel):
    github_url: str
    default_branch: str = "main"
    confluence_space_key: Optional[str] = None
    config_json: dict = {}


class RepositoryUpdate(BaseModel):
    default_branch: Optional[str] = None
    confluence_space_key: Optional[str] = None
    config_json: Optional[dict] = None


class RepositoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    github_url: str
    default_branch: str
    confluence_space_key: Optional[str]
    config_json: dict
    created_at: datetime


# --- Job ---

class JobCreate(BaseModel):
    repo_id: int
    trigger_type: TriggerType = TriggerType.manual


class JobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    repo_id: int
    trigger_type: TriggerType
    status: JobStatus
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]


# --- PageMapping ---

class PageMappingResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    repo_id: int
    code_path: str
    doc_type: DocType
    confluence_page_id: Optional[str]
    last_synced_at: Optional[datetime]


# --- Processing Log ---

class ProcessingLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    job_id: int
    step: str
    message: str
    created_at: datetime


# --- Job Payload (for Redis queue) ---

class JobPayload(BaseModel):
    job_id: int
    repo_id: int
    github_url: str
    branch: str
    changed_files: list[str] = []
    trigger_type: TriggerType
    confluence_space_key: Optional[str] = None
