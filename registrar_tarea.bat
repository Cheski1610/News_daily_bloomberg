@echo off
REM ============================================================
REM  Script para registrar la tarea en el Programador de tareas
REM  de Windows. Ejecutar UNA VEZ como Administrador.
REM ============================================================

SET "SCRIPT_DIR=%~dp0"
SET "PYTHON_PATH=%SCRIPT_DIR%venv\Scripts\python.exe"
SET "SCRIPT_PATH=%SCRIPT_DIR%main.py"
SET "TASK_NAME=ResumenNoticias_Bloomberg"

IF NOT EXIST "%PYTHON_PATH%" (
    echo ERROR: Entorno virtual no encontrado en %PYTHON_PATH%
    echo Ejecuta primero setup.bat para crear el entorno virtual.
    pause
    exit /b 1
)

echo Registrando tarea "%TASK_NAME%"...

schtasks /Create /TN "%TASK_NAME%" ^
    /TR "\"%PYTHON_PATH%\" \"%SCRIPT_PATH%\"" ^
    /SC DAILY ^
    /ST 20:00 ^
    /RU "%USERNAME%" ^
    /F

IF %ERRORLEVEL% EQU 0 (
    echo.
    echo Tarea creada correctamente. Se ejecutara todos los dias a las 20:00.
    echo Para verificar: schtasks /Query /TN "%TASK_NAME%"
    echo Para eliminar:  schtasks /Delete /TN "%TASK_NAME%" /F
) ELSE (
    echo.
    echo ERROR: No se pudo crear la tarea. Asegurate de ejecutar como Administrador.
)

pause
