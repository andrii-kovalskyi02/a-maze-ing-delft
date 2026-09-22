@echo off
setlocal

REM Always run from the folder this file lives in, no matter where you
REM double-click it from - so a shortcut to this file works from anywhere,
REM including your Desktop, as long as this .bat itself stays in the
REM project folder next to main_pygame.py.
cd /d "%~dp0"

REM Prefer this project's own virtual environment if it has one, otherwise
REM fall back to whatever "python" is on PATH.
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
) else (
    set PYTHON=python
)

"%PYTHON%" main_pygame.py

REM If the game crashed, keep this window open so the error is readable
REM instead of the window vanishing instantly.
if errorlevel 1 (
    echo.
    echo The game exited with an error - see above.
    pause
)