@echo off
REM FX Haber Endeksi - hatti bastan sona kostur (yerel TAM hat; cron'daki hafif adimlar degil)
REM Adimlar sirayla; biri duserse zincir durur.
call "%~dp0..\_ortak\ortak.bat" calistir "Aktarılacak Projeler\indices" "FX Haber Endeksi" "run.py --fetch-history" "ozet_uret.py"
pause
