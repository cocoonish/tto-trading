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
from datetime import date, datetime, timedelta

from ayar import IZLEMLER, RITIM, RITIM_ALAN, GRUPLAR, Izlem, HAT_ADI, GUNLUK_RITIM_GUN
import gozlem
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / "ortak"))
from bicim import sayi as _sayi, yuzde as _yuzde, AYLAR_TR as _AYLAR_TR  # noqa: E402  — sayı yazımı TEK yerden (ortak/bicim.py)

# Haber tonu olayının σ tabanı: denetimin anılma zorunluluğuyla AYNI eşik
# (denetim.OLAGANDISI_SIGMA, biçim 3). İki ayrı sayı bir gün ayrışırsa
# yazar sayfada görmediği bir hareketi anmaya zorlanır ya da tersi.
HABER_TONU_SIGMA = 2.0


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


# VERİ NOTU KALIBI (01.10.2026): "{ad} ({dönem}): {seviye} (önceki {x}; {±fark})".
#
# Eski kalıp önce farkı, sonra iki seviyeyi yazıyordu ve birimi üç kez
# basıyordu ("YP mevduatı 2,7 mlr USD arttı: 228,1 mlr USD → 230,8 mlr USD");
# 143 ölçüm cümlesinin 105'i böyleydi ve HİÇBİRİ verinin hangi döneme ait
# olduğunu söylemiyordu — 30.09'da okur 18.09 haftasının verisini bugünün
# değişimi sanıyordu. Bir piyasa notunda seviye önce gelir, kıyas parantezde,
# dönem adın yanında; birim bir kez yazılır (yüzde seviyenin farkı puandır).
AY_KISA = ("Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara")


def donem_yaz(t: str, hat: str = "", bugun: datetime | date | None = None,
              ceyreklik: bool | None = None) -> str:
    """Veri tarihinin okura yazımı: aylık "Ağu" · çeyreklik "2026 Ç2" ·
    günlük/haftalık "18.09". Yıl, bültenin yılından farklıysa yazılır.
    Tanınmayan yazım olduğu gibi kalır (uydurma dönem yazılmaz).
    `ceyreklik` verilmezse hattan okunur (CEYREKLIK_HAT); bir izlemin saati
    hattın çeyreklik ALANIysa çağıran söyler (bkz. `_donem`)."""
    import re as _re
    from ayar import CEYREKLIK_HAT
    yil_simdi = (bugun or datetime.now()).year
    ceyrek = (hat in CEYREKLIK_HAT) if ceyreklik is None else ceyreklik
    t = str(t or "").strip()
    m = _re.match(r"^(\d{2})\.(\d{4})$", t)
    if m:
        ay, yil = int(m.group(1)), int(m.group(2))
        if not 1 <= ay <= 12:
            return t
        if ceyrek:
            return f"{yil} Ç{(ay - 1) // 3 + 1}"
        return AY_KISA[ay - 1] + ("" if yil == yil_simdi else f" {yil}")
    m = _re.match(r"^(\d{2})\.(\d{2})\.(\d{4})$", t)
    if m:
        return f"{m.group(1)}.{m.group(2)}" + ("" if int(m.group(3)) == yil_simdi else f".{m.group(3)}")
    return _surum_yaz(t)


def _donem(iz: Izlem, t: str, bugun: datetime | date | None = None) -> str:
    """Bir izlemin dönem yazımı: çeyreklik hat YA DA çeyreklik saat alanı."""
    from ayar import CEYREKLIK_ALAN, CEYREKLIK_HAT
    return donem_yaz(t, iz.hat, bugun,
                     ceyreklik=iz.hat in CEYREKLIK_HAT or (iz.hat, iz.tarih_alani) in CEYREKLIK_ALAN)


def _ad_donem(ad: str, donem: str) -> str:
    """"Cari açık (12 aylık birikimli)" + "Tem" → "Cari açık (12 aylık birikimli, Tem)":
    iki parantez yan yana okunmaz."""
    if not donem:
        return ad
    if ad.endswith(")") and "(" in ad:
        return f"{ad[:-1]}, {donem})"
    return f"{ad} ({donem})"


