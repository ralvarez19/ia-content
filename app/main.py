"""FastAPI app entry point."""
from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import (
    GCP_LOCATION, GCP_PROJECT, GCS_BUCKET, VEO_MODEL,
    is_deepseek_configured, is_elevenlabs_configured, is_veo_configured,
)
from app.routes import jobs as jobs_route

app = FastAPI(
    title="ia-content backend",
    description="Backend local para generar videos cortos verticales con Veo + ElevenLabs.",
    version="0.1.0",
)

# CORS abierto: app es solo local. Si vas a exponerla a internet, ajusta esto.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs_route.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
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
