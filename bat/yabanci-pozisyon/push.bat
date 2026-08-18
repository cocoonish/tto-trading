@echo off
REM Yabanci Pozisyonu - proje klasoru + site ciktisini commit'le ve GitHub'a gonder
REM (push oncesi gomulu-anahtar taramasi; bulursa DURUR)
call "%~dp0..\_ortak\ortak.bat" push "Aktarılacak Projeler\ForeignHoldings" "Yabanci Pozisyonu" "yabanci-pozisyon"
pause
