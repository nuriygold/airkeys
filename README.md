# ⌘ AirKeys

**Turn your iPad into a wireless AI keyboard for your Mac — no app install, no cable, no account.**

AirKeys is a Progressive Web App (PWA) that runs in Safari on any iPad and sends keystrokes to your Mac over WebSocket. It includes a full QWERTY layout, modifier keys, voice input, and Claude-powered AI text suggestions — all in a single-port Python server you can tunnel over the internet in seconds.

**Live demo:** [airkeys.vercel.app](https://airkeys.vercel.app) &nbsp;|&nbsp; **Source:** [github.com/nuriygold/airkeys](https://github.com/nuriygold/airkeys)

> The Vercel deployment serves the static frontend UI. To use AirKeys as a keyboard, run the local Python server (see Setup below) and connect your iPad to it.

---

## Features

| Feature | Details |
|---|---|
| Full QWERTY keyboard | Numbers, punctuation, all standard keys |
| Modifier keys | ⌘ Cmd, ⌃ Ctrl, ⌥ Alt, ⇧ Shift — tap to latch, auto-release after combo |
| Arrow keys | ← → on main layer, ↑ ↓ on F-key layer |
| F1–F12 | Swipe to F-key layer via tab bar |
| Voice input | 🎤 mic button — uses Web Speech API |
| AI suggestions | Claude Haiku generates 3 completions as you type |
| n8n automation | Slash commands trigger n8n webhooks — response typed back on Mac |
| Auto-reconnect | PWA reconnects automatically if connection drops |
| QR code | Terminal prints a QR for instant iPad connection |
| No install | Opens in Safari — no App Store, no signing |

---

## Architecture

```
iPad Safari (PWA)
    │
    │  WebSocket / HTTPS tunnel
    ▼
Python async server (port 8766)
    ├── HTTP: serves static/index.html + ws_config.js
    └── WebSocket: receives key events, calls pyautogui
            │
            ▼
        Mac keystrokes (pyautogui)
            │
        Claude Haiku API (AI suggestions)
```

- **Frontend:** Single `index.html` — vanilla JS, no framework, no build step
- **Backend:** `server.py` — Python asyncio + `websockets` library, single port for HTTP and WebSocket
- **Tunnel:** `localhost.run` SSH reverse tunnel — free, no account, HTTPS out of the box

---

## Setup

### Requirements

- Mac with Python 3.10+
- iPad with Safari
- Both on the same Wi-Fi **or** use the tunnel for remote access

### Install & Run

**Tab 1 — start the server:**

```bash
bash launch.sh
```

This installs Python dependencies (`websockets`, `pyautogui`, `anthropic`, `qrcode`) and starts the server on port 8766. A QR code appears in the terminal for local Wi-Fi access.

**Tab 2 — open a public HTTPS tunnel (optional, for cross-network access):**

```bash
ssh -R 80:localhost:8766 nokey@localhost.run
```

No account needed. You'll get a URL like `https://abc123.localhost.run` — open it on your iPad.

### AI Suggestions (optional)

Set your Anthropic API key to enable Claude-powered completions:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
bash launch.sh
```

Or place it in `~/.openclaw/secrets.json`:

```json
{ "anthropic_api_key": "sk-ant-..." }
```

---

## n8n Workflow Integration

AirKeys can send text to an [n8n](https://n8n.io) webhook and type the response back on your Mac — turning your keyboard into a two-way automation terminal.

### Setup

1. In n8n, create a new workflow and add a **Webhook** node (method: POST). Copy its URL.
2. Set the webhook URL before starting AirKeys:

```bash
export N8N_WEBHOOK_URL=https://your-n8n-instance.com/webhook/airkeys
bash launch.sh
```

AirKeys works fine without this — the integration is fully optional.

### Slash Commands

Type text in the keyboard, then use one of these methods to trigger n8n:

| Method | What happens |
|--------|-------------|
| Tap **⚡n8n** button | Sends the current buffer to n8n with `action: "default"` |
| Type `/n8n <text>` → tap ⚡n8n | Sends text with `action: "default"` |
| Type `/summarize <text>` → tap ⚡n8n | Sends with `action: "summarize"` |
| Type `/translate <text>` → tap ⚡n8n | Sends with `action: "translate"` |

The response from n8n is:
- Shown in a green panel on the iPad
- Typed on the Mac via pyautogui

### Webhook Payload

AirKeys POSTs JSON to your webhook URL:

```json
{
  "text": "the text content",
  "action": "default | summarize | translate"
}
```

Your n8n workflow should return JSON with a `text` field (or `output` / `message`):

```json
{ "text": "the response to type on the Mac" }
```

### Sample Workflow

Import `n8n-workflow-example.json` into n8n for a ready-to-use workflow with three branches:

- **summarize** → GPT-4o-mini summarizes the text
- **translate** → GPT-4o-mini translates to Spanish
- **default** → echoes back with a timestamp

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, vanilla JS, Web Speech API |
| PWA | `apple-mobile-web-app-capable` meta tags |
| Backend | Python 3, asyncio, websockets, aiohttp |
| Keystroke injection | pyautogui |
| AI suggestions | Anthropic Claude Haiku (`claude-haiku-4-5-20251001`) |
| Automation | n8n webhooks (optional, via `N8N_WEBHOOK_URL`) |
| Tunnel | localhost.run (SSH reverse proxy) |

---

## Project Structure

```
airkeys/
├── server.py                  # Python async server (HTTP + WebSocket, port 8766)
├── launch.sh                  # One-command launcher (installs deps + starts server)
├── requirements.txt           # Python dependencies
├── n8n-workflow-example.json  # Importable n8n workflow (summarize / translate / echo)
└── static/
    ├── index.html             # Full PWA keyboard UI
    └── ws_config.js           # Auto-generated WebSocket URL (written at server start)
```

---

## How It Works

1. `launch.sh` starts `server.py` on port 8766
2. Server writes `ws_config.js` with the correct WebSocket URL (auto-detects `ws://` vs `wss://`)
3. iPad opens the URL → Safari loads `index.html`
4. Tap a key → JS sends `{"type":"key","value":"a"}` over WebSocket
5. Server receives the message → `pyautogui.press("a")` fires on the Mac
6. Modifier combos (e.g. ⌘+C) are sent as `{"type":"combo","keys":["cmd","c"]}`
7. Every ~600ms of typing, a `suggest` message is sent → Claude returns 3 completions as chips

---

