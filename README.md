# ⌘ AirKeys

**Turn your iPad into a wireless AI keyboard for your Mac — no app install, no cable, no account.**

AirKeys is a Progressive Web App (PWA) that runs in Safari on any iPad and sends keystrokes to your Mac over WebSocket. It includes a full QWERTY layout, modifier keys, voice input, and Claude-powered AI text suggestions — all in a single-port Python server you can tunnel over the internet in seconds.

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

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, vanilla JS, Web Speech API |
| PWA | `apple-mobile-web-app-capable` meta tags |
| Backend | Python 3, asyncio, websockets |
| Keystroke injection | pyautogui |
| AI | Anthropic Claude Haiku (`claude-haiku-4-5-20251001`) |
| Tunnel | localhost.run (SSH reverse proxy) |

---

## Project Structure

```
airkeys/
├── server.py          # Python async server (HTTP + WebSocket, port 8766)
├── launch.sh          # One-command launcher (installs deps + starts server)
├── requirements.txt   # Python dependencies
└── static/
    ├── index.html     # Full PWA keyboard UI
    └── ws_config.js   # Auto-generated WebSocket URL (written at server start)
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

## Built for LovHack

AirKeys was built in under 24 hours for the **LovHack** hackathon. The goal: eliminate the friction of switching between an iPad and Mac keyboard during creative work.

---

## License

MIT
