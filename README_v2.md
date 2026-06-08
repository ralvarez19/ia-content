# 🎬 ia-content v2 — Backend FastAPI + Frontend Flutter

Convierte el pipeline original en un sistema cliente/servidor local:

* **Backend** Python/FastAPI en `app/` — orquesta DeepSeek + ElevenLabs + Veo 3 + FFmpeg.
* **Frontend** Flutter Desktop/Mobile en `flutter_app/` — panel de control para crear jobs.

El pipeline original (`pipeline.py`) se mantiene intacto. Hay un respaldo en
`backup_pipeline_original.py`.

---

## 📁 Estructura nueva

```
C:\ia-content\
│
├── app\                     ← Backend FastAPI
│   ├── main.py              ← FastAPI app + /health
│   ├── config.py            ← Carga .env y paths
│   ├── models.py            ← Pydantic Job, JobStatus, JobSummary
│   ├── routes\jobs.py       ← Endpoints REST
│   ├── services\
│   │   ├── script_service.py    ← Parte el diálogo en N segmentos
│   │   ├── prompt_builder.py    ← Genera prompts cinematográficos por clip
│   │   ├── tts_service.py       ← ElevenLabs + fallback pyttsx3
│   │   ├── veo_service.py       ← Veo 3 fast + image-to-video + last-frame
│   │   ├── ffmpeg_service.py    ← Ensamble 1080x1920 + voz + música
│   │   ├── storage_service.py   ← Persistencia en disco (data/jobs/)
│   │   └── job_runner.py        ← Orquestador del pipeline por job
│   └── utils\logger.py      ← Logger por job → data/jobs/{id}/logs.txt
│
├── flutter_app\             ← App Flutter (Windows desktop por defecto)
│   ├── pubspec.yaml
│   └── lib\
│       ├── main.dart
│       ├── config.dart      ← BASE_URL del backend
│       ├── models\video_job.dart
│       ├── services\api_service.dart
│       ├── screens\         ← home + progreso + historial
│       └── widgets\         ← job_card, reference_image_picker
│
├── data\jobs\<job_id>\      ← Por cada generación
│   ├── job.json
│   ├── logs.txt
│   ├── reference.png        ← (si se subió imagen referencial)
│   ├── audio.mp3
│   ├── clips\clip_001.mp4
│   └── final.mp4
│
├── uploads\reference\       ← (reservado para uso futuro)
├── output\                  ← (legacy del pipeline.py original)
├── music\                   ← Tracks .mp3 / .wav para fondo
│
├── pipeline.py              ← (sin tocar) — pipeline batch original
├── backup_pipeline_original.py
├── requirements.txt
└── .env
```

---

## 🚀 Cómo correr

### 1. Backend (FastAPI)

```powershell
cd C:\ia-content
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Solo local (tu PC):
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Para usar la app Flutter desde el celular en la misma red:
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Endpoints disponibles:

| Método | Ruta | Qué hace |
|---|---|---|
| GET  | `/health` | Estado + qué servicios están configurados |
| POST | `/jobs` | Crea un nuevo job (multipart, soporta imagen) |
| GET  | `/jobs` | Lista jobs recientes |
| GET  | `/jobs/{id}` | Estado completo del job |
| GET  | `/jobs/{id}/logs` | Logs en texto plano |
| GET  | `/jobs/{id}/download` | Descarga `final.mp4` |
| GET  | `/jobs/{id}/reference` | Imagen referencial subida |

Docs interactivas en: <http://127.0.0.1:8000/docs>

### 2. Frontend (Flutter)

```powershell
cd C:\ia-content\flutter_app
flutter pub get
flutter run -d windows
```

Si vas a usar la app desde el celular, edita `lib/config.dart`:

```dart
static const String backendBaseUrl = 'http://192.168.1.X:8000';
```

(reemplaza `192.168.1.X` por la IP LAN de tu PC, y asegúrate de haber
arrancado uvicorn con `--host 0.0.0.0`).

---

## 🔑 .env esperado

```
DEEPSEEK_API_KEY=sk-...
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjVDRZzb
GOOGLE_CLOUD_PROJECT=mitologia-videos
GOOGLE_CLOUD_LOCATION=us-central1
GCS_BUCKET=gs://mitologia-videos-veo-marcelo
# Opcional — si NO existe gcloud-key.json, el backend usa ADC
# GOOGLE_APPLICATION_CREDENTIALS=./gcloud-key.json
```

Si vas con ADC, antes de arrancar uvicorn hace falta una vez:

```powershell
gcloud auth application-default login
```

> ⚠️ `GOOGLE_CLOUD_LOCATION=global` **no funciona** con Veo. El backend lo
> reemplaza automáticamente por `us-central1`.

---

## 🎨 Cómo funciona el flujo de generación

```
POST /jobs (multipart)
        │
        ▼
