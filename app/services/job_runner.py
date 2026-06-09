"""Orquestador del job multi-escena. Cada escena ⇒ un clip Veo."""
from __future__ import annotations
from pathlib import Path
from typing import List, Optional

from app.config import VEO_CLIP_DURATION, is_veo_configured
from app.models import Job, JobStatus
from app.services import (
    ffmpeg_service,
    prompt_builder,
    storage_service as storage,
    tts_service,
    veo_service,
)
from app.utils.logger import JobLogger


def _full_narration(job: Job) -> str:
    """Concatena el diálogo de todas las escenas en un único texto para TTS."""
    parts = [s.dialogue.strip() for s in job.scenes if s.dialogue.strip()]
    return " ".join(parts)


def run_job(job_id: str) -> None:
    job = storage.load_job(job_id)
    if not job:
        return

    logger = JobLogger(storage.log_file(job_id))
    logger.step(f"=== Inicia job {job_id} — {job.title} ===")
    logger.info(
        f"scenes={len(job.scenes)} duration={job.duration_seconds}s "
        f"voice={job.generate_voice} video={job.generate_video}"
    )

    try:
        job.status = JobStatus.RUNNING
        job.progress = 5
        job.current_step = "preparando"
        storage.save_job(job)

        # ── 1. Resumen de escenas + imágenes ────────────────────────
        logger.step("1/4 escenas")
        any_ref = False
        scene_refs: List[Optional[Path]] = []
        for i, sc in enumerate(job.scenes):
            ref = storage.find_scene_reference(job_id, i)
            scene_refs.append(ref)
            if ref:
                any_ref = True
            logger.info(
                f"  scene {sc.scene_number}: '{sc.scene_description[:50]}…' "
                f"({len(sc.dialogue.split())} palabras) "
                f"ref={'sí' if ref else 'no'}"
            )

        ctx = prompt_builder.PromptContext(
            title=job.title,
            style=job.style,
            aspect_ratio=job.aspect_ratio,
            has_any_reference=any_ref,
        )

        prompts = [
            prompt_builder.build_scene_prompt(
                ctx, sc, len(job.scenes), scene_has_image=(scene_refs[i] is not None)
            )
            for i, sc in enumerate(job.scenes)
        ]
        for i, p in enumerate(prompts):
            logger.info(f"prompt {i+1}: {p[:180]}…")

        # ── 2. Voz (un solo audio para toda la narración) ───────────
        audio_path: Optional[Path] = None
        if job.generate_voice:
            logger.step("2/4 generando voz")
            job.progress = 20
            job.current_step = "generando voz"
            storage.save_job(job)
            audio_path = tts_service.generate_voice(
                text=_full_narration(job),
                out_path=storage.audio_path(job_id),
                logger=logger,
                voice_id=job.voice_id,
            )
            if audio_path:
                logger.info(f"voz lista: {audio_path.name}")
            else:
                logger.warn("voz no disponible — video saldrá sin narración")
        else:
            logger.info("2/4 voz: SKIPPED (generate_voice=false)")

        # ── 3. Clips (uno por escena) ───────────────────────────────
        logger.step(f"3/4 generando {len(job.scenes)} clips")
        clips: List[Path] = []
        # seed: empieza None; si la escena tiene su propia imagen la usamos,
        # si no, usamos el último frame del clip anterior
        rolling_seed: Optional[Path] = None

        usar_veo = job.generate_video and is_veo_configured()
        if not usar_veo:
            reason = ("generate_video=false" if not job.generate_video
                      else "Veo no configurado en .env")
            logger.warn(f"Veo desactivado → fallback pantalla negra ({reason})")

        for i, sc in enumerate(job.scenes):
            job.progress = 20 + int((i / max(1, len(job.scenes))) * 60)
            job.current_step = f"escena {i+1}/{len(job.scenes)}"
            storage.save_job(job)

            clip_out = storage.clip_path(job_id, i)
            # Prioridad de seed: imagen de la escena > último frame anterior
            seed = scene_refs[i] or rolling_seed

            if usar_veo:
                logger.step(f"  Veo escena {i+1}/{len(job.scenes)}")
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
                    # Extraer último frame como semilla para la PRÓXIMA escena
                    seed_next = storage.job_dir(job_id) / "clips" / f"seed_{i+1:03d}.png"
                    new_seed = veo_service.extract_last_frame(clip, seed_next, logger)
                    rolling_seed = new_seed or rolling_seed
                    continue
                logger.warn(f"  Veo falló escena {i+1} → fallback negro")

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

        final_out = storage.final_path(job_id)
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
