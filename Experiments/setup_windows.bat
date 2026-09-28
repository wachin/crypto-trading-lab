@echo off
REM One-click setup for Windows, using cmd.exe so PowerShell's execution
REM policy is never involved. Creates .venv, installs every dependency
REM (including ccxt) and installs the project itself.
REM
REM Run it by double-clicking, or from a terminal:
REM     Experiments\setup_windows.bat

setlocal
cd /d "%~dp0.."

echo ============================================================
echo  Crypto Trading Lab - Windows setup
echo  Working directory: %CD%
echo ============================================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)

echo [1/5] Checking Python...
%PY% --version
if errorlevel 1 goto :error

echo.
echo [2/5] Creating the virtualenv (.venv)...
if not exist ".venv\Scripts\python.exe" (
    %PY% -m venv .venv
    if errorlevel 1 goto :error
) else (
    echo       .venv already exists, reusing it.
)

echo.
echo [3/5] Activating and upgrading pip...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
if errorlevel 1 goto :error

echo.
echo [4/5] Installing every dependency (this downloads PyQt6 and ccxt)...
python -m pip install -r "Experiments\requirements-all.txt"
if errorlevel 1 goto :error

echo.
echo [5/5] Installing Crypto Trading Lab itself...
python -m pip install -e .
if errorlevel 1 goto :error

echo.
echo ============================================================
echo  Setup finished.
echo.
echo  Next:  Experiments\run_verify.cmd
echo  (or activate the venv and run:  python Experiments\verify.py)
echo ============================================================
echo.
pause
exit /b 0

:error
echo.
echo ============================================================
echo  Something failed. Copy the last lines above and send them
echo  back together with Experiments\CHECKLIST.md.
echo ============================================================
echo.
pause
exit /b 1
