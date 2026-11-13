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
    $License = Get-ChildItem -LiteralPath $TempDir -Recurse -File -Filter 'LICENSE' | Select-Object -First 1
    if ($null -eq $License) { throw 'FFmpeg license is missing from the archive.' }
    New-Item -ItemType Directory -Force (Join-Path $Base 'licenses') | Out-Null
    Copy-Item -LiteralPath $License.FullName -Destination (Join-Path $Base 'licenses/FFmpeg-LICENSE.txt') -Force
    $Build = & $FFmpeg -version
    $Version = [regex]::Match($Build[0], 'ffmpeg version (\d+\.\d+(?:\.\d+)?)').Groups[1].Value
    if (-not $Version) { throw 'Could not identify the FFmpeg source version.' }
    @("Binary provider: https://www.gyan.dev/ffmpeg/builds/", "Corresponding FFmpeg source: https://ffmpeg.org/releases/ffmpeg-$Version.tar.xz", "", $Build) |
        Set-Content -Encoding UTF8 (Join-Path $Base 'licenses/FFmpeg-source.txt')
    Write-Host 'FFmpeg ready.'
}
finally {
    Remove-Item -LiteralPath $TempZip -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction SilentlyContinue
}
