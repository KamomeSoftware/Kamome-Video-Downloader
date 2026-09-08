@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Kamome Video Downloader v0.6.4 - Portable Build

set "VERSION=0.6.4"
set "APPNAME=KamomeVideoDownloader"
set "PORTABLEDIR=output\KamomeVideoDownloader"
set "ZIPFILE=output\KamomeVideoDownloader_v%VERSION%_Portable.zip"

echo ============================================================
echo  Kamome Video Downloader v%VERSION% - Portable Build
echo ============================================================
echo.

echo [1/7] Checking Python...
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
  echo Python 3 is required only on this BUILD PC.
  echo End users do NOT need Python.
  goto :fail
)

where curl.exe >nul 2>nul
if errorlevel 1 (
  echo curl.exe was not found. Windows 10/11 normally includes it.
  goto :fail
)

if not exist tools mkdir tools
if not exist plugins mkdir plugins
if not exist licenses mkdir licenses

echo.
echo [2/7] Preparing isolated build environment...
if exist .buildenv rmdir /s /q .buildenv
%PY% -m venv .buildenv
if errorlevel 1 goto :fail
call .buildenv\Scripts\activate.bat
python -m pip install --disable-pip-version-check --quiet --upgrade pip pyinstaller
if errorlevel 1 goto :fail

echo.
echo [3/7] Preparing yt-dlp and FFmpeg...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_tools.ps1"
if errorlevel 1 goto :fail

echo.
echo [4/7] Building portable application folder...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist %APPNAME%.spec del /q %APPNAME%.spec
python -m PyInstaller --noconfirm --clean --onedir --windowed --name %APPNAME% app\main.py
if errorlevel 1 goto :fail

echo.
echo [5/7] Adding portable resources...
if exist output rmdir /s /q output
mkdir output
mkdir "%PORTABLEDIR%"
xcopy /e /i /y "dist\%APPNAME%\*" "%PORTABLEDIR%\" >nul
if errorlevel 1 goto :fail
copy /y app_config.json "%PORTABLEDIR%\app_config.json" >nul
copy /y README.txt "%PORTABLEDIR%\README.txt" >nul
copy /y README_en.txt "%PORTABLEDIR%\README_en.txt" >nul
xcopy /e /i /y tools "%PORTABLEDIR%\tools" >nul
xcopy /e /i /y plugins "%PORTABLEDIR%\plugins" >nul
xcopy /e /i /y licenses "%PORTABLEDIR%\licenses" >nul

rem No settings.json is bundled. The app creates it beside the EXE on first use.

echo.
echo [6/7] Creating distributable ZIP...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -LiteralPath '%PORTABLEDIR%' -DestinationPath '%ZIPFILE%' -Force"
if errorlevel 1 goto :fail

echo.
echo [7/7] Cleaning temporary build files...
call deactivate >nul 2>nul
if exist .buildenv rmdir /s /q .buildenv >nul 2>nul
if exist build rmdir /s /q build >nul 2>nul
if exist dist rmdir /s /q dist >nul 2>nul
if exist %APPNAME%.spec del /q %APPNAME%.spec >nul 2>nul

echo.
echo ============================================================
echo BUILD COMPLETE
echo.
echo Portable folder:
echo   %PORTABLEDIR%
echo.
echo Distributable ZIP:
echo   %ZIPFILE%
echo.
echo End users only need to extract the ZIP and run:
echo   KamomeVideoDownloader.exe
echo ============================================================
if exist output explorer.exe output
pause
exit /b 0

:fail
echo.
echo Cleaning temporary build files after failure...
call deactivate >nul 2>nul
if exist .buildenv rmdir /s /q .buildenv >nul 2>nul
if exist build rmdir /s /q build >nul 2>nul
if exist dist rmdir /s /q dist >nul 2>nul
if exist %APPNAME%.spec del /q %APPNAME%.spec >nul 2>nul
if exist "%TEMP%\kamome_ffmpeg.zip" del /q "%TEMP%\kamome_ffmpeg.zip" >nul 2>nul
if exist "%TEMP%\kamome_ffmpeg_extract" rmdir /s /q "%TEMP%\kamome_ffmpeg_extract" >nul 2>nul

echo.
echo ============================================================
echo BUILD FAILED - see the message above.
echo ============================================================
pause
exit /b 1
