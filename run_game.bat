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

REM Make sure pygame is actually installed before trying to launch, instead
REM of just crashing with an unhelpful ModuleNotFoundError. Installs
REM pygame-ce (a more actively maintained drop-in replacement - same
REM "import pygame" the game already uses, so nothing else changes).
"%PYTHON%" -c "import pygame" >nul 2>&1
if errorlevel 1 (
    echo Setting up pygame, this only happens once...
    "%PYTHON%" -m pip install pygame-ce
    if errorlevel 1 (
        echo.
        echo Could not install pygame-ce. Check your internet connection, or
        echo that "%PYTHON%" is a working Python install.
        pause
        exit /b 1
    )
)

"%PYTHON%" main_pygame.py

REM If the game crashed, keep this window open so the error is readable
REM instead of the window vanishing instantly.
if errorlevel 1 (
    echo.
    echo The game exited with an error - see above.
    pause
)