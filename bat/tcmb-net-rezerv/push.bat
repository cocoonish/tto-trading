@echo off
REM TCMB Net Rezerv - proje klasoru + site ciktisini commit'le ve GitHub'a gonder
REM (push oncesi gomulu-anahtar taramasi; bulursa DURUR)
call "%~dp0..\_ortak\ortak.bat" push "Aktarılacak Projeler\TCMBNetRezerv" "TCMB Net Rezerv" "tcmb-net-rezerv"
pause
