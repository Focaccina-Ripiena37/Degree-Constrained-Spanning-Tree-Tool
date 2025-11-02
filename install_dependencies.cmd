@echo off
setlocal enabledelayedexpansion

REM ==============================================
REM DCST Tool - Setup (Windows)
REM - Crea un ambiente virtuale locale (.venv)
REM - Installa le dipendenze da requirements.txt
REM - (Opzionale) --with-pandas per la tabella PNG
REM ==============================================

set "PROJECT_DIR=%~dp0"
pushd "%PROJECT_DIR%" >nul 2>&1

echo ================================
echo DCST Tool - Setup Dependencies
echo ================================

REM 1) Verifica Python (>=3.10)
where python >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Python non trovato nel PATH. Installa Python 3.10+ da https://www.python.org/downloads/ e riprova.
    echo Suggerimento: durante l'installazione, seleziona "Add Python to PATH".
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python -V 2^>^&1') do set PYVER=%%v
echo Trovato Python %PYVER%

REM 2) Crea venv locale se mancante
IF NOT EXIST .venv\Scripts\python.exe (
    echo Creazione ambiente virtuale .venv ...
    python -m venv .venv
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERRORE] Creazione venv fallita.
        pause
        exit /b 1
    )
)

set "VENV_PY=.venv\Scripts\python.exe"
set "VENV_PIP=.venv\Scripts\pip.exe"

REM 3) Aggiorna pip/setuptools/wheel
echo Aggiornamento strumenti di packaging...
"%VENV_PY%" -m pip install --upgrade pip setuptools wheel
IF %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Aggiornamento pip/setuptools/wheel fallito.
    pause
    exit /b 1
)

REM 4) Installa dipendenze core da requirements.txt
echo Installazione dipendenze da requirements.txt ...
"%VENV_PIP%" install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo [ERRORE] Installazione dipendenze fallita.
    pause
    exit /b 1
)

REM 5) Opzionale: pandas per immagine tabella combinata
IF /I "%1"=="--with-pandas" (
    echo Installazione opzionale: pandas ...
    "%VENV_PIP%" install pandas>=2.2.3
)

echo.
echo ================================
echo Setup completato.
echo Per eseguire l'app:
echo.
echo   .venv\Scripts\activate
echo   python run.py
echo.
echo Argomento opzionale: --with-pandas per abilitare l'immagine della tabella riassuntiva.
echo ================================
echo.
popd >nul 2>&1
pause
exit /b 0
