@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo [1/2] Creating virtual environment...
  py -3 -m venv .venv
  echo [2/2] Installing MarkItDown PDF dependencies...
  .venv\Scripts\python.exe -m pip install -e "packages\markitdown[pdf]" PyMuPDF
)
echo.
echo MarkItDown web UI: http://127.0.0.1:8765
start "" http://127.0.0.1:8765
.venv\Scripts\python.exe local_web\server.py
pause
