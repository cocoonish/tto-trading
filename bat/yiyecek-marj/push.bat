@echo off
REM Yiyecek Hizmetleri Marji - proje klasoru + site ciktisini commit'le ve GitHub'a gonder
REM (push oncesi gomulu-anahtar taramasi; bulursa DURUR)
call "%~dp0..\_ortak\ortak.bat" push "Research\marj" "Yiyecek Hizmetleri Marji" "yiyecek-hizmetleri-marj"
pause
