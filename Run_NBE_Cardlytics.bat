@echo off
setlocal
cd /d "%~dp0"
title NBE Cardlytics
echo ================================================
echo   NBE Cardlytics - one click launcher
echo ================================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY goto :nopython

%PY% -c "import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>nul
if errorlevel 1 goto :oldpython

if not exist "venv\Scripts\activate.bat" (
  echo [1/3] Creating the environment...
  %PY% -m venv venv
  if errorlevel 1 goto :fail
)
call "venv\Scripts\activate.bat"

echo [2/3] Checking libraries. The first run takes a few minutes.
python -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 goto :nointernet

echo [3/3] Starting the app. Your browser will open by itself.
echo Close this window to stop the app.
echo.
streamlit run app.py --server.headless false --browser.gatherUsageStats false
echo.
echo The app has stopped.
pause
exit /b 0

:nopython
echo Python was not found on this computer.
echo Install Python 3.9 or newer from python.org.
echo Tick "Add Python to PATH" during the install, then run this file again.
pause
exit /b 1

:oldpython
echo Your Python is too old. Install Python 3.9 or newer from python.org.
pause
exit /b 1

:nointernet
echo Installing the libraries failed. Check your internet connection and run this file again.
pause
exit /b 1

:fail
echo Could not create the environment. Close other windows using this folder and try again.
pause
exit /b 1
