$ErrorActionPreference = 'Stop'

$Base  = Split-Path -Parent $MyInvocation.MyCommand.Path
$Tools = Join-Path $Base 'tools'
$TempZip = Join-Path $env:TEMP 'kamome_ffmpeg.zip'
$TempDir = Join-Path $env:TEMP 'kamome_ffmpeg_extract'

New-Item -ItemType Directory -Force -Path $Tools | Out-Null

function Download-File([string]$Url, [string]$Destination) {
    if (Test-Path -LiteralPath $Destination) {
        Remove-Item -LiteralPath $Destination -Force -ErrorAction SilentlyContinue
    }
    $curl = Get-Command curl.exe -ErrorAction Stop
    & $curl.Source -L --fail --retry 3 --retry-delay 2 --progress-bar -o $Destination $Url
    if ($LASTEXITCODE -ne 0) {
        throw "Download failed: $Url"
    }
}

Write-Host 'Downloading latest yt-dlp...'
$YtDlp = Join-Path $Tools 'yt-dlp.exe'
Download-File 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe' $YtDlp

Write-Host ''
Write-Host 'Preparing FFmpeg...'
$FFmpeg  = Join-Path $Tools 'ffmpeg.exe'
$FFprobe = Join-Path $Tools 'ffprobe.exe'

if ((Test-Path -LiteralPath $FFmpeg) -and (Test-Path -LiteralPath $FFprobe)) {
    Write-Host 'Existing FFmpeg found - keeping it.'
    exit 0
}

# Clean leftovers from a failed previous build.
Remove-Item -LiteralPath $TempZip -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction SilentlyContinue

try {
    Download-File 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' $TempZip

    Write-Host 'Extracting FFmpeg...'
    New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
    Expand-Archive -LiteralPath $TempZip -DestinationPath $TempDir -Force

    $FFmpegFound = Get-ChildItem -LiteralPath $TempDir -Recurse -File -Filter 'ffmpeg.exe' | Select-Object -First 1
    $FFprobeFound = Get-ChildItem -LiteralPath $TempDir -Recurse -File -Filter 'ffprobe.exe' | Select-Object -First 1

    if ($null -eq $FFmpegFound -or $null -eq $FFprobeFound) {
        throw 'ffmpeg.exe or ffprobe.exe was not found in the downloaded archive.'
    }

    Copy-Item -LiteralPath $FFmpegFound.FullName -Destination $FFmpeg -Force
    Copy-Item -LiteralPath $FFprobeFound.FullName -Destination $FFprobe -Force
    Write-Host 'FFmpeg ready.'
}
finally {
    Remove-Item -LiteralPath $TempZip -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}
