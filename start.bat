@echo off
title Price Tracker
color 0A
echo.
echo  ==========================================
echo   Price Tracker - Starting up...
echo  ==========================================
echo.

cd /d "%~dp0"

REM Check Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Docker is not running.
    echo  Please open Docker Desktop and wait for it to start,
    echo  then double-click this file again.
    echo.
    pause
    exit /b 1
)

echo  Docker is running. Starting the app...
echo  (First start takes 3-5 minutes to build. After that it is fast.)
echo.

docker compose up --build -d

if errorlevel 1 (
    echo.
    echo  Something went wrong. Showing logs...
    docker compose logs --tail=30
    pause
    exit /b 1
)

echo.
echo  ==========================================
echo   App is running!
echo   Open your browser and go to:
echo   http://localhost:3000
echo  ==========================================
echo.
echo  To stop the app, run stop.bat
echo.

REM Open the browser automatically
timeout /t 3 /nobreak >nul
start http://localhost:3000

pause
