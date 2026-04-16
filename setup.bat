@echo off
REM ============================================================
REM  Setup: crea el entorno virtual e instala dependencias
REM  Ejecutar UNA VEZ antes de correr el proyecto.
REM ============================================================

SET "VENV_DIR=%~dp0venv"

echo Creando entorno virtual en %VENV_DIR%...
python -m venv "%VENV_DIR%"

IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: No se pudo crear el entorno virtual. Verifica que Python este instalado.
    pause
    exit /b 1
)

echo Instalando dependencias...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"

echo.
echo Listo. Entorno virtual configurado en: %VENV_DIR%
echo.
echo Siguientes pasos:
echo   1. Copia .env.example a .env y agrega tus API keys
echo   2. Para correr manualmente:   venv\Scripts\python.exe main.py
echo   3. Para el scheduler diario:  venv\Scripts\python.exe scheduler.py
echo   4. Para registrar en Windows: registrar_tarea.bat (como Administrador)
pause