def _kiyas_sayi(v: float, birim: str, ondalik: int) -> str:
    """Parantez içindeki önceki değer: yüzde işaretini taşır (sayının
    parçası), öbür birimler seviyede bir kez yazıldığı için tekrarlanmaz."""
    return _yuzde(v, ondalik) if birim == "%" else _sayi(v, ondalik)


def _fark_isaretli(fark: float, birim: str, ondalik: int) -> str:
    """İşaretli fark: yüzde seviyenin farkı PUAN, öbürleri birimsiz."""
    s = _sayi(fark, ondalik, True)
    return f"{s} puan" if birim == "%" else s


def _delta_cumlesi(iz: Izlem, eski: float, yeni: float, fark: float,
                   donem: str = "", ek: str = "") -> str:
    """Delta olayının cümlesi (sonundaki nokta hariç).

    Eksi bir dengede "azaldı" aritmetik olarak doğru, okurun diliyle TERSTİR
    (bkz. ayar.Izlem.eksi_ad): iki uç da eksiyse cümle açığın adıyla ve mutlak
    değerlerle kurulur; işaret değişirse fiil işaretin kendisini söyler.
    Sayılar Olay kaydında işaretleriyle durur — değişen yalnız okunuş.
    `ek` (bağlam ölçüsü) parantezin İÇİNE girer: tek günlük okumayı okuyan
    biri ortalamayı aynı satırda görmeli."""
    b, o = iz.birim, iz.ondalik
    son = f"; {ek}" if ek else ""
    if iz.eksi_ad and eski < 0 and yeni < 0:
        fiil = "genişledi" if yeni < eski else "daraldı"
        return (f"{_ad_donem(iz.eksi_ad, donem)}: {_sev(abs(yeni), b, o)} "
                f"(önceki {_kiyas_sayi(abs(eski), b, o)}; {_fark_yaz(abs(fark), b, o)} {fiil}{son})")
    if iz.eksi_ad and (eski < 0) != (yeni < 0):
        fiil = "artıdan eksiye döndü" if yeni < 0 else "eksiden artıya döndü"
        return (f"{_ad_donem(iz.ad, donem)}: {_sev(yeni, b, o)} "
                f"(önceki {_kiyas_sayi(eski, b, o)}; {fiil}{son})")
    return (f"{_ad_donem(iz.ad, donem)}: {_sev(yeni, b, o)} "
            f"(önceki {_kiyas_sayi(eski, b, o)}; {_fark_isaretli(fark, b, o)}{son})")


def _baglam(iz: Izlem, simdi: dict) -> str:
    """Tek günlük okumanın yanına yazılan ikinci ölçü (bkz. ayar.Izlem.baglam).

    ÖLÇÜLEMEYEN YAZILMAZ: anahtar yoksa ya da sayı değilse cümle bağlamsız
    kurulur. Uydurma bir ortalama, ortalamasız cümleden kötüdür."""
    if not iz.baglam:
        return ""
    anahtar, etiket = iz.baglam
    v = simdi.get(anahtar)
    if v is None or isinstance(v, bool) or not isinstance(v, (int, float)):
        return ""
    return f" {etiket} {_sev(float(v), iz.birim, iz.ondalik)}"


def _seviye(buyukluk: float, iz: Izlem) -> str | None:
    """Olayın seviyesi; None ise olay YOK.

    `yayim` bayrağı taşıyan anahtarda taban `dikkat`tir: takvimli bir
    istatistikte haber, hareketin büyüklüğü değil YAYIMIN KENDİSİDİR (bkz.
    ayar.Izlem.yayim). O bayrak yalnız saati İLERLEMİŞ anahtarlara ulaşır —
    süzgeç `topla`da, çünkü kıyas noktasını yalnız orası biliyor.
    """
    if iz.onemli is not None and buyukluk >= iz.onemli:
        return "onemli"
    if iz.dikkat is not None and buyukluk >= iz.dikkat:
        return "dikkat"
    return "dikkat" if iz.yayim else None


def _ayni_donem(iz: Izlem, simdi: dict | None, once: dict | None) -> bool:
    """İki görüntü aynı dönemin ölçümü mü (`Izlem.donem_alani`)? Alan tanımlı
    değilse ya da iki tarafta da yoksa evet — davranış değişmez."""
    if not iz.donem_alani or not isinstance(once, dict) or not isinstance(simdi, dict):
        return True
    a, b = simdi.get(iz.donem_alani), once.get(iz.donem_alani)
    return a is None or b is None or str(a) == str(b)


