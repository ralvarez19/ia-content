"""Modelos Pydantic para jobs.

Cada job ahora se compone de N escenas, una por clip. Cada escena trae su
propia descripción, su diálogo y opcionalmente su propia imagen referencial.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Scene(BaseModel):
    scene_number: int                  # 1-based
    scene_description: str             # qué se ve en esta escena
    dialogue: str                      # texto que se va a narrar mientras corre
    has_reference_image: bool = False  # marcado por el server cuando se sube


class JobCreateResponse(BaseModel):
    job_id: str
    status: JobStatus


class Job(BaseModel):
    job_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])

    # Input desde el cliente
    title: str
    scenes: List[Scene]
    duration_seconds: int = 60
    aspect_ratio: str = "9:16"
    generate_voice: bool = True
    generate_video: bool = True
    voice_id: Optional[str] = None
    style: Optional[str] = None
    music_enabled: bool = False

    # Estado runtime
    status: JobStatus = JobStatus.QUEUED
    progress: int = 0
    current_step: str = ""
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    error: Optional[str] = None
    output_video: Optional[str] = None

    @property
    def clips_count(self) -> int:
        return len(self.scenes)

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat()


class JobSummary(BaseModel):
    job_id: str
    title: str
    status: JobStatus
    progress: int
    created_at: str
    scenes_count: int
    output_video: Optional[str] = None
