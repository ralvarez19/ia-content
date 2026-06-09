"""Endpoints REST.

POST /jobs ahora acepta:
  - title, duration, etc. como Form
  - scenes: JSON con lista de escenas
  - scene_image_<idx>: UN UploadFile por escena que tenga imagen (idx 0-based)

Ejemplo de scenes JSON:
[
  {"scene_number": 1, "scene_description": "Templo griego al atardecer",
   "dialogue": "Zeus alzó su rayo..."},
  {"scene_number": 2, "scene_description": "El monte Olimpo",
   "dialogue": "Los dioses temblaron..."}
]
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter, BackgroundTasks, File, Form, HTTPException, Request, UploadFile,
)
from fastapi.responses import FileResponse, PlainTextResponse

from app.models import Job, JobCreateResponse, JobStatus, JobSummary, Scene
from app.services import job_runner, storage_service as storage

router = APIRouter()


_ALLOWED_IMG = {".png", ".jpg", ".jpeg", ".webp"}


@router.post("/jobs", response_model=JobCreateResponse)
async def create_job(
    request: Request,
    background: BackgroundTasks,
):
    """Crea un job multi-escena.

    Espera form-data con campos:
      - title (str, requerido)
      - scenes (str JSON, requerido)
      - duration_seconds (int, default 60)
      - aspect_ratio (str, default 9:16)
      - generate_voice (bool, default true)
      - generate_video (bool, default true)
      - voice_id (str opcional)
      - style (str opcional)
      - music_enabled (bool, default false)
      - scene_image_0, scene_image_1, ... (archivos opcionales)
    """
    form = await request.form()

    def get_str(name: str, default: str = "") -> str:
        v = form.get(name)
        return str(v) if v is not None else default

    def get_bool(name: str, default: bool = False) -> bool:
        v = form.get(name)
        if v is None:
            return default
        return str(v).lower() in ("true", "1", "yes", "on")

    def get_int(name: str, default: int) -> int:
        try:
            return int(form.get(name, default))
        except Exception:
            return default

    title = get_str("title").strip()
    if not title:
        raise HTTPException(400, "title es requerido")

    scenes_raw = get_str("scenes").strip()
    if not scenes_raw:
        raise HTTPException(400, "scenes (JSON) es requerido")

    try:
        scenes_data = json.loads(scenes_raw)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"scenes JSON inválido: {e}")

    if not isinstance(scenes_data, list) or not scenes_data:
        raise HTTPException(400, "scenes debe ser una lista no vacía")
    if len(scenes_data) > 20:
        raise HTTPException(400, "máximo 20 escenas")

    scenes: List[Scene] = []
    for i, raw in enumerate(scenes_data):
        if not isinstance(raw, dict):
            raise HTTPException(400, f"escena {i} no es objeto")
        desc = str(raw.get("scene_description", "")).strip()
        dlg = str(raw.get("dialogue", "")).strip()
        if not desc:
            raise HTTPException(400, f"escena {i+1}: scene_description vacío")
        if not dlg:
            raise HTTPException(400, f"escena {i+1}: dialogue vacío")
        scenes.append(Scene(
            scene_number=int(raw.get("scene_number", i + 1)),
            scene_description=desc,
            dialogue=dlg,
        ))

    duration_seconds = get_int("duration_seconds", 60)
    if duration_seconds < 5 or duration_seconds > 240:
        raise HTTPException(400, "duration_seconds debe estar entre 5 y 240")

    job = Job(
        title=title,
        scenes=scenes,
        duration_seconds=duration_seconds,
        aspect_ratio=get_str("aspect_ratio", "9:16"),
        generate_voice=get_bool("generate_voice", True),
        generate_video=get_bool("generate_video", True),
        voice_id=(get_str("voice_id") or None),
        style=(get_str("style") or None),
        music_enabled=get_bool("music_enabled", False),
    )

    # Guardar imágenes por escena
    for i, sc in enumerate(scenes):
        uploaded = form.get(f"scene_image_{i}")
        if uploaded is None or not hasattr(uploaded, "filename"):
            continue
        filename = (uploaded.filename or "").lower()
        ext = Path(filename).suffix.lower()
        if ext not in _ALLOWED_IMG:
            raise HTTPException(
                400, f"scene_image_{i}: extensión no soportada ({ext})"
            )
        out = storage.scene_reference_path(job.job_id, i, ext.lstrip("."))
        out.parent.mkdir(parents=True, exist_ok=True)
        data = await uploaded.read()
        out.write_bytes(data)
        sc.has_reference_image = True

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


@router.get("/jobs/{job_id}/scene_image/{scene_index}")
def get_scene_image(job_id: str, scene_index: int):
    p = storage.find_scene_reference(job_id, scene_index)
    if not p:
        raise HTTPException(404, "sin imagen para esa escena")
    return FileResponse(str(p))
