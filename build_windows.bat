@echo off
setlocal
set "GOST_VERSION=3.2.6"
set "GOST_ASSET=gost_%GOST_VERSION%_windows_amd64.zip"
set "GOST_RELEASE_BASE=https://github.com/go-gost/gost/releases/download/v%GOST_VERSION%"
set "GOST_URL=%GOST_RELEASE_BASE%/%GOST_ASSET%"
set "GOST_CHECKSUMS_URL=%GOST_RELEASE_BASE%/checksums.txt"
set "GOST_DEST=resources\bin\windows\gost.exe"
set "GOST_DOWNLOAD_DIR=build_workspace\downloads"
set "GOST_ARCHIVE=%GOST_DOWNLOAD_DIR%\%GOST_ASSET%"
set "GOST_CHECKSUMS=%GOST_DOWNLOAD_DIR%\checksums.txt"

echo === Step 1: Preparing build workspace ===
if exist build_workspace rmdir /s /q build_workspace
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ShadowGram.spec del /q ShadowGram.spec
mkdir build_workspace
if errorlevel 1 exit /b 1

echo === Step 2: Ensuring PyInstaller installed ===
call .venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 exit /b 1

call .venv\Scripts\python.exe -m pip install pyinstaller
if errorlevel 1 exit /b 1

echo === Step 3: Ensuring gost.exe available ===
if /i "%SHADOWGRAM_REFRESH_GOST%"=="1" if exist "%GOST_DEST%" del /q "%GOST_DEST%"
if not exist "%GOST_DEST%" (
 mkdir resources\bin\windows >nul 2>nul
 mkdir "%GOST_DOWNLOAD_DIR%" >nul 2>nul
 powershell -NoProfile -ExecutionPolicy Bypass -File scripts\ensure_gost_windows.ps1 ^
  -GostUrl "%GOST_URL%" ^
  -ChecksumsUrl "%GOST_CHECKSUMS_URL%" ^
  -AssetName "%GOST_ASSET%" ^
  -ArchivePath "%GOST_ARCHIVE%" ^
  -ChecksumsPath "%GOST_CHECKSUMS%" ^
  -ExtractDir "%GOST_DOWNLOAD_DIR%\gost_extract" ^
  -TargetPath "%GOST_DEST%"
 if errorlevel 1 exit /b 1
)

echo === Step 4: Building Windows executable ===
call .venv\Scripts\pyinstaller.exe --noconfirm --clean --onedir --name ShadowGram ^
  --add-data "resources;resources" ^
  ShadowGram.py
if errorlevel 1 exit /b 1

echo === Step 5: Collecting output ===
xcopy /e /i /y dist\ShadowGram build_workspace\ShadowGram\
if exist resources\icons\green\GrobTyan_logo.ico copy /y resources\icons\green\GrobTyan_logo.ico build_workspace\ShadowGram\ >nul
if exist resources\bin\windows\gost.exe (
 mkdir build_workspace\ShadowGram\resources\bin\windows >nul 2>nul
 copy /y resources\bin\windows\gost.exe build_workspace\ShadowGram\resources\bin\windows\gost.exe >nul
)

echo === Done ===
echo EXE bundle: build_workspace\ShadowGram\ShadowGram.exe

endlocal
