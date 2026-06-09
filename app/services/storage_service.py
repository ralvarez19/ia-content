"""Persistencia de jobs en disco. Una carpeta por job, una imagen por escena."""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from app.config import JOBS_DIR
from app.models import Job, JobStatus, JobSummary


def job_dir(job_id: str) -> Path:
    d = JOBS_DIR / job_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "clips").mkdir(parents=True, exist_ok=True)
    (d / "references").mkdir(parents=True, exist_ok=True)
    return d


def job_file(job_id: str) -> Path:
    return job_dir(job_id) / "job.json"


def log_file(job_id: str) -> Path:
    return job_dir(job_id) / "logs.txt"


def scene_reference_path(job_id: str, scene_index: int, ext: str = "png") -> Path:
    """Ruta donde se guarda la imagen referencial de UNA escena (0-based index)."""
    return job_dir(job_id) / "references" / f"scene_{scene_index+1:03d}.{ext}"


def find_scene_reference(job_id: str, scene_index: int) -> Optional[Path]:
    for ext in ("png", "jpg", "jpeg", "webp"):
        p = job_dir(job_id) / "references" / f"scene_{scene_index+1:03d}.{ext}"
        if p.exists():
            return p
    return None


def audio_path(job_id: str) -> Path:
    return job_dir(job_id) / "audio.mp3"


def clip_path(job_id: str, idx: int) -> Path:
    return job_dir(job_id) / "clips" / f"clip_{idx+1:03d}.mp4"


def final_path(job_id: str) -> Path:
    return job_dir(job_id) / "final.mp4"


def save_job(job: Job) -> None:
    job.touch()
    job_file(job.job_id).write_text(
        job.model_dump_json(indent=2), encoding="utf-8"
    )


def load_job(job_id: str) -> Optional[Job]:
    p = job_file(job_id)
    if not p.exists():
        return None
    try:
        return Job.model_validate_json(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_jobs(limit: int = 50) -> List[JobSummary]:
    out: List[JobSummary] = []
    if not JOBS_DIR.exists():
        return out
    folders = sorted(
        [p for p in JOBS_DIR.iterdir() if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    for folder in folders[:limit]:
        job = load_job(folder.name)
        if not job:
            continue
        out.append(JobSummary(
            job_id=job.job_id,
            title=job.title,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at,
            scenes_count=len(job.scenes),
            output_video=job.output_video,
        ))
    return out


def update_status(
    job_id: str,
    status: Optional[JobStatus] = None,
    progress: Optional[int] = None,
    step: Optional[str] = None,
    error: Optional[str] = None,
    output_video: Optional[str] = None,
) -> Optional[Job]:
    job = load_job(job_id)
    if not job:
        return None
    if status is not None:       job.status = status
    if progress is not None:     job.progress = max(0, min(100, progress))
    if step is not None:         job.current_step = step
    if error is not None:        job.error = error
    if output_video is not None: job.output_video = output_video
    save_job(job)
    return job
