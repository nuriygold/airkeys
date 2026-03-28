#!/usr/bin/env python3
"""
AirKeys — AI Wireless Keyboard Server
iPad PWA → WebSocket → Mac keystrokes via pyautogui

Single-port design: HTTP static serving + WebSocket on the same port (8766).
One tunnel (ngrok / localhost.run / Cloudflare) covers everything.
"""

import asyncio
import json
import os
import socket
import qrcode
from pathlib import Path

import websockets
from websockets.asyncio.server import serve as ws_serve
from websockets.http11 import Request, Response
from websockets.datastructures import Headers
import pyautogui

# ── Config ────────────────────────────────────────────────────────────────────
PORT       = 8766          # single port for both HTTP and WebSocket
STATIC_DIR = Path(__file__).parent / "static"

MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.js':   'application/javascript; charset=utf-8',
    '.css':  'text/css; charset=utf-8',
    '.png':  'image/png',
    '.ico':  'image/x-icon',
    '.json': 'application/json',
    '.txt':  'text/plain; charset=utf-8',
}

# ── API key ───────────────────────────────────────────────────────────────────
def load_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        for p in [
            Path.home() / ".openclaw" / "secrets.json",
            Path("/Users/claw/openclaw/workspace/secrets.json"),
        ]:
            if p.exists():
                try:
                    key = json.loads(p.read_text()).get("anthropic_api_key", "")
                    if key:
                        break
                except Exception:
                    pass
    return key

ANTHROPIC_API_KEY = load_api_key()

# ── Local IP ──────────────────────────────────────────────────────────────────
def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()

LOCAL_IP = get_local_ip()

# ── Keystroke handler ─────────────────────────────────────────────────────────
pyautogui.FAILSAFE = False
pyautogui.PAUSE    = 0

SPECIAL_KEY_MAP = {
    "return": "return", "enter": "return",
    "backspace": "backspace", "delete": "delete",
    "escape": "escape", "tab": "tab", "space": "space",
    "up": "up", "down": "down", "left": "left", "right": "right",
    "home": "home", "end": "end",
    "pageup": "pageup", "pagedown": "pagedown",
    "f1":"f1","f2":"f2","f3":"f3","f4":"f4","f5":"f5","f6":"f6",
    "f7":"f7","f8":"f8","f9":"f9","f10":"f10","f11":"f11","f12":"f12",
    "cmd": "command", "command": "command",
    "ctrl": "ctrl", "alt": "alt", "shift": "shift",
    "capslock": "capslock",
}

def handle_key_event(msg):
    t = msg.get("type")
    if t == "key":
        pyautogui.press(msg["value"])
    elif t == "special":
        pyautogui.press(SPECIAL_KEY_MAP.get(msg["value"].lower(), msg["value"]))
    elif t == "text":
        pyautogui.write(msg["value"], interval=0.01)
    elif t == "combo":
        pyautogui.hotkey(*[SPECIAL_KEY_MAP.get(k.lower(), k) for k in msg["keys"]])

# ── AI Suggestions ────────────────────────────────────────────────────────────
async def get_suggestions(text: str) -> list:
    if not ANTHROPIC_API_KEY or not text.strip():
        return []
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        raw = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": (
                f'The user is typing: "{text}"\n'
                "Suggest 3 short completions (2-4 words each). "
                "Reply ONLY with a JSON array of 3 strings."
            )}]
        ).content[0].text.strip()
        return json.loads(raw)
    except Exception as e:
        print(f"[suggestions] {e}")
        return []

# ── HTTP static file handler ──────────────────────────────────────────────────
def serve_static(path: str) -> Response:
    """Return a websockets HTTP Response for a static file."""
    path = path.lstrip("/").split("?")[0].split("#")[0] or "index.html"
    file_path = STATIC_DIR / path
    # Security: don't escape static dir
    try:
        file_path.resolve().relative_to(STATIC_DIR.resolve())
    except ValueError:
        return Response(403, "Forbidden", Headers([]), b"Forbidden")

    if not file_path.exists() or not file_path.is_file():
        file_path = STATIC_DIR / "index.html"
    if not file_path.exists():
        return Response(404, "Not Found", Headers([]), b"Not Found")

    content = file_path.read_bytes()
    mime    = MIME_TYPES.get(file_path.suffix.lower(), "application/octet-stream")
    return Response(200, "OK", Headers([
        ("Content-Type",   mime),
        ("Content-Length", str(len(content))),
        ("Cache-Control",  "no-cache"),
    ]), content)

# ── WebSocket + HTTP combined handler ────────────────────────────────────────
connected_clients: set = set()

async def process_request(connection, request: Request):
    """Called for every incoming HTTP request.
    Return None → proceed with WebSocket handshake.
    Return Response → send it as plain HTTP and close.
    """
    upgrade = request.headers.get("Upgrade", "").lower()
    if upgrade == "websocket":
        return None   # hand off to ws_handler
    return serve_static(request.path)

async def ws_handler(websocket):
    connected_clients.add(websocket)
    print(f"[+] iPad connected: {websocket.remote_address}")
    try:
        async for raw in websocket:
            try:
                msg   = json.loads(raw)
                mtype = msg.get("type")

                if mtype in ("key", "special", "text", "combo"):
                    handle_key_event(msg)

                elif mtype == "suggest":
                    suggestions = await get_suggestions(msg.get("text", ""))
                    await websocket.send(json.dumps({"type": "suggestions", "items": suggestions}))

                elif mtype == "ping":
                    await websocket.send(json.dumps({"type": "pong"}))

            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"[error] {e}")
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f"[-] iPad disconnected: {websocket.remote_address}")

# ── QR Code ───────────────────────────────────────────────────────────────────
def print_qr(url: str):
    qr = qrcode.QRCode(border=1)
    qr.add_data(url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

# ── Main ──────────────────────────────────────────────────────────────────────
async def main():
    local_url = f"http://{LOCAL_IP}:{PORT}"

    # ws_config.js: auto-detect WebSocket URL from page host at runtime
    # Works for local, ngrok, Cloudflare — no env var needed
    ws_config = STATIC_DIR / "ws_config.js"
    ws_config.write_text(
        "// Auto-detects host — works locally and via any tunnel\n"
        "window.AIRKEYS_WS = (location.protocol === 'https:' ? 'wss://' : 'ws://')"
        " + location.host;\n"
    )

    print("\n" + "═" * 52)
    print("  ✦  AirKeys — AI Wireless Keyboard")
    print("═" * 52)
    print(f"  Local URL : {local_url}")
    print(f"  Port      : {PORT}  (HTTP + WebSocket on same port)")
    ai_status = "✓ enabled (Claude Haiku)" if ANTHROPIC_API_KEY else "✗ disabled (no API key)"
    print(f"  AI mode   : {ai_status}")
    print("═" * 52)
    print("\n  Local QR (same-network access):\n")
    print_qr(local_url)
    print(f"\n  Or open: {local_url}")
    print("\n  For remote access (different network):")
    print("  ssh -R 80:localhost:8766 nokey@localhost.run")
    print("  ↳ gives you a public HTTPS URL — no account needed\n")

    async with ws_serve(ws_handler, "0.0.0.0", PORT,
                        process_request=process_request):
        print(f"  Waiting for connection... (Ctrl+C to stop)\n")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[AirKeys stopped]")
