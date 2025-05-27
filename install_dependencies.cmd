@echo off
title DCST Tool - Installazione
chcp 65001 >nul
cls

echo ============================================
echo    DCST Tool - Installazione Dipendenze
echo ============================================
echo.

:: Verifica la versione di Windows
ver | findstr /i "10\." > nul
if %errorlevel% neq 0 (
    echo [Errore] Questo script richiede Windows 10 o superiore.
    pause
    exit /b 1
)

:: Controlla se Python è installato
echo Verificando Python...
where python > nul 2>&1
if %errorlevel% neq 0 (
    echo Python non trovato. Si consiglia di installare Python 3.9 o superiore.
    echo Puoi installarlo eseguendo il seguente comando:
    echo winget install -e --id Python.Python.3.9
    pause
    exit /b 1
)

:: Controlla la versione di Python
for /f "delims=" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python trovato: %PYTHON_VERSION%

:: Controlla i requisiti minimi hardware
echo Verificando le specifiche del sistema...

:: Controllo CPU (minimo 4 core)
for /f "tokens=2 delims==" %%A in ('wmic cpu get NumberOfCores /value ^| find "="') do set CPU_CORES=%%A
if %CPU_CORES% LSS 4 (
    echo [Attenzione] Il sistema ha solo %CPU_CORES% core. Potrebbero verificarsi rallentamenti.
) else (
    echo CPU ok: %CPU_CORES% core.
)

:: Controllo RAM (minimo 8 GB)
for /f "tokens=2 delims==" %%A in ('wmic OS get TotalVisibleMemorySize /value ^| find "="') do set /a RAM_MB=%%A/1024
if %RAM_MB% LSS 8192 (
    echo [Attenzione] Il sistema ha solo %RAM_MB% MB di RAM. Potrebbero verificarsi rallentamenti.
) else (
    echo RAM ok: %RAM_MB% MB disponibili.
)

:: Controllo spazio su disco (minimo 500 MB)
for /f "tokens=2 delims==" %%A in ('wmic logicaldisk where "DeviceID='C:'" get FreeSpace /value ^| find "="') do set /a DISK_MB=%%A/1024/1024
if %DISK_MB% LSS 500 (
    echo [Errore] Spazio su disco insufficiente! Disponibili solo %DISK_MB% MB.
    pause
    exit /b 1
) else (
    echo Spazio su disco ok: %DISK_MB% MB disponibili.
)

:: Installa le dipendenze
echo Installando le dipendenze Python...
python -m pip install --upgrade pip
python -m pip install networkx numpy pandas psutil memory_profiler

:: Verifica che tutto sia installato correttamente
python -c "import networkx, numpy, pandas, psutil, memory_profiler; print('Installazione completata con successo!')"

echo.
echo [Successo] Tutto installato correttamente!
pause
exit /b 0
