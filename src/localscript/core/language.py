from __future__ import annotations

from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0


def detect_language(text: str) -> str:
    normalized = text.strip()
    if not normalized:
        return "unknown"
    if normalized.isascii():
        return "en"
    try:
        return detect(normalized)
    except LangDetectException:
        return "unknown"
