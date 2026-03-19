"""
MiniFlow Engine — FastAPI backend

HTTP:      POST http://localhost:8765/invoke/:command
           GET  http://localhost:8765/health
           GET  http://localhost:8765/callback        ← OAuth token receiver
WebSocket: ws://localhost:8765/ws
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import re
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

import config
import agent
import audio
import dictation
import history
import dictionary
import shortcuts

import pathlib
_log_path = pathlib.Path.home() / "miniflow" / "miniflow.log"
_log_path.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s %(name)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(_log_path), encoding="utf-8"),
    ],
)
log = logging.getLogger("main")

# ── WebSocket connection manager ──

class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)

    async def broadcast(self, event: str, payload: Any):
        msg = json.dumps({"event": event, "payload": payload})
        for ws in list(self.connections):
            try:
                await ws.send_text(msg)
            except Exception:
                self.connections.remove(ws)

manager = ConnectionManager()

# ── App lifespan ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("MiniFlow engine starting on http://localhost:8765")
    dictation.set_event_broadcaster(manager.broadcast)
    agent.set_event_broadcaster(manager.broadcast)
    yield
    log.info("MiniFlow engine shutting down")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Health check ──

@app.get("/health")
async def health():
    return {"status": "ok"}

# ── OAuth callback (legacy, unused) ──

_SUCCESS_HTML = """
<!DOCTYPE html>
<html>
<head><title>MiniFlow — Connected</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       display:flex;justify-content:center;align-items:center;
       height:100vh;margin:0;background:#0f1923;color:#fff}
  .box{text-align:center}
  h2{font-size:1.4rem;font-weight:600;margin-bottom:.5rem}
  p{color:#8899aa;font-size:.9rem}
</style></head>
<body><div class="box">
  <h2>✓ Connected successfully</h2>
  <p>You can close this window and return to MiniFlow.</p>
</div></body></html>
"""

_FAIL_HTML = """
<!DOCTYPE html>
<html>
<head><title>MiniFlow — Error</title>
<style>
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
       display:flex;justify-content:center;align-items:center;
       height:100vh;margin:0;background:#0f1923;color:#fff}
  .box{text-align:center}
  h2{font-size:1.4rem;font-weight:600;margin-bottom:.5rem;color:#ff6b6b}
  p{color:#8899aa;font-size:.9rem}
</style></head>
<body><div class="box">
  <h2>Connection failed</h2>
  <p>{error}</p>
</div></body></html>
"""

@app.get("/callback")
async def oauth_callback(data: str = "", state: str = ""):
    if not data:
        return HTMLResponse(_FAIL_HTML.format(error="No token data received."), status_code=400)
    try:
        # The Vercel proxy encodes the payload as base64url JSON
        # (or AES-256-GCM if ENCRYPTION_KEY is set on Vercel — we support plain only)
        padding = 4 - len(data) % 4
        padded = data + ("=" * (padding % 4))
        raw = base64.urlsafe_b64decode(padded).decode("utf-8")
        payload = json.loads(raw)
        provider = payload.get("provider")
        if not provider:
            raise ValueError("Missing provider in token payload")
        oauth.save_token(provider, payload)
        log.info(f"OAuth token saved for: {provider}")
        await manager.broadcast("oauth-connected", {"provider": provider})
        return HTMLResponse(_SUCCESS_HTML)
    except Exception as e:
        log.error(f"OAuth callback error: {e}")
        return HTMLResponse(_FAIL_HTML.format(error=str(e)), status_code=400)

# ── WebSocket endpoint ──

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(ws)

# ── Invoke dispatcher ──

async def _transcribe_audio(b: dict):
    import base64
    bundle_id = b.get("bundleID")
    if bundle_id:
        agent.set_target_app(bundle_id)
    wav_bytes = base64.b64decode(b["audio"])
    transcript = await audio.transcribe(wav_bytes)
    settings = config.get_advanced_settings()
    if settings.get("filler_removal"):
        transcript = _remove_filler_words(transcript, config.get_all_filler_words())
    if settings.get("numeral_mode"):
        transcript = _convert_numerals(transcript)
    transcript = dictionary.apply(transcript)
    transcript = shortcuts.apply(transcript)
    return {"transcript": transcript}


try:
    from word2number import w2n as _w2n_mod
    def _w2i(phrase: str) -> str | None:
        try:
            return str(_w2n_mod.word_to_num(phrase))
        except Exception:
            return None
except ImportError:
    def _w2i(phrase: str) -> str | None:  # type: ignore[misc]
        return None

_DIGIT_WORDS = {
    "zero": "0", "oh": "0", "one": "1", "two": "2", "three": "3",
    "four": "4", "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
}

_COMPOUND_WORDS = frozenset({
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
    "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
    "hundred", "thousand", "million", "billion",
})

_ANY_NUM_WORD = frozenset(set(_DIGIT_WORDS) | _COMPOUND_WORDS)

# Ordinal units: only used when following a tens number or in a date context.
_ORDINAL_UNITS = {
    "first": (1, "st"), "second": (2, "nd"), "third": (3, "rd"),
    "fourth": (4, "th"), "fifth": (5, "th"), "sixth": (6, "th"),
    "seventh": (7, "th"), "eighth": (8, "th"), "ninth": (9, "th"),
}

_ORDINAL_ALL = {
    **_ORDINAL_UNITS,
    "tenth": (10, "th"), "eleventh": (11, "th"), "twelfth": (12, "th"),
    "thirteenth": (13, "th"), "fourteenth": (14, "th"), "fifteenth": (15, "th"),
    "sixteenth": (16, "th"), "seventeenth": (17, "th"), "eighteenth": (18, "th"),
    "nineteenth": (19, "th"), "twentieth": (20, "th"),
    "thirtieth": (30, "th"), "fortieth": (40, "th"), "fiftieth": (50, "th"),
    "sixtieth": (60, "th"), "seventieth": (70, "th"), "eightieth": (80, "th"),
    "ninetieth": (90, "th"),
}

_MONTHS = frozenset({
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
})


def _convert_numerals(text: str) -> str:
    """Convert spoken number words to numerals.

    PIN/phone  : 'two five six four'                → '2564'
    Plus prefix: 'plus one four four four'          → '+1444'
    Compound   : 'twenty-five'                      → '25'
    Decimal    : 'one point five'                   → '1.5'
    Time       : 'three forty-five P M'             → '3:45 PM'
    Date ord.  : 'April twenty-seventh'             → 'April 27th'
    """
    if not text:
        return text

    # ── Pre-passes ────────────────────────────────────────────────────────────
    # Hyphenated compounds + ordinals: "twenty-five" / "twenty-seventh" → two tokens
    text = re.sub(
        r'\b(twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)'
        r'-(one|two|three|four|five|six|seven|eight|nine|'
        r'first|second|third|fourth|fifth|sixth|seventh|eighth|ninth)\b',
        r'\1 \2', text, flags=re.I,
    )
    # Spaced AM/PM: "P M" / "A M" → "PM" / "AM"
    text = re.sub(r'\bA\s+M\b', 'AM', text, flags=re.I)
    text = re.sub(r'\bP\s+M\b', 'PM', text, flags=re.I)

    def _clean(tok: str) -> str:
        return re.sub(r"[.,;:!?'\"]+$", "", tok).lower()

    def _trail(tok: str) -> str:
        return tok[len(re.sub(r"[.,;:!?'\"]+$", "", tok)):]

    def _is_compound_start(idx: int) -> bool:
        """True when token starts a compound number span."""
        c = _clean(tokens[idx])
        if c in _COMPOUND_WORDS:
            return True
        # digit word immediately before a compound word (e.g. "one hundred")
        if c in _DIGIT_WORDS and idx + 1 < len(tokens) and _clean(tokens[idx + 1]) in _COMPOUND_WORDS:
            return True
        return False

    tokens = text.split()
    out: list[str] = []
    i = 0

    while i < len(tokens):
        c = _clean(tokens[i])

        # ── plus prefix → phone / country code ───────────────────────────────
        if c == "plus" and i + 1 < len(tokens) and _clean(tokens[i + 1]) in _DIGIT_WORDS:
            i += 1
            run = "+"
            while i < len(tokens) and _clean(tokens[i]) in _DIGIT_WORDS:
                dig = _DIGIT_WORDS[_clean(tokens[i])]
                trail = _trail(tokens[i])
                i += 1
                if trail:
                    out.append(run + dig + trail)
                    run = ""
                    break
                run += dig
            if run:
                out.append(run)
            continue

        # ── compound number span (word2number) ───────────────────────────────
        if _is_compound_start(i):
            j = i
            parts: list[str] = []
            while j < len(tokens):
                ct = _clean(tokens[j])
                if ct in _ANY_NUM_WORD:
                    parts.append(ct)
                    j += 1
                elif ct == "and" and j + 1 < len(tokens) and _clean(tokens[j + 1]) in _ANY_NUM_WORD:
                    j += 1  # skip "and"; w2n handles without it
                else:
                    break

            phrase = " ".join(parts)
            converted = _w2i(phrase)
            if converted is not None:
                trail = _trail(tokens[j - 1])
                c_next = _clean(tokens[j]) if j < len(tokens) else ""
                if not trail and c_next in _ORDINAL_UNITS:
                    # "twenty seventh" → "27th"
                    unit_val, unit_suf = _ORDINAL_UNITS[c_next]
                    unit_trail = _trail(tokens[j])
                    out.append(str(int(converted) + unit_val) + unit_suf + unit_trail)
                    j += 1
                elif not trail and c_next in ("am", "pm"):
                    # Multi-token span + AM/PM → try hour:minute split first
                    # e.g. "ten thirty AM" → 10:30 AM, not "40 AM"
                    time_str = None
                    if len(parts) > 1:
                        hr = _w2i(parts[0])
                        mn = _w2i(" ".join(parts[1:]))
                        if hr and mn and 1 <= int(hr) <= 12 and 0 <= int(mn) <= 59:
                            time_str = f"{int(hr)}:{int(mn):02d} {tokens[j].upper()}"
                    out.append(time_str if time_str else converted + " " + tokens[j].upper())
                    j += 1
                else:
                    out.append(converted + trail)
                i = j
                continue
            # word2number failed → fall through to digit-sequence path if applicable
            if c not in _DIGIT_WORDS:
                out.append(tokens[i])
                i += 1
                continue

        # ── single-digit word sequence → concatenated run (PIN / code) ───────
        if c in _DIGIT_WORDS:
            run = ""
            while i < len(tokens) and _clean(tokens[i]) in _DIGIT_WORDS:
                dig = _DIGIT_WORDS[_clean(tokens[i])]
                trail = _trail(tokens[i])
                i += 1
                if trail:
                    out.append(run + dig + trail)
                    run = ""
                    break
                run += dig
            if run:
                out.append(run)
            continue

        out.append(tokens[i])
        i += 1

    # ── Post-passes ───────────────────────────────────────────────────────────
    result = " ".join(out)
    # Phone fragments: "+1, 732, 405, 1036" → "+17324051036"
    result = re.sub(
        r'\+\d+(?:,\s*\d+)+',
        lambda m: '+' + re.sub(r'\D', '', m.group(0)),
        result,
    )
    # Decimal: "1 point 5" → "1.5"
    result = re.sub(r'(\d+)\s+[Pp]oint\s+(\d+)', r'\1.\2', result)
    # Time: "3 45 PM" → "3:45 PM"  (minute must be 00-59)
    result = re.sub(r'\b(\d{1,2})\s+([0-5]\d)\s*(AM|PM)\b', r'\1:\2 \3', result)

    # ── Ordinal post-passes (date context only) ───────────────────────────────
    _ord_unit_pat = '|'.join(re.escape(w) for w in _ORDINAL_UNITS)
    _ord_all_pat  = '|'.join(re.escape(w) for w in _ORDINAL_ALL)
    _month_pat    = '|'.join(re.escape(m) for m in _MONTHS)

    def _ord_unit_val(word: str) -> tuple[int, str]:
        return _ORDINAL_UNITS[word.lower()]

    def _ord_all_val(word: str) -> tuple[int, str]:
        return _ORDINAL_ALL[word.lower()]

    # "20 seventh" → "27th"  (STT pre-digitised the tens word)
    result = re.sub(
        rf'\b(\d+)\s+({_ord_unit_pat})([.,;:!?]?)\b',
        lambda m: str(int(m.group(1)) + _ord_unit_val(m.group(2))[0])
                  + _ord_unit_val(m.group(2))[1] + m.group(3),
        result, flags=re.I,
    )
    # "April seventh" / "January twentieth" → "April 7th" / "January 20th"
    result = re.sub(
        rf'\b({_month_pat})\s+({_ord_all_pat})([.,;:!?]?)\b',
        lambda m: m.group(1) + ' '
                  + str(_ord_all_val(m.group(2))[0]) + _ord_all_val(m.group(2))[1]
                  + m.group(3),
        result, flags=re.I,
    )
    # "seventh of April" / "first of January" → "7th of April" / "1st of January"
    result = re.sub(
        rf'\b({_ord_all_pat})\s+of\s+({_month_pat})\b',
        lambda m: str(_ord_all_val(m.group(1))[0]) + _ord_all_val(m.group(1))[1]
                  + ' of ' + m.group(2),
        result, flags=re.I,
    )

    # ── Large ordinals (always convert in numeral mode) ───────────────────────
    # "millionth" → "1000000th";  "10 millionth" → "10000000th"
    _LARGE_ORDINALS = {
        "hundredth":    100,
        "thousandth":   1_000,
        "millionth":    1_000_000,
        "billionth":    1_000_000_000,
    }
    for word, mult in _LARGE_ORDINALS.items():
        result = re.sub(
            rf'\b(?:(\d+)\s+)?{word}\b',
            lambda m, mult=mult: str((int(m.group(1)) if m.group(1) else 1) * mult) + "th",
            result, flags=re.I,
        )
    return result


def _remove_filler_words(text: str, words: list[str]) -> str:
    if not text or not words:
        return text
    candidates = [w.strip().lower() for w in words if isinstance(w, str) and w.strip()]
    if not candidates:
        return text
    # Longer phrases first so we don't partially match them.
    candidates = sorted(set(candidates), key=len, reverse=True)
    pattern = r"\\b(?:%s)\\b" % "|".join(re.escape(w) for w in candidates)
    cleaned = re.sub(pattern, "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = re.sub(r"^\s*,\s*", "", cleaned)
    cleaned = re.sub(r",\s*,+", ",", cleaned)
    cleaned = re.sub(r",\s*(?=[.?!]|$)", "", cleaned)
    cleaned = re.sub(r",\s*(\S)", r", \1", cleaned)
    return cleaned


@app.post("/invoke/{command}")
async def invoke(command: str, body: dict = {}):
    handlers = {
        # Audio
        "transcribe_audio":      lambda b: _transcribe_audio(b),
        # Agent
        "execute_command":       lambda b: agent.execute_command(b["command"]),
        # Config
        "save_api_key":          lambda b: config.save_api_key(b["service"], b["key"]),
        "get_api_key":           lambda b: config.get_api_key(b["service"]),
        "has_api_keys":          lambda b: config.has_api_keys(),
        "save_language":         lambda b: config.save_language(b["language"]),
        "get_language":          lambda b: config.get_language(),
        "get_advanced_settings": lambda b: config.get_advanced_settings(),
        "save_advanced_setting": lambda b: config.save_advanced_setting(b["key"], b["value"]),
        "save_user_name":        lambda b: config.save_user_name(b["name"]),
        "get_user_name":         lambda b: config.get_user_name(),
        # Dictation
        "start_dictation":       lambda b: dictation.start_dictation(),
        "stop_dictation":        lambda b: dictation.stop_dictation(),
        "get_dictation_status":  lambda b: dictation.get_dictation_status(),
        "check_accessibility":   lambda b: dictation.check_accessibility(),
        "open_accessibility_settings": lambda b: dictation.open_accessibility_settings(),
        # History
        "get_history":           lambda b: history.get_history(),
        "clear_history":         lambda b: history.clear_history(),
        # Dictionary
        "add_dictionary_word":   lambda b: dictionary.add_word(b["from"], b["to"]),
        "remove_dictionary_word": lambda b: dictionary.remove_word(b["from"]),
        "get_dictionary":        lambda b: dictionary.get_dictionary(),
        "import_dictionary":     lambda b: dictionary.import_dictionary(b["entries"]),
        # Shortcuts
        "add_shortcut":          lambda b: shortcuts.add_shortcut(b["trigger"], b["expansion"]),
        "remove_shortcut":       lambda b: shortcuts.remove_shortcut(b["trigger"]),
        "get_shortcuts":         lambda b: shortcuts.get_shortcuts(),
        # App
        "open_settings":         lambda b: None,
    }

    handler = handlers.get(command)
    if not handler:
        return {"error": f"Unknown command: {command}"}

    try:
        result = handler(body)
        if asyncio.iscoroutine(result):
            result = await result
        return result
    except Exception as e:
        log.error(f"[{command}] {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import sys
    import uvicorn

    # When frozen (PyInstaller bundle), GUI apps don't inherit shell env vars —
    # SSL_CERT_FILE / REQUESTS_CA_BUNDLE are unset and all HTTPS calls fail.
    # Auto-configure from the certifi bundle that PyInstaller packages.
    if getattr(sys, "frozen", False):
        try:
            import certifi
            cert = certifi.where()
            os.environ.setdefault("SSL_CERT_FILE", cert)
            os.environ.setdefault("REQUESTS_CA_BUNDLE", cert)
        except Exception:
            pass

    uvicorn.run(app, host="127.0.0.1", port=8765, reload=False)
