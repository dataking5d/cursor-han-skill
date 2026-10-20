@echo off
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion
title Cursor 汉化助手

cd /d "%~dp0"

echo.
echo ==========================================================
echo            Cursor 汉化助手
echo ==========================================================
echo.

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY (
    echo   [失败] 没有找到 Python。
    echo.
    echo   请先安装 Python 3.8 或更高版本：
    echo     https://www.python.org/downloads/
    echo.
    echo   安装时记得勾选 "Add Python to PATH"，装完后重新运行本文件。
    echo.
    pause
    exit /b 1
)

echo   使用 %PY% 执行汉化...
echo.

%PY% scripts\cursor_han.py
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
    echo   全部搞定！现在请完全退出 Cursor 再重新打开。
) else (
    echo   汉化过程中有问题，请把上面的信息发给别人帮忙看看。
    echo   日志在: %LOCALAPPDATA%\cursor-han\cursor-han.log
)
echo.
pause
exit /b %RC%
