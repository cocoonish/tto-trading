@echo off
REM ============================================================================
REM  ortak.bat - tum proje bat'larinin paylastigi yardimci. Dogrudan calistirilmaz.
REM
REM  Kullanim (proje bat'indan):
REM    call "%~dp0..\_ortak\ortak.bat" <islem> <proje_klasoru> <ekran_adi> [args...]
REM    islem: kur | guncelle | calistir | push
REM
REM  Sozlesme:
REM   - Repo koku = bu dosyanin iki ust klasoru (bat\_ortak\ -> kok).
REM   - EVDS anahtari sirayla: TTO_EVDS_KEY ortam degiskeni -> proje\.evds_key
REM     -> kok\.evds_key. Bulunamazsa 'calistir' uyarir; EVDS'e giden adimlar duser.
REM   - 'push' yalniz o projenin klasorunu + site/public/projeler/<slug> ciktisini
REM     stage'ler; commit oncesi gomulu-anahtar taramasi yapar, bulursa DURUR.
REM   - Klasor adlari Turkce harf icerebilir; bu dosya UTF-8 kod sayfasina gecer.
REM ============================================================================
setlocal EnableDelayedExpansion
chcp 65001 >nul

set "ISLEM=%~1"
set "PROJE=%~2"
set "AD=%~3"
shift & shift & shift

pushd "%~dp0..\.." || (echo [HATA] repo koku bulunamadi & exit /b 1)
set "KOK=%CD%"
popd
set "PDIR=%KOK%\%PROJE%"
if not exist "%PDIR%" (echo [HATA] proje klasoru yok: "%PDIR%" & exit /b 1)

where py >nul 2>&1 && (set "PY=py -3") || (set "PY=python")
set "VPY=%PDIR%\.venv\Scripts\python.exe"

if not defined TTO_EVDS_KEY (
  if exist "%PDIR%\.evds_key" (
    set /p TTO_EVDS_KEY=<"%PDIR%\.evds_key"
  ) else if exist "%KOK%\.evds_key" (
    set /p TTO_EVDS_KEY=<"%KOK%\.evds_key"
  )
)

echo.
echo ================================================================
echo   %AD%  --  %ISLEM%
echo   %PDIR%
echo ================================================================
echo.

if /i "%ISLEM%"=="kur"      goto :kur
if /i "%ISLEM%"=="guncelle" goto :guncelle
if /i "%ISLEM%"=="calistir" goto :calistir
if /i "%ISLEM%"=="push"     goto :push
echo [HATA] bilinmeyen islem: %ISLEM%
exit /b 1

REM ---------------------------------------------------------------------------
:kur
REM  Her proje kendi .venv'ini alir: paylasilan ortam bir projenin surum
REM  sabitini digerine bulastirirdi (ornek: indices torch/transformers ister).
if not exist "%VPY%" (
  echo [1/2] Sanal ortam olusturuluyor...
  %PY% -m venv "%PDIR%\.venv" || (echo [HATA] venv olusturulamadi & exit /b 1)
) else (
  echo [1/2] Sanal ortam mevcut, atlaniyor.
)
echo [2/2] Bagimliliklar yukleniyor...
"%VPY%" -m pip install --upgrade pip -q
if exist "%PDIR%\requirements.txt" (
  "%VPY%" -m pip install -r "%PDIR%\requirements.txt" || (echo [HATA] pip install basarisiz & exit /b 1)
) else (
  echo [UYARI] requirements.txt yok, bagimlilik yuklenmedi.
)
echo.
echo [OK] Kurulum tamam.
goto :son

REM ---------------------------------------------------------------------------
:guncelle
pushd "%KOK%"
echo [1/2] git pull...
git pull --rebase --autostash || (echo [HATA] git pull basarisiz & popd & exit /b 1)
popd
if not exist "%VPY%" (
  echo [UYARI] Sanal ortam yok; once KUR calistirin.
  goto :son
)
echo [2/2] Bagimliliklar guncelleniyor...
if exist "%PDIR%\requirements.txt" (
  "%VPY%" -m pip install -r "%PDIR%\requirements.txt" --upgrade -q || (echo [HATA] pip guncelleme basarisiz & exit /b 1)
)
echo.
echo [OK] Guncelleme tamam.
goto :son

REM ---------------------------------------------------------------------------
:calistir
REM  Kalan argumanlarin her biri proje klasorunde sirayla kosturulan bir komuttur.
REM  Biri duserse zincir DURUR: yarim cikti siteye kopyalanmasin.
if not exist "%VPY%" (
  echo [HATA] Sanal ortam yok; once KUR calistirin.
  exit /b 1
)
if not defined TTO_EVDS_KEY (
  echo [UYARI] EVDS anahtari bulunamadi ^(TTO_EVDS_KEY / .evds_key^).
  echo         EVDS'e giden adimlar hata verecektir.
  echo.
)
pushd "%PDIR%"
set /a N=0
:calistir_dongu
if "%~1"=="" goto :calistir_bitti
set /a N+=1
echo [adim !N!] %~1
"%VPY%" %~1
if errorlevel 1 (
  echo.
  echo [HATA] adim !N! basarisiz: %~1
  echo        Zincir durduruldu.
  popd
  exit /b 1
)
shift
goto :calistir_dongu
:calistir_bitti
popd
echo.
echo [OK] %AD% calisti ^(!N! adim^).
goto :son

REM ---------------------------------------------------------------------------
:push
REM  %~1 = site slug'i (bos olabilir). Yalniz bu proje + site ciktisi stage'lenir.
set "SLUG=%~1"
pushd "%KOK%"
echo [1/4] Degisiklikler stage'leniyor...
git add -A -- "%PROJE%"
if defined SLUG if exist "site\public\projeler\%SLUG%" git add -A -- "site\public\projeler\%SLUG%"

echo [2/4] Anahtar sizintisi taramasi...
REM  Stage'lenmis EKLENEN satirlarda gomulu kimlik bilgisi ara: *KEY/TOKEN/SECRET/
REM  PASSWORD = "..." (6+ alfanumerik). Env okuma ve bos string gecer.
git diff --cached | findstr /R /C:"^+.*[Kk][Ee][Yy] *= *[\"'][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9]" /C:"^+.*[Tt][Oo][Kk][Ee][Nn] *= *[\"'][A-Za-z0-9]" /C:"^+.*[Ss][Ee][Cc][Rr][Ee][Tt] *= *[\"'][A-Za-z0-9]" /C:"^+.*[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd] *= *[\"'][A-Za-z0-9]" >nul 2>&1
if not errorlevel 1 (
  echo.
  echo [DURDU] Stage'lenen degisiklikte gomulu anahtara benzeyen satir var:
  git diff --cached | findstr /R /C:"^+.*[Kk][Ee][Yy] *= *[\"'][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9][A-Za-z0-9]" /C:"^+.*[Tt][Oo][Kk][Ee][Nn] *= *[\"'][A-Za-z0-9]" /C:"^+.*[Ss][Ee][Cc][Rr][Ee][Tt] *= *[\"'][A-Za-z0-9]" /C:"^+.*[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd] *= *[\"'][A-Za-z0-9]"
  echo         Anahtar kaynak koda GOMULMEZ; .evds_key dosyasina koyun.
  git reset -q
  popd
  exit /b 1
)
git diff --cached --name-only | findstr /I /C:".evds_key" >nul 2>&1
if not errorlevel 1 (
  echo [DURDU] .evds_key dosyasi stage'de! .gitignore'u kontrol edin.
  git reset -q & popd & exit /b 1
)

git diff --cached --quiet
if not errorlevel 1 (
  echo [BILGI] Commit'lenecek degisiklik yok.
  popd
  goto :son
)
echo [3/4] Commit...
for /f "tokens=1-3 delims=/. " %%a in ("%DATE%") do set "TARIH=%%a.%%b.%%c"
git commit -q -m "veri: %AD% guncellemesi (%TARIH%)" || (echo [HATA] commit basarisiz & popd & exit /b 1)
echo [4/4] Push...
git push || (echo [HATA] push basarisiz - once GUNCELLE ile pull deneyin & popd & exit /b 1)
popd
echo.
echo [OK] %AD% GitHub'a gonderildi.
goto :son

:son
endlocal
exit /b 0
