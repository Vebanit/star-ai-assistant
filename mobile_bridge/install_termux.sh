#!/data/data/com.termux/files/usr/bin/sh
set -eu

pkg update
pkg install -y python termux-api

echo "Termux packages installed."
echo "Now run:"
echo "export STAR_BASE_URL=\"http://YOUR-LAPTOP-IP:8000\""
echo "export STAR_DEVICE_ID=\"bajrangi_phone\""
echo "export STAR_DEVICE_NAME=\"Bajrangi Phone\""
echo "python termux_star_bridge.py"
