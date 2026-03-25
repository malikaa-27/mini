"""
Audio — streams PCM chunks to the Smallest AI Waves WebSocket API in real-time.
Falls back to REST POST if the streaming connection fails.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Callable, Awaitable

import httpx
import websockets

import config

log = logging.getLogger("audio")

_WSS_URL = "wss://api.smallest.ai/waves/v1/pulse/get_text"
_REST_URL = "https://waves-api.smallest.ai/api/v1/pulse/get_text"


async def stream_transcribe(
    chunk_queue: asyncio.Queue,
    on_partial: Callable[[str], Awaitable[None]] | None = None,
) -> str:
    """
    Connect to Smallest AI WSS, forward raw PCM chunks from chunk_queue,
    collect partial transcripts, and return the final transcript.
    Put None into chunk_queue to signal end of audio.
    """
    try:
        key = config.get_smallest_key()
    except ValueError as e:
        raise RuntimeError(str(e)) from e

    headers = {"Authorization": f"Bearer {key}"}
    url = f"{_WSS_URL}?language=en&model=pulse"

    final_transcript = ""
    t0 = time.perf_counter()

    async with websockets.connect(url, additional_headers=headers) as ws:
        async def sender():
            while True:
                chunk = await chunk_queue.get()
                if chunk is None:  # sentinel — end of audio
                    await ws.close()
                    return
                await ws.send(chunk)

        async def receiver():
            nonlocal final_transcript
            try:
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                    except Exception:
                        continue
                    text = (data.get("transcription") or data.get("transcript")
                            or data.get("text") or "")
                    is_final = data.get("is_final", False) or data.get("isFinal", False)
                    if text and on_partial:
                        await on_partial(text)
                    if is_final and text:
                        final_transcript = text
            except websockets.exceptions.ConnectionClosed:
                pass

        await asyncio.gather(sender(), receiver())

    stt_ms = (time.perf_counter() - t0) * 1000
    log.info(f"[LATENCY] Streaming STT: {stt_ms:.0f}ms | transcript: '{final_transcript}'")
    return final_transcript


async def transcribe(wav_bytes: bytes) -> str:
    """Fallback: POST complete WAV to REST endpoint."""
    try:
        key = config.get_smallest_key()
    except ValueError as e:
        raise RuntimeError(str(e)) from e

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "audio/wav"}
    params = {"model": "pulse", "language": "en"}

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(_REST_URL, headers=headers, params=params, content=wav_bytes)
        resp.raise_for_status()
        data = resp.json()
    stt_ms = (time.perf_counter() - t0) * 1000

    transcript = data.get("transcription") or data.get("transcript") or ""
    log.info(f"[LATENCY] REST STT: {stt_ms:.0f}ms | transcript: '{transcript}'")
    return transcript
