@echo off
setlocal enabledelayedexpansion
title Smart YT VLC Player

:: ===== FIND VLC =====
set "VLC="
if exist "C:\Program Files\VideoLAN\VLC\vlc.exe" set "VLC=C:\Program Files\VideoLAN\VLC\vlc.exe"
if exist "C:\Program Files (x86)\VideoLAN\VLC\vlc.exe" set "VLC=C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"

if not defined VLC (
    echo VLC not found!
    pause
    exit
)

:: ===== INPUT =====
echo ==============================
echo SMART YT → VLC PLAYER
echo ==============================
echo.
set /p url=Enter YouTube URL or Playlist:
echo.

:: ===== DETECT PLAYLIST =====
yt-dlp --print "%(playlist_count)s" "%url%" > temp.txt 2>nul
set /p count=<temp.txt
del temp.txt

if not "%count%"=="" (
    set type=playlist
) else (
    set type=video
)

echo Detected: %type%
echo.

:: ===== MENU =====
if "%type%"=="playlist" (
    echo [M] Music Playlist (Audio)
    echo [V] Video Playlist
) else (
    echo [M] Audio Only
    echo [V] Video Mode
)

echo [B] Auto Best
echo ==============================
set /p mode=Choose mode (M/V/B):

:: ===== BUILD LIST =====
if "%type%"=="playlist" (
    yt-dlp --flat-playlist --print "%%(title)s|%%(webpage_url)s" "%url%" > list.txt
) else (
    yt-dlp --print "%%(title)s|%%(webpage_url)s" "%url%" > list.txt
)

:: Count total
set total=0
for /f %%a in (list.txt) do set /a total+=1

set index=0

:: ===== LOOP =====
:next
set /a index+=1
if %index% GTR %total% goto end

:: Get current item
for /f "tokens=1,* delims=|" %%a in ('more +%index%-1 list.txt') do (
    set title=%%a
    set vid=%%b
    goto play
)

:play
cls
echo ==============================
echo Now Playing (!index!/%total%)
echo !title!
echo ==============================
echo.

:: ===== PLAYBACK =====

:: AUDIO MODE (PIPE)
if /I "%mode%"=="M" (
    start "" /b cmd /c yt-dlp -f bestaudio "!vid!" -o - ^| "%VLC%" --network-caching=3000 --play-and-exit -
)

:: VIDEO MODE (DIRECT - STABLE)
if /I "%mode%"=="V" (
    start "" "%VLC%" --play-and-exit "!vid!"
)

:: AUTO BEST (same as video, VLC handles it)
if /I "%mode%"=="B" (
    start "" "%VLC%" --play-and-exit "!vid!"
)

:: ===== WAIT / CONTROL =====
echo Controls: [N] Next  [Q] Quit
choice /c NQ /n >nul

if errorlevel 2 goto quit
if errorlevel 1 (
    taskkill /im vlc.exe /f >nul 2>&1
    goto next
)

goto next

:: ===== EXIT =====
:quit
taskkill /im vlc.exe /f >nul 2>&1

:end
del list.txt
echo.
echo Finished playlist.
pause