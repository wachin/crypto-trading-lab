@echo off
REM Activate the virtualenv and run the functional verification.
REM Run it by double-clicking, or from a terminal:
REM     Experiments\run_verify.cmd
REM
REM Add extra flags by editing the last line, e.g.
REM     python Experiments\verify.py --tests --gui --network

setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\activate.bat" (
    echo No .venv found. Run Experiments\setup_windows.bat first.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

echo Running the fast offline checks...
python Experiments\verify.py
echo.
echo Tip: re-run with the slower stages when those steps pass:
echo     python Experiments\verify.py --gui
echo     python Experiments\verify.py --network
echo     python Experiments\verify.py --tests
echo.
pause
