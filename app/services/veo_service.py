"""Servicio Veo 3 (Vertex AI) con soporte de image-to-video.

Estrategia de continuidad:
  - Si el usuario subió una imagen referencial → la usamos como primer frame
    del clip 1.
  - Para clips 2..N: extraemos el último frame del clip anterior y lo
    pasamos como primer frame del siguiente.
  - Si falla la generación de un clip, retornamos None y el orquestador
    cae al fallback (pantalla negra) sin tumbar el job.
"""
from __future__ import annotations
import base64
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

import requests

from app.config import (
    GCP_PROJECT, GCP_LOCATION, GCS_BUCKET, VEO_MODEL,
    VEO_CLIP_DURATION, VEO_POLL_INTERVAL, VEO_POLL_MAX,
    is_veo_configured,
)
from app.utils.logger import JobLogger


# ──────────────────────────────────────────────────────────────────────
#  Resolución de ejecutables (gcloud, gsutil, ffmpeg) en Windows
# ──────────────────────────────────────────────────────────────────────
def _resolve_exe(name: str) -> str:
    return shutil.which(name) or shutil.which(f"{name}.cmd") or name


def _get_access_token(logger: JobLogger) -> Optional[str]:
    r = subprocess.run(
        [_resolve_exe("gcloud"), "auth", "print-access-token"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        logger.warn(f"gcloud auth print-access-token falló: {r.stderr[:200]}")
        return None
    return r.stdout.strip()


# ──────────────────────────────────────────────────────────────────────
#  Helpers de imágenes
# ──────────────────────────────────────────────────────────────────────
_IMG_MIME = {
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def _encode_image(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    mime = _IMG_MIME.get(path.suffix.lower(), "image/png")
    b = base64.b64encode(path.read_bytes()).decode("ascii")
    return {"bytesBase64Encoded": b, "mimeType": mime}


def extract_last_frame(video: Path, out_image: Path, logger: JobLogger) -> Optional[Path]:
    """Saca el último frame del clip como PNG. Sirve de anchor para el siguiente."""
    if not video.exists():
        return None
    out_image.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [_resolve_exe("ffmpeg"), "-y", "-sseof", "-0.5", "-i", str(video),
         "-update", "1", "-q:v", "2", str(out_image)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not out_image.exists():
        logger.warn(f"No pude extraer último frame: {r.stderr[:200]}")
        return None
    return out_image


# ──────────────────────────────────────────────────────────────────────
#  Llamada Veo
# ──────────────────────────────────────────────────────────────────────
def generate_clip(
    prompt: str,
    out_path: Path,
    logger: JobLogger,
    seed_image: Optional[Path] = None,
    duration_seconds: int = VEO_CLIP_DURATION,
    aspect_ratio: str = "9:16",
) -> Optional[Path]:
    """Genera un clip Veo. Devuelve la ruta local si tuvo éxito, None si no."""
    if not is_veo_configured():
        logger.warn("Veo no configurado (falta GCP_PROJECT o GCS_BUCKET)")
        return None

    token = _get_access_token(logger)
    if not token:
        return None

    base = (
        f"https://{GCP_LOCATION}-aiplatform.googleapis.com/v1/"
        f"projects/{GCP_PROJECT}/locations/{GCP_LOCATION}/"
        f"publishers/google/models/{VEO_MODEL}"
    )

    instance: dict = {"prompt": prompt}
    if seed_image:
        img = _encode_image(seed_image)
        if img:
            instance["image"] = img
            logger.info(f"Veo: usando seed_image ({seed_image.name})")
        else:
            logger.warn(f"Seed image no encodeable: {seed_image}")

    payload = {
        "instances": [instance],
        "parameters": {
            "durationSeconds": int(duration_seconds),
            "aspectRatio": aspect_ratio,
            "sampleCount": 1,
            "storageUri": GCS_BUCKET,
            "generateAudio": False,
        },
    }

    try:
        r = requests.post(
            f"{base}:predictLongRunning",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json=payload, timeout=30,
        )
    except Exception as e:
        logger.warn(f"Veo POST excepción: {e}")
        return None

    if r.status_code != 200:
        logger.warn(f"Veo error {r.status_code}: {r.text[:300]}")
        return None

    op_name = r.json().get("name")
    if not op_name:
        logger.warn("Veo no devolvió operation name")
        return None

    logger.info(f"Veo operation: {op_name.split('/')[-1]} (esperando...)")

    for attempt in range(VEO_POLL_MAX):
        time.sleep(VEO_POLL_INTERVAL)
        try:
            poll = requests.post(
                f"{base}:fetchPredictOperation",
                headers={"Authorization": f"Bearer {token}",
                         "Content-Type": "application/json"},
                json={"operationName": op_name},
                timeout=20,
            ).json()
        except Exception as e:
            logger.warn(f"Veo poll excepción: {e}")
            continue

        if poll.get("error"):
            logger.warn(f"Veo error en operación: {poll['error']}")
            return None

        if not poll.get("done"):
            continue

        # Algunas respuestas usan response.videos[], otras response.generatedSamples[]
        resp = poll.get("response", {})
        videos = resp.get("videos") or resp.get("generatedSamples") or []
        if not videos:
            preds = resp.get("predictions", [])
            if preds:
                videos = preds
        if not videos:
            logger.warn(f"Veo respuesta sin videos: {str(resp)[:300]}")
            return None

        v0 = videos[0]
        uri = (v0.get("gcsUri")
               or v0.get("video", {}).get("uri")
               or v0.get("uri", ""))
        if not uri:
            logger.warn(f"Veo sin URI en {str(v0)[:200]}")
            return None

        out_path.parent.mkdir(parents=True, exist_ok=True)
        cp = subprocess.run(
            [_resolve_exe("gsutil"), "cp", uri, str(out_path)],
            capture_output=True, text=True,
        )
        if cp.returncode != 0:
            logger.warn(f"gsutil cp falló: {cp.stderr[:200]}")
            return None
        return out_path

    logger.warn("Veo timeout (6 min sin done=true)")
    return None


# ──────────────────────────────────────────────────────────────────────
#  Fallback: pantalla negra
# ──────────────────────────────────────────────────────────────────────
def generate_black_clip(
    out_path: Path,
    duration: float,
    logger: JobLogger,
    aspect_ratio: str = "9:16",
) -> Path:
    w, h = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        [_resolve_exe("ffmpeg"), "-y",
         "-f", "lavfi", "-i", f"color=c=black:s={w}x{h}:r=30:d={duration}",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
         str(out_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        logger.error(f"No pude generar clip negro: {r.stderr[:200]}")
    return out_path
