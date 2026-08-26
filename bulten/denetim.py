#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten KALİTE DENETİMİ — yayından önce koşar, eksikse durdurur.

Neden var: bülteni her sabah bir ajan yazıyor ve kimse başında durmuyor. "Bugünkü
kadar ayrıntılı olacak mı, atladığımız bir şey olacak mı" sorusunun cevabı güven
değil ÖLÇÜM olmalı. Bu script bülteni açar, yazının ve verinin standardı tutup
tutmadığını madde madde ölçer ve tutmuyorsa çıkış kodu 1 verir.

  python3 bulten/denetim.py                 # bugünün bülteni
  python3 bulten/denetim.py 2026-08-23      # belirli gün
  python3 bulten/denetim.py --hepsi         # bütün arşiv
  python3 bulten/denetim.py --ayrinti       # geçen maddeleri de yaz

Denetim üç sınıf bulgu üretir:
  ENGEL   yayına gitmemeli (eksik bölüm, kısa yazı, atıfsız büyük hareket, kod dili)
  UYARI   düzeltilmeli ama yayını durdurmaz (özet oranı düşük, kaynak okunamamış)
  BİLGİ   sayısal döküm
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import date, datetime
from pathlib import Path

BURASI = Path(__file__).resolve().parent
KOK = BURASI.parent
BULTEN = KOK / "site" / "src" / "data" / "bulten"

# ─────────────────────────── standart (görev metinlerindeki hedeflerle aynı)
HABER_BOLUM_ASGARI = 200      # kelime — her haber bölümü
YAZI_BOLUM_ASGARI = 300       # kelime — yazı-özel bölümler
YORUM_ASGARI = {"gunluk": 350, "haftalik": 600}
ZORUNLU_HABER_BOLUMU = ["tr_makro", "tr_piyasa", "global_makro", "global_politika",
                        "global_piyasa"]
ZORUNLU_YAZI_BOLUMU = ["faiz_fx_surucu", "emtia_surucu", "risk_firsat", "beklenti"]
ASGARI_ENSTRUMAN = 40
ASGARI_TL_FAIZ = 18
ASGARI_TUREV = 7
ASGARI_HABER = 25
ASGARI_OZET_ORANI = 0.35
ASGARI_KILIT = 3
ASGARI_KRITIK_TAKVIM = 3
BUYUK_HAREKET_ESIGI = 1.5     # % — bunu aşan hareket metinde ANILMALI

# Okura hiçbir şey söylemeyen geliştirici dili
KOD_DILI = re.compile(
    r"\b[a-z_][a-z0-9_]*\.(py|json|csv|mdx|astro)\b|"
    r"\bozet\.json\b|\bayar\.py\b|guncelle\.py|\bhat(?:ı|ın|lar)?\b\s*(?:koş|düş)|"
    r"\b[a-z]+_[a-z]+_[a-z]+\b(?![^<]*</code>)", re.I)
# Yatırım tavsiyesi sayılabilecek kalıplar
TAVSIYE = re.compile(
    r"\b(al[ıi]n|sat[ıi]n|pozisyon a[çc]|hedef fiyat|tavsiye ediyoruz|öneriyoruz|"
    r"kesinlikle al|kesinlikle sat|portföy[üu]n[üu]ze ekleyin)\b", re.I)


