@echo off
rem ==========================================================
rem   Cursor Hanhua Assistant (Windows)
rem   NOTE: this file intentionally contains ASCII only.
rem   All Chinese messages are printed by the Python script,
rem   which handles UTF-8 correctly on every console.
rem ==========================================================
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion
title Cursor Hanhua Assistant
cd /d "%~dp0"

echo.
echo ==========================================================
echo             Cursor Hanhua Assistant
echo ==========================================================
echo.

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo   [FAILED] Python was not found.
    echo.
    echo   Please install Python 3.8 or newer from:
    echo     https://www.python.org/downloads/
    echo.
    echo   IMPORTANT: tick "Add Python to PATH" during setup,
    echo   then close and reopen this window.
    echo.
    pause
    exit /b 1
)

echo   Running with %PY% ...
echo.
%PY% scripts\cursor_han.py
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo   All done! Now QUIT Cursor completely, then open it again.
) else (
    echo   Something went wrong. Please share the output above.
    echo   Log: %LOCALAPPDATA%\cursor-han\cursor-han.log
)
echo.
pause
exit /b %RC%
