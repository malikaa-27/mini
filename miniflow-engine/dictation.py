"""
Dictation — keystroke injection into the focused app.
Uses pyobjc Quartz CGEvent for key simulation (same API as the old Rust impl).
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
from typing import Callable, Awaitable

log = logging.getLogger("dictation")
_broadcaster: Callable | None = None
_active = False


def set_event_broadcaster(fn: Callable):
    global _broadcaster
    _broadcaster = fn


async def _emit(event: str, payload):
    if _broadcaster:
        await _broadcaster(event, payload)


try:
    from Quartz import AXIsProcessTrusted as _AXIsProcessTrusted
    def AXIsProcessTrusted() -> bool:
        return _AXIsProcessTrusted()
except Exception:
    def AXIsProcessTrusted() -> bool:
        return False


def check_accessibility() -> bool:
    return AXIsProcessTrusted()


def open_accessibility_settings():
    subprocess.Popen([
        "open",
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
    ])


def get_dictation_status() -> bool:
    return _active


async def start_dictation():
    global _active
    _active = True
    await _emit("dictation-status", {"active": True, "error": None})
    log.info("Dictation started")


async def stop_dictation():
    global _active
    _active = False
    await _emit("dictation-status", {"active": False, "error": None})
    log.info("Dictation stopped")


def type_text(text: str):
    """Inject text into the focused app via CGEvent.

    \\n in text is emitted as Shift+Return so it inserts a new line
    without submitting forms / sending messages.
    """
    try:
        import Quartz
        if not text:
            return
        src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
        log.info(f"type_text: injecting {len(text)} chars (trusted={AXIsProcessTrusted()})")
        kVK_Return = 0x24
        segments = text.split('\n')
        for idx, segment in enumerate(segments):
            if segment:
                down = Quartz.CGEventCreateKeyboardEvent(src, 0, True)
                up   = Quartz.CGEventCreateKeyboardEvent(src, 0, False)
                Quartz.CGEventKeyboardSetUnicodeString(down, len(segment), segment)
                Quartz.CGEventKeyboardSetUnicodeString(up,   len(segment), segment)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, down)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, up)
            if idx < len(segments) - 1:
                ret_down = Quartz.CGEventCreateKeyboardEvent(src, kVK_Return, True)
                ret_up   = Quartz.CGEventCreateKeyboardEvent(src, kVK_Return, False)
                Quartz.CGEventSetFlags(ret_down, Quartz.kCGEventFlagMaskShift)
                Quartz.CGEventSetFlags(ret_up,   Quartz.kCGEventFlagMaskShift)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, ret_down)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, ret_up)
        log.info("type_text: done")
    except Exception as e:
        log.error(f"type_text failed: {e}")
