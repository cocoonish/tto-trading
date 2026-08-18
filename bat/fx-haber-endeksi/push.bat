@echo off
REM FX Haber Endeksi - proje klasoru + site ciktisini commit'le ve GitHub'a gonder
REM (push oncesi gomulu-anahtar taramasi; bulursa DURUR)
call "%~dp0..\_ortak\ortak.bat" push "Aktarılacak Projeler\indices" "FX Haber Endeksi" "fx-haber-endeksi"
pause