def izlem_olayi(iz: Izlem, simdi: dict, once: dict | None,
                tarih: str, onceki_tarih: str, bugun: datetime | date | None = None) -> Olay | None:
    """`bugun`: bültenin günü — dönem yazımının yılı ondan okunur (duvar saati
    yalnız yedektir; donmuş bir fikstür yıl dönünce başka bir dönem yazmasın)."""
    yeni = simdi.get(iz.anahtar)
    if yeni is None or isinstance(yeni, bool) or not isinstance(yeni, (int, float)):
        return None
    donem = _donem(iz, tarih, bugun)
    # Kıyas noktası BAŞKA bir dönemin ölçümüyse (program yılı, yılbaşından
    # birikim) fark bir hareket değildir: kıyas yokmuş gibi davranılır.
    if not _ayni_donem(iz, simdi, once):
        once = None

    # AKIM: değerin kendisi olaydır (haftalık net akım gibi); kıyas gerekmez.
    if iz.tip == "akim":
        sv = _seviye(abs(yeni), iz)
        if not sv:
            return None
        yon = "giriş" if yeni > 0 else "çıkış"
        return Olay(iz.grup, sv, iz.ad,
                    f"{_ad_donem(iz.ad, donem)}: {_sev(abs(yeni), iz.birim, iz.ondalik)} net {yon}.",
                    iz.hat, iz.anahtar, yeni, None, None, iz.birim, tarih, onceki_tarih,
                    iz.aciklama)

    # SEVİYE: eşiğin aşılması olaydır (fark değil, mutlak seviye).
    if iz.tip == "seviye":
        sv = _seviye(abs(yeni), iz)
        if not sv:
            return None
        return Olay(iz.grup, sv, iz.ad,
                    f"{_ad_donem(iz.ad, donem)}: {_sev(yeni, iz.birim, iz.ondalik)}.",
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
        return Olay(iz.grup, "onemli", iz.ad,
                    _delta_cumlesi(iz, eski, yeni, fark, donem) + ".",
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
                    f"{_ad_donem(iz.ad, donem)}: {_s(yeni, iz.ondalik)} "
                    f"(önceki {_s(eski, iz.ondalik)}; {_yuzde(oran, 2, True)}).",
                    iz.hat, iz.anahtar, yeni, eski, oran, "%", tarih, onceki_tarih,
                    iz.aciklama)

    # delta (varsayılan)
    # SIFIR FARK OLAY DEĞİLDİR. Eşikli anahtarlarda bu zaten sağlanıyordu
    # (eşik sıfırdan büyük), ama `yayim` bayrağı tabanı `dikkat`e çektiği için
    # değişmeyen bir sayı da cümleye dönüyordu — ölçüldü: "GSYH yıllık büyüme
    # 0,00 puan azaldı: %2,32 → %2,32." Yayım olayı yayımı duyurur, DEĞİŞİMİ
    # anlatır; anlatacak değişim yoksa cümle kurulmaz.
    if abs(fark) < 5e-3:
        return None
    sv = _seviye(abs(fark), iz)
    if not sv:
        return None
    # BAĞLAM CÜMLENİN İÇİNDE, DİPNOTTA DEĞİL. Tek günlük sıçramayı okuyan biri
    # ortalamayı da aynı satırda görmeli; ayrı bir yere yazılsaydı sıçramanın
    # yanıltıcılığı ancak arayan için görünür olurdu.
    ek = _baglam(iz, simdi).strip()
    return Olay(iz.grup, sv, iz.ad,
                _delta_cumlesi(iz, eski, yeni, fark, donem, ek) + ".",
                iz.hat, iz.anahtar, yeni, eski, fark, iz.birim, tarih, onceki_tarih,
                iz.aciklama)


def _yas_saat(zaman_metni: str) -> float | None:
    """Damganın yaşı (saat). Damga ve şimdi aynı cetvelde: UTC (gozlem._an)."""
    t = gozlem._an(zaman_metni)
    if t is None:
        return None
    return (_simdi() - t).total_seconds() / 3600


def _simdi() -> datetime:
    """UTC naif şimdi; sınamalar `datetime`i sarabilsin diye modülün adından okunur."""
    from datetime import timezone as _tz
    return datetime.now(_tz.utc).replace(tzinfo=None)


def _surum_yaz(v) -> str:
    """Veri sürümünün okura yazımı. ISO damga ("2026-09-28 19:31 UTC") sitenin
    tarih sözleşmesine (GG.AA.YYYY) çevrilir; saat düşer — okura giden bilgi
    hangi GÜNÜN verisi olduğudur. GG.AA.YYYY ve aylık AA.YYYY yazımı olduğu gibi
    kalır: aylık bir sürümü güne çevirmek o ayın son gününü ilan etmek olurdu."""
    import re as _re
    t = str(v or "")
    m = _re.match(r"^(\d{4})-(\d{2})-(\d{2})", t)
    return f"{m.group(3)}.{m.group(2)}.{m.group(1)}" if m else t


def yeni_veri_olaylari(hatlar: list[str], pencere_saat: float = 30.0,
                       esik: datetime | None = None) -> list[Olay]:
    """Hangi hattın verisi bir önceki sayıdan bu yana ilerledi?

    İki süzgeç (01.10.2026): (1) GÜNLÜK ritimli hat yazılmaz — her iş günü
    ilerleyen bir hattın "yeni veri" satırı haber değildir ve son 12 sayıda
    veri günlüğünün 108 satırının 95'i bu sekiz hattandı (sınır
    ayar.GUNLUK_RITIM_GUN). (2) Pencere bir önceki sayının ölçüm anıdır
    (`esik`); yoksa eski 30 saatlik pencere sürer."""
    out = []
    for hat in hatlar:
        if RITIM.get(hat, 99) < GUNLUK_RITIM_GUN:
            continue
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
        # SAAT GERÇEKTEN İLERLEMELİ. Kıyas dizge eşitsizliğiyle yapılıyordu ve
        # iki sahte bildirim ölçüldü (10.09.2026 sayısı): Büyüme hattı yalnız
        # tarih YAZIMI değiştiği için (30.06.2026 → 06.2026, iki sayısı da
        # birebir aynı) "ilerledi" diye duyuruldu; OVP hattı ise 09.09.2026 →
        # 08.09.2026 GERİLEMESİNİ "ilerledi" diye bastı. İkisi de okura yeni
        # veri geldiğini söylüyordu ve gelmemişti.
        if not gozlem._ileri_gitti(str(onc.get("v")), str(v)):
            continue
        if esik is not None:
            an = gozlem._an(ilk.get("t", ""))
            if an is not None and an <= esik:
                continue
        else:
            yas = _yas_saat(ilk.get("t", ""))
            if yas is None or yas > pencere_saat:
                continue
        # Okur dili: "veri sürümü ilerledi" iç defterin adıydı ve bir satırda
        # ISO tarih ile UTC saati basıyordu. Satır NE geldiğini söyler.
        yeni, eski = _surum_yaz(v), _surum_yaz(onc.get("v"))
        metin = (f"{HAT_ADI.get(hat, hat)}: yeni veri, {yeni}"
                 + (f" (önceki {eski})." if eski and eski != yeni else "."))
        out.append(Olay("diger", "bilgi", f"{hat}: yeni veri", metin,
                        hat=hat, tarih=v, onceki_tarih=str(onc.get("v"))))
    return out


HATIRLATMA_GUN = 7     # süren gecikme ilk gün ve sonra haftada bir yazılır


def _gecikme(hat: str, sg: tuple[str, str] | None, azami_gun: int,
             ad: str = "", esik: datetime | None = None,
             simdi_an: datetime | None = None) -> Olay | None:
    """Bir saatin donukluk süresi ritmi aşıyorsa olay üret.

    SIKLIK (01.10.2026): satır her sabah yeniden basılıyordu ve yalnız sayacı
    değişiyordu ("14 gündür · 15 gündür · 16 gündür"). Aynı gecikme İLK
    sayıda ve sonra HAFTADA BİR yazılır: eşik aşıldığı an (`ilk` + azami+1
    gün) ile bir önceki sayının ölçüm anı (`esik`) arasında bir hatırlatma
    sınırı geçildiyse. `esik` yoksa her gün yazılır (eski davranış)."""
    if not sg:
        return None
    surum, ilk = sg
    yas = _yas_saat(ilk)
    if yas is None:
        return None
    gun = int(yas // 24)
    if gun <= azami_gun:
        return None
    if esik is not None:
        ilk_an = gozlem._an(ilk)
        simdi = simdi_an or _simdi()
        if ilk_an is not None:
            asim = ilk_an + timedelta(days=azami_gun + 1)
            hafta = timedelta(days=HATIRLATMA_GUN)
            n_simdi = (simdi - asim) // hafta
            n_esik = (esik - asim) // hafta if esik >= asim else -1
            if n_simdi <= n_esik:
                return None
    hat_adi = HAT_ADI.get(hat, hat)      # okura slug değil ad
    etiket = f"{hat_adi} — {ad}" if ad else hat_adi
    tarih = _surum_yaz(surum)
    return Olay("diger", "dikkat", f"{etiket}: veri gecikti",
                f"{etiket}: son yayım {tarih}; o günden beri yeni yayım yok "
                f"({gun} gün; olağan aralık en çok {azami_gun} gün).",
                hat=hat, tarih=surum,
                aciklama=f"Bu verinin panodaki sayıları {tarih} tarihlidir.")


def gecikme_olaylari(esik: datetime | None = None) -> list[Olay]:
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
        o = _gecikme(hat, gozlem.son_gorulme(hat), azami_gun, esik=esik)
        if o:
            out.append(o)
    for (hat, alan), (azami_gun, ad) in RITIM_ALAN.items():
        o = _gecikme(hat, gozlem.alan_son_gorulme(hat, alan), azami_gun, ad, esik=esik)
        if o:
            out.append(o)
    return out


def haber_endeksi_olaylari(esik_sigma: float = 0.0, esik: datetime | None = None,
                           bugun: datetime | date | None = None) -> list[Olay]:
    """FX haber-duyarlılık endeksinde günün en olağandışı hareketleri.

    EŞİK DEĞİL SIRALAMA. Sabit bir eşik burada işlemiyor: gerçek tarihçeyle
    ölçüldüğünde snapshot'tan snapshot'a 15 varlığın 9-12'si kategori
    değiştiriyor ve |Δ| medyanı bant genişliği kadar. "Kategori değişti" diyen
    bir kural her gün on sahte olay üretirdi. Hat bu yüzden en olağandışı
    ÜÇ hareketi kendisi sıralayıp `hareket` alanında veriyor; burada yalnız
    cümleye çevriliyor.

    SIRALAMANIN ÜSTÜNE σ TABANI (01.10.2026, `esik_sigma`): sıralama her gün
    üç hareket verir ve arşivdeki 72 σ'lı cümlenin 62'si 2σ'nın altındaydı
    (medyan 1,3σ) — 1σ'lık bir ton oynaması her sabah "olağandışı" diye
    basılıyordu. Ölçüm katmanı tabanı ölçer; σ'sı ölçülemeyen hareket tabanı
    geçmiş sayılmaz. Kategori etiketi ("Alıcı", "Satıcı") cümleye girmez:
    bülten satırında tavsiye diliyle okunuyordu, σ hareketi zaten söylüyor.
    Fark yuvarlanmış uçlardan hesaplanır: görünen iki sayının farkı görünen
    farka eşit olmalı (87 cümlenin 20'sinde değildi).
    """
    d = gozlem.anlik("fx-haber-endeksi")
    if not d:
        return []
    hareketler = d.get("hareket") or []
    if not hareketler:
        return []
    # ZAMAN KAPISI (01.10.2026, inceleme): endeks hafta sonu ve bazı günler
    # ilerlemiyor; ilerlemediği günde aynı ≥2σ hareket ikinci, üçüncü sayıda
    # yeniden "olağandışı" basılıyordu (11–14.09'da aynı altın hareketi üç
    # sayıda). Hareket ancak endeksin saati bir önceki sayıdan sonra
    # ilerlediyse bugünün olayıdır.
    if esik is not None and not gozlem.bugun_yeni("fx-haber-endeksi", d, "hareket", "_tarih", esik):
        return []
    kiyas = d.get("hareket_kiyas_tarih") or ""
    tarih = str(d.get("_tarih", ""))[:10]
    olaylar = []
    for m in hareketler:
        z = m.get("z")
        if esik_sigma > 0 and not (isinstance(z, (int, float)) and abs(z) >= esik_sigma):
            continue
        ad = str(m.get("ad") or "")
        ad = ad[:1].upper() + ad[1:]
        once_r, deger_r = round(float(m["onceki"]), 2), round(float(m["deger"]), 2)
        parca = [f"önceki {_s(once_r, 2, True)}" + (f" ({_surum_yaz(kiyas)})" if kiyas else ""),
                 _s(deger_r - once_r, 2, True)]
        if z is not None:
            parca.append(f"{_s(z, 1, True)}σ")
        if m.get("makale"):
            parca.append(f"{m['makale']} makale")
        olaylar.append(Olay(
            grup="haber", seviye="dikkat",
            baslik=f"Haber tonu — {ad}",
            metin=(f"Haber tonu, {ad} ({donem_yaz(_surum_yaz(tarih), '', bugun)}): "
                   f"{_s(deger_r, 2, True)} ({'; '.join(parca)})."),
            hat="fx-haber-endeksi", anahtar=m["kod"],
            deger=m["deger"], onceki=m["onceki"], fark=m["fark"],
            tarih=tarih, onceki_tarih=kiyas,
        ))
    return olaylar


def _sayi_mi(v) -> bool:
    return v is not None and not isinstance(v, bool) and isinstance(v, (int, float))


def hafta_tablosu(esik: datetime | None, bugun: datetime | date | None = None) -> list[dict]:
    """HAFTAYA BAKIŞIN "bu hafta güncellenen öbür seriler" tablosu — EŞİKSİZ.

    Kapsam: izlemler + ayar.HAFTALIK_KALEMLER. Satır, anahtarın saati bir önceki
    HAFTALIK sayının ölçüm anına (`esik`) göre İLERLEDİYSE yazılır (olaylarla
    aynı kural: gozlem.bugun_yeni) ve kıyas o anda güncel olan görüntüdür, yani
    fark HAFTANIN farkıdır. Eşiği aşıp olay cümlesine dönüşen izlem tabloya
    GİRMEZ: o sayfada "Bu hafta gelen veriler" bölümünde zaten cümle olarak
    duruyor ve aynı sayı iki yerde basılmaz.

    Ölçülemeyen boş bırakılır: kıyas noktası bulunamayan satır önceki değeri
    "—" ile taşır, fark yazılmaz; esik yoksa (ilk haftalık sayı) tablo YOK —
    "haftanın farkı" o zaman tanımsızdır.
    """
    if esik is None:
        return []
    from ayar import HAFTALIK_KALEMLER
    kalemler = [(iz, True) for iz in IZLEMLER] + [(iz, False) for iz in HAFTALIK_KALEMLER]
    satirlar: dict[str, list[dict]] = {}
    anlik: dict[str, dict | None] = {}
    for iz, izlem_mi in kalemler:
        if iz.grup in ("haber", "diger"):
            continue
        if iz.hat not in anlik:
            anlik[iz.hat] = gozlem.anlik(iz.hat)
        simdi = anlik[iz.hat]
        if not simdi or not _sayi_mi(simdi.get(iz.anahtar)):
            continue
        v = gozlem.anahtar_tarihi(simdi, iz.anahtar, iz.tarih_alani)
        if not gozlem.bugun_yeni(iz.hat, simdi, iz.anahtar, iz.tarih_alani, esik):
            continue
        onc = gozlem.esikteki(iz.hat, esik, iz.anahtar)
        if onc is None or gozlem.anahtar_tarihi(onc["d"], iz.anahtar, iz.tarih_alani) == v:
            onc = gozlem.onceki_surum_anahtar(iz.hat, iz.anahtar, iz.tarih_alani, v)
        once_d = onc.get("d") if onc else None
        onceki_v = gozlem.anahtar_tarihi(once_d, iz.anahtar, iz.tarih_alani) if once_d else ""
        if izlem_mi:
            o = izlem_olayi(iz, simdi, once_d, v, onceki_v, bugun)
            if o is not None and o.seviye in ("onemli", "dikkat"):
                continue
        yeni = float(simdi[iz.anahtar])
        eski = once_d.get(iz.anahtar) if isinstance(once_d, dict) else None
        eski = float(eski) if _sayi_mi(eski) else None
        if not _ayni_donem(iz, simdi, once_d):          # başka dönemin ölçümü
            eski, onceki_v = None, ""
        b, od = iz.birim, iz.ondalik
        fark = ""
        if eski is not None and iz.tip not in ("akim", "seviye"):
            if iz.tip == "yuzde":
                fark = _yuzde((yeni / eski - 1) * 100, 2, True) if eski else ""
            else:
                fark = _fark_isaretli(yeni - eski, b, od)
        satirlar.setdefault(iz.grup, []).append({
            "hat": iz.hat, "hat_ad": HAT_ADI.get(iz.hat, ""), "anahtar": iz.anahtar,
            "ad": iz.ad, "donem": _donem(iz, v, bugun),
            "onceki_donem": _donem(iz, onceki_v, bugun) if onceki_v else "",
            "deger": _sev(yeni, b, od),
            "onceki": _sev(eski, b, od) if eski is not None else "—",
            "fark": fark,
        })
    return [{"id": gid, "baslik": gbaslik, "satirlar": satirlar[gid]}
            for gid, gbaslik in GRUPLAR if satirlar.get(gid)]


def topla(esik: datetime | None = None, haftalik: bool = False,
          bugun: datetime | date | None = None) -> list[Olay]:
    """Bültenin olayları. `esik`: bir önceki sayının ölçüm anı (UTC naif) —
    yalnız ondan SONRA ilk kez görülen sürüm bugünün olayıdır (bkz.
    gozlem.bugun_yeni). Haber tonu yalnız |z| ≥ 2 hareketi olaya çevirir."""
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
            # AYNI VERİ SÜRÜMÜ İKİ KEZ DUYURULMAZ.
            #
            # 10.09.2026: kıyas noktası "saati bugünkünden farklı olan en son
            # görüntü" oldu ve bir ölçüm "saati önceki SÜRÜME göre ilerlediyse"
            # duyuruldu. 01.10.2026'da ölçüldü: bu soru bir kez ilerlemiş sürüm
            # için her gün evettir — 143 ölçüm cümlesinin 106'sı (%74,1) daha
            # önce aynı veri tarihiyle basılmıştı, "Lokanta / ev yemeği oranı"
            # 17 sayı üst üste çıktı. Eksik olan zaman sorusuydu: sürüm ayrıca
            # bir önceki SAYININ ölçüm anından sonra ilk kez görülmüş olmalı.
            # Değer saat ilerlemeden değişmişse bu bir REVİZYONdur ve denetimin
            # kendi ölçütü onu adıyla listeler.
            if not gozlem.bugun_yeni(hat, simdi, iz.anahtar, iz.tarih_alani, esik):
                continue
            # KIYAS NOKTASI bir önceki sayının anındaki görüntüdür: okur "bir
            # önceki sayıdan bu yana ne değişti"yi okur (haftalık sayıda haftanın
            # farkı). Esik yoksa ya da o anda anahtar yoksa eski kıyas noktası.
            onc = gozlem.esikteki(hat, esik, iz.anahtar) if esik is not None else None
            if onc is None or gozlem.anahtar_tarihi(onc["d"], iz.anahtar, iz.tarih_alani) == v:
                onc = gozlem.onceki_surum_anahtar(hat, iz.anahtar, iz.tarih_alani, v)
            once_d = onc.get("d") if onc else None
            onceki_v = (gozlem.anahtar_tarihi(once_d, iz.anahtar, iz.tarih_alani)
                        if once_d else "")
            o = izlem_olayi(iz, simdi, once_d, v, onceki_v, bugun)
            if o:
                olaylar.append(o)
    olaylar += yeni_veri_olaylari(list(RITIM), esik=esik)
    olaylar += gecikme_olaylari(esik)
    olaylar += haber_endeksi_olaylari(HABER_TONU_SIGMA, esik, bugun)
    sira = {g: i for i, (g, _) in enumerate(GRUPLAR)}
    onem = {"onemli": 0, "dikkat": 1, "bilgi": 2}
    olaylar.sort(key=lambda o: (onem.get(o.seviye, 3), sira.get(o.grup, 99), o.baslik))
    return olaylar


if __name__ == "__main__":
    for o in topla():
        im = {"onemli": "!!", "dikkat": " ·", "bilgi": " i"}.get(o.seviye, "  ")
        print(f" {im} [{o.grup:10s}] {o.metin}")
