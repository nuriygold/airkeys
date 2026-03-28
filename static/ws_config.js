// Auto-detects host — works locally and via any tunnel
window.AIRKEYS_WS = (location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host;
