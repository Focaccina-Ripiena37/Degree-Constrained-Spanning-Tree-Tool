@echo off
setlocal enabledelayedexpansion

echo ================================
echo DCST Tool - Setup Dependencies
echo ================================

REM 1. Controlla se Python è già installato
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python non trovato. Inizio download e installazione di Python 3.10.11...
    powershell -Command "Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe -OutFile python_installer.exe"
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python_installer.exe
) ELSE (
    echo Python è già installato.
)

REM 2. Verifica che python ora funzioni
python --version || (
    echo Errore: Python non è stato installato correttamente.
    pause
    exit /b 1
)

REM 3. Aggiorna pip
echo Aggiornamento pip...
python -m pip install --upgrade pip

REM 4. Installa le dipendenze globalmente
echo Installazione dipendenze...
pip install pandas numpy matplotlib networkx psutil pillow memory_profiler scipy

echo ================================
echo Tutto pronto!
echo Ora puoi eseguire:
echo.
echo     python run.py
echo.
echo ================================

pause
exit /b 0
