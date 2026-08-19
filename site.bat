@echo off
REM ============================================================================
REM  TTO Trading - SITEYI BASLAT  (cift tiklamak yeterli)
REM
REM  Ne yapar: Node/npm denetler -> gerekiyorsa npm install -> Astro dev sunucusu
REM  -> tarayiciyi http://localhost:4321 adresinde acar. Kapatmak: Ctrl+C.
REM
REM  Ornekler:  site.bat            site.bat --port 4400
REM             site.bat --derle    (uretim derlemesi, sunucu acmaz)
REM             site.bat --onizle   (derlenmis siteyi sun)
REM ============================================================================
chcp 65001 >nul
title TTO Trading - site
pushd "%~dp0"
where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")
%PY% site_baslat.py %*
set "KOD=%ERRORLEVEL%"
popd
if not "%KOD%"=="0" (
  echo.
  echo [!] Site baslatilamadi ^(cikis %KOD%^). Yukaridaki mesaja bakin.
  pause
)
exit /b %KOD%
