"""TTS: ElevenLabs primario, pyttsx3 como fallback local."""
from __future__ import annotations
import subprocess
import wave
from pathlib import Path
from typing import Optional

from app.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
from app.utils.logger import JobLogger


def generate_voice(
    text: str,
    out_path: Path,
    logger: JobLogger,
    voice_id: Optional[str] = None,
) -> Optional[Path]:
    """Devuelve la ruta al audio generado, o None si todo falló."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    vid = voice_id or ELEVENLABS_VOICE_ID

    if ELEVENLABS_API_KEY:
        logger.info(f"TTS: ElevenLabs (voice_id={vid})")
        if _try_elevenlabs(text, out_path, vid, logger):
            return out_path
        logger.warn("ElevenLabs falló, intento pyttsx3 local")

    if _try_pyttsx3(text, out_path, logger):
        return out_path

    logger.warn("Ningún motor TTS funcionó, genero silencio")
    silent = out_path.with_suffix(".wav")
    _silent_wav(silent, seconds=max(30, min(120, len(text.split()) // 2)))
    return silent


def _try_elevenlabs(text: str, out: Path, voice_id: str, logger: JobLogger) -> bool:
    try:
        from elevenlabs.client import ElevenLabs
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128",
        )
        with open(out, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        ok = out.exists() and out.stat().st_size > 1000
        return ok
    except Exception as e:
        logger.warn(f"ElevenLabs exception: {e}")
        return False


def _try_pyttsx3(text: str, out: Path, logger: JobLogger) -> bool:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        for v in engine.getProperty("voices"):
            if any(t in v.id.lower() for t in ("es", "spanish", "español")):
                engine.setProperty("voice", v.id)
                break
        engine.setProperty("rate", 155)
        engine.setProperty("volume", 1.0)

        wav = out.with_suffix(".wav")
        engine.save_to_file(text, str(wav))
        engine.runAndWait()
        if not wav.exists() or wav.stat().st_size < 500:
            logger.warn("pyttsx3 produjo WAV vacío")
            return False

        # Convertir a MP3
        r = subprocess.run(
            ["ffmpeg", "-y", "-i", str(wav), "-codec:a", "libmp3lame",
             "-qscale:a", "4", str(out)],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            wav.unlink(missing_ok=True)
            return True
        logger.warn(f"ffmpeg WAV->MP3 falló: {r.stderr[:200]}")
        return False
    except Exception as e:
        logger.warn(f"pyttsx3 exception: {e}")
        return False


def _silent_wav(path: Path, seconds: int = 30) -> None:
    sr = 44100
    with wave.open(str(path), "w") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(b"\x00\x00" * (sr * seconds))
