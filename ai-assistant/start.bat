@echo off
cd /d "%~dp0"

echo ==========================================
echo   KI-Assistent starten
echo ==========================================

:: Pruefen ob .env existiert
if not exist ".env" (
    echo.
    echo  FEHLER: .env Datei fehlt!
    echo  Kopiere .env.example zu .env und trage deinen API-Key ein:
    echo  ANTHROPIC_API_KEY=sk-ant-...
    echo.
    pause
    exit /b 1
)

:: Pruefen ob venv existiert, sonst erstellen
if not exist "venv\Scripts\activate.bat" (
    echo  Erstelle virtuelle Umgebung...
    py -m venv venv
)

:: Aktivieren
call venv\Scripts\activate.bat

:: Dependencies installieren
echo  Installiere Abhaengigkeiten...
pip install -r requirements.txt -q

echo.
echo  Starte auf http://localhost:8765
echo  Browser oeffnet sich automatisch...
echo  Strg+C zum Beenden
echo.

:: Browser nach kurzer Pause oeffnen
start /min "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8765"

:: Server starten
uvicorn main:app --host 0.0.0.0 --port 8765 --reload

pause
