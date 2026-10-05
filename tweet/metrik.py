#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ETKİLEŞİM ÖLÇÜMÜ — gönderilerin X'te ne kadar okunduğu (05.10.2026).

Depoda tek bir etkileşim ölçüsü yoktu: hangi uzunluğun, saatin ya da biçimin
daha iyi okunduğu ancak tahmin edilebiliyordu. "Uydurma yok" ilkesinin X
tarafındaki karşılığı bu ölçümdür. Bu modül YALNIZ OKUR ve biriktirir; eşik,
"en iyi saat" ya da biçim hükmü KURMAZ (ölçülmemiş bir seviyeye eşik konmaz;
örneklem bugün birkaç biçim 3 gönderisi).

NEREDE KOŞAR. Ayrı bir iş akışı ya da cron YOK: X'te refresh token tek
kullanımlıktır ve her yenilemede döner; ayrı bir okuma koşusu jetonu bir kez
daha döndürür ve commit'lenmezse ertesi sabahın gönderimini yakar (30.08'de
yaşandı). Okuma bu yüzden gonder.py'nin İÇİNDE, gönderim BİTTİKTEN sonra ve
AYNI erişim jetonuyla yapılır — ek jeton dönüşü sıfır. Gönderim olmayan gün
okuma da yoktur; günlük bülten her gün gittiği için haftalık ritim tutar.
Yeni cron eklenmedi: yayin_takvimi.json tweet.yml'in cron indekslerine bağlı.

ASLA GÖNDERİMİ ETKİLEMEZ. `haftalik()` hiçbir koşulda istisna yükseltmez;
402 (kredi), 403 (kapsam), ağ hatası ve bozuk yanıt yutulur, sebebi
metrik.json'a `son_hata` olarak yazılır (ölçülemeyen boş bırakılır, sebebi
yazılır). gonder.py çağrıyı ayrıca sarar. GEÇİCİ hata (429, 5xx, ağ) ayrıca
`gecici_hata_ani` yazar ve haftalık sınırı beklemeden en erken 12 saat sonraki
gönderim koşusunda bir kez daha denenir (`zamani_geldi`); kalıcı hata bekler.

CETVEL. Gösterim birikimli bir sayıdır; farklı yaşlardaki gönderiler
kıyaslanamaz. Her gönderi iki SABİT eşikte kaydedilir — yaşı 24 saati geçtikten
sonraki ilk okumada ("24s") ve 7 günü geçtikten sonraki ilk okumada ("7g", yaş
< 30 gün) — ve gerçek yaş ölçümün yanına saat olarak yazılır; kıyas yapan okur
yaşı görür. "24s"nin üst sınırı 7 değil 10 GÜNDÜR (`UST_24S`) ve "7g" ancak
"24s" ÖNCEKİ bir okumada yazılmışsa ya da yaş 10 günü geçtiyse yazılır. Sebep
ölçüldü: okuma gönderimden SONRA ve haftada bir koşar, yani okuma koşusunda
atılan gönderi bir sonraki okumada tanım gereği ≥ 7 günlüktür; üst sınır 7
günken o gönderi (ve cron gecikmesiyle bir sonrakinin gönderisi) "24s"yi HİÇ
almıyor, doğrudan "7g"ye düşüyordu — günlük gönderide ~%21, okuma gününe bağlı
yanlı bir eksik. Haftalık okumada "24s" yaşı bu yüzden ~1–10 gün arası dağılır.
Bir eşik okumada kaçırıldıysa (yaş > 10 gün) o bant boş kalır (uydurulmaz).
İlk okumada ve atlanan ya da başarısız bir okumadan sonra "7g" 30 güne kadar
yaşları birlikte taşır; bant içi kıyas da `yas_saat` ile yapılır.

Alanlar: tür · biçim sürümü · karakter uzunluğu · gönderim anı ve İstanbul
saati · gösterim · beğeni · yanıt · yeniden paylaşım · alıntı · yer imi. Hesap
adı YAZILMAZ (istekte kullanıcı genişletmesi yok).

    python3 tweet/metrik.py           # metrik.json özetini bas (ağa çıkmaz)
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

BURASI = Path(__file__).resolve().parent
METRIK = BURASI / "metrik.json"
ARSIV = BURASI / "arsiv"
UC = "https://api.x.com/2/tweets"

HAFTA = dt.timedelta(days=7)
PENCERE = dt.timedelta(days=30)
# "24s" bandının üst sınırı: 7 gün + 24 saat + okuma aralığının payı. Ölçüldü
# (gerçek defterin gönderim deseni, 14 başlangıç fazı): 9 günde %1,4, 10 günde
# %0 gönderi "24s"yi kaçırıyor; 7 günde %21.
UST_24S = dt.timedelta(days=10)
# (bant adı, eşik, üst sınır) — belge; kural `bant_sec`te (7g'nin kapısı var).
BANTLAR = (("24s", dt.timedelta(hours=24), UST_24S),
           ("7g", HAFTA, PENCERE))
