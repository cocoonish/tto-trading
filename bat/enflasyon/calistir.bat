@echo off
REM Enflasyon Panosu - hatti bastan sona kostur (veri -> metrik -> grafik -> ozet)
REM Adimlar sirayla; biri duserse zincir durur (yarim cikti uretilmez).
call "%~dp0..\_ortak\ortak.bat" calistir "Aktarılacak Projeler\Enflasyon" "Enflasyon Panosu" "veri.py" "metrik.py" "grafik.py" "ozet_uret.py"
pause
