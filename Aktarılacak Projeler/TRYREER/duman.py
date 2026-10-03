#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TRY REER — duman sınaması. Ağa çıkmaz, saniyeler sürer.

`guncelle.py` bu dosyayı hattın ADIMLARINDAN ÖNCE koşturur ve düşerse hat hiç
koşmaz, siteye kopyalama olmaz. Sınama `--denetle` yazan birinin eline
bırakılmaz: zamanlanmış koşu `--denetle` demez.

BURADAKİ HER MADDE BİR ARIZAYA KARŞILIK GELİR. Bir sigortanın hangi arızaya
karşı çalıştığı konduğu gün yazılmazsa, sonraki oturum onu her arızaya karşı
sanır — bu yüzden her maddenin başında gerekçe yazılı.

Özet üreticisi SENTETİK bir çerçevede, GERÇEKTEN KOŞTURULARAK sınanır (geçici
dizine kopyalanır, uydurma bir seri ve damga verilir, alt süreç olarak
çalıştırılır). İçe aktarmak yetmez: dosya bir betiktir, tepeden aşağı koşar ve
kusurlarının çoğu ancak koşarken görünür. Depodaki gerçek ozet.json'a
DOKUNULMAZ.

Koşum:  python3 duman.py     (çıkış kodu 0 = geçti, 1 = düştü)
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parent
SAYFA = KOK.parents[1] / "site" / "src" / "content" / "projeler" / "try-reer.mdx"

_DUSEN: list[str] = []


def sor(kosul: bool, ad: str, aciklama: str = "") -> None:
    if kosul:
        print(f"  ✓ {ad}")
    else:
        print(f"✗ {ad}" + (f" — {aciklama}" if aciklama else ""))
        _DUSEN.append(ad)


def cerceve(tmp: Path, son_ay: str, damga_ay: str | None,
            kaynak: str = "evds") -> dict:
    """Uydurma bir REDK serisi + damga kur, ozet_uret.py'yi ALT SÜREÇ olarak
    koştur, ürettiği ozet.json'u döndür.

    `son_ay` ve `damga_ay` ISO ("2026-08") verilir: girdinin yazımı hattın
    KAYNAK sözleşmesidir (main.py damgaya "%Y-%m" yazar), okura giden yazım
    ayrı bir sorudur ve maddelerde o sınanır.
    """
    d = tmp / son_ay.replace("-", "") / (damga_ay or "damgasiz")
    d.mkdir(parents=True, exist_ok=True)
    shutil.copy2(KOK / "ozet_uret.py", d / "ozet_uret.py")

    yil, ay = (int(x) for x in son_ay.split("-"))
    satirlar = ["Dönem,CPI_REER,PPI_REER,Composite_REER,MA_10Y,MA_5Y,"
                "Deviation_10Y_Pct,Deviation_5Y_Pct,PPI_MA_10Y,"
                "PPI_Deviation_10Y_Pct,CPI_MA_10Y,CPI_Deviation_10Y_Pct,Kaynak"]
    for k in range(3):
        a = ay - (2 - k)
        y = yil + (a - 1) // 12
        a = (a - 1) % 12 + 1
        satirlar.append(f"{y:04d}-{a:02d}-01,105.0,101.0,103.8,97.0,92.0,"
                        f"7.0,12.9,90.6,11.7,100.1,4.9,{kaynak}")
    (d / "reer_analysis_data.csv").write_text("\n".join(satirlar) + "\n",
                                              encoding="utf-8")
    if damga_ay:
        (d / "kaynak_damgasi.json").write_text(json.dumps({
            "kaynak": kaynak,
            "kaynak_etiket": "TCMB EVDS" if kaynak == "evds"
                             else "yerel Excel (yedek)",
            "son_gozlem": damga_ay,
            "gecikme_ay": 1,
            "bayat": False,
            "eksik_aylar": [],
            "cekim_zamani": "2026-09-04 13:04",
        }, ensure_ascii=False), encoding="utf-8")

    r = subprocess.run([sys.executable, "-u", "ozet_uret.py"], cwd=str(d),
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"ozet_uret.py düştü ({son_ay}): {r.stderr[-400:]}")
    return json.loads((d / "ozet.json").read_text(encoding="utf-8"))


