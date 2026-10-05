# MarkItDown PDF → Markdown — Render deployment

This package is ready for Render.

Render settings:
- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `python local_web/server.py`
- Health Check Path: `/health`

The server binds to `0.0.0.0` and reads Render's `PORT` environment variable.

IMPORTANT:
Upload the CONTENTS of this ZIP to the ROOT of your GitHub repository.
These must be visible at repository root:
requirements.txt
render.yaml
local_web/
packages/

Do not add an extra outer project directory.
