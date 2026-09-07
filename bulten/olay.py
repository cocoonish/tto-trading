#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bülten — olay motoru: eşikleri uygular, cümleyi kurar.

Girdi: hatların güncel ozet.json'ları + gecmis/ deposu.
Çıktı: olay listesi. Her olay bir cümle, bir seviye (önemli/dikkat) ve
kanıtı (eski değer, yeni değer, fark) taşır. Yorum YOK — yorum ayrı katman.

Tasarım kararı: olayın metni burada, veriyle BİRLİKTE üretilir. Yorum katmanı
bu cümleleri yeniden yazabilir ama SAYIYI üretemez; sayı hep buradan gelir.
Böylece bültende uydurma rakam bulunamaz.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from ayar import IZLEMLER, RITIM, RITIM_ALAN, GRUPLAR, Izlem, HAT_ADI
import gozlem
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "ortak"))
from bicim import sayi as _sayi, yuzde as _yuzde  # noqa: E402  — sayı yazımı TEK yerden (ortak/bicim.py)


@dataclass
class Olay:
    grup: str
    seviye: str            # "onemli" | "dikkat" | "bilgi"
    baslik: str
    metin: str
    hat: str = ""
    anahtar: str = ""
    deger: float | None = None
    onceki: float | None = None
    fark: float | None = None
    birim: str = ""
    tarih: str = ""
    onceki_tarih: str = ""
    aciklama: str = ""


def _s(x: float, ondalik: int = 1, isaret: bool = False) -> str:
    """Türkçe sayı biçimi (ortak/bicim.sayi): binlik nokta, ondalık virgül, eksi U+2212."""
    return _sayi(x, ondalik, isaret)


def _yon(fark: float, artis: str = "arttı", azalis: str = "azaldı") -> str:
    return artis if fark > 0 else azalis


# BİR SEVİYENİN BİRİMİ İLE FARKININ BİRİMİ AYNI DEĞİLDİR.
#
# Ölçüldü (07.09.2026): olay cümleleri "Tüketici kredisi büyümesi 12,8 %
# azaldı: 43,0 → 30,2 %." diye çıkıyordu ve iki ayrı kusur taşıyordu.
#   (1) BİÇİM: birim sayının ARKASINA ekleniyordu; sözleşme (ortak/bicim)
#       yüzdeyi ÖNE alır. Derlenmiş sayfada 40 yerde "N %" yazıyordu.
#   (2) ÖLÇÜ: %43,0'dan %30,2'ye inen bir oranın farkı 12,8 PUANDIR, %12,8
#       değil. İkisi farklı büyüklükler — %12,8'lik bir düşüş 43,0'ı 37,5'e
#       indirirdi. Yani cümle yalnız çirkin değil, YANLIŞTI.
#
# `ayar.IZLEMLER`in 56 kaydından 30'u `tip="delta"` + `birim="%"`: devalüasyon
# hızı, TLREF, AOFM, TÜFE ailesi, kredi büyümeleri, DİBS getirileri, bütçe
# oranları. Hepsi bu cümleden geçiyordu.
FARK_BIRIMI = {"%": "puan"}


def _sev(v: float, birim: str, ondalik: int) -> str:
    """SEVİYE: birimiyle, sözleşmenin yazımıyla ("%37,00" · "48,03 mlr USD")."""
    if birim == "%":
        return _yuzde(v, ondalik)
    return f"{_sayi(v, ondalik)} {birim}".strip()


def _fark_yaz(v: float, birim: str, ondalik: int) -> str:
    """FARK: yüzde cinsinden bir seviyenin farkı PUANDIR, yüzde değil."""
    b = FARK_BIRIMI.get(birim, birim)
    return f"{_sayi(v, ondalik)} {b}".strip()


def _seviye(buyukluk: float, iz: Izlem) -> str | None:
    if iz.onemli is not None and buyukluk >= iz.onemli:
        return "onemli"
    if iz.dikkat is not None and buyukluk >= iz.dikkat:
        return "dikkat"
    return None


