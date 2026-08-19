@echo off
REM Canli panel (dashboard) - kok panel.py uzerinden; on kosullari (paket + veri) denetler.
chcp 65001 >nul
pushd "%~dp0..\.."
where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")
%PY% panel.py hazine %*
set "KOD=%ERRORLEVEL%"
popd
if not "%KOD%"=="0" echo. & echo [!] Panel baslatilamadi (cikis %KOD%).
pause
exit /b %KOD%
