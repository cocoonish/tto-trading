#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Haber takviminin BEŞİNCİ geçişi: FOMC basın toplantısının saat KURALI (bulut koşucusu).

Üçüncü ve dördüncü geçiş ölçtü: Fed'in aylık etkinlik sayfaları ve takvim beslemesi basın toplantısını
ayrı saatle yalnız Eylül 2025'ten sonra listeliyor (17.09.2025'ten itibaren "FOMC Press Conference ·
2:30 p.m."); öncesinde kayıt "FOMC Meeting · 2:00 p.m. · Press Conference" ve oradaki saat KARARIN
yayım saati. Tek istisna 30.01.2019: o ayın sayfasındaki duyuru basın toplantısının saatini yazıyor.
Basın toplantısının saati tarih tarih kaynakta olmadığına göre kaynağı Fed'in KURALIDIR: Fed'in
13.03.2013 duyurusu karar metnini 14:00'e, basın toplantısının başlangıcını "yaklaşık 14:30"a koydu ve
toplantı takvimi duyuruları kuralı yineleyebilir. Bu geçiş o belgeleri Fed'in KENDİ kataloğundan bulur:

  1. Basın duyuruları sayfası istenir ve sayfanın okuduğu JSON adresi sayfadan çözülür (adres tahmin
     edilmez). Sayfa adres vermezse Fed'in bilinen besleme adı (`/json/ne-press.json`) ADAY olarak
     denenir ve künyeye aday diye yazılır.
  2. Katalogdan 2012'den bu yana başlığı toplantı takvimi, basın toplantısı, basın brifingi ya da yayım
     saati değişikliği geçen her duyuru indirilir.
  3. Katalog okunamazsa ya da bir belge katalogda yoksa, bu oturumda arama motoruyla bulunmuş dört
     adres (BILINEN) ayrıca istenir ve künyeye "katalog dışı" diye yazılır.

PARÇA (`TTO_PARCA`): `fed-kural` · `londra-tatil` (dördüncü geçişin parçası; aynı iş akışı kuyruğunda
yer tutmasın diye burada da çağrılabilir). Yalnız indirir; kural ayrıştırmada (`takvim_kur.fomc_kurali`).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import arsiv_takvim3 as a3
import arsiv_takvim4 as a4

HAM = a3.HAM
KOK = "https://www.federalreserve.gov"
SAYFA = KOK + "/newsevents/pressreleases.htm"
ADAY_BESLEME = KOK + "/json/ne-press.json"
BASLIK = re.compile(r"(?i)schedule|news conference|press conference|press briefing|time change|release time")
#: Arama motoruyla bulunan adresler (16.10.2026): kural (13.03.2013), 2019 ve 2020 takvimleri, 2025–2026 takvimi.
BILINEN = ["/newsevents/pressreleases/monetary20130313a.htm", "/newsevents/pressreleases/monetary20180525a.htm",
           "/newsevents/pressreleases/monetary20190517a.htm", "/newsevents/pressreleases/monetary20240809a.htm"]


class Kunye5(a3.Kunye):
    def __init__(self, parca: str):
        self.yol = HAM / f"manifest5_{parca}.json"
        self.v = json.loads(self.yol.read_text(encoding="utf-8")) if self.yol.exists() else {}


def _kayitlar(veri: bytes) -> list[dict]:
    """Beslemenin kayıtları: bağlantısı /newsevents/pressreleases/ altında olan her sözlük. Alan adları
    tahmin edilmez; bağlantı, başlık ve tarih değerin biçiminden tanınır ve ham alanlar da saklanır."""
    try:
        d = json.loads(veri.decode("utf-8-sig", errors="replace"))
    except ValueError:
        return []
    yigin, out = [d], []
    while yigin:
        x = yigin.pop()
        if isinstance(x, list):
            yigin.extend(x)
        elif isinstance(x, dict):
            dizge = {k: v for k, v in x.items() if isinstance(v, str)}
            bag = next((v for v in dizge.values() if "/newsevents/pressreleases/" in v), None)
            if bag:
                baslik = max((v for v in dizge.values() if v != bag and not re.fullmatch(r"[\d/:.\sAPMapm-]*", v)),
                             key=len, default="")
                tarih = next((v for v in dizge.values() if re.search(r"\b(19|20)\d{2}\b", v) and v != bag
                              and v != baslik), "")
                out.append({"bag": bag, "baslik": baslik, "tarih": tarih, "alan": sorted(x)})
            yigin.extend(v for v in x.values() if isinstance(v, (list, dict)))
    return out