def izlem_olayi(iz: Izlem, simdi: dict, once: dict | None,
                tarih: str, onceki_tarih: str) -> Olay | None:
    yeni = simdi.get(iz.anahtar)
    if yeni is None or isinstance(yeni, bool) or not isinstance(yeni, (int, float)):
        return None

    # AKIM: değerin kendisi olaydır (haftalık net akım gibi); kıyas gerekmez.
    if iz.tip == "akim":
        sv = _seviye(abs(yeni), iz)
        if not sv:
            return None
        yon = "giriş" if yeni > 0 else "çıkış"
        return Olay(iz.grup, sv, iz.ad,
                    f"{iz.ad}: {_sev(abs(yeni), iz.birim, iz.ondalik)} net {yon}.",
                    iz.hat, iz.anahtar, yeni, None, None, iz.birim, tarih, onceki_tarih,
                    iz.aciklama)

    # SEVİYE: eşiğin aşılması olaydır (fark değil, mutlak seviye).
    if iz.tip == "seviye":
        sv = _seviye(abs(yeni), iz)
        if not sv:
            return None
        return Olay(iz.grup, sv, iz.ad,
                    f"{iz.ad}: {_sev(yeni, iz.birim, iz.ondalik)}.",
                    iz.hat, iz.anahtar, yeni, None, None, iz.birim, tarih, onceki_tarih,
                    iz.aciklama)

    if once is None:
        return None
    eski = once.get(iz.anahtar)
    if eski is None or isinstance(eski, bool) or not isinstance(eski, (int, float)):
        return None
    fark = yeni - eski

    if iz.tip == "degisim":
        if abs(fark) < 1e-12:
            return None
        isaret = "+" if fark > 0 else "−"
        return Olay(iz.grup, "onemli", iz.ad,
                    f"{iz.ad} değişti: {_sev(eski, iz.birim, iz.ondalik)} → "
                    f"{_sev(yeni, iz.birim, iz.ondalik)} "
                    f"({isaret}{_fark_yaz(abs(fark), iz.birim, iz.ondalik)}).",
                    iz.hat, iz.anahtar, yeni, eski, fark, iz.birim, tarih, onceki_tarih,
                    iz.aciklama)

    if iz.tip == "yuzde":
        if eski == 0:
            return None
        oran = (yeni / eski - 1) * 100
        sv = _seviye(abs(oran), iz)
        if not sv:
            return None
        return Olay(iz.grup, sv, iz.ad,
                    f"{iz.ad} %{_s(abs(oran), 2)} {_yon(oran, 'yükseldi', 'geriledi')}: "
                    f"{_s(eski, iz.ondalik)} → {_s(yeni, iz.ondalik)}.",
                    iz.hat, iz.anahtar, yeni, eski, oran, "%", tarih, onceki_tarih,
                    iz.aciklama)

    # delta (varsayılan)
    sv = _seviye(abs(fark), iz)
    if not sv:
        return None
    return Olay(iz.grup, sv, iz.ad,
                f"{iz.ad} {_fark_yaz(abs(fark), iz.birim, iz.ondalik)} {_yon(fark)}: "
                f"{_sev(eski, iz.birim, iz.ondalik)} → {_sev(yeni, iz.birim, iz.ondalik)}.",
                iz.hat, iz.anahtar, yeni, eski, fark, iz.birim, tarih, onceki_tarih,
                iz.aciklama)


