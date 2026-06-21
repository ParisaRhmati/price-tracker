@echo off
title Price Tracker - Import Excel
color 0B

cd /d "%~dp0"

if "%~1"=="" (
    echo.
    echo  HOW TO USE:
    echo  Drag and drop your links.xlsx file onto this import.bat icon.
    echo.
    pause
    exit /b 0
)

set XLSXFILE=%~1
echo.
echo  Importing: %XLSXFILE%
echo.

REM Copy the file into the running backend container
docker compose cp "%XLSXFILE%" backend:/tmp/import.xlsx

if errorlevel 1 (
    echo.
    echo  ERROR: Could not copy the file.
    echo  Make sure the app is running first (double-click start.bat).
    pause
    exit /b 1
)

REM Run the import
docker compose exec backend python manage.py import_excel /tmp/import.xlsx

if errorlevel 1 (
    echo.
    echo  Import failed. Check the error above.
) else (
    echo.
    echo  Import successful! Refresh your browser to see the updated products.
)

echo.
pause
