#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Veri iş akışının KOŞU DEFTERİ — `bulten/kosu_nabzi.json`.

Neden defter, neden tek kayıt değil: dosya 04.09.2026'ya kadar her koşuda
ÜZERİNE yazıyordu, yani yalnız SON koşuyu tutuyordu. "Bu sabahki veri penceresi
ateşlendi mi" sorusu bu yüzden geriye dönük CEVAPSIZDI — 04.09 sabahı altı
cron'un hiçbiri ateşlenmemişti ve depoda bunun izi yoktu; dosyada 03.09 18:51
duruyordu ve aynı dosya "sağlıklı" ile "iki gündür hiç koşmadı" hâllerini ayırt
edilemez gösteriyordu. Bu, "bir denetimin KAPSAMI denetimin parçasıdır"
kusurunun bir eşi: nabız var, okunuyor, hata vermiyor, ama sorulan soruyu
göremiyor.

UYUMLULUK SÖZLEŞMESİ — bozulamaz. İki okuyucu bu dosyanın ÜST DÜZEY alanlarını
okuyor: `denetim.Denetim.nabiz()` ve `zincir.durum()`. İkisi de `veri_kosusu`
ile `sonuc` bekliyor. Defter o alanları KALDIRMAZ; en son kaydın kopyası olarak
üst düzeyde tutar. Yani eski okuyucu yeni dosyayı hiç değişmeden okur.

Bu dosya bilerek AYRI bir modül: kod veri.yml'in içinde gömülü bir heredoc
olsaydı duman sınaması onu çağıramaz, ancak bir KOPYASINI sınayabilirdi — ve
iki kopya bir gün sessizce ayrışır.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent

# Kaç koşu saklanır. 60 ≈ 8–9 iş günü (günde 6 cron + elle tetiklemeler) — yani
# "sabah penceresi kaç günde ateşlendi" sorusuna cevap verecek kadar, dosyayı
# okunmaz yapmayacak kadar. Eşik değil, pencere.
AZAMI = 60

_ACIKLAMA = (
    "Veri iş akışının koşu defteri. Üst düzeydeki veri_kosusu/sonuc alanları EN SON "
    "kaydın kopyasıdır (denetim.py ve zincir.py onları okur); kosular listesi son "
    f"{AZAMI} koşuyu tutar, en eski başta. Tek kayıt tutulduğu sürece 'sabah veri "
    "penceresi ateşlendi mi' sorusu geriye dönük cevapsızdı."
)


def yol(kok: Path | None = None) -> Path:
    return (kok or BURASI) / "kosu_nabzi.json"


def oku(p: Path) -> dict:
    """Defteri oku. Bozuk ya da eksik dosya İSTİSNA FIRLATMAZ: nabız tutmak
    hiçbir zaman koşuyu düşürmemeli — kayıt tutamamak, kayıt tutmamaktan iyidir
    ama koşuyu öldürmekten de iyidir."""
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:                                          # noqa: BLE001
        return {}


def _kosular(d: dict) -> list[dict]:
    """Mevcut kayıtlar. ESKİ BİÇİM GÖÇÜ: dosyada yalnız üst düzey `veri_kosusu`
    varsa (defter öncesi sürüm) o tek koşu kayıp sayılmaz, deftere ilk satır
    olarak alınır."""
    k = d.get("kosular")
    if isinstance(k, list):
        return [x for x in k if isinstance(x, dict)]
    if d.get("veri_kosusu"):
        return [{"zaman": str(d["veri_kosusu"]), "sonuc": str(d.get("sonuc", "bilinmiyor")),
                 "tetik": "bilinmiyor"}]
    return []


def kaydet(p: Path, *, sonuc: str, tetik: str = "bilinmiyor", cron: str | None = None,
           butce_dk: float | None = None, atlanan_butce: list[str] | None = None,
           an: dt.datetime | None = None) -> dict:
    """Bir koşuyu deftere yaz ve dosyayı kur. Yazılan sözlüğü döndürür."""
    d = oku(p)
    kayit: dict = {
        "zaman": (an or dt.datetime.now(dt.timezone.utc)).isoformat(timespec="seconds"),
        "sonuc": sonuc or "bilinmiyor",
        "tetik": tetik or "bilinmiyor",
    }
    if cron:
        # Hangi PENCERE ateşlendi. Altı cron var ve arıza gün-biçimli değil
        # pencere-biçimli: 04.09'da sabah penceresi (13 2) düştü, öğleden
        # sonrakiler koştu. Tetik adı tek başına bunu ayırt edemez.
        kayit["cron"] = cron
    # 5. ve 6. maddeler (sabah bütçesi, hat sıralaması/kesme) HENÜZ YOK.
    # Alanlar burada duruyor ki o maddeler geldiğinde defterin biçimi
    # değişmesin; bugün hiçbir çağıran onları DOLDURMUYOR ve boş alan
    # yazılmıyor — "ölçülmemiş bir şeyi ölçülmüş gibi göstermektense boş
    # bırakılır".
    if butce_dk is not None:
        kayit["butce_dk"] = butce_dk
    if atlanan_butce:
        kayit["atlanan_butce"] = list(atlanan_butce)

    kosular = _kosular(d)
    kosular.append(kayit)
    kosular = kosular[-AZAMI:]

    yeni = {
        "_aciklama": _ACIKLAMA,
        # UYUMLULUK: en son kaydın kopyası. denetim.nabiz() ve zincir.durum()
        # bu iki alanı okuyor; biçim değişse de onlar kırılmaz.
        "veri_kosusu": kayit["zaman"],
        "sonuc": kayit["sonuc"],
        "kaynak": "veri.yml",
        "kosular": kosular,
    }
    p.write_text(json.dumps(yeni, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return yeni


def son_pencereler(d: dict, gun: int = 7) -> list[dict]:
    """Son `gun` gündeki koşular — 'sabah penceresi ateşlendi mi' sorusunun
    ham verisi. Bugün hiçbir kapı bunu okumuyor: ölçüm önce birikir, eşik
    ancak ölçüldükten sonra konur."""
    sinir = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=gun)
    cikti = []
    for k in _kosular(d):
        try:
            t = dt.datetime.fromisoformat(str(k.get("zaman", "")).replace("Z", "+00:00"))
        except Exception:                                      # noqa: BLE001
            continue
        if t >= sinir:
            cikti.append(k)
    return cikti


def main() -> int:
    ortam = os.environ.get
    butce = ortam("TTO_BUTCE_DK")
    atlanan = [x for x in (ortam("TTO_ATLANAN_BUTCE") or "").replace(",", " ").split() if x]
    d = kaydet(
        yol(),
        sonuc=ortam("ADIM_SONUC") or "bilinmiyor",
        tetik=ortam("TETIK") or "bilinmiyor",
        cron=ortam("CRON") or None,
        butce_dk=float(butce) if butce else None,
        atlanan_butce=atlanan or None,
    )
    son = d["kosular"][-1]
    print(f"nabız: {son['zaman']} · {son['sonuc']} · {son['tetik']}"
          + (f" · {son['cron']}" if son.get("cron") else "")
          + f"  (defterde {len(d['kosular'])} koşu)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
