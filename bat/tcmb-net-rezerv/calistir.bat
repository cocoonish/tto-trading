@echo off
REM TCMB Net Rezerv - hatti bastan sona kostur (yerel TAM hat; cron'daki hafif adimlar degil)
REM Adimlar sirayla; biri duserse zincir durur.
call "%~dp0..\_ortak\ortak.bat" calistir "Aktarılacak Projeler\TCMBNetRezerv" "TCMB Net Rezerv" "net_rezerv.py" "grafik.py" "ozet_uret.py"
pause
