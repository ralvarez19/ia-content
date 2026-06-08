# 🏛️ Mitología Épica — Pipeline Automatizado TikTok/Reels

Pipeline Python que genera videos cortos (45–60 seg) de mitología para TikTok e Instagram Reels,
con **fallbacks automáticos** para cada servicio. Si no tienes una API, usa la siguiente opción disponible.

---

## 📁 Estructura del proyecto

```
C:\ia-content\
│
├── pipeline.py          ← orquestador principal
├── topics.txt           ← lista de temas (edita cada semana)
├── .env                 ← tus credenciales (créalo desde .env.example)
├── .env.example         ← plantilla de credenciales
│
├── scripts\             ← guiones generados (txt)
├── audio\               ← voces generadas (mp3/wav)
├── clips\               ← clips de video generados (mp4)
├── music\               ← pon aquí tus tracks de fondo (mp3/wav)
└── output\              ← videos finales listos para publicar
```

---

## ⚙️ Cómo funciona (4 pasos automáticos)

```
topics.txt
    │
    ▼
[1] GUIÓN     OpenAI GPT-4o-mini  →  DeepSeek  →  Ollama local
    │
    ▼
[2] VOZ       ElevenLabs          →  pyttsx3 (voz del sistema)
    │
    ▼
[3] VIDEO     Veo 3 (Vertex AI)   →  Pantalla negra narrada
    │
    ▼
[4] ENSAMBLE  FFmpeg  (concat + música de fondo + 1080x1920)
    │
    ▼
output\video_final.mp4
```

El pipeline **nunca se detiene**: si un servicio no está disponible o falla, pasa automáticamente al siguiente.

---

## 🚀 Instalación

### 1. Requisitos del sistema

