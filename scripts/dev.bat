@echo off
setlocal
set "PROJECT_ROOT=%~dp0.."
set "PYTHON=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
"%PYTHON%" "%PROJECT_ROOT%\manage.py" dev %*
set "SCRIPT_EXIT=%ERRORLEVEL%"
endlocal & exit /b %SCRIPT_EXIT%
