"""Endpoints REST para crear, consultar y descargar jobs."""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile,
)
from fastapi.responses import FileResponse, PlainTextResponse

from app.models import Job, JobCreateResponse, JobStatus, JobSummary
from app.services import job_runner, storage_service as storage

router = APIRouter()


_ALLOWED_IMG = {".png", ".jpg", ".jpeg", ".webp"}


@router.post("/jobs", response_model=JobCreateResponse)
async def create_job(
    background: BackgroundTasks,
    title: str = Form(...),
    scene: str = Form(...),
    dialogue: str = Form(...),
    clips_count: int = Form(6),
    duration_seconds: int = Form(60),
    aspect_ratio: str = Form("9:16"),
    generate_voice: bool = Form(True),
    generate_video: bool = Form(True),
    use_reference_image: bool = Form(False),
    voice_id: Optional[str] = Form(None),
    style: Optional[str] = Form(None),
    music_enabled: bool = Form(False),
    reference_image: Optional[UploadFile] = File(None),
):
    if clips_count < 1 or clips_count > 20:
        raise HTTPException(400, "clips_count debe estar entre 1 y 20")
    if duration_seconds < 5 or duration_seconds > 180:
        raise HTTPException(400, "duration_seconds debe estar entre 5 y 180")

    job = Job(
        title=title.strip() or "Sin título",
        scene=scene.strip(),
        dialogue=dialogue.strip(),
        clips_count=clips_count,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        generate_voice=generate_voice,
        generate_video=generate_video,
        use_reference_image=use_reference_image,
        voice_id=(voice_id or None),
        style=(style or None),
        music_enabled=music_enabled,
    )

    # Guardar imagen referencial si vino
    if reference_image and reference_image.filename:
        ext = Path(reference_image.filename).suffix.lower()
        if ext not in _ALLOWED_IMG:
            raise HTTPException(400, f"Extensión no soportada: {ext}")
        ref_out = storage.reference_path(job.job_id, ext.lstrip("."))
        ref_out.parent.mkdir(parents=True, exist_ok=True)
        data = await reference_image.read()
        ref_out.write_bytes(data)
        job.has_reference_image = True

    storage.save_job(job)
    background.add_task(job_runner.run_job, job.job_id)
    return JobCreateResponse(job_id=job.job_id, status=job.status)


@router.get("/jobs", response_model=List[JobSummary])
def list_jobs(limit: int = 50):
    return storage.list_jobs(limit=limit)


@router.get("/jobs/{job_id}", response_model=Job)
def get_job(job_id: str):
    job = storage.load_job(job_id)
    if not job:
        raise HTTPException(404, "job no encontrado")
    return job


@router.get("/jobs/{job_id}/logs", response_class=PlainTextResponse)
def get_logs(job_id: str):
    if not storage.load_job(job_id):
        raise HTTPException(404, "job no encontrado")
    p = storage.log_file(job_id)
    return p.read_text(encoding="utf-8") if p.exists() else ""


@router.get("/jobs/{job_id}/download")
def download_video(job_id: str):
    job = storage.load_job(job_id)
    if not job:
        raise HTTPException(404, "job no encontrado")
    p = storage.final_path(job_id)
    if not p.exists():
        raise HTTPException(404, "video aún no generado")
    return FileResponse(
        path=str(p),
        media_type="video/mp4",
        filename=f"{(job.title or job.job_id).replace(' ', '_')}.mp4",
    )


@router.get("/jobs/{job_id}/reference")
def get_reference(job_id: str):
    p = storage.find_reference(job_id)
    if not p:
        raise HTTPException(404, "no hay reference image para este job")
    return FileResponse(str(p))
