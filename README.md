# MiniFlow

macOS menu-bar voice assistant. Hold **Fn** to speak — MiniFlow transcribes, understands, and acts.

---

## What it does

- **Voice commands** — "Send a Slack message to John saying I'll be late" → done
- **Dictation** — hold Fn anywhere, speak, release — text is typed at your cursor
- **App integrations** — None (MVP)
- **Always available** — lives in your menu bar, no window to manage

---

## Prerequisites

| Requirement | Minimum |
|-------------|---------|
| macOS | Ventura 13.0 or later |
| Architecture | Apple Silicon (arm64) |
| API Keys | Smallest AI (required) |

---

## Installation

### 1. Install MiniFlow

1. Open the DMG and drag **MiniFlow.app** into the **Applications** folder
2. Open **Terminal** (search "Terminal" in Spotlight)
3. Paste this command and press Enter:

```bash
xattr -cr /Applications/MiniFlow.app && open /Applications/MiniFlow.app
```

This clears the macOS security flag and launches MiniFlow. You only need to do this once.

### 2. Grant permissions

On first launch, macOS will ask for:

- **Microphone** — required for voice input
- **Accessibility** — required for typing text into other apps

If you accidentally deny either, re-enable in:
**System Settings → Privacy & Security → Microphone / Accessibility**

### 3. Add your API keys

On first launch, wait **~10 seconds** for the engine to start (it decompresses in the background on first run). Then open **Settings → Keys** and enter:

| Key | Where to get it |
|-----|----------------|
| Smallest AI API Key | [waves.smallest.ai](https://waves.smallest.ai) → Dashboard |

Keys are stored locally in `~/miniflow/miniflow_keys.json` and never leave your machine except to call the respective APIs.

---

## Usage

| Action | Result |
|--------|--------|
| **Hold Fn** | Start listening |
| **Release Fn** | Stop — command is processed |
| **Type in command bar** | Run a text command manually |
| **Click menu bar icon** | Open / close the window |

### Example commands

- "Open Slack"
- "Summarize this"
- "Rewrite this more professionally"
- "Fix grammar"
- "Write a quick follow up email saying I'll send the deck tomorrow"

---

## Connecting integrations

Connectors are disabled in the MVP build.

---

## What's in the .app bundle

The app is fully self-contained — no Python, no Xcode, nothing to install.

- Swift/SwiftUI menu-bar app
- Bundled Python backend (FastAPI, runs on `localhost:8765`)
- All connectors and agent logic included

---

## Building from source

```bash
# 1. Clone
git clone https://github.com/your-org/miniflow.git
cd miniflow

# 2. Install Python deps
cd miniflow-engine && pip install -r requirements.txt && cd ..

# 3. Build everything (backend + app + DMG)
./build_all.sh
```

Output: `build/MiniFlow-0.2.0.dmg`

Apps built locally bypass Gatekeeper — no `xattr` step needed.

---

## Troubleshooting

**App doesn't respond to Fn key**
→ Check Accessibility permission in System Settings → Privacy & Security.

**Transcription never starts**
→ Check Microphone permission. Verify your Smallest AI API key is set in Settings → Keys.

**"Engine failed to start" on first launch**
→ Wait a few seconds and try again — the engine decompresses on first run.

**Commands don't execute**
→ Verify your OpenAI API key is valid and has available credits.

**Check logs**
```bash
tail -f ~/miniflow/miniflow.log
```
