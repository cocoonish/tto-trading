@echo off
REM TRY REER - hatti bastan sona kostur (yerel TAM hat; cron'daki hafif adimlar degil)
REM Adimlar sirayla; biri duserse zincir durur.
call "%~dp0..\_ortak\ortak.bat" calistir "Aktarılacak Projeler\TRYREER" "TRY REER" "main.py" "usdtry_reer_analysis.py" "ozet_uret.py"
pause
