"""Divide el diálogo del usuario en N partes (una por clip).

El usuario nos da el diálogo completo y la cantidad de clips. La tarea es
particionarlo en chunks balanceados, respetando límites de frase cuando se
puede para que la narración suene natural.
"""
from __future__ import annotations
import re
from typing import List


_SENT_SPLIT = re.compile(r"(?<=[\.\!\?])\s+")


def split_dialogue(dialogue: str, n_clips: int) -> List[str]:
    """Parte `dialogue` en `n_clips` segmentos balanceados.

    Estrategia:
      1. Si hay suficientes frases (>= n_clips), agrupa frases en bloques
         con cantidad de palabras similar.
      2. Si hay menos frases que clips, parte por palabras.
    """
    dialogue = dialogue.strip()
    if not dialogue:
        return [""] * n_clips
    if n_clips <= 1:
        return [dialogue]

    sentences = [s.strip() for s in _SENT_SPLIT.split(dialogue) if s.strip()]

    if len(sentences) == n_clips:
        return sentences
    if len(sentences) > n_clips:
        return _group_sentences(sentences, n_clips)
    return _split_by_words(dialogue, n_clips)


def _group_sentences(sentences: List[str], n: int) -> List[str]:
    total_words = sum(len(s.split()) for s in sentences)
    target = total_words / n
    out: List[str] = []
    buf: List[str] = []
    buf_words = 0
    for s in sentences:
        w = len(s.split())
        buf.append(s)
        buf_words += w
        if buf_words >= target and len(out) < n - 1:
            out.append(" ".join(buf))
            buf = []
            buf_words = 0
    if buf:
        out.append(" ".join(buf))
    # Si quedamos cortos por redondeo, rellenar con "" para llegar a n
    while len(out) < n:
        out.append("")
    return out[:n]


def _split_by_words(text: str, n: int) -> List[str]:
    words = text.split()
    if not words:
        return [""] * n
    chunk = max(1, len(words) // n)
    parts = [" ".join(words[i*chunk:(i+1)*chunk]) for i in range(n - 1)]
    parts.append(" ".join(words[(n-1)*chunk:]))
    return parts
