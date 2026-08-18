@echo off
REM Hazine Ihrac - proje klasoru + site ciktisini commit'le ve GitHub'a gonder
REM (push oncesi gomulu-anahtar taramasi; bulursa DURUR)
call "%~dp0..\_ortak\ortak.bat" push "Aktarılacak Projeler\hazineihrac" "Hazine Ihrac" "hazine-ihrac"
pause