def kur_tanimi_maddeleri(tmp: Path) -> list[tuple[bool, str, str]]:
    """(7) Yerel aylık kur önbelleği TANIMIYLA okunur ve yazılır (ağa çıkmaz:
    ortak/usdtry'nin yerine sahte bir modül konur)."""
    import contextlib
    import io
    import types

    import pandas as pd
    sys.path.insert(0, str(KOK))
    with contextlib.redirect_stdout(io.StringIO()):
        import usdtry_reer_analysis as R
    u = R._kur_modulu()
    yol = tmp / "usdtry_reer_data.csv"
    asil_yol, asil_modul = R.USDTRY_LOCAL_CSV, R._kur_modulu
    R.USDTRY_LOCAL_CSV = str(yol)
    m: list[tuple[bool, str, str]] = []

    def oku():
        with contextlib.redirect_stdout(io.StringIO()):
            return R.load_usdtry_local()

    def yaz(ek: str, tanim: str = ""):
        v = f",{tanim}" if ek else ""
        yol.write_text(f"Dönem,USDTRY,High,Low{ek}\n2026-07-01,47.0,47.5,46.6{v}\n"
                       f"2026-08-01,47.8,48.2,47.5{v}\n", encoding="utf-8")

    def cek(tanim):
        kur = types.SimpleNamespace(seri=pd.Series([47.0, 47.2, 47.9], index=pd.to_datetime(
            ["2026-07-30", "2026-07-31", "2026-08-03"]), name="usdtry"), uyarilar=[], tanim=tanim)
        R._kur_modulu = lambda: types.SimpleNamespace(SUTUN=u.SUTUN, seri=lambda **_: kur)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                return R.fetch_usdtry_yfinance()
        finally:
            R._kur_modulu = asil_modul

    try:
        yaz("")
        m.append((oku() is None, "tanımsız yerel aylık kur taze sayılmıyor",
                  "kur_tanimi sütunu olmayan dosya bugünkü tanım diye okundu"))
        yaz(",kur_tanimi", u.ONCEKI_SUTUN)
        m.append((oku() is None, "önceki tanımla yazılmış yerel aylık kur taze sayılmıyor",
                  f"{u.ONCEKI_SUTUN} ile yazılmış dosya okundu"))
        yaz(",kur_tanimi", u.SUTUN)
        df = oku()
        m.append((df is not None and len(df) == 2 and df["kur_tanimi"].unique().tolist() == [u.SUTUN],
                  "bugünkü tanımla yazılmış yerel aylık kur okunuyor ve tanımını taşıyor",
                  f"okunan: {None if df is None else df.to_dict('list')}"))
        eski = cek(u.ONCEKI_SUTUN)
        eski.to_csv(yol, index=False)
        m.append((eski["kur_tanimi"].unique().tolist() == [u.ONCEKI_SUTUN] and oku() is None,
                  "eski tanımla dönen seri bugünkü diye işaretlenmiyor (sonraki koşu yeniden çeker)",
                  f"işaret: {eski['kur_tanimi'].unique().tolist()}"))
        yeni = cek(u.SUTUN)
        yeni.to_csv(yol, index=False)
        df = oku()
        m.append((df is not None and len(df) == 2,
                  "bugünkü tanımla çekilen aylık kur bir sonraki koşuda yerelden okunuyor",
                  f"okunan: {None if df is None else len(df)} ay"))
    finally:
        R.USDTRY_LOCAL_CSV, R._kur_modulu = asil_yol, asil_modul
    return m


def sayfa_anahtarlari() -> set[str]:
    """Proje sayfasının <Deger> ile ADIYLA çağırdığı anahtarlar."""
    if not SAYFA.exists():
        return set()
    m = SAYFA.read_text(encoding="utf-8")
    return set(re.findall(r'<Deger[^>]*?anahtar="([^"]+)"', m))


