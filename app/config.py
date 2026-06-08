"""Configuración global del backend. Lee del .env y define paths."""
from __future__ import annotations
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Forzar UTF-8 en consola Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ── Paths ────────────────────────────────────────────────────────────
DATA_DIR     = BASE_DIR / "data"
JOBS_DIR     = DATA_DIR / "jobs"
UPLOADS_DIR  = BASE_DIR / "uploads" / "reference"
OUTPUT_DIR   = BASE_DIR / "output"
MUSIC_DIR    = BASE_DIR / "music"

for d in [DATA_DIR, JOBS_DIR, UPLOADS_DIR, OUTPUT_DIR, MUSIC_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── LLM (DeepSeek primero, OpenAI opcional) ──────────────────────────
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")

# ── TTS ──────────────────────────────────────────────────────────────
ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")

# ── Veo / Vertex ─────────────────────────────────────────────────────
GCP_PROJECT  = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
# Si el usuario puso "global", Veo no lo acepta; lo forzamos a us-central1
if GCP_LOCATION.lower() == "global":
    GCP_LOCATION = "us-central1"
GCS_BUCKET   = os.getenv("GCS_BUCKET", "")
VEO_MODEL    = os.getenv("VEO_MODEL", "veo-3.0-fast-generate-001")

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
# Si el archivo no existe, ignorar (usaremos ADC)
if GOOGLE_APPLICATION_CREDENTIALS and not Path(GOOGLE_APPLICATION_CREDENTIALS).exists():
    GOOGLE_APPLICATION_CREDENTIALS = ""

# ── Veo defaults ─────────────────────────────────────────────────────
VEO_CLIP_DURATION = 8         # segundos por clip que entrega Veo 3
VEO_POLL_INTERVAL = 10        # segundos entre polls
VEO_POLL_MAX      = 36        # 36 * 10 = 6 minutos máximo

# ── Servidor ─────────────────────────────────────────────────────────
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

def is_veo_configured() -> bool:
    return bool(GCP_PROJECT and GCS_BUCKET)

def is_elevenlabs_configured() -> bool:
    return bool(ELEVENLABS_API_KEY)

def is_deepseek_configured() -> bool:
    return bool(DEEPSEEK_API_KEY)
