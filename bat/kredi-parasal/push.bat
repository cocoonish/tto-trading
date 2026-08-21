@echo off
REM Kredi & Parasal Buyuklukler - proje klasoru + site ciktisini commit'le ve GitHub'a gonder
REM (push oncesi gomulu-anahtar taramasi; bulursa DURUR)
call "%~dp0..\_ortak\ortak.bat" push "Aktarılacak Projeler\Kredi" "Kredi & Parasal Buyuklukler" "kredi-parasal"
pause
