@echo off
title Price Tracker - Stop
color 0C
echo.
echo  Stopping Price Tracker...
echo.

cd /d "%~dp0"

docker compose down

echo.
echo  App stopped. Your data is safe.
echo.
pause
