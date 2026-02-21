import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from common.models.base import Base


class TriggerType(str, enum.Enum):
    webhook = "webhook"
    manual = "manual"
    scheduled = "scheduled"


class JobStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class DocType(str, enum.Enum):
    api_reference = "api_reference"
    architecture = "architecture"
    walkthrough = "walkthrough"


class DestinationPlatform(str, enum.Enum):
    confluence = "confluence"
    notion = "notion"


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_url = Column(String(500), nullable=False, unique=True)
    default_branch = Column(String(100), default="main")
    destination_platform = Column(
        Enum(DestinationPlatform), default=DestinationPlatform.confluence, nullable=False
    )
    destination_config = Column(JSON, default=dict)
    config_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    page_mappings = relationship("PageMapping", back_populates="repository", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="repository", cascade="all, delete-orphan")


class PageMapping(Base):
    __tablename__ = "page_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    code_path = Column(String(1000), nullable=False)
    doc_type = Column(Enum(DocType), nullable=False)
    destination_page_id = Column(String(100))
    last_synced_at = Column(DateTime)

    repository = relationship("Repository", back_populates="page_mappings")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    trigger_type = Column(Enum(TriggerType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.pending)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error = Column(Text)

    repository = relationship("Repository", back_populates="jobs")
    logs = relationship("ProcessingLog", back_populates="job", cascade="all, delete-orphan")


class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    step = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="logs")