# Geçici okuma hatasından sonra yeniden deneme: haftalık sınırı beklemeden, en
# erken bu kadar sonra (bir sonraki gönderim koşusu; aynı koşuda döngü yok).
YENIDEN_DENEME = dt.timedelta(hours=12)
ISTANBUL = dt.timezone(dt.timedelta(hours=3))          # 2016'dan beri yaz saati yok
ALANLAR = (("gosterim", "impression_count"), ("begeni", "like_count"),
           ("yanit", "reply_count"), ("yeniden", "retweet_count"),
           ("alinti", "quote_count"), ("yer_imi", "bookmark_count"))


def _an(s) -> dt.datetime | None:
    try:
        a = dt.datetime.fromisoformat(str(s))
    except (TypeError, ValueError):
        return None
    return a if a.tzinfo else a.replace(tzinfo=dt.timezone.utc)


def yukle(yol: Path = METRIK) -> dict:
    try:
        d = json.loads(yol.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:                                          # noqa: BLE001
        return {}


def zamani_geldi(kayit: dict, simdi: dt.datetime) -> bool:
    """Haftada bir: son DENEME (başarılı ya da değil) yedi günden eskiyse. Tek
    istisna GEÇİCİ hata (429, 5xx, ağ): son deneme geçici hatayla bittiyse
    (`gecici_hata_ani` son denemeden eski değil) en erken YENIDEN_DENEME sonra
    bir kez daha denenir. Önce tek bir 503 bir hafta beklemeye çeviriyordu ve
    o haftanın gönderileri "24s" bandını kalıcı kaybediyordu. Kalıcı hata
    (402 kredi, 403 kapsam, öbür 4xx) haftalık sınırda kalır: her koşuda yeniden
    sormak her koşuda aynı hatayı üretir."""
    son = _an(kayit.get("son_deneme"))
    if son is None or simdi - son >= HAFTA:
        return True
    gecici = _an(kayit.get("gecici_hata_ani"))
    return gecici is not None and gecici >= son and simdi - gecici >= YENIDEN_DENEME


def bant_sec(yas: dt.timedelta, yazilmis_bantlar: set[str]) -> str | None:
    """Bu okumada yazılacak TEK bant (ya da None). `yazilmis_bantlar` gönderinin
    ÖNCEKİ okumalarda yazılmış bantları. "24s": yaş [24 sa, 10 g) ve henüz yok.
    "7g": yaş ≥ 7 g, henüz yok ve ya "24s" önceki bir okumada yazılmış ya da yaş
    ≥ 10 g (24s artık kaçırılmıştır). Aynı okuma iki ayrı yaşın ölçüsü sayılmaz;
    "7g"si yazılmış gönderiye sonradan "24s" yazılmaz (eski cetvelin kayıtları)."""
    if not yazilmis_bantlar & {"24s", "7g"} and BANTLAR[0][1] <= yas < UST_24S:
        return "24s"
    if "7g" not in yazilmis_bantlar and HAFTA <= yas < PENCERE \
            and ("24s" in yazilmis_bantlar or yas >= UST_24S):
        return "7g"
    return None


def okunacaklar(defter: dict, kayit: dict, simdi: dt.datetime) -> list[dict]:
    """Son 30 günün kimlikli gönderilerinden, bir bandı bu okumada dolacak olanlar
    (`bant_sec`). Kaçırılan bant boş kalır."""
    yazilmis: dict[str, set[str]] = {}
    for o in kayit.get("olcumler") or []:
        yazilmis.setdefault(o.get("anahtar"), set()).add(o.get("bant"))
    out = []
    for anahtar, v in defter.items():
        idler = (v or {}).get("idler") or []
        gonderim = _an((v or {}).get("zaman"))
        if not idler or gonderim is None:
            continue
        yas = simdi - gonderim
        if not (dt.timedelta(0) <= yas < PENCERE):
            continue
        bant = bant_sec(yas, yazilmis.get(anahtar, set()))
        if bant:
            out.append({"anahtar": anahtar, "kimlik": str(idler[0]),
                        "gonderim": gonderim, "bant": bant, "yas": yas})
    return out


def _bicim(anahtar: str, bulten_dizin: Path | None) -> int | str | None:
    tur, ad = anahtar.split(":", 1)
    if tur == "analiz":
        return "analiz"
    if tur == "bulten" and bulten_dizin is not None:
        try:
            b = json.loads((bulten_dizin / f"{ad}.json").read_text(encoding="utf-8"))
            return int(b.get("surum") or 2)
        except Exception:                                      # noqa: BLE001
            return None
    return None


def _uzunluk(anahtar: str, arsiv: Path) -> int | None:
    """Gönderilen metnin karakter uzunluğu — arşivdeki metinden (zincirse toplam)."""
    yol = arsiv / (anahtar.replace(":", "-") + ".txt")
    if not yol.exists():
        return None
    govde = yol.read_text(encoding="utf-8").split("\n", 2)
    parcalar = (govde[2] if len(govde) > 2 else "").strip().split("\n\n---\n\n")
    return sum(len(p.strip()) for p in parcalar)


def _istek_varsayilan(url: str, params: dict, erisim: str):
    import requests
    return requests.get(url, params=params, timeout=30,
                        headers={"Authorization": f"Bearer {erisim}"})


def haftalik(erisim: str, defter: dict, yol: Path = METRIK, simdi: dt.datetime | None = None,
             istek=None, arsiv: Path | None = None, bulten_dizin: Path | None = None) -> str:
    """Zamanı geldiyse okur ve yazar; ne yaptığını tek satırla döndürür.
    HİÇBİR KOŞULDA istisna yükseltmez."""
    try:
        return _haftalik(erisim, defter, yol, simdi or dt.datetime.now(dt.timezone.utc),
                         istek or _istek_varsayilan, arsiv or ARSIV, bulten_dizin)
    except BaseException as e:                                 # noqa: BLE001 — gönderim asla etkilenmez
        return f"metrik okunamadı ({type(e).__name__}: {str(e)[:120]}) — gönderim etkilenmedi"


def gecici_mi(kod: int | None = None, hata: BaseException | None = None) -> bool:
    """Geçici okuma hatası: HTTP 429 ya da 5xx, ya da ağ hatası (OSError —
    requests.RequestException ve Timeout/ConnectionError alt sınıfları dahil).
    Bozuk yanıt (ValueError), 402 ve 403 kalıcı sayılır."""
    if hata is not None:
        return isinstance(hata, OSError)
    return kod is not None and (kod == 429 or kod >= 500)


def _haftalik(erisim, defter, yol, simdi, istek, arsiv, bulten_dizin) -> str:
    kayit = yukle(yol)
    if not zamani_geldi(kayit, simdi):
        return f"metrik: haftalık sınır — son deneme {kayit.get('son_deneme')}"
    liste = okunacaklar(defter, kayit, simdi)
    kayit["surum"] = 1
    kayit["son_deneme"] = simdi.isoformat(timespec="seconds")
    kayit.pop("gecici_hata_ani", None)         # yalnız BU denemenin sonucu yazar
    kayit.setdefault("olcumler", [])
    if not liste:
        kayit.pop("son_hata", None)
        _yaz(yol, kayit)
        return "metrik: bandı dolan gönderi yok"
    kimlikler = sorted({o["kimlik"] for o in liste})[:100]
    try:
        yanit = istek(UC, {"ids": ",".join(kimlikler), "tweet.fields": "public_metrics"}, erisim)
        kod = getattr(yanit, "status_code", None)
        if kod != 200:
            kayit["son_hata"] = f"HTTP {kod}"
            if gecici_mi(kod=kod):
                kayit["gecici_hata_ani"] = kayit["son_deneme"]
            _yaz(yol, kayit)
            return (f"metrik: X {kod} — okunamadı, sebebi kayda yazıldı"
                    + ("; geçici, sonraki koşuda yeniden denenir" if gecici_mi(kod=kod) else "")
                    + "; gönderim etkilenmedi")
        veri = {str(t.get("id")): t.get("public_metrics") or {} for t in (yanit.json().get("data") or [])}
    except Exception as e:                                     # noqa: BLE001
        kayit["son_hata"] = f"{type(e).__name__}: {str(e)[:120]}"
        if gecici_mi(hata=e):
            kayit["gecici_hata_ani"] = kayit["son_deneme"]
        _yaz(yol, kayit)
        return f"metrik: istek düştü ({kayit['son_hata']}) — gönderim etkilenmedi"
    yeni = 0
    for o in liste:
        pm = veri.get(o["kimlik"])
        if pm is None:
            continue                                           # silinmiş ya da dönmemiş gönderi: ölçülemedi
        tur = o["anahtar"].split(":", 1)[0]
        kayit["olcumler"].append({
            "anahtar": o["anahtar"], "kimlik": o["kimlik"], "tur": tur,
            "bicim": _bicim(o["anahtar"], bulten_dizin),
            "uzunluk": _uzunluk(o["anahtar"], arsiv),
            "gonderim": o["gonderim"].isoformat(timespec="seconds"),
            "gonderim_saat_tsi": o["gonderim"].astimezone(ISTANBUL).strftime("%H:%M"),
            "olcum": simdi.isoformat(timespec="seconds"),
            "bant": o["bant"], "yas_saat": round(o["yas"].total_seconds() / 3600, 1),
            **{ad: pm.get(alan) for ad, alan in ALANLAR},
        })
        yeni += 1
    kayit.pop("son_hata", None)
    _yaz(yol, kayit)
    return f"metrik: {yeni}/{len(liste)} gönderi ölçüldü"


def _yaz(yol: Path, kayit: dict) -> None:
    yol.write_text(json.dumps(kayit, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    k = yukle()
    print(f"metrik.json: {len(k.get('olcumler') or [])} ölçüm · son deneme {k.get('son_deneme')}"
          + (f" · son hata {k['son_hata']}" if k.get("son_hata") else ""))
