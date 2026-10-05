#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
if [ ! -x ".venv/bin/python" ]; then
  echo "[1/2] Creating virtual environment..."
  python3 -m venv .venv
  echo "[2/2] Installing MarkItDown PDF dependencies..."
  .venv/bin/python -m pip install -e 'packages/markitdown[pdf]' PyMuPDF
fi
echo "MarkItDown web UI: http://127.0.0.1:8765"
if command -v open >/dev/null 2>&1; then open http://127.0.0.1:8765; fi
exec .venv/bin/python local_web/server.py
