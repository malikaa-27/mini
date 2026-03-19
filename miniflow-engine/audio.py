"""
Audio — receives a complete WAV recording from Swift and transcribes it via a
single HTTP POST to the Smallest AI Waves REST API (one-shot, no WebSocket).
"""

from __future__ import annotations

import logging
import time

import httpx

import config

log = logging.getLogger("audio")


async def transcribe(wav_bytes: bytes) -> str:
    """POST raw WAV bytes to the Waves REST endpoint and return the transcript."""
    try:
        key = config.get_smallest_key()
    except ValueError as e:
        raise RuntimeError(str(e)) from e

    url = "https://waves-api.smallest.ai/api/v1/pulse/get_text"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "audio/wav",
    }
    params = {"model": "pulse", "language": "en"}

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, headers=headers, params=params, content=wav_bytes)
        resp.raise_for_status()
        data = resp.json()
    stt_ms = (time.perf_counter() - t0) * 1000

    transcript = data.get("transcription") or data.get("transcript") or ""
    log.info(f"[LATENCY] Smallest AI STT: {stt_ms:.0f}ms | transcript: '{transcript}'")
    return transcript
