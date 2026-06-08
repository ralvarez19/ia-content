"""Modelos Pydantic para jobs."""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class Job(BaseModel):
    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])

    # Input desde el cliente
    title: str
    scene: str
    dialogue: str
    clips_count: int = 6
    duration_seconds: int = 60
    aspect_ratio: str = "9:16"
    generate_voice: bool = True
    generate_video: bool = True
    use_reference_image: bool = False
    voice_id: Optional[str] = None
    style: Optional[str] = None
    music_enabled: bool = False
    has_reference_image: bool = False  # set por el server

    # Estado runtime
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    current_step: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    error: Optional[str] = None
    output_video: Optional[str] = None

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat()


class JobSummary(BaseModel):
    """Versión liviana para listados."""
    job_id: str
    title: str
    status: JobStatus
    progress: int
    created_at: str
    output_video: Optional[str] = None
