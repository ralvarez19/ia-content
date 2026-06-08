"""Ensamble final con FFmpeg: clips + voz + música opcional → 1080x1920 mp4."""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional

from app.config import MUSIC_DIR
from app.utils.logger import JobLogger


def _resolve_exe(name: str) -> str:
    return shutil.which(name) or shutil.which(f"{name}.cmd") or name


def get_duration(path: Path) -> float:
    r = subprocess.run(
        [_resolve_exe("ffprobe"), "-v", "error",
         "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1",
         str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def first_music_track() -> Optional[Path]:
    if not MUSIC_DIR.exists():
        return None
    candidates = list(MUSIC_DIR.glob("*.mp3")) + list(MUSIC_DIR.glob("*.wav"))
    return candidates[0] if candidates else None


def assemble(
    clips: List[Path],
    audio: Path,
    output: Path,
    logger: JobLogger,
    aspect_ratio: str = "9:16",
    target_duration: Optional[float] = None,
    music: Optional[Path] = None,
) -> Path:
    """Ensambla todo en `output`. Devuelve `output`."""
    if not clips:
        raise ValueError("Sin clips para ensamblar")

    ff = _resolve_exe("ffmpeg")
    w, h = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)

    audio_dur = get_duration(audio) if audio and audio.exists() else 0.0
    final_dur = float(target_duration or audio_dur or (len(clips) * 8))

    # 1) Concatenar clips de video al tamaño/duración objetivo
    workdir = output.parent
    concat_list = workdir / f"{output.stem}_concat.txt"
    per_clip = final_dur / len(clips)
    # FFmpeg concat demuxer necesita forward slashes en Windows
    with concat_list.open("w", encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{c.resolve().as_posix()}'\n")
            f.write(f"duration {per_clip:.3f}\n")
        # El último file se repite sin duration por exigencia del demuxer
        f.write(f"file '{clips[-1].resolve().as_posix()}'\n")

    raw_video = workdir / f"{output.stem}_raw.mp4"
    r = subprocess.run([
        ff, "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_list),
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,"
               f"crop={w}:{h},setsar=1,fps=30",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-t", f"{final_dur:.3f}",
        "-an",
        str(raw_video),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        logger.error(f"ffmpeg concat falló: {r.stderr[-500:]}")
        raise RuntimeError("ffmpeg concat failed")

    # 2) Pista de audio (voz + música opcional)
    audio_final = audio
    if music and music.exists() and audio and audio.exists():
        mixed = workdir / f"{output.stem}_mixed.mp3"
        r = subprocess.run([
            ff, "-y",
            "-i", str(audio), "-i", str(music),
            "-filter_complex",
            f"[0:a]volume=1.0[v];"
            f"[1:a]volume=0.15,aloop=loop=-1:size=2e9,atrim=0:{final_dur}[b];"
            f"[v][b]amix=inputs=2:duration=first:dropout_transition=0[out]",
            "-map", "[out]",
            "-t", f"{final_dur:.3f}",
            str(mixed),
        ], capture_output=True, text=True)
        if r.returncode == 0:
            audio_final = mixed
        else:
            logger.warn(f"Mix con música falló, uso voz sola: {r.stderr[-300:]}")

    # 3) Mux final
    output.parent.mkdir(parents=True, exist_ok=True)
    if audio_final and audio_final.exists():
        r = subprocess.run([
            ff, "-y",
            "-i", str(raw_video), "-i", str(audio_final),
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart",
            str(output),
        ], capture_output=True, text=True)
    else:
        # Sin audio
        r = subprocess.run([
            ff, "-y", "-i", str(raw_video),
            "-c:v", "copy", "-movflags", "+faststart",
            str(output),
        ], capture_output=True, text=True)
    if r.returncode != 0:
        logger.error(f"ffmpeg mux final falló: {r.stderr[-500:]}")
        raise RuntimeError("ffmpeg mux failed")

    # 4) Limpieza
    concat_list.unlink(missing_ok=True)
    raw_video.unlink(missing_ok=True)
    mixed = workdir / f"{output.stem}_mixed.mp3"
    if mixed.exists():
        mixed.unlink(missing_ok=True)

    return output
