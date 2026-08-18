@echo off
REM TTO Trading - tum veri hatlarini guncelle (Windows sarmalayici)
REM Parametresiz: etkilesimli menu.  Ornek: guncelle.bat --hepsi --tam --commit
chcp 65001 >nul
pushd "%~dp0"
where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")
%PY% guncelle.py %*
set "KOD=%ERRORLEVEL%"
popd
if not "%KOD%"=="0" echo. & echo [!] Bazi hatlar dustu (cikis %KOD%). Yukaridaki ozete bakin.
pause
exit /b %KOD%
