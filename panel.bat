@echo off
REM TTO Trading - canli panelleri baslat (Windows sarmalayici)
REM Parametresiz: menu.  Ornekler: panel.bat hazine | panel.bat fx --port 8600 | panel.bat --liste
chcp 65001 >nul
pushd "%~dp0"
where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")
%PY% panel.py %*
set "KOD=%ERRORLEVEL%"
popd
if not "%KOD%"=="0" echo. & echo [!] Panel baslatilamadi (cikis %KOD%). Yukaridaki mesaja bakin.
pause
exit /b %KOD%
