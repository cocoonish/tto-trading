@echo off
REM USDTRY Devaluasyon - proje klasoru + site ciktisini commit'le ve GitHub'a gonder
REM (push oncesi gomulu-anahtar taramasi; bulursa DURUR)
call "%~dp0..\_ortak\ortak.bat" push "Aktarılacak Projeler\USDTRYDeval" "USDTRY Devaluasyon" "usdtry-deval"
pause
