@echo off
REM TRY REER - proje klasoru + site ciktisini commit'le ve GitHub'a gonder
REM (push oncesi gomulu-anahtar taramasi; bulursa DURUR)
call "%~dp0..\_ortak\ortak.bat" push "Aktarılacak Projeler\TRYREER" "TRY REER" "try-reer"
pause