def kos() -> int:
    print("TRY REER duman sınaması")
    with tempfile.TemporaryDirectory(prefix="reer_duman_") as t:
        tmp = Path(t)
        oz = cerceve(tmp, "2026-08", "2026-08")

        # (1) OKURA GİDEN AYLIK SAAT AA.YYYY YAZILIR.
        # 09.09.2026'da ölçüldü: sayfa "son gözlem 2026-08" basıyordu. Biçim
        # sözleşmesi (ortak/bicim.py = site/src/lib/bicim.ts) aylık bir saati
        # AA.YYYY yazar; ISO yazım okur diline ait değildir ve okur dili
        # ölçütü 7 karakterlik bir etiketi CÜMLE saymadığı için sessiz
        # geçiyordu — yani hiçbir kapı sormuyordu.
        sor(re.fullmatch(r"\d{2}\.\d{4}", str(oz.get("son_gozlem"))) is not None,
            "son_gozlem AA.YYYY yazımında",
            f"gelen: {oz.get('son_gozlem')!r} (ISO yazım okura basılamaz)")

        # (2) TEK GÖZLEM, TEK GÜN. `_tarih` ile `son_gozlem` aynı satırdan
        # doğuyor; ayrışırlarsa sayfa aynı cümlede iki farklı ay söyler.
        sor(oz.get("_tarih") == oz.get("son_gozlem"),
            "_tarih ile son_gozlem aynı ayı söylüyor",
            f"{oz.get('_tarih')!r} ≠ {oz.get('son_gozlem')!r}")

        # (3) DAMGA KIYASI KAYNAĞIN YAZIMINDA KALIR.
        # main.py kaynak_damgasi.json'a "%Y-%m" yazar. Okura giden anahtarın
        # yazımı değiştirilirken kıyas da AA.YYYY'ye kaydırılsaydı damga ile
        # özet HER koşuda ayrışır, kaynak "bilinmiyor"a düşer ve sayfadaki
        # kaynak etiketi — hattın gerçekten EVDS'ten geldiği hâlde — yalan
        # söylerdi. İki yönlü sorulur: tutan damga düşürmemeli, TUTMAYAN
        # damga da sessiz geçmemeli.
        sor(oz.get("kaynak") == "evds",
            "damga ile özet aynı ayı söylerken kaynak korunuyor",
            f"kaynak={oz.get('kaynak')!r} (ISO kıyas kaymış olabilir)")
        ayrik = cerceve(tmp, "2026-08", "2026-05")
        sor(ayrik.get("kaynak") == "bilinmiyor" and ayrik.get("tazelik") == "bilinmiyor",
            "ayrışan damga kaynağı 'bilinmiyor'a düşürüyor",
            f"kaynak={ayrik.get('kaynak')!r}, tazelik={ayrik.get('tazelik')!r}")

        # (4) SAYFANIN ADIYLA ÇAĞIRDIĞI ANAHTAR HER KOŞUDA YAZILIR.
        # Eksik anahtar sayfada statik yedeğinde donar; yayın kapısı da
        # (sayfa sınavı, 1. ölçüt) ENGEL üretir.
        cagrilan = sayfa_anahtarlari()
        eksik = sorted(cagrilan - set(oz))
        sor(bool(cagrilan) and not eksik,
            "sayfanın çağırdığı her anahtar özette var",
            f"eksik: {eksik}" if cagrilan else "sayfa okunamadı")

        # (5) KOŞU ANINDA DONAN HÜKÜM SAYFAYA BASILMAZ.
        # 09.09.2026'da ölçüldü: sayfa "bugüne göre 1 ay gecikme, durum:
        # güncel" diyordu ve iki değer de koşu anına bağlıydı. Hat bir daha
        # koşamazsa cümle aylarca aynı kalır; üstelik "bayat" hükmü otomatik
        # koşuda ERİŞİLEMEZ (main.py gecikme > TAZELIK_ESIGI_AY iken
        # RuntimeError ile düşer, yani ozet.json hiç yeniden yazılmaz). Okura
        # giden tek dürüst ölçü TARİHTİR. Yapısal kilit: bir sonraki oturum
        # bu iki anahtarı sayfaya geri koyarsa duman DÜŞER.
        donan = sorted({"gecikme_ay", "tazelik"} & cagrilan)
        sor(not donan,
            "koşu anında donan hüküm sayfa metninde çağrılmıyor",
            f"sayfada: {donan} — bunlar render anında tarihten çıkarılmalı")

        # (6) EŞİK TEK YERDE. ozet_uret.py'nin tazelik eşiği main.py'nin
        # TAZELIK_ESIGI_AY'ı ile aynı olmak zorunda; iki ayrı sabit bir gün
        # sessizce ayrışır ve sayfa ile hattın kendi hükmü çelişir.
        m_ana = re.search(r"^TAZELIK_ESIGI_AY\s*=\s*(\d+)",
                          (KOK / "main.py").read_text(encoding="utf-8"), re.M)
        m_ozet = re.search(r"gecikme_ay\s*>\s*(\d+)",
                           (KOK / "ozet_uret.py").read_text(encoding="utf-8"))
        sor(bool(m_ana and m_ozet) and m_ana.group(1) == m_ozet.group(1),
            "tazelik eşiği main.py ile ozet_uret.py'de aynı",
            f"main={m_ana.group(1) if m_ana else '?'} · "
            f"ozet={m_ozet.group(1) if m_ozet else '?'}")

        # (7) AYLIK KUR ÖNBELLEĞİ GÜNLÜK SERİNİN TANIMINI TAŞIR.
        # 03.10.2026'da ölçüldü: yerel usdtry_reer_data.csv REDK'nin son
        # ayını kapsadıkça ortak/usdtry'ye hiç gidilmiyordu ve dosya hangi
        # kapanış tanımıyla yazıldığını söylemiyordu. 02.10.2026 (saatlik bar)
        # ve 03.10.2026 (cumartesi barı olmayan cuma ölçülmez) değişiklikleri
        # bu hatta bu yüzden ulaşmamıştı: aylık ortalama kur 260 ayın
        # medyanında %0,09, en çok %1,7 (11.2021) eski tanımda kalıyordu.
        for kosul, ad, aciklama in kur_tanimi_maddeleri(tmp):
            sor(kosul, ad, aciklama)

    if _DUSEN:
        print(f"\nDUMAN SINAMASI DÜŞTÜ ({len(_DUSEN)} madde)")
        return 1
    print("\nduman sınaması geçti")
    return 0


if __name__ == "__main__":
    sys.exit(kos())
