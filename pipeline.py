"""
╔══════════════════════════════════════════════════════════════╗
║        PIPELINE: Mitología Épica → TikTok / Reels           ║
║                                                              ║
║  Fallbacks automáticos:                                      ║
║   Guión  → OpenAI → DeepSeek → Ollama (local)               ║
║   Voz    → ElevenLabs → pyttsx3 (local)                     ║
║   Video  → Veo 3 (Vertex AI) → pantalla negra narrada       ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, sys, time, json, subprocess, textwrap, struct, wave
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ──────────────────────────────────────────────
#  RUTAS
# ──────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
SCRIPTS_DIR = BASE_DIR / "scripts"
AUDIO_DIR   = BASE_DIR / "audio"
CLIPS_DIR   = BASE_DIR / "clips"
MUSIC_DIR   = BASE_DIR / "music"
OUTPUT_DIR  = BASE_DIR / "output"
TOPICS_FILE = BASE_DIR / "topics.txt"

for d in [SCRIPTS_DIR, AUDIO_DIR, CLIPS_DIR, MUSIC_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────
#  CREDENCIALES
# ──────────────────────────────────────────────
OPENAI_API_KEY      = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY    = os.getenv("DEEPSEEK_API_KEY", "")
OLLAMA_MODEL        = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_URL          = os.getenv("OLLAMA_URL", "http://localhost:11434")

ELEVENLABS_API_KEY  = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")

GCP_PROJECT         = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GCP_LOCATION        = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GCS_BUCKET          = os.getenv("GCS_BUCKET", "")

# ──────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────
def log(icon, msg):
    print(f"  {icon}  {msg}")

def cmd(args, **kwargs):
    """Ejecuta un comando y devuelve True si tuvo éxito."""
    result = subprocess.run(args, capture_output=True, text=True, **kwargs)
    return result.returncode == 0, result

# ══════════════════════════════════════════════
#  PASO 1 — GUIÓN  (OpenAI → DeepSeek → Ollama)
# ══════════════════════════════════════════════

SCRIPT_SYSTEM = (
    "Eres un guionista experto en contenido viral de mitología para TikTok/Reels en español. "
    "Estructura SIEMPRE: HOOK 5s (pregunta impactante) + DESARROLLO 40s (historia dramática con datos) "
    "+ CTA 5s (invitar a seguir). Máximo 150 palabras. "
    "Lenguaje dinámico, sin intro genérica. Empieza DIRECTO con el hook. "
    "Devuelve SOLO el guión, sin etiquetas."
)

def _guion_openai(tema: str) -> str | None:
    if not OPENAI_API_KEY:
        return None
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": SCRIPT_SYSTEM},
                      {"role": "user",   "content": f"Tema: {tema}"}],
            max_tokens=300, temperature=0.85
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        log("⚠️", f"OpenAI falló: {e}")
        return None

def _guion_deepseek(tema: str) -> str | None:
    if not DEEPSEEK_API_KEY:
        return None
    try:
        import requests
        r = requests.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                     "Content-Type": "application/json"},
            json={"model": "deepseek-chat",
                  "messages": [{"role": "system", "content": SCRIPT_SYSTEM},
                                {"role": "user",   "content": f"Tema: {tema}"}],
                  "max_tokens": 300, "temperature": 0.85},
            timeout=30
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log("⚠️", f"DeepSeek falló: {e}")
        return None

def _guion_ollama(tema: str) -> str | None:
    try:
        import requests
        prompt = f"{SCRIPT_SYSTEM}\n\nTema: {tema}"
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        log("⚠️", f"Ollama falló: {e}")
        return None

def generar_guion(tema: str) -> str:
    log("📝", f"Generando guión: {tema}")

    for nombre, fn in [("OpenAI", _guion_openai),
                       ("DeepSeek", _guion_deepseek),
                       ("Ollama", _guion_ollama)]:
        log("🔄", f"Intentando con {nombre}...")
        guion = fn(tema)
        if guion:
            log("✅", f"Guión generado con {nombre} ({len(guion.split())} palabras)")
            return guion

    # Fallback hardcoded
    log("⚠️", "Todos los LLMs fallaron. Usando guión genérico.")
    return (
        f"¿Sabías que {tema} cambió la historia de la mitología para siempre? "
        f"Los dioses del Olimpo guardaban este secreto celosamente. "
        f"Lo que ocurrió aquella noche sacudió los cimientos del mundo antiguo. "
        f"Sígueme para descubrir más secretos que la historia olvidó."
    )


# ══════════════════════════════════════════════
#  PASO 2 — VOZ  (ElevenLabs → pyttsx3 local)
# ══════════════════════════════════════════════

def _voz_elevenlabs(guion: str, out: Path) -> bool:
    if not ELEVENLABS_API_KEY:
        return False
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio = client.text_to_speech.convert(
            text=guion,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        with open(out, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        return out.exists() and out.stat().st_size > 1000
    except Exception as e:
        log("⚠️", f"ElevenLabs falló: {e}")
        return False

def _voz_pyttsx3(guion: str, out: Path) -> bool:
    """Voz local del sistema usando pyttsx3 → guarda como WAV → convierte a MP3."""
    try:
        import pyttsx3
        engine = pyttsx3.init()

        # Intentar seleccionar voz en español
        voices = engine.getProperty("voices")
        for v in voices:
            if any(lang in v.id.lower() for lang in ["es", "spanish", "español"]):
                engine.setProperty("voice", v.id)
                break

        engine.setProperty("rate", 155)   # velocidad narrativa
        engine.setProperty("volume", 1.0)

        wav_path = out.with_suffix(".wav")
        engine.save_to_file(guion, str(wav_path))
        engine.runAndWait()

        if not wav_path.exists() or wav_path.stat().st_size < 500:
            return False

        # Convertir WAV → MP3 con ffmpeg si está disponible
        ok, _ = cmd(["ffmpeg", "-y", "-i", str(wav_path),
                     "-codec:a", "libmp3lame", "-qscale:a", "4", str(out)])
        if ok:
            wav_path.unlink(missing_ok=True)
            return True
        else:
            # Dejar el WAV renombrado como "mp3" (ffmpeg se encargará después)
            wav_path.rename(out.with_suffix(".wav"))
            return False

    except Exception as e:
        log("⚠️", f"pyttsx3 falló: {e}")
        return False

def generar_voz(guion: str, slug: str) -> Path:
    log("🎙️", "Generando voz...")
    audio_path = AUDIO_DIR / f"{slug}.mp3"

    for nombre, fn in [("ElevenLabs", _voz_elevenlabs),
                       ("pyttsx3 (local)", _voz_pyttsx3)]:
        log("🔄", f"Intentando con {nombre}...")
        if fn(guion, audio_path):
            log("✅", f"Voz generada con {nombre}")
            return audio_path

    # Último recurso: silencio de 55 segundos en WAV mínimo
    log("⚠️", "Sin motor de voz disponible. Generando silencio.")
    audio_path = AUDIO_DIR / f"{slug}.wav"
    _generar_silencio_wav(audio_path, segundos=55)
    return audio_path

def _generar_silencio_wav(path: Path, segundos: int = 55):
    """Genera un archivo WAV de silencio usando solo stdlib."""
    sample_rate = 44100
    n_samples   = sample_rate * segundos
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(b"\x00\x00" * n_samples)


# ══════════════════════════════════════════════
#  PASO 3 — VIDEO  (Veo 3 → pantalla negra)
# ══════════════════════════════════════════════

def _clip_veo3(prompt: str, slug: str, idx: int) -> Path | None:
    if not all([GCP_PROJECT, GCS_BUCKET]):
        return None
    try:
        import requests as req
        token_r = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True, text=True
        )
        if token_r.returncode != 0:
            return None
        token = token_r.stdout.strip()

        endpoint = (
            f"https://{GCP_LOCATION}-aiplatform.googleapis.com/v1/"
            f"projects/{GCP_PROJECT}/locations/{GCP_LOCATION}/"
            f"publishers/google/models/veo-3.0-generate-preview:predictLongRunning"
        )
        payload = {"instances": [{"prompt": prompt, "parameters": {
            "durationSeconds": 8, "aspectRatio": "9:16",
            "sampleCount": 1, "storageUri": GCS_BUCKET
        }}]}
        r = req.post(endpoint,
                     headers={"Authorization": f"Bearer {token}",
                               "Content-Type": "application/json"},
                     json=payload, timeout=30)
        if r.status_code != 200:
            log("⚠️", f"Veo3 error {r.status_code}")
            return None

        op_name = r.json().get("name")
        poll_url = f"https://{GCP_LOCATION}-aiplatform.googleapis.com/v1/{op_name}"

        for _ in range(30):
            time.sleep(10)
            poll = req.get(poll_url,
                           headers={"Authorization": f"Bearer {token}"},
                           timeout=15).json()
            if poll.get("done"):
                uri = (poll.get("response", {})
                           .get("predictions", [{}])[0]
                           .get("video", {}).get("uri", ""))
                if not uri:
                    return None
                clip_path = CLIPS_DIR / f"{slug}_clip{idx}.mp4"
                ok, _ = cmd(["gsutil", "cp", uri, str(clip_path)])
                return clip_path if ok else None

    except Exception as e:
        log("⚠️", f"Veo3 excepción: {e}")
        return None

def _clip_negro(slug: str, idx: int, duration: float = 8.0) -> Path:
    """Genera un clip MP4 de pantalla negra con ffmpeg."""
    clip_path = CLIPS_DIR / f"{slug}_clip{idx}.mp4"
    cmd([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=1080x1920:r=30:d={duration}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        str(clip_path)
    ])
    return clip_path

def _prompt_para_veo(tema: str, guion: str, fn_guion) -> str:
    """Genera un prompt cinematográfico para Veo 3 usando el LLM disponible."""
    system = (
        "Generate a single cinematic video prompt in English for Veo 3. "
        "Format: [shot type] + [subject] + [action] + [setting] + [lighting] + [mood]. "
        "Style: epic fantasy, vertical 9:16, photorealistic. No text overlays. "
        "Return ONLY the prompt, no explanation."
    )
    # Reutilizamos el mismo LLM que generó el guión
    for _, fn in [("OpenAI", _guion_openai),
                  ("DeepSeek", _guion_deepseek),
                  ("Ollama", _guion_ollama)]:
        # Hack: sustituimos el system prompt temporalmente
        original = globals().get("SCRIPT_SYSTEM")
        try:
            import openai, requests as req
        except:
            pass

        prompt_user = f"Mythology topic: {tema}. Script summary: {guion[:150]}"
        # Llamada directa según disponibilidad
        result = None
        if OPENAI_API_KEY:
            try:
                import openai
                c = openai.OpenAI(api_key=OPENAI_API_KEY)
                r = c.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": system},
                               {"role": "user", "content": prompt_user}],
                    max_tokens=120, temperature=0.7)
                result = r.choices[0].message.content.strip()
            except:
                pass
        if not result and DEEPSEEK_API_KEY:
            try:
                import requests as req2
                r = req2.post("https://api.deepseek.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
                    json={"model": "deepseek-chat",
                          "messages": [{"role": "system", "content": system},
                                        {"role": "user", "content": prompt_user}],
                          "max_tokens": 120},
                    timeout=20)
                result = r.json()["choices"][0]["message"]["content"].strip()
            except:
                pass
        if result:
            return result
        break

    # Fallback prompt genérico
    return (
        f"Extreme close-up of a powerful Greek god standing on Mount Olympus, "
        f"dramatic golden lightning in the background, epic cinematic lighting, "
        f"vertical 9:16 composition, photorealistic, dark fantasy atmosphere"
    )

def generar_clips(tema: str, guion: str, slug: str, n: int = 4) -> list[Path]:
    log("🎬", f"Generando {n} clips de video...")
    clips = []

    usar_veo = all([GCP_PROJECT, GCS_BUCKET])
    if not usar_veo:
        log("ℹ️", "Sin credenciales de Veo 3 → usando pantalla negra narrada")

    for i in range(n):
        if usar_veo:
            log("🔄", f"Veo 3 → clip {i+1}/{n}...")
            prompt = _prompt_para_veo(tema, guion, None)
            clip = _clip_veo3(prompt, slug, i)
            if clip:
                log("✅", f"Clip {i+1} generado con Veo 3")
                clips.append(clip)
                continue
            log("⚠️", f"Veo 3 falló en clip {i+1} → pantalla negra")

        clip = _clip_negro(slug, i)
        log("✅", f"Clip {i+1} generado (pantalla negra)")
        clips.append(clip)
        time.sleep(1)

    return clips


# ══════════════════════════════════════════════
#  PASO 4 — ENSAMBLE FFMPEG
# ══════════════════════════════════════════════

def get_duration(path: Path) -> float:
    ok, r = cmd(["ffprobe", "-v", "error", "-show_entries",
                 "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
                 str(path)])
    try:
        return float(r.stdout.strip())
    except:
        return 55.0

def get_music() -> Path | None:
    tracks = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
    return tracks[0] if tracks else None

def ensamblar(clips: list[Path], audio: Path, slug: str,
              music: Path | None = None) -> Path:
    log("🎞️", "Ensamblando con FFmpeg...")
    output = OUTPUT_DIR / f"{slug}.mp4"
    dur    = get_duration(audio)

    # Crear lista de concatenación
    concat_txt = OUTPUT_DIR / f"{slug}_list.txt"
    clip_dur = dur / len(clips)
    with open(concat_txt, "w") as f:
        for c in clips:
            f.write(f"file '{c.resolve()}'\nduration {clip_dur:.2f}\n")

    raw = OUTPUT_DIR / f"{slug}_raw.mp4"
    cmd([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,"
               "crop=1080:1920,setsar=1",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-t", str(dur), str(raw)
    ])

    # Audio: voz sola o mezclada con música
    if music and music.exists():
        mixed = OUTPUT_DIR / f"{slug}_mix.mp3"
        cmd([
            "ffmpeg", "-y",
            "-i", str(audio), "-i", str(music),
            "-filter_complex",
            f"[0:a]volume=1.0[v];[1:a]volume=0.15,atrim=0:{dur}[b];[v][b]amix=inputs=2:duration=first[out]",
            "-map", "[out]", str(mixed)
        ])
        audio_final = mixed
    else:
        audio_final = audio

    cmd([
        "ffmpeg", "-y",
        "-i", str(raw), "-i", str(audio_final),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(output)
    ])

    # Limpieza
    concat_txt.unlink(missing_ok=True)
    raw.unlink(missing_ok=True)
    if music and (OUTPUT_DIR / f"{slug}_mix.mp3").exists():
        (OUTPUT_DIR / f"{slug}_mix.mp3").unlink(missing_ok=True)

    log("✅", f"Video final: {output}")
    return output


# ══════════════════════════════════════════════
#  ORQUESTADOR
# ══════════════════════════════════════════════

def procesar(tema: str) -> dict:
    slug = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + \
           tema[:20].replace(" ", "_").lower()

    print(f"\n{'═'*58}")
    print(f"  🏛️  {tema}")
    print(f"{'═'*58}")

    res = {"tema": tema, "slug": slug, "ok": False}

    try:
        guion = generar_guion(tema)
        (SCRIPTS_DIR / f"{slug}.txt").write_text(guion, encoding="utf-8")

        audio  = generar_voz(guion, slug)
        clips  = generar_clips(tema, guion, slug, n=4)
        music  = get_music()
        video  = ensamblar(clips, audio, slug, music)

        res.update({"guion": guion, "video": str(video), "ok": True})
        print(f"\n  🎉  Listo → {video}\n")

    except Exception as e:
        log("❌", f"Error: {e}")
        res["error"] = str(e)

    return res


def run_batch():
    if not TOPICS_FILE.exists():
        print(f"\n❌ No encontré {TOPICS_FILE}")
        print("   Crea topics.txt con un tema por línea.")
        return

    temas = [l.strip() for l in TOPICS_FILE.read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]

    if not temas:
        print("❌ topics.txt está vacío.")
        return

    print(f"\n🚀  Batch: {len(temas)} temas  →  {OUTPUT_DIR}\n")
    resultados = []

    for i, tema in enumerate(temas, 1):
        print(f"[{i}/{len(temas)}]", end="")
        resultados.append(procesar(tema))
        time.sleep(2)

    ok = sum(1 for r in resultados if r["ok"])
    print(f"\n{'═'*58}")
    print(f"  📊  {ok}/{len(temas)} videos generados exitosamente")
    print(f"  📁  {OUTPUT_DIR}")

    log_path = BASE_DIR / f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_path.write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    print(f"  📋  Log → {log_path}")


# ══════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) > 1:
        procesar(" ".join(sys.argv[1:]))
    else:
        run_batch()
