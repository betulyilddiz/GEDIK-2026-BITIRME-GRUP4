@echo off
setlocal
pushd "%~dp0"
set "ROOTLENS_BUILD=build:preview"
set "ROOTLENS_ENTRY=preview.py"
set "ROOTLENS_PORT=8012"
if /i "%~1"=="live" (
    set "ROOTLENS_BUILD=build:live"
    set "ROOTLENS_ENTRY=live.py"
    set "ROOTLENS_PORT=8013"
)
where npm >nul 2>nul || (
    echo Node.js ve npm gerekli.
    goto failed
)
if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>nul
    if errorlevel 1 (
        python -m venv .venv
    ) else (
        py -3 -m venv .venv
    )
    if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -m pip install -r "services\analyzer\requirements.txt"
if errorlevel 1 goto failed
pushd frontend
call npm ci
if errorlevel 1 (
    popd
    goto failed
)
call npm run %ROOTLENS_BUILD%
if errorlevel 1 (
    popd
    goto failed
)
popd
echo Tarayicida http://127.0.0.1:%ROOTLENS_PORT% adresini acin.
".venv\Scripts\python.exe" "services\analyzer\%ROOTLENS_ENTRY%"
if errorlevel 1 goto failed
popd
exit /b 0

:failed
echo RootLens baslatilamadi. Yukaridaki hatayi kontrol edin.
popd
pause
exit /b 1
