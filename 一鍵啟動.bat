@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo =====================================
echo   每日新聞站 - 一鍵啟動 (Windows)
echo =====================================
echo.

REM 找 Python（優先 python，其次 py）
where python >nul 2>nul
if %ERRORLEVEL%==0 (
    set PYCMD=python
) else (
    where py >nul 2>nul
    if %ERRORLEVEL%==0 (
        set PYCMD=py
    ) else (
        echo [錯誤] 找不到 Python，請先安裝 https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

%PYCMD% 一鍵啟動.py

echo.
echo （按任意鍵關閉視窗）
pause >nul
