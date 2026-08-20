@echo off
REM ============================================================================
REM  TTO Trading - SITEYI YAYINA GONDER
REM  site/ klasorunu public depoya (cocoonish.github.io) kopyalar, commit'ler,
REM  push eder; GitHub Actions derleyip Pages'e koyar (~2 dk).
REM  Bu depo private kalir; Research/ ve veri hatlari YAYINLANMAZ.
REM
REM  Ornekler:  yayinla.bat
REM             yayinla.bat -m "SMC dersi guncellendi"
REM             yayinla.bat --kuru          (ne olacagini goster, gonderme)
REM ============================================================================
chcp 65001 >nul
title TTO Trading - yayinla
pushd "%~dp0"
where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")
%PY% yayinla.py %*
set "KOD=%ERRORLEVEL%"
popd
echo.
if not "%KOD%"=="0" echo [!] Yayin tamamlanmadi ^(cikis %KOD%^).
pause
exit /b %KOD%
