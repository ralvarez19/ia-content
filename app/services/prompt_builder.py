"""Construye prompts cinematográficos por clip manteniendo continuidad.

Cada prompt incluye:
  - "Anchor visual" compartido entre todos los clips (estilo, escenario,
    iluminación, paleta, época)
  - Descripción específica del clip (acción/cámara) derivada del segmento
    del diálogo correspondiente
  - Indicador de posición ("Clip N of M")
  - Restricciones explícitas de continuidad
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PromptContext:
    scene: str
    dialogue: str
    style: Optional[str] = None
    reference_description: Optional[str] = None  # texto que describe la imagen ref
    aspect_ratio: str = "9:16"
    has_reference_image: bool = False


def _style_anchor(ctx: PromptContext) -> str:
    """Bloque que se repite en todos los clips para forzar continuidad."""
    bits = [
        f"Vertical cinematic {ctx.aspect_ratio} video",
        ctx.scene.strip().rstrip(".") if ctx.scene else "epic mythological scene",
    ]
    if ctx.style:
        bits.append(ctx.style.strip().rstrip("."))
    if ctx.reference_description:
        bits.append(f"matching the reference image: {ctx.reference_description}")
    bits.extend([
        "photorealistic",
        "cinematic lighting",
        "dramatic shadows",
        "high detail",
        "smooth camera motion",
        "no text overlays",
        "no on-screen captions",
        "consistent character design across the entire sequence",
        "consistent setting, color palette, lighting, and time period across all clips",
    ])
    return ", ".join(bits)


def _shot_for_index(idx: int, total: int) -> str:
    """Sugiere un tipo de toma según la posición del clip en la secuencia."""
    if idx == 0:
        return "establishing wide shot with a strong visual hook in the first second"
    if idx == total - 1:
        return "slow push-in close-up that resolves the emotional beat"
    rotation = [
        "medium tracking shot following the subject",
        "low-angle hero shot",
        "slow crane shot rising over the setting",
        "over-the-shoulder dramatic angle",
        "side dolly shot revealing the environment",
        "tight close-up on the subject's face",
    ]
    return rotation[(idx - 1) % len(rotation)]


def build_clip_prompt(
    ctx: PromptContext,
    clip_idx: int,
    total_clips: int,
    narration_segment: str,
) -> str:
    """Devuelve el prompt completo en inglés listo para Veo."""
    anchor = _style_anchor(ctx)
    shot = _shot_for_index(clip_idx, total_clips)
    pos = f"Clip {clip_idx + 1} of {total_clips}"

    continuity = (
        "Maintain strict visual continuity with previous clips: same architecture, "
        "same color palette, same lighting, same time of day, no sudden character "
        "changes, no modern objects, no scene cuts to unrelated locations."
    )
    if ctx.has_reference_image:
        continuity += (
            " Treat the supplied reference image as the canonical look of this world; "
            "every clip is a different angle/moment within the SAME scene shown there."
        )

    narration_hint = ""
    if narration_segment.strip():
        # Mantenemos el narration tag para que Veo entienda la energía,
        # pero le decimos que NO escriba el texto en pantalla.
        narration_hint = (
            f" The narration over this clip says: \"{narration_segment.strip()}\". "
            "Match the on-screen action to the emotional beat of that narration."
        )

    return (
        f"{anchor}. {pos}. {shot}.{narration_hint} {continuity}"
    )


def build_all_prompts(
    ctx: PromptContext,
    narration_chunks: List[str],
) -> List[str]:
    n = len(narration_chunks)
    return [
        build_clip_prompt(ctx, i, n, narration_chunks[i])
        for i in range(n)
    ]
