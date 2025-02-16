@echo off

:: Verifica dei permessi di amministratore
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Per favore, esegui questo script come amministratore.
    pause
    exit /b
)

:: Installa le dipendenze necessarie
echo Installazione delle dipendenze...
pip install networkx matplotlib pandas tabulate numpy tqdm Pillow

:: Conferma di installazione completata
echo Installazione completata!
pause
