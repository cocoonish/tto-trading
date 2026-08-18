@echo off
REM USDTRY Devaluasyon - hatti bastan sona kostur (yerel TAM hat; cron'daki hafif adimlar degil)
REM Adimlar sirayla; biri duserse zincir durur.
call "%~dp0..\_ortak\ortak.bat" calistir "Aktarılacak Projeler\USDTRYDeval" "USDTRY Devaluasyon" "usdtry_deval_plotly.py" "usdtry_weekly_trends.py" "usdtry_monthly_trends.py" "ozet_uret.py"
pause
