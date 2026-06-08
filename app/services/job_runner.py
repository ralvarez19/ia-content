"""Orquestador del job: corre los 4 pasos del pipeline en un thread."""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from app.config import VEO_CLIP_DURATION, is_elevenlabs_configured, is_veo_configured
from app.models import Job, JobStatus
from app.services import (
    ffmpeg_service,
    prompt_builder,
    script_service,
    storage_service as storage,
    tts_service,
    veo_service,
)
from app.utils.logger import JobLogger


def run_job(job_id: str) -> None:
    """Punto de entrada que FastAPI dispara en background.

    No levanta excepciones hacia afuera: cualquier fallo se registra y se
    marca el job como FAILED.
    """
    job = storage.load_job(job_id)
    if not job:
        return

    logger = JobLogger(storage.log_file(job_id))
    logger.step(f"=== Inicia job {job_id} — {job.title} ===")
    logger.info(
        f"clips={job.clips_count} duración={job.duration_seconds}s "
        f"voz={job.generate_voice} video={job.generate_video} "
        f"refimg={job.use_reference_image and job.has_reference_image}"
    )

    try:
        job.status = JobStatus.RUNNING
        job.progress = 5
        job.current_step = "preparando"
        storage.save_job(job)

        # ── 1. Partir diálogo en N segmentos ────────────────────────
        logger.step("1/4 partiendo diálogo en segmentos")
        chunks = script_service.split_dialogue(job.dialogue, job.clips_count)
        for i, c in enumerate(chunks):
            logger.info(f"  chunk {i+1}: {len(c.split())} palabras")

        ref_img: Optional[Path] = None
        if job.use_reference_image and job.has_reference_image:
            ref_img = storage.find_reference(job.job_id)
            if ref_img:
                logger.info(f"reference image: {ref_img.name}")

        ctx = prompt_builder.PromptContext(
            scene=job.scene,
            dialogue=job.dialogue,
            style=job.style,
            aspect_ratio=job.aspect_ratio,
            has_reference_image=bool(ref_img),
            reference_description=(
                "the supplied reference frame (use as canonical look)"
                if ref_img else None
            ),
        )
        prompts = prompt_builder.build_all_prompts(ctx, chunks)
        for i, p in enumerate(prompts):
            logger.info(f"prompt {i+1}: {p[:160]}...")

        # ── 2. Generar voz ──────────────────────────────────────────
        audio_path: Optional[Path] = None
        if job.generate_voice:
            logger.step("2/4 generando voz")
            job.progress = 20
            job.current_step = "generando voz"
            storage.save_job(job)
            audio_path = tts_service.generate_voice(
                text=job.dialogue,
                out_path=storage.audio_path(job.job_id),
                logger=logger,
                voice_id=job.voice_id,
            )
            if audio_path:
                logger.info(f"voz lista: {audio_path.name}")
            else:
                logger.warn("voz no disponible — el video saldrá sin narración")
        else:
            logger.info("2/4 voz: SKIPPED (generate_voice=false)")

        # ── 3. Generar clips ────────────────────────────────────────
        logger.step(f"3/4 generando {job.clips_count} clips")
        clips: List[Path] = []
        seed: Optional[Path] = ref_img  # primer clip usa la imagen del usuario

        usar_veo = job.generate_video and is_veo_configured()
        if not usar_veo:
            reason = ("generate_video=false" if not job.generate_video
                      else "Veo no configurado en .env")
            logger.warn(f"Veo desactivado → fallback pantalla negra ({reason})")

        for i in range(job.clips_count):
            job.progress = 20 + int((i / job.clips_count) * 60)
            job.current_step = f"clip {i+1}/{job.clips_count}"
            storage.save_job(job)

            clip_out = storage.clip_path(job.job_id, i)

            if usar_veo:
                logger.step(f"  Veo clip {i+1}/{job.clips_count}")
                clip = veo_service.generate_clip(
                    prompt=prompts[i],
                    out_path=clip_out,
                    logger=logger,
                    seed_image=seed,
                    duration_seconds=VEO_CLIP_DURATION,
                    aspect_ratio=job.aspect_ratio,
                )
                if clip:
                    clips.append(clip)
                    # extraer último frame como semilla del siguiente clip
                    seed_next = storage.job_dir(job.job_id) / "clips" / f"seed_{i+1:03d}.png"
                    new_seed = veo_service.extract_last_frame(clip, seed_next, logger)
                    if new_seed:
                        seed = new_seed
                    continue
                logger.warn(f"  Veo falló clip {i+1} → fallback negro")

            # fallback
            black = veo_service.generate_black_clip(
                clip_out, duration=VEO_CLIP_DURATION,
                logger=logger, aspect_ratio=job.aspect_ratio,
            )
            clips.append(black)

        # ── 4. Ensamble final ───────────────────────────────────────
        logger.step("4/4 ensamblando video final")
        job.progress = 85
        job.current_step = "ensamblando"
        storage.save_job(job)

        music = ffmpeg_service.first_music_track() if job.music_enabled else None
        if music:
            logger.info(f"música de fondo: {music.name}")

        final_out = storage.final_path(job.job_id)
        ffmpeg_service.assemble(
            clips=clips,
            audio=audio_path if audio_path else Path("/__nope__"),
            output=final_out,
            logger=logger,
            aspect_ratio=job.aspect_ratio,
            target_duration=float(job.duration_seconds),
            music=music,
        )

        job.status = JobStatus.COMPLETED
        job.progress = 100
        job.current_step = "completado"
        job.output_video = str(final_out)
        storage.save_job(job)
        logger.step(f"=== JOB COMPLETADO → {final_out} ===")

    except Exception as e:
        logger.error(f"FALLO: {e}")
        job = storage.load_job(job_id) or job
        job.status = JobStatus.FAILED
        job.error = str(e)
        job.current_step = "fallido"
        storage.save_job(job)
