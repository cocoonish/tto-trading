#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bütün zincir tek komutla: sınamalar → takvim → takvimin fiyat sınaması → veri denetimi → koşu → karşı olgu →
ölçüm → şekiller (ev stiliyle) → ders metinleri → kapı.

Fiyat arşivi ve takvimin ham sayfaları bulutta indirilir (arastirma-veri.yml) ve depoda durur; bu betik ağa çıkmaz.
Okunan her girdi okunmadan önce SHA-256 özüne karşı sınanır, yani zincir değişmiş bir girdi dosyasıyla koşamaz: arşivin
yıllık dakika dosyaları kendi künyelerindeki özlerle (dukascopy.oku_ham), kalite denetiminin saatlik çapraz sınama
dosyaları ve takvimin ham sayfaları ise dizinlerinin kendi `ozler.json` dosyasıyla (`ozler.sina`; kalite.main ve
takvim_kur.main okumadan önce çağırır). Takvim veri denetiminden ÖNCE kurulur: veri denetiminin haber makası ölçüsü
takvimi okur ve eski bir takvimle ölçmemelidir.

Adımlardan biri düşerse SONRAKİ adımlar koşmaz. Son dört adım (ölçüm → şekiller → ders metinleri → kapı) tek bir
yayın katmanı yazar (YAYIN_YOLLARI: ölçüm dosyası, figür dizini, sekiz ders); o katman ölçüm adımından önce yedeklenir
ve dört adımdan biri düşerse yedek geri konur. Yani yarım bir yayın katmanı (yeni ölçüm ve yeni figürlerle eski dersler)
diskte kalmaz; düşüşten sonra katman, zincir başlamadan önceki hâlidir. Daha önceki adımların çıktısı (takvim, veri
denetimi, koşu, karşı olgu) geri alınmaz: onlar yayın katmanının girdisidir ve bir sonraki koşu onları baştan yazar.

Ön koşul: ön kaydın git geçmişini baştan sona taşıyan bir klon. Ön kaydın geçmişi (metodoloji dersindeki tablo)
depodan okunur; git'siz bir kopyada ya da sınırı ön kaydın ilk commit'ini kesen sığ bir klonda (git clone --depth 1,
actions/checkout öntanımlısı) zincir ilk adımda adıyla düşer — geçmiş uydurulmaz. Öyle bir klonda: git fetch
--deepen=N ya da --unshallow.

Ortam:  python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt   (sürümleri sabit)
Koşum:  .venv/bin/python hepsi.py [--sinamasiz] [--kosusuz]
  --sinamasiz   birim sınamalarını atlar (yalnız yerel yineleme için; yayından önceki koşu sınamalıdır)
  --kosusuz     strateji koşusunu atlar ve depodaki koşu çıktısından ölçer (ders metni yinelemesi için)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parents[1]
PY = sys.executable

ADIMLAR = [
    ("sınamalar", [PY, "-m", "pytest", "-q", "testler"], "sinama"),
    ("takvim", [PY, "takvim_kur.py"], None),
    ("takvimin fiyat sınaması", [PY, "takvim_sina.py"], None),
    ("veri denetimi", [PY, "kalite.py"], None),
    ("strateji koşusu", [PY, "kosu.py"], "kosu"),
    # Sonuçlardan sonra değişen kuralların etkisi (metodoloji dersi). Kod ve koşu çıktısı kayıttakiyle aynıysa
    # yeniden koşmaz; değiştiyse her kuralı geçici kopyada eski hâline döndürüp koşar (dört paralel süreçle ~25 dk).
    ("karşı olgu", [PY, "karsi_olgu.py"], None),
    ("ölçüm", [PY, "ders_olcum.py"], None),
    ("şekiller", [PY, "sekil.py"], None),
    ("ders metinleri", [PY, "ders_yaz.py"], None),
    ("kapı", [PY, "dogrula.py"], None),
]


