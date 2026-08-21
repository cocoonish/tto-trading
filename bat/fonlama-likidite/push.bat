@echo off
REM TCMB Fonlama & Likidite - proje klasoru + site ciktisini commit'le ve GitHub'a gonder
REM (push oncesi gomulu-anahtar taramasi; bulursa DURUR)
call "%~dp0..\_ortak\ortak.bat" push "Aktarılacak Projeler\Fonlama" "TCMB Fonlama & Likidite" "fonlama-likidite"
pause
