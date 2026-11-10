@echo off
setlocal
pushd "%~dp0..\astronomy-shop"
docker info >nul 2>nul
if errorlevel 1 (
    echo Docker Desktop'u acin ve Docker basladiktan sonra tekrar deneyin.
    goto failed
)
set "ROOTLENS_COMPOSE_ENV=compose.demo.env"
if exist ".env" set "ROOTLENS_COMPOSE_ENV=.env"
docker compose --env-file "%ROOTLENS_COMPOSE_ENV%" -f compose.yaml -f compose.observability.yaml up -d --build
if errorlevel 1 goto failed
docker compose -f compose.rootlens.yaml up -d --build
if errorlevel 1 goto failed
echo RootLens http://localhost:5173
echo Astronomy Shop http://localhost:8080
echo Odeme ariza ayarlari http://localhost:8080/feature
popd
pause
exit /b 0

:failed
echo Canli Astronomy Shop baslatilamadi. Yukaridaki hatayi kontrol edin.
popd
pause
exit /b 1
