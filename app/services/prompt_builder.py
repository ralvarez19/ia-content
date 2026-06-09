"""Construye prompts cinematográficos por escena, manteniendo continuidad.

Con escenas explícitas: cada escena tiene su propia descripción y diálogo,
por lo que el prompt builder ya NO tiene que partir el texto. Solo arma el
anchor visual compartido + la descripción específica de la escena +
indicaciones de continuidad.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

from app.models import Scene


@dataclass
class PromptContext:
    title: str
    style: Optional[str] = None
    aspect_ratio: str = "9:16"
    has_any_reference: bool = False


def _global_anchor(ctx: PromptContext) -> str:
    """Lo que se repite en TODOS los prompts para forzar continuidad global."""
    bits = [
        f"Vertical cinematic {ctx.aspect_ratio} video",
        f'topic "{ctx.title}"' if ctx.title else "epic cinematic short",
    ]
    if ctx.style:
        bits.append(ctx.style.strip().rstrip("."))
    bits.extend([
        "photorealistic",
        "cinematic lighting",
        "dramatic shadows",
        "high detail",
        "smooth camera motion",
        "no text overlays",
        "no on-screen captions",
        "consistent character design across the entire sequence",
        "consistent color palette, lighting, and time period across all clips",
    ])
    return ", ".join(bits)


def _shot_for_index(idx: int, total: int) -> str:
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


def build_scene_prompt(
    ctx: PromptContext,
    scene: Scene,
    total_scenes: int,
    scene_has_image: bool,
) -> str:
    """Devuelve el prompt en inglés listo para Veo, para UNA escena específica."""
    anchor = _global_anchor(ctx)
    idx = scene.scene_number - 1
    shot = _shot_for_index(idx, total_scenes)
    pos = f"Scene {scene.scene_number} of {total_scenes}"

    description = scene.scene_description.strip().rstrip(".")
    narration = scene.dialogue.strip()

    continuity = (
        "Maintain strict visual continuity with previous scenes: same characters, "
        "same color palette, same lighting consistency, no sudden style cuts, "
        "no modern objects in historical settings."
    )
    if scene_has_image:
        continuity += (
            " A reference image for THIS specific scene is provided; treat it as "
            "the canonical look (subject identity, framing, colors). Animate the "
            "scene starting from that image."
        )
    elif ctx.has_any_reference:
        continuity += (
            " Some other scenes have explicit reference images; keep the same "
            "world/style they establish."
        )

    narration_hint = ""
    if narration:
        narration_hint = (
            f' The narration over this scene says: "{narration}". '
            "Match the on-screen action to the emotional beat of that narration."
        )

    return f"{anchor}. {pos}. {shot}. {description}.{narration_hint} {continuity}"
