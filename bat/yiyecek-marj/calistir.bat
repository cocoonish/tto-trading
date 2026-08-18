@echo off
REM Yiyecek Hizmetleri Marji - hatti bastan sona kostur (yerel TAM hat; cron'daki hafif adimlar degil)
REM Adimlar sirayla; biri duserse zincir durur.
call "%~dp0..\_ortak\ortak.bat" calistir "Research\marj" "Yiyecek Hizmetleri Marji" "src\run_all.py" "src\web_cikti.py" "src\ozet_uret.py"
pause
