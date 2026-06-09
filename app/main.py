"""FastAPI app entry point con middleware de request logging."""
from __future__ import annotations
import time
import logging
import socket

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    GCP_LOCATION, GCP_PROJECT, GCS_BUCKET, HOST, PORT, VEO_MODEL,
    is_deepseek_configured, is_elevenlabs_configured, is_veo_configured,
)
from app.routes import jobs as jobs_route

# Logging básico para que se vea cada request en la consola de uvicorn
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-5s | %(message)s",
)
log = logging.getLogger("ia-content")


app = FastAPI(
    title="ia-content backend",
    description="Backend local para generar videos cortos verticales con Veo + ElevenLabs.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Loguea cada request: client IP, método, ruta, status, latencia.

    Esto ayuda a debug de conectividad: si la app Flutter manda algo, lo ves
    aparecer en la consola del backend al instante.
    """
    started = time.time()
    client = request.client.host if request.client else "?"
    log.info(f"→ {request.method} {request.url.path} from {client}")
    try:
        response = await call_next(request)
    except Exception as e:
        log.exception(f"✗ {request.method} {request.url.path} EXC: {e}")
        raise
    dur_ms = int((time.time() - started) * 1000)
    log.info(f"← {request.method} {request.url.path} {response.status_code} ({dur_ms} ms)")
    return response


app.include_router(jobs_route.router)


def _local_ips() -> list[str]:
    """Devuelve las IPs LAN de esta máquina para mostrarlas en /health."""
    ips: list[str] = []
    try:
        host = socket.gethostname()
        for _, _, _, _, sa in socket.getaddrinfo(host, None, socket.AF_INET):
            ip = sa[0]
            if ip and ip not in ips and not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips


@app.get("/health")
def health():
    return {
        "status": "ok",
        "host": HOST,
        "port": PORT,
        "local_ips": _local_ips(),
        "services": {
            "deepseek":   is_deepseek_configured(),
            "elevenlabs": is_elevenlabs_configured(),
            "veo":        is_veo_configured(),
        },
        "veo": {
            "model":    VEO_MODEL,
            "project":  GCP_PROJECT,
            "location": GCP_LOCATION,
            "bucket":   GCS_BUCKET,
        },
    }