def _yas_saat(zaman_metni: str) -> float | None:
    try:
        t = datetime.fromisoformat(zaman_metni.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None
    return (datetime.now() - t).total_seconds() / 3600


def yeni_veri_olaylari(hatlar: list[str], pencere_saat: float = 30.0) -> list[Olay]:
    """Hangi hattın verisi son koşuda ilerledi? Bülten 'bugün ne yayımlandı' der."""
    out = []
    for hat in hatlar:
        simdi = gozlem.anlik(hat)
        if not simdi:
            continue
        v = gozlem._tarih_of(simdi)
        onc = gozlem.onceki_surum(hat, v)
        if onc is None:
            continue
        ilk = next((k for k in gozlem.gecmis_oku(hat) if k.get("v") == v), None)
        if not ilk:
            continue
        yas = _yas_saat(ilk.get("t", ""))
        if yas is not None and yas <= pencere_saat:
            out.append(Olay("diger", "bilgi", f"{hat}: yeni veri",
                            f"{HAT_ADI.get(hat, hat)}: veri sürümü ilerledi ({onc.get('v')} → {v}).",
                            hat=hat, tarih=v, onceki_tarih=str(onc.get("v"))))
    return out


def _gecikme(hat: str, sg: tuple[str, str] | None, azami_gun: int,
             ad: str = "") -> Olay | None:
    """Bir saatin donukluk süresi ritmi aşıyorsa olay üret."""
    if not sg:
        return None
    surum, ilk = sg
    yas = _yas_saat(ilk)
    if yas is None:
        return None
    gun = int(yas // 24)
    if gun <= azami_gun:
        return None
    hat_adi = HAT_ADI.get(hat, hat)      # okura slug değil ad
    etiket = f"{hat_adi} — {ad}" if ad else hat_adi
    return Olay("diger", "dikkat", f"{etiket}: veri gecikti",
                f"{etiket}: son veri sürümü {surum}; {gun} gündür yenilenmedi "
                f"(beklenen ritim ≤ {azami_gun} gün).",
                hat=hat, tarih=surum,
                aciklama="Kaynak yayımlamamış olabilir; sayfadaki sayılar bu "
                         "sürümde donmuş demektir.")


def gecikme_olaylari() -> list[Olay]:
    """Bir hattın verisi beklenen ritmin ötesinde sessizse söyle.

    'Sessiz bayatlama' denetiminin bültendeki karşılığı: kaynak yayımlamadıysa
    da bunu BİLMEK gerekir, çünkü sayfadaki sayılar o sürümde donmuştur.

    İki kademe var, çünkü bir ozet.json birden fazla saat taşır: hattın ana
    saati (`_tarih`) ve içindeki farklı ritimli alanlar. Yalnız ana saate
    bakılırsa, günlük bileşen tıkırdarken haftalık bileşenin donması sessizce
    geçer — bu denetimin tam da yakalaması gereken durum.
    """
    out = []
    for hat, azami_gun in RITIM.items():
        o = _gecikme(hat, gozlem.son_gorulme(hat), azami_gun)
        if o:
            out.append(o)
    for (hat, alan), (azami_gun, ad) in RITIM_ALAN.items():
        o = _gecikme(hat, gozlem.alan_son_gorulme(hat, alan), azami_gun, ad)
        if o:
            out.append(o)
    return out


def haber_endeksi_olaylari() -> list[Olay]:
    """FX haber-duyarlılık endeksinde günün en olağandışı hareketleri.

    EŞİK DEĞİL SIRALAMA. Sabit bir eşik burada işlemiyor: gerçek tarihçeyle
    ölçüldüğünde snapshot'tan snapshot'a 15 varlığın 9-12'si kategori
    değiştiriyor ve |Δ| medyanı bant genişliği kadar. "Kategori değişti" diyen
    bir kural her gün on sahte olay üretirdi. Hat bu yüzden en olağandışı
    ÜÇ hareketi kendisi sıralayıp `hareket` alanında veriyor; burada yalnız
    cümleye çevriliyor.

    Kıyas noktası cümlede AÇIKÇA yazar: snapshot'lar arası mesafe sabit değil
    (hat günlük koşmaya yeni geçti, tarihçedeki eski aralıklar haftalarca).
    "Endeks döndü" demek, ne kadar sürede döndüğünü söylemeden yanıltır.
    """
    d = gozlem.anlik("fx-haber-endeksi")
    if not d:
        return []
    hareketler = d.get("hareket") or []
    if not hareketler:
        return []
    gun = d.get("hareket_gun")
    kiyas = d.get("hareket_kiyas_tarih") or "önceki okuma"
    ne_kadar = (f"{gun} günde" if isinstance(gun, int) and gun > 0 else "önceki okumaya göre")
    olaylar = []
    for m in hareketler:
        z = m.get("z")
        olcu = (f"{_s(z, 1, True)} standart sapma" if z is not None
                else "hattın oynaklık tarihçesi henüz σ için yetmiyor")
        kat = ""
        if m.get("kat") and m.get("onceki_kat") and m["kat"] != m["onceki_kat"]:
            kat = f", {m['onceki_kat']} → {m['kat']}"
        olaylar.append(Olay(
            grup="haber", seviye="dikkat",
            baslik=f"Haber tonu — {m['ad']}",
            metin=(f"{m['ad']} haber-duyarlılık endeksi {ne_kadar} "
                   f"{_s(m['onceki'], 2, True)}'den {_s(m['deger'], 2, True)}'ye geçti "
                   f"({_s(m['fark'], 2, True)}{kat}; {olcu}; {m.get('makale', '?')} makale, "
                   f"kıyas {kiyas}). Sebebini haber akışından bul."),
            hat="fx-haber-endeksi", anahtar=m["kod"],
            deger=m["deger"], onceki=m["onceki"], fark=m["fark"],
            tarih=str(d.get("_tarih", ""))[:10], onceki_tarih=kiyas,
        ))
    elenen = d.get("hareket_elenen") or 0
    if elenen:
        olaylar.append(Olay(
            grup="haber", seviye="bilgi",
            baslik="Haber tonu — kapsamı zayıf varlıklar",
            metin=(f"{elenen} varlık az makaleli olduğu için olağandışılık "
                   "sıralamasına girmedi: o endekslerde tek bir haber okumayı "
                   "savurabilir, hareketleri gürültüden ayrılamaz."),
            hat="fx-haber-endeksi",
        ))
    return olaylar


def topla() -> list[Olay]:
    olaylar: list[Olay] = []
    for hat in sorted({iz.hat for iz in IZLEMLER}):
        simdi = gozlem.anlik(hat)
        if not simdi:
            continue
        # Kıyas noktası İZLEM BAŞINA aranır: aynı dosyadaki günlük ve haftalık
        # seriler farklı saatlerde ilerler; hepsini hattın ana saatiyle
        # kıyaslamak haftalık serinin hareketini bir günde siler.
        for iz in [i for i in IZLEMLER if i.hat == hat]:
            v = gozlem.anahtar_tarihi(simdi, iz.anahtar, iz.tarih_alani)
            onc = gozlem.onceki_surum_anahtar(hat, iz.anahtar, iz.tarih_alani, v)
            once_d = onc.get("d") if onc else None
            onceki_v = (gozlem.anahtar_tarihi(once_d, iz.anahtar, iz.tarih_alani)
                        if once_d else "")
            o = izlem_olayi(iz, simdi, once_d, v, onceki_v)
            if o:
                olaylar.append(o)
    olaylar += yeni_veri_olaylari(list(RITIM))
    olaylar += gecikme_olaylari()
    olaylar += haber_endeksi_olaylari()
    sira = {g: i for i, (g, _) in enumerate(GRUPLAR)}
    onem = {"onemli": 0, "dikkat": 1, "bilgi": 2}
    olaylar.sort(key=lambda o: (onem.get(o.seviye, 3), sira.get(o.grup, 99), o.baslik))
    return olaylar


if __name__ == "__main__":
    for o in topla():
        im = {"onemli": "!!", "dikkat": " ·", "bilgi": " i"}.get(o.seviye, "  ")
        print(f" {im} [{o.grup:10s}] {o.metin}")
