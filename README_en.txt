Kamome Video Downloader v0.6.5 Portable
Developer: Kamome Software

A simple Windows GUI for yt-dlp.

PORTABLE EDITION
No installation is required.
Extract the distribution ZIP to any writable folder and run KamomeVideoDownloader.exe.

Kamome itself does not store its settings in AppData or the Windows registry.
settings.json and the yt-dlp update-check timestamp are stored beside the application.
You can move or copy the entire folder, including to a USB drive.
To remove the application, simply delete its folder.
Note: Windows itself may keep OS-level history, security logs, or temporary information outside Kamome's control.

Features
- Automatic video analysis after pasting a URL
- Thumbnail/title/uploader/duration preview
- Resolution, FPS, codec and estimated-size format list
- MP4 downloads
- Embeds the source thumbnail as MP4 cover art while keeping the thumbnail image file
- Embeds metadata including title, uploader/channel, upload date and source URL
- Firefox / Chrome / Edge cookie support
- Japanese / English UI; first launch follows the Windows language
- Daily yt-dlp update check
- Kamome application update check via GitHub Releases
- Ko-fi Support Development link

Official
Developer: Kamome Software
GitHub: https://github.com/KamomeSoftware/Kamome-Video-Downloader
Support: https://ko-fi.com/kamome92970

This application is an independent GUI front-end and is not affiliated with or endorsed by Google LLC, YouTube, yt-dlp, or FFmpeg.
It can work with sites supported by yt-dlp, but site changes can temporarily break compatibility.
Use it only for content you are authorized to download and follow each service's terms and applicable law.

Changes in v0.6.5 Portable
- Application-added log messages are now always in English.
--------------------------
- Restores the previous window state on the next launch.
- If the app was closed maximized, it opens maximized next time.
- In normal mode, the previous window size and screen position are restored.
- If a saved position is off-screen after a monitor-layout change, the window is moved back into the visible desktop.
- Window state and geometry are stored in the portable settings.json beside the executable.

Building
--------
Run build_portable.bat on the Windows build PC.
Python 3 and an internet connection are required only on the build PC.
PyInstaller is installed into a temporary .buildenv and removed after the build.
The script prepares yt-dlp and FFmpeg and builds a portable folder with PyInstaller --onedir.

Outputs:
output\KamomeVideoDownloader\
output\KamomeVideoDownloader_v0.6.5_Portable.zip

End users do not need Python, PyInstaller, or Inno Setup.


v0.6.5 changes
---------------
- Added Open update page / Later / Skip this version choices.
- Later suppresses the same update for the rest of the day.
- Skip suppresses that specific version; a newer release is shown again.
- Added the new Kamome icon to the EXE, window and taskbar.
