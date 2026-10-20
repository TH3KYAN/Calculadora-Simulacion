@echo off
chcp 65001 >nul
cd /d "%~dp0"

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && python -c "import sys" >nul 2>nul && set "PY=python"
)
if not defined PY (
    if exist "%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" (
        set PY="%USERPROFILE%\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
    )
)

if not defined PY (
    echo No se encontro Python 3.10 o superior.
    echo.
    echo Instala Python desde https://www.python.org/downloads/
    echo y marca la opcion "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

%PY% main.py
if errorlevel 1 (
    echo.
    echo La aplicacion termino con un error. Revisa el mensaje anterior.
    pause
)
