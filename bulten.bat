@echo off
REM ============================================================================
REM  TTO Trading - GUNLUK BULTEN
REM  Veri hatlarindaki degisimleri esiklerle tarar, ekonomik takvimi ve kaynak
REM  taramasini ekler, site/src/data/bulten/ altina JSON yazar. Site /bulten/
REM  sayfasinda gosterir.
REM
REM  Ornekler:  bulten.bat
REM             bulten.bat --guncelle      (once veri hatlarini tazele)
REM             bulten.bat --habersiz      (RSS taramasini atla)
REM ============================================================================
chcp 65001 >nul
title TTO Trading - gunluk bulten
pushd "%~dp0"
where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")
%PY% bulten.py %*
set "KOD=%ERRORLEVEL%"
popd
echo.
if not "%KOD%"=="0" echo [!] Bulten uretilemedi ^(cikis %KOD%^).
pause
exit /b %KOD%
