#!/bin/bash
# AirKeys launcher — installs deps if needed, then starts the server
cd "$(dirname "$0")"

echo "🔧 Checking dependencies..."
pip3 install -r requirements.txt -q --break-system-packages 2>/dev/null || \
  pip3 install -r requirements.txt -q

echo "🚀 Starting AirKeys..."
python3 server.py
