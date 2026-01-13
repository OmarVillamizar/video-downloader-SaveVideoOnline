@echo off
title FlashLoad Launcher
color 0b

echo ===================================================
echo       Iniciando FlashLoad - Video Downloader
echo ===================================================

:: Check if venv exists
if not exist "venv" (
    echo [INFO] Creando entorno virtual...
    python -m venv venv
)

:: Activate venv
call venv\Scripts\activate

:: Install requirements if not already present (simplified check)
if not exist "venv\Lib\site-packages\flask" (
    echo [INFO] Instalando dependencias...
    pip install flask yt-dlp
)

:: Run ffmpeg setup
echo.
echo [INFO] Verificando FFmpeg...
python setup_ffmpeg.py

echo.
echo [INFO] Iniciando servidor...
echo [INFO] La aplicacion se abrira en tu navegador predeterminado.
echo.

:: Open browser in background after a short delay
start "" "http://127.0.0.1:5000"

:: Run the app
python app.py

pause
