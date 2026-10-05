@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_CMD="
where py >nul 2>&1 && set "PYTHON_CMD=py"
if not defined PYTHON_CMD where python >nul 2>&1 && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  echo [错误] 未找到 Python。
  echo 请先安装 Python 3.10 或更高版本，并勾选 Add Python to PATH。
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/3] 正在创建 Python 环境...
  %PYTHON_CMD% -m venv .venv
  if errorlevel 1 goto :fail
)

set "PY=.venv\Scripts\python.exe"

if not exist ".venv\.deps_ok" (
  echo [2/3] 正在安装/更新依赖，首次启动可能需要几分钟...
  "%PY%" -m pip install --upgrade pip
  if errorlevel 1 goto :fail
  "%PY%" -m pip install -e "packages\markitdown[all]" fastapi uvicorn python-multipart pymupdf
  if errorlevel 1 goto :fail
  echo ok>".venv\.deps_ok"
)

if exist ".server.pid" (
  del ".server.pid" >nul 2>&1
)

echo [3/3] 正在启动论文转换器...
start "MarkItDown Server" /min cmd /c "cd /d "%~dp0" && "%PY%" local_web\server.py"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8765"
echo.
echo 已启动： http://127.0.0.1:8765
echo 浏览器会自动打开。请保持此窗口不要关闭。
echo.
echo 关闭本窗口不会自动停止后台服务；如需停止，可关闭“MarkItDown Server”窗口。
pause
exit /b 0

:fail
echo.
echo [错误] 安装或启动失败，请查看上面的错误信息。
pause
exit /b 1
