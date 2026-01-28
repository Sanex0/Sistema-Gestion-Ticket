@echo off
REM Wrapper to run the email ingestor in the project's virtualenv
REM Sets PYTHONPATH so the script can import the package modules
setlocal
set PYTHONPATH=%~dp0
"%~dp0.venv\Scripts\python.exe" "%~dp0flask_app\services\email_ingest.py" --idle
endlocal