def git_on_kosulu() -> str | None:
    """Ön kaydın git geçmişi baştan sona okunabiliyor mu (tek tanım: ders_olcum.gecmis_sorunu); okunamıyorsa zincir
    hesaba girişmeden düşer."""
    import ders_olcum
    return ders_olcum.gecmis_sorunu()


#: Yayın katmanının ilk adımı: bu adımdan kapıya kadar yazılan her şey birlikte kalır ya da birlikte geri alınır.
YAYIN_ILK = "ölçüm"


def yayin_yollari() -> list[Path]:
    """Yayın katmanının dosyaları: ölçüm dosyası, figür dizini (sekil.py ve ders_yaz.py'nin ön kayıt kopyası) ve sekiz
    ders. Liste ders sırasından (adlar.DERS_SIRA) kurulur; elle tutulan bir ders listesi yeni bir dersi dışarıda bırakırdı."""
    import adlar
    icerik = KOK / "site" / "src" / "content" / "arastirma"
    return ([BURASI / "cikti" / "ders" / "olcum.json", KOK / "site" / "public" / "arastirma" / "fx-gunici"]
            + [icerik / f"{s}.mdx" for s in adlar.DERS_SIRA])


class Yedek:
    """Yayın katmanının yedeği: al() her yolu (dosya ya da dizin) geçici dizine kopyalar, geri() her yolu yedekteki
    hâline döndürür — yedekte olmayan yol (o anda yoktu) silinir, dizin içinde sonradan eklenen dosyalar da gider."""

    def __init__(self, yollar: list[Path]):
        self.yollar = yollar
        self.dizin = Path(tempfile.mkdtemp(prefix="fxg_yedek_"))
        self.vardi: dict[Path, bool] = {}

    def _yer(self, i: int) -> Path:
        return self.dizin / str(i)

    def al(self) -> None:
        for i, y in enumerate(self.yollar):
            self.vardi[y] = y.exists()
            if y.is_dir():
                shutil.copytree(y, self._yer(i))
            elif y.exists():
                shutil.copy2(y, self._yer(i))

    def geri(self) -> None:
        for i, y in enumerate(self.yollar):
            if y.is_dir():
                shutil.rmtree(y)
            elif y.exists():
                y.unlink()
            if self.vardi.get(y):
                (shutil.copytree if self._yer(i).is_dir() else shutil.copy2)(self._yer(i), y)

    def sil(self) -> None:
        shutil.rmtree(self.dizin, ignore_errors=True)


def main(argv: list[str]) -> int:
    sorun = git_on_kosulu()
    if sorun:
        print(f"✗ ön koşul: {sorun}")
        return 2
    atla = {"sinama"} if "--sinamasiz" in argv else set()
    if "--kosusuz" in argv:
        atla.add("kosu")
    t0 = time.monotonic()
    yedek: Yedek | None = None
    try:
        for ad, komut, anahtar in ADIMLAR:
            if anahtar in atla:
                print(f"· {ad}: atlandı")
                continue
            if ad == YAYIN_ILK:
                yedek = Yedek(yayin_yollari())
                yedek.al()
            t1 = time.monotonic()
            print(f"▶ {ad}", flush=True)
            r = subprocess.run(komut, cwd=BURASI)
            if r.returncode != 0:
                print(f"✗ {ad} düştü (çıkış {r.returncode}); sonraki adımlar koşmadı")
                if yedek:
                    yedek.geri()
                    print("↺ yayın katmanı (ölçüm, figürler, dersler) zincirden önceki hâline geri kondu")
                return r.returncode
            print(f"✓ {ad} · {time.monotonic() - t1:.0f} sn", flush=True)
    except BaseException:
        # Kesilen bir koşu da (Ctrl-C, sinyal) yarım katman bırakmaz.
        if yedek:
            yedek.geri()
            print("↺ yayın katmanı zincirden önceki hâline geri kondu (koşu kesildi)")
        raise
    finally:
        if yedek:
            yedek.sil()
    print(f"✓ zincir tamam · {(time.monotonic() - t0) / 60:.1f} dk")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
