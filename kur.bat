@echo off
REM ============================================================================
REM  TTO Trading - KURULUM  (yeni bilgisayarda calistirilacak ILK sey)
REM
REM  Ne yapar: on kosullari denetler (Python, Node, EVDS anahtari) -> 7 veri
REM  hattinin her biri icin .venv + requirements.txt -> site icin npm install
REM  -> marj hatti icin Playwright Chromium (gerekiyorsa). Tekrari guvenlidir.
REM
REM  Ornekler:  kur.bat
REM             kur.bat --hat tcmb hazine     (yalniz bu hatlar)
REM             kur.bat --site-yok            (npm install atla)
REM             kur.bat --liste               (ne kurulacak, goster)
REM ============================================================================
chcp 65001 >nul
title TTO Trading - kurulum
pushd "%~dp0"
where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")
%PY% kur.py %*
set "KOD=%ERRORLEVEL%"
popd
echo.
if not "%KOD%"=="0" echo [!] Bazi adimlar dustu ^(cikis %KOD%^). Yukaridaki ozete bakin.
pause
exit /b %KOD%
