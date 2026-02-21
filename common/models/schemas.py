from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from common.models.tables import DestinationPlatform, DocType, JobStatus, TriggerType


# --- Repository ---

class RepositoryCreate(BaseModel):
    github_url: str
    default_branch: str = "main"
    destination_platform: DestinationPlatform = DestinationPlatform.confluence
    destination_config: dict = {}
    config_json: dict = {}


class RepositoryUpdate(BaseModel):
    default_branch: Optional[str] = None
    destination_platform: Optional[DestinationPlatform] = None
    destination_config: Optional[dict] = None
    config_json: Optional[dict] = None


class RepositoryResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    github_url: str
    default_branch: str
    destination_platform: DestinationPlatform
    destination_config: dict
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
    destination_page_id: Optional[str]
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
    destination_platform: DestinationPlatform = DestinationPlatform.confluence
    destination_config: dict = {}


# --- Sync Request/Response (shared between doc-processor and doc-sync) ---

class SyncRequest(BaseModel):
    repo_id: int
    code_path: str
    doc_type: DocType
    content: str
    title: Optional[str] = None
    destination_platform: DestinationPlatform = DestinationPlatform.confluence
    destination_config: dict = {}


class SyncResponse(BaseModel):
    destination_page_id: str
    page_url: str