def fed_kural() -> None:
    k = Kunye5("fed-kural")
    s = k.kaydet(a3.getir(SAYFA))
    adresler: list[str] = []
    if s.get("dosya"):
        t = (HAM / s["dosya"]).read_text(encoding="utf-8", errors="replace")
        for m in re.findall(r"""["']((?:https://www\.federalreserve\.gov)?/[^"'\s]+\.json)["']""", t):
            u = m if m.startswith("http") else KOK + m
            if u not in adresler:
                adresler.append(u)
    print(f"sayfanın okuduğu JSON adresi: {adresler or 'yok'}", flush=True)
    kayit: list[dict] = []
    for u in adresler + ([ADAY_BESLEME] if ADAY_BESLEME not in adresler else []):
        b = k.kaydet(a3.getir(u))
        k.v[u]["kaynak"] = "sayfadan" if u in adresler else "aday (sayfa adres vermedi ya da başka adres verdi)"
        if b.get("dosya"):
            kk = _kayitlar((HAM / b["dosya"]).read_bytes())
            k.v[u]["kayit"] = len(kk)
            kayit += kk
        time.sleep(1.0)
    secilen: dict[str, dict] = {}
    for x in kayit:
        yil = re.search(r"\b(20\d{2})\b", x["tarih"]) or re.search(r"(20\d{2})\d{4}", x["bag"])
        if yil and int(yil.group(1)) >= 2012 and BASLIK.search(x["baslik"]):
            u = x["bag"] if x["bag"].startswith("http") else KOK + x["bag"]
            secilen.setdefault(u, x)
    print(f"katalog kaydı: {len(kayit)} · başlığı tutan (2012 →): {len(secilen)}", flush=True)
    for u, x in sorted(secilen.items()):
        print(f"    {x['tarih'][:24]:24s}  {x['baslik'][:110]}", flush=True)
    for u in secilen:
        if a3.kalan() < 60:
            break
        k.kaydet(a3.getir(u))
        k.v[u].update({"kaynak": "katalog", "baslik": secilen[u]["baslik"], "tarih": secilen[u]["tarih"]})
        time.sleep(1.0)
    for h in BILINEN:
        u = KOK + h
        if u in secilen or a3.kalan() < 60:
            continue
        k.kaydet(a3.getir(u))
        k.v[u]["kaynak"] = "katalog dışı (arama motoru)"
        time.sleep(1.0)
    k.v["_katalog"] = {"adres": adresler, "kayit": len(kayit), "secilen": len(secilen)}
    k.yaz()


PARCALAR = {"fed-kural": fed_kural, "londra-tatil": a4.londra_tatil}


def main() -> int:
    HAM.mkdir(parents=True, exist_ok=True)
    istenen = os.environ.get("TTO_PARCA", "").split() or list(PARCALAR)
    bilinmeyen = [p for p in istenen if p not in PARCALAR]
    if bilinmeyen:
        raise SystemExit(f"bilinmeyen parça: {bilinmeyen} (tanınan: {list(PARCALAR)})")
    for p in istenen:
        print(f"── {p}", flush=True)
        PARCALAR[p]()
    print(f"bitti: {time.monotonic() - a3.T0:.0f} sn · {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC")
    return 0


if __name__ == "__main__":
    sys.exit(main())
