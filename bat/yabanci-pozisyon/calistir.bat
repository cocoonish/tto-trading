@echo off
REM Yabanci Pozisyonu - hatti bastan sona kostur (yerel TAM hat; cron'daki hafif adimlar degil)
REM Adimlar sirayla; biri duserse zincir durur.
call "%~dp0..\_ortak\ortak.bat" calistir "Aktarılacak Projeler\ForeignHoldings" "Yabanci Pozisyonu" "main.py" "ozet_uret.py"
pause