[1] Guion split        El diálogo del usuario se parte en N segmentos
                       balanceados por palabras/frases.
        │
        ▼
[2] Prompt builder     Genera N prompts cinematográficos en inglés con un
                       "anchor visual" compartido (escena, estilo, paleta,
                       iluminación, referencia opcional) + acción específica
                       por clip + restricciones de continuidad explícitas.
        │
        ▼
[3] Voz (ElevenLabs)   eleven_multilingual_v2, fallback a pyttsx3 si la
                       API falla; último fallback: silencio WAV.
        │
        ▼
[4] Clips (Veo 3 fast) - Clip 1 recibe la imagen referencial del usuario
                         como first frame (si se subió)
                       - Clip N (N>1) recibe el ÚLTIMO FRAME del clip N-1
                         como first frame → continuidad visual encadenada
                       - generateAudio=false (cobra menos)
                       - Si un clip falla → pantalla negra de 8s, el job
                         sigue
        │
        ▼
[5] Ensamble FFmpeg    Concat clips → escala/crop a 1080x1920 → mezcla con
                       voz (y música opcional al 15% de volumen) →
                       final.mp4 con +faststart para web.
```

### Continuidad visual

* Sin imagen referencial → cada clip usa el último frame del anterior como
  seed. Esto encadena la secuencia visualmente.
* Con imagen referencial → el clip 1 arranca exactamente desde esa imagen,
  los siguientes encadenan a partir del último frame. Todos comparten el
  mismo "anchor" textual en el prompt.

### Fallbacks
| Paso | Primario | Fallback |
|---|---|---|
| Voz | ElevenLabs | pyttsx3 → silencio WAV |
| Video | Veo 3 fast | Pantalla negra 8s/clip |
| Mux | FFmpeg con voz+música | FFmpeg solo con voz |

El job **nunca queda colgado**: si algo falla irreparablemente, se marca
como `failed` con el error en `job.error`.

---

## 💰 Costos por video (referencia)

Para un video de 60s = 8 clips × 8s:

| Servicio | Costo |
|---|---|
| DeepSeek (si se usa para refinar prompts) | < $0.01 |
| ElevenLabs voz (~60s) | ~$0.30 |
| Veo 3 fast sin audio (8 clips) | ~$2-3 |
| **Total estimado** | **~$2.5-3.5** |

Si bajas a 4 clips (cada uno se estira a 16s en el ensamble): ~$1.5
total, pero la imagen se ve más "estática".

---

## ✅ Reglas que se mantuvieron del original

* Sin login, sin JWT, sin Firebase
* API keys solo en `.env` del backend, nunca llegan al frontend Flutter
* Carpetas del pipeline original (`scripts/`, `audio/`, `clips/`,
  `output/`) intactas
* `pipeline.py` original sigue funcionando vía `python pipeline.py`
* Backup en `backup_pipeline_original.py` por si querés revertir

---

## 🐛 Troubleshooting

**"gcloud auth print-access-token falló"** → corré
`gcloud auth application-default login` en PowerShell.

**Veo 404 "Publisher Model not found"** → verificá que el modelo del
`.env` exista (default: `veo-3.0-fast-generate-001`). Modelos disponibles
en us-central1: `veo-3.0-generate-001`, `veo-3.0-fast-generate-001`.

**ElevenLabs 401** → key inválida o sin créditos.

**FFmpeg no encontrado** → instalá FFmpeg y agregalo al PATH del sistema.

**Backend devuelve 500 al crear job** → revisá `data/jobs/<id>/logs.txt`,
es el primer lugar donde mirar.

**Flutter no encuentra el backend** → si arrancaste uvicorn con
`--host 127.0.0.1`, la app Flutter solo conecta desde la misma PC. Para
celular: `--host 0.0.0.0` + cambiar `BASE_URL` en `lib/config.dart`.