def _duz(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def _kelime(html: str) -> int:
    return len(_duz(html).split())


def _sade(m: str) -> str:
    m = unicodedata.normalize("NFKD", (m or "").lower())
    return re.sub(r"[^a-z0-9ğüşiöç ]", " ", m)


class Denetim:
    def __init__(self, b: dict, ayrinti: bool = False):
        self.b = b
        self.ayrinti = ayrinti
        self.engel: list[str] = []
        self.uyari: list[str] = []
        self.bilgi: list[str] = []
        self.gecen: list[str] = []

    def _ok(self, m: str):
        self.gecen.append(m)

    # ────────────────────────────────────────────── bölümler ve uzunluk
    def yazi(self):
        b = self.b
        tur = b.get("tur", "gunluk")
        g = b.get("gundem") or {}
        if b.get("gundem_kaynagi") != "yazili":
            self.engel.append("Gündem yazısı YAZILMAMIŞ — sayfada yalnız otomatik taban "
                              "metin var (gundem_kaynagi 'yazili' değil).")
        for bid in ZORUNLU_HABER_BOLUMU:
            n = _kelime(g.get(bid, ""))
            if n == 0:
                self.engel.append(f"Gündem bölümü BOŞ: {bid}")
            elif n < HABER_BOLUM_ASGARI:
                self.engel.append(f"Gündem bölümü kısa: {bid} — {n} kelime "
                                  f"(asgari {HABER_BOLUM_ASGARI})")
            else:
                self._ok(f"{bid}: {n} kelime")
        for bid in ZORUNLU_YAZI_BOLUMU:
            n = _kelime(g.get(bid, ""))
            if n == 0:
                self.engel.append(f"Yazı bölümü BOŞ: {bid}")
            elif n < YAZI_BOLUM_ASGARI:
                self.engel.append(f"Yazı bölümü kısa: {bid} — {n} kelime "
                                  f"(asgari {YAZI_BOLUM_ASGARI})")
            else:
                self._ok(f"{bid}: {n} kelime")
        ny = _kelime(b.get("yorum") or "")
        hedef = YORUM_ASGARI.get(tur, 350)
        if ny == 0:
            self.engel.append("Okuma yazısı (yorum) YOK")
        elif ny < hedef:
            self.engel.append(f"Okuma yazısı kısa: {ny} kelime (asgari {hedef})")
        else:
            self._ok(f"okuma: {ny} kelime")
        oz = b.get("ozet") or {}
        if not oz.get("ne_oldu") or not oz.get("ne_bekleniyor"):
            self.uyari.append("Kural tabanlı özet ('ne oldu / ne bekleniyor') eksik")

    # ────────────────────────────────────────────── veri katmanları
    def veri(self):
        b = self.b
        p = b.get("piyasa") or {}
        n_enst = sum(len(g.get("satirlar", [])) for g in p.get("gruplar", []))
        if n_enst < ASGARI_ENSTRUMAN:
            self.engel.append(f"Piyasa fotoğrafı eksik: {n_enst} enstrüman "
                              f"(asgari {ASGARI_ENSTRUMAN})")
        else:
            self._ok(f"piyasa: {n_enst} enstrüman")
        if len(p.get("tr_faizleri", [])) < ASGARI_TL_FAIZ:
            self.engel.append(f"TL faiz seti eksik: {len(p.get('tr_faizleri', []))} satır "
                              f"(asgari {ASGARI_TL_FAIZ})")
        if len(p.get("turetilmis", [])) < ASGARI_TUREV:
            self.uyari.append(f"Türev büyüklük az: {len(p.get('turetilmis', []))} "
                              f"(asgari {ASGARI_TUREV})")
        if p.get("eksik"):
            self.uyari.append("Piyasa verisi gelmeyen: " + ", ".join(p["eksik"]))
        if p.get("hata"):
            self.engel.append(f"Piyasa katmanı düştü: {p['hata']}")

        kritik = b.get("kritik_takvim") or []
        if len(kritik) < ASGARI_KRITIK_TAKVIM:
            self.uyari.append(f"Kritik takvim zayıf: {len(kritik)} kayıt")
        else:
            self._ok(f"kritik takvim: {len(kritik)} kayıt")

        h = b.get("haberler") or {}
        maddeler = [m for bol in h.get("bolumler", []) for m in bol.get("maddeler", [])]
        if len(maddeler) < ASGARI_HABER:
            self.engel.append(f"Haber taraması zayıf: {len(maddeler)} madde "
                              f"(asgari {ASGARI_HABER})")
        else:
            self._ok(f"haber: {len(maddeler)} madde")
        ozetli = sum(1 for m in maddeler if m.get("ozet"))
        oran = ozetli / max(1, len(maddeler))
        if oran < ASGARI_OZET_ORANI:
            self.uyari.append(f"Haberlerin yalnız %{oran*100:.0f}'i özetli "
                              f"(hedef %{ASGARI_OZET_ORANI*100:.0f}) — kaynak sayfaları "
                              "okunamamış olabilir")
        kilit = next((bol for bol in h.get("bolumler", []) if bol.get("id") == "kilit"), None)
        n_kilit = len(kilit.get("maddeler", [])) if kilit else 0
        if n_kilit < ASGARI_KILIT:
            self.uyari.append(f"Kilit gelişme sayısı düşük: {n_kilit}")
        else:
            self._ok(f"kilit gelişme: {n_kilit}")
        if h.get("okunamayan"):
            self.uyari.append("Okunamayan kaynak: " + ", ".join(h["okunamayan"]))

    # ────────────────────────────────────────────── atıf: hareket ve kilit haber
    def _metin(self) -> str:
        g = self.b.get("gundem") or {}
        return _sade(" ".join([_duz(v) for v in g.values()]) + " " +
                     _duz(self.b.get("yorum") or ""))

    def atif(self):
        metin = self._metin()
        p = self.b.get("piyasa") or {}
        hareket = (p.get("en_cok_hareket") or {})
        anahtar_kelime = {
            "USD/TRY": ["usd try", "dolar kuru", "usdtry"],
            "BIST 100": ["bist"], "BIST 30": ["bist"], "BIST Bankacılık": ["bist", "banka"],
            "S&P 500": ["s p 500", "sp 500", "abd hisse", "wall"],
            "Nasdaq 100": ["nasdaq"], "Dow Jones": ["dow"], "Russell 2000": ["russell"],
            "VIX": ["vix", "oynaklık"], "Brent": ["brent", "petrol"], "WTI": ["wti", "petrol"],
            "Altın (XAU, ons)": ["altın"], "Gümüş (XAG, ons)": ["gümüş"],
            "Platin": ["platin"], "Bakır": ["bakır"], "Bitcoin": ["bitcoin", "kripto"],
            "Dolar endeksi (DXY)": ["dolar endeksi", "dxy"],
            "Doğal gaz (Henry Hub)": ["doğal gaz"], "RBOB benzin": ["benzin"],
            "Kalorifer yakıtı": ["distilat", "kalorifer", "motorin"],
            "Nikkei 225": ["nikkei"], "Hang Seng": ["hang seng"], "DAX": ["dax"],
            "STOXX Europe 600": ["stoxx", "avrupa hisse"], "FTSE 100": ["ftse"],
            "CAC 40": ["cac"], "FTSE MIB": ["mib", "italya"],
        }

        def anilmis(ad: str) -> bool:
            for k in anahtar_kelime.get(ad, [_sade(ad)]):
                if k in metin:
                    return True
            return _sade(ad).split()[0] in metin

        for kip, etiket in (("gunluk", "günün"), ("haftalik", "haftanın")):
            for x in (hareket.get(kip) or [])[:3]:
                if x.get("deger") is None or abs(x["deger"]) < BUYUK_HAREKET_ESIGI:
                    continue
                if not anilmis(x["ad"]):
                    self.engel.append(
                        f"ATIFSIZ HAREKET — {etiket} en büyük hareketlerinden "
                        f"{x['ad']} (%{x['deger']}) metinde hiç anılmamış. "
                        "Sebebini yaz ya da 'sebebi anlaşılmıyor' de.")
                else:
                    self._ok(f"{x['ad']} (%{x['deger']}) anılmış")

        # kilit gelişmeler metinde geçiyor mu
        h = self.b.get("haberler") or {}
        kilit = next((b for b in h.get("bolumler", []) if b.get("id") == "kilit"), None)
        for m in (kilit or {}).get("maddeler", [])[:4]:
            kelimeler = [w for w in _sade(m["baslik"]).split() if len(w) > 5][:6]
            if kelimeler and not any(w in metin for w in kelimeler):
                self.uyari.append(f"Kilit gelişme metinde işlenmemiş olabilir: "
                                  f"{m['baslik'][:70]}")

    # ────────────────────────────────────────────── dil ve üslup
    def dil(self):
        g = self.b.get("gundem") or {}
        tam = " ".join([_duz(v) for v in g.values()]) + " " + _duz(self.b.get("yorum") or "")
        for m in set(KOD_DILI.findall(tam)):
            pass
        bulunan = KOD_DILI.search(tam)
        if bulunan:
            self.engel.append(f"Okura anlamsız geliştirici dili: '{bulunan.group(0)}' "
                              "— dosya/alan/kod adı bültende geçmez.")
        else:
            self._ok("kod dili yok")
        t = TAVSIYE.search(tam)
        if t:
            self.engel.append(f"Yatırım tavsiyesi kalıbı: '{t.group(0)}'")
        else:
            self._ok("tavsiye dili yok")

    # ────────────────────────────────────────────── tazelik
    def tazelik(self):
        try:
            import ayar, gozlem                       # noqa: E402
        except Exception:
            return
        # Hattın ana saati ve içindeki farklı ritimli alanlar AYRI denetlenir;
        # yalnız ana saate bakmak, günlük bileşeni ilerleyen bir hattın haftalık
        # bileşeni donduğunda denetimi kör bırakır.
        saatler = [(hat, gozlem.son_gorulme(hat), azami, "")
                   for hat, azami in ayar.RITIM.items()]
        saatler += [(hat, gozlem.alan_son_gorulme(hat, alan), azami, ad)
                    for (hat, alan), (azami, ad) in ayar.RITIM_ALAN.items()]
        gecikmis = []
        for hat, sg, azami, ad in saatler:
            if not sg:
                continue
            try:
                t = datetime.fromisoformat(sg[1].replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue
            gun = (datetime.now() - t).days
            if gun > azami:
                gecikmis.append(f"{hat}{f' — {ad}' if ad else ''} ({gun}g)")
        if gecikmis:
            self.uyari.append("Veri gecikmiş hatlar: " + ", ".join(gecikmis))

    def tekrar(self):
        """Aynı olgu bültenin birden çok yerinde yeniden ANLATILIYOR mu.

        Bülten uzadıkça aynı hikâye bölümden bölüme kopyalanıyor ve okur dördüncü
        kez aynı cümleyi okuyor. Ölçü: farklı bölümlerde birebir geçen 7 kelimelik
        öbekler, bin kelimeye normalize edilmiş. Özet bölümlerinin (kilit, yorum)
        diğerlerine değmesi tanımı gereği meşru; ağır ihlal ÖZET OLMAYAN iki
        bölümün birbirini tekrar etmesidir — sayılan budur.
        """
        import tekrar as _t
        r = _t.olc(self.b)
        y = r["yogunluk"]
        ornek = "; ".join(f"[{'+'.join(yer)}] …{s}…"
                          for s, yer in r["agir"][:3])
        if y > _t.YOGUNLUK_ENGEL:
            self.engel.append(
                f"TEKRAR fazla: bin kelimede {y} ağır tekrar (üst sınır "
                f"{_t.YOGUNLUK_ENGEL}) — {len(r['agir'])} öbek aynen yineleniyor. "
                f"Bir olguyu bir kez tam anlat; ikinci geçişte ya yeni bir işlem "
                f"yap ya tek cümleyle an. Örnek: {ornek}")
        elif y > _t.YOGUNLUK_UYARI:
            self.uyari.append(
                f"Tekrar yüksek: bin kelimede {y} ağır tekrar "
                f"(hedef ≤{_t.YOGUNLUK_UYARI}). Örnek: {ornek}")
        else:
            self._ok(f"tekrar düşük: bin kelimede {y} ağır tekrar")
        if len(r["sayi"]) >= _t.SAYI_ADET_ESIK:
            en = ", ".join(f"{s} ({len(yer)} bölüm)" for s, yer in r["sayi"][:5])
            self.uyari.append(
                f"{len(r['sayi'])} sayı {_t.SAYI_BOLUM_ESIK}+ bölümde tekrarlanıyor — "
                f"her tekrarda üzerine yeni bir işlem yapılmıyorsa kes: {en}")

    def tema(self):
        """Tema defteri bakımı yapılmış mı, yazıda temaya atıf var mı.

        Defter bültenin hafızası: güncellenmezse bülten her gün sıfırdan başlar ve
        haftalarca süren anlatıları göremez.
        """
        t = self.b.get("temalar") or {}
        temalar = t.get("temalar") or []
        if not temalar:
            self.uyari.append("Tema defteri boş ya da okunamadı")
            return
        bugun = self.b.get("tarih")
        canli = [x for x in temalar if x.get("durum") in ("aktif", "izlemede")]
        bayat = [x["ad"] for x in canli if str(x.get("son_guncelleme", "")) < str(bugun)]
        if bayat:
            self.uyari.append("Tema defteri bugün güncellenmemiş: " + ", ".join(bayat))
        else:
            self._ok(f"tema defteri güncel ({len(temalar)} tema)")
        # Her canlı temanın BU koşudaki gelişmesi yazılmalı: tema bölümü bültenin en
        # çok okunan yerlerinden biri ve boş bir "gelişme" alanı okura hiçbir şey vermez.
        yazisiz = [x["ad"] for x in canli if len(_duz(x.get("gelisme", "")).split()) < 15]
        if yazisiz:
            self.engel.append("Tema gelişmesi yazılmamış (her canlı tema için bu koşuda "
                              "ne değiştiği 2-4 cümleyle yazılmalı): " + ", ".join(yazisiz))
        else:
            self._ok(f"tema gelişmeleri yazılı ({len(canli)} canlı tema)")
        metin = self._metin()
        anilan = [x["ad"] for x in temalar
                  if any(w in metin for w in _sade(x["ad"]).split() if len(w) > 4)]
        if not anilan:
            self.engel.append("Yazıda hiçbir temaya atıf yok — gündem olayları listeliyor "
                              "ama piyasayı anlatmıyor olabilir. En az bir temanın adını "
                              "kullanıp tezinin güçlenip güçlenmediğini söyle.")
        else:
            self._ok(f"temaya atıf: {', '.join(anilan[:3])}")

    def izleme(self):
        """Süreklilik: bültenin verdiği sözler takip ediliyor mu.

        `bulten/izleme.json` önceki bültenlerin "şunu izleyeceğiz" dediği konuların
        defteri. Vadesi gelmiş açık bir kayıt metinde hiç anılmamışsa bülten dizi
        olmaktan çıkar, her gün sıfırdan başlar. Kasıtlı olarak UYARI seviyesinde:
        yazarı kısıtlamak için değil, unutmasın diye.
        """
        y = BURASI / "izleme.json"
        if not y.exists():
            return
        try:
            defter = json.loads(y.read_text(encoding="utf-8"))
        except Exception:
            self.uyari.append("İzleme defteri (izleme.json) okunamadı")
            return
        self._karne(defter)
        bugun = str(self.b.get("tarih") or "")
        acik = [k for k in defter.get("kayitlar", []) if k.get("durum") == "acik"]
        vadeli = [k for k in acik if str(k.get("vade", "9999")) <= bugun]
        if not vadeli:
            if acik:
                self._ok(f"izleme defteri: {len(acik)} açık kayıt, vadesi gelen yok")
            return
        metin = self._metin()
        sessiz = []
        for k in vadeli:
            kelimeler = [w for w in _sade(k.get("konu", "")).split() if len(w) > 4]
            if not any(w in metin for w in kelimeler):
                sessiz.append(k["konu"])
        if sessiz:
            self.uyari.append("Vadesi gelen izleme kaydı metinde anılmamış (önceki "
                              "bülten söz vermişti — hesabını ver ya da kaydı kapat): "
                              + " · ".join(sessiz))
        else:
            self._ok(f"izleme defteri: vadesi gelen {len(vadeli)} kayıt metinde işlenmiş")

    def _karne(self, defter: dict):
        """Kapanan sözler NOTLANDI mı — karnenin var olma şartı.

        Defter okura açıldığı andan itibaren "kaç söz tuttu" sorusu meşrudur.
        Cevabı ancak kaydı kapatan taraf `isabet` alanını doldurursa doğar;
        doldurmazsa sayfa "isabet oranı verilmiyor" der ve defter yarım kalır.
        Bu yüzden notsuz kapanış uyarıdır — engel değil, çünkü bazı kayıtlar
        (bir sorunun cevabının bulunması gibi) tuttu/tutmadı ile ölçülmez.
        """
        kapanan = [k for k in defter.get("kayitlar", [])
                   if k.get("durum") == "kapandi"]
        if not kapanan:
            return
        notsuz = [k["konu"] for k in kapanan
                  if str(k.get("isabet", "")).lower() not in ("tuttu", "tutmadi", "kismen")]
        if notsuz:
            self.uyari.append(
                f"Kapanan {len(notsuz)} söz notlanmamış (isabet: tuttu | tutmadi | "
                "kismen) — karne bu yüzden isabet oranı veremiyor: "
                + " · ".join(notsuz[:3]) + ("…" if len(notsuz) > 3 else ""))
        else:
            self._ok(f"söz karnesi: kapanan {len(kapanan)} kaydın hepsi notlanmış")

    def kos(self) -> int:
        self.yazi(); self.veri(); self.atif(); self.tekrar()
        self.tema(); self.izleme(); self.dil(); self.tazelik()
        tur = self.b.get("tur", "gunluk")
        print(f"{'═' * 74}")
        print(f"  BÜLTEN DENETİMİ · {self.b.get('tr_tarih', self.b.get('tarih'))} "
              f"· {'haftaya bakış' if tur == 'haftalik' else 'günlük'}")
        print(f"{'═' * 74}")
        if self.ayrinti:
            for m in self.gecen:
                print(f"  ✓ {m}")
        for m in self.uyari:
            print(f"  ! {m}")
        for m in self.engel:
            print(f"  ✗ {m}")
        print(f"\n  {len(self.gecen)} ölçüt geçti · {len(self.uyari)} uyarı · "
              f"{len(self.engel)} ENGEL")
        if self.engel:
            print("\n  Bülten bu hâliyle YAYINA GİTMEMELİ. Yukarıdaki engelleri giderip "
                  "denetimi tekrar koşturun.")
        return 1 if self.engel else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("tarih", nargs="?", default=None)
    ap.add_argument("--hepsi", action="store_true")
    ap.add_argument("--ayrinti", action="store_true")
    a = ap.parse_args()

    sys.path.insert(0, str(BURASI))
    if a.hepsi:
        dosyalar = sorted(BULTEN.glob("*.json"))
    else:
        t = a.tarih or date.today().isoformat()
        dosyalar = [BULTEN / f"{t}.json"]
    kod = 0
    for y in dosyalar:
        if not y.exists():
            print(f"bülten yok: {y.name}")
            kod = 1
            continue
        b = json.loads(y.read_text(encoding="utf-8"))
        kod |= Denetim(b, a.ayrinti).kos()
        print()
    return kod


if __name__ == "__main__":
    sys.exit(main())