- Python 3.10 o superior
- [FFmpeg](https://ffmpeg.org/download.html) instalado y en el PATH
  - Windows: descarga el zip, extrae, y agrega la carpeta `bin` al PATH del sistema
  - Verifica con: `ffmpeg -version`

### 2. Instalar dependencias Python

```bash
pip install openai elevenlabs google-cloud-aiplatform requests python-dotenv pyttsx3
```

### 3. Crear archivo de credenciales

```bash
# En la carpeta C:\ia-content\
copy .env.example .env
# Abre .env con el bloc de notas y rellena las APIs que tengas
```

---

## 🔑 Configuración de credenciales

### Guión — Elige al menos UNA opción:

#### Opción A: OpenAI (recomendado, mejor calidad)
1. Ve a https://platform.openai.com/api-keys
2. Crea una API key
3. En `.env`: `OPENAI_API_KEY=sk-proj-...`

#### Opción B: DeepSeek (más barato, casi igual de bueno)
1. Ve a https://platform.deepseek.com
2. Crea cuenta → API Keys → Nueva key
3. En `.env`: `DEEPSEEK_API_KEY=sk-...`
4. Costo: ~$0.001 por guión (10x más barato que OpenAI)

#### Opción C: Ollama (gratis, corre en tu PC)
1. Descarga Ollama: https://ollama.ai
2. Instala y corre: `ollama pull llama3`
3. Inicia el servidor: `ollama serve`
4. No requiere configuración en `.env` (ya está por defecto)

---

### Voz — Elige al menos UNA opción:

#### Opción A: ElevenLabs (recomendado, calidad cinematográfica)
1. Ve a https://elevenlabs.io → registrate
2. Panel → Profile → API Key → copia la key
3. Ve a Voices → elige un narrador épico en español → copia el Voice ID
4. En `.env`:
   ```
   ELEVENLABS_API_KEY=tu-api-key
   ELEVENLABS_VOICE_ID=id-de-tu-voz
   ```
5. Voces recomendadas para mitología en español: busca "dramatic", "narrator", "epic"

#### Opción B: pyttsx3 (gratis, voz del sistema)
- No requiere configuración
- Usa la voz del sistema operativo (Windows tiene voces en español instaladas)
- Calidad menor pero funcional para pruebas
- Para mejorar: Panel de Control → Voz → agregar voces en español

---

### Video — Elige al menos UNA opción:

#### Opción A: Veo 3 via Vertex AI (máxima calidad)

1. **Crear proyecto en Google Cloud**
   - Ve a https://console.cloud.google.com
   - Crea un proyecto nuevo (ej: `mitologia-videos`)
   - Activa la facturación (requiere tarjeta, pero tienen $300 de crédito gratis)

2. **Habilitar APIs necesarias**
   ```bash
   gcloud services enable aiplatform.googleapis.com
   gcloud services enable storage.googleapis.com
   ```

3. **Crear cuenta de servicio**
   - IAM → Cuentas de Servicio → Crear
   - Rol: `Vertex AI User` + `Storage Object Admin`
   - Crear key JSON → descarga como `gcloud-key.json`
   - Pon el archivo en `C:\ia-content\gcloud-key.json`

4. **Crear bucket de Cloud Storage**
   ```bash
   gsutil mb -l us-central1 gs://mi-bucket-mitologia
   ```

5. **Instalar Google Cloud SDK**
   - Descarga: https://cloud.google.com/sdk/docs/install
   - Autentica: `gcloud auth login`

6. **Configurar .env**
   ```
   GOOGLE_APPLICATION_CREDENTIALS=./gcloud-key.json
   GOOGLE_CLOUD_PROJECT=mitologia-videos
   GOOGLE_CLOUD_LOCATION=us-central1
   GCS_BUCKET=gs://mi-bucket-mitologia
   ```

#### Opción B: Pantalla negra narrada (sin costo, sin configuración)
- Si no configuras Veo 3, el pipeline genera automáticamente clips negros
- El video queda con la narración sobre fondo negro
- Útil para probar el pipeline antes de gastar dinero
- Puedes agregar imágenes estáticas en el futuro

---

## 🎵 Música de fondo

1. Genera tracks épicos gratuitos en https://suno.com
   - Prompt sugerido: `"epic orchestral mythology, dark dramatic, cinematic, no lyrics"`
2. Descarga los tracks como MP3
3. Cópialos a `C:\ia-content\music\`
4. El pipeline los mezcla automáticamente al 15% de volumen

---

## ▶️ Uso

### Modo batch (recomendado — procesa todos los temas de topics.txt)

```bash
cd C:\ia-content
python pipeline.py
```

### Modo individual (un solo tema)

```bash
python pipeline.py "Zeus y sus amantes secretas"
```

### Flujo semanal sugerido

```
Lunes (30 min):
  1. Abre topics.txt
  2. Escribe 5 temas nuevos
  3. Corre: python pipeline.py
  4. El sistema genera todo solo (tarda ~15-30 min por video)

Jueves (25 min):
  1. Revisa los 5 videos en output\
  2. Sube a TikTok/Reels con los hashtags del nicho
```

---

## 📊 Costos estimados por video

| Servicio | Costo por video |
|---|---|
| OpenAI GPT-4o-mini (guión) | ~$0.002 |
| DeepSeek (alternativa) | ~$0.0002 |
| ElevenLabs (60 seg de voz) | ~$0.30 |
| Veo 3 (4 clips × 8 seg) | ~$0.80–1.20 |
| **Total aprox.** | **~$1.10–1.50 por video** |

Con 5 videos/semana = ~$6–8/semana = ~$25–32/mes

---

## 🐛 Solución de problemas

**`ffmpeg: command not found`**
→ FFmpeg no está en el PATH. Agrega la carpeta `bin` de FFmpeg a las variables de entorno del sistema.

**`Error: openai module not found`**
→ Corre: `pip install openai`

**`pyttsx3 no genera audio en español`**
→ Ve a Configuración → Hora e idioma → Voz → Agregar voces → busca "Español"

**`Veo 3 error 403 PERMISSION_DENIED`**
→ Verifica que la cuenta de servicio tenga el rol `Vertex AI User` en IAM.

**`Videos quedan en negro aunque configuré Veo 3`**
→ Verifica que `gcloud auth print-access-token` funcione en tu terminal.
→ Asegúrate de que el bucket GCS existe y tienes permisos de escritura.

**`El pipeline se cuelga en Ollama`**
→ Verifica que Ollama esté corriendo: `ollama serve` en otra terminal.

---

## 📈 Próximos pasos

- [ ] Agregar subtítulos automáticos con Whisper
- [ ] Auto-publicar en TikTok vía Buffer API
- [ ] Soporte para imágenes estáticas como fallback de Veo 3
- [ ] Panel web simple para monitorear el batch

---

*Pipeline creado para automatizar contenido de mitología épica en español.*
*Stack: Python · OpenAI/DeepSeek/Ollama · ElevenLabs/pyttsx3 · Veo 3 · FFmpeg*
