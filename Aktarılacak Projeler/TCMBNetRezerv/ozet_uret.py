#!/usr/bin/env python3
"""Canlı özet (ozet.json) — gunluk.csv + haftalik_rezerv.csv'den, internetsiz.

Sayfa metnindeki oynak sayılar MDX'e gömülmez; `<Deger proje anahtar>` ile
buradan okunur. Böylece veri tazelenince sayfa metni MDX'e dokunmadan
güncellenir.

Anahtar grupları:
  g_* / h_*        eski (Stand-By 2A) tanım — MDX'te kullanılıyor, KIRILMAZ
  p_*              piyasa tanımı: seviye, kırılım, swap
  ak_*             altın fiyat etkisinden arındırılmış akım
  alt_*            altın girdileri ve tanıları
  eski_*           karşılaştırma serisi ve tanım farkı
  uyari_*          tazelik/kimlik denetiminin sonucu (net_rezerv.py yazar)
"""
import datetime as dt
import json
import os

import pandas as pd

import altin_etkisi

BASE = os.path.dirname(os.path.abspath(__file__))
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# Girdi dosyalarının kendisi bayat olabilir: net_rezerv.py çökse ya da hiç
# koşmasa bu script eski CSV'den sapasağlam bir ozet.json üretir ve sayfa
# "her şey yolunda" görünür. Dosya damgası bunu yakalar.
BAYAT_GUN = 4  # iş günü mertebesinde bir pencere (hafta sonu payı dahil)
_bayat: list[str] = []


def _oku(ad: str) -> pd.DataFrame:
    yol = os.path.join(BASE, ad)
    yas = (dt.datetime.now() - dt.datetime.fromtimestamp(os.path.getmtime(yol))).days
    if yas > BAYAT_GUN:
        _bayat.append(f"{ad} {yas} gün önce yazılmış")
    return pd.read_csv(yol, parse_dates=["Tarih"])


g = _oku("gunluk.csv")
h = _oku("haftalik_rezerv.csv")
gs, hs = g.iloc[-1], h.iloc[-1]

# --- Akım etiketinin hizası -------------------------------------------------
# Akım serisi L ile etiketlenir ve L → L+1 hareketini taşır.
#
# BU KONU BİR KEZ YANLIŞ ÇÖZÜLDÜ, ÖLÇÜMLE DÜZELTİLDİ. Bir ara "referans piyasa
# tabloları akımı BİTİŞ gününe etiketliyor" varsayılarak burada etiket bir iş
# günü ileri kaydırılıyordu. Varsayım YANLIŞMIŞ. Bağımsız bir günlük referansa
# karşı yapılan hiza taraması (net_rezerv.py --kontrol-dogrula, kayma −1/0/+1)
# net sonuç veriyor: kayma 0'da |ort| hata 0,45 mlr USD, ±1'de 2,2 — yani
# referans da akımı BAŞLANGIÇ gününe etiketliyor, tıpkı bizim gibi. Aylık
# toplamda da aynı: Haziran 2026 için etiket bazlı toplamımız 22,26, referans
# 22,3; kapanış bazlı toplam 21,3 tutuyor.
#
# Dolayısıyla sunum katmanı HAM etiketi kullanır. Hizayı varsaymak yerine
# ölçmek gerekiyordu; ölçüm --kontrol-dogrula çıktısında durur.
_gunler = list(g["Tarih"])


def _onceki_isgunu(t: pd.Timestamp) -> pd.Timestamp:
    i = _gunler.index(t)
    return _gunler[i - 1] if i > 0 else t


def _yuvarla(x, basamak=1):
    """NaN'i JSON'a 'None' değil, sayfada görülebilir '-' olarak taşır."""
    return None if pd.isna(x) else round(float(x), basamak)


# Swap hariç seri, swap çapası bulunamayan günlerde bilerek NaN kalır
# (sahte uzatma yok) — özet için son GEÇERLİ noktalar alınır.
gsh = g.dropna(subset=["swap_haric_net_rezerv_usd"]).iloc[-1]
hsh = h.dropna(subset=["swap_haric_net_rezerv_usd"]).iloc[-1]
# Swap kaleminin (II.2+II.3) en son YAYIMLANDIĞI gün
gozlem = g[g["swap_gozlem"].astype(str).str.lower().isin(["true", "1"])]

# Son 20 iş gününde mutlak değerce en büyük üç günlük hareket (mlr USD).
# Sayfadaki "öne çıkan hareketler" cümlesi bu üç çiftten okunur — elle yazılmaz.
PENCERE = 20
son = g.dropna(subset=["net_rezerv_usd"]).tail(PENCERE + 1).copy()
son["d"] = son["net_rezerv_usd"].diff()
uclar = son.dropna(subset=["d"]).reindex(
    son.dropna(subset=["d"])["d"].abs().sort_values(ascending=False).index
).head(3).sort_values("Tarih")
#
# ETİKET İLE SAAT AYRI ANAHTARLARDIR. Bu üçlünün gün yazısı bir zamanlar
# `u1_tarih` adıyla ve `GG.AA` yazımıyla duruyordu; ikisi birden kusurdu.
# 09.09.2026'da ölçüldü: `_tarih` soneki taşıyan bir alanı hem bültenin
# karanlık denetimi hem sayfadaki canlı değer bileşeni SAAT sanıyor, ama
# `11.08` biçim sözleşmesinde (GG.AA.YYYY · AA.YYYY · ISO) çözülmüyor —
# ikisi de alanı SESSİZCE atlıyordu, yani bu sekiz alan bayatlık denetiminin
# tamamen dışındaydı. Ayrıştıramayan bir denetim hep "sorun yok" der.
# Şimdi üç ayrı iş üç ayrı anahtarda: `u1_delta` değer, `u1_delta_tarih`
# onun saati (tam yazımla, çözülür), `u1_etiket` sayfada basılan kısa gün.
# Saatin yaşı pencereyle SINIRLIDIR ve bayatlık eşiğine değmez: 903 kayan
# pencerede ölçüldü, 21 işlem günü takvimde en fazla 35 gün kaplıyor
# (medyan 28) — hem karanlık denetiminin hem canlı değer bileşeninin
# öntanımlı 45 günlük eşiğinin altında, yani sahte "donmuş seri" üretmez.
uc_alanlar = {}
for i, (_, r) in enumerate(uclar.iterrows(), start=1):
    uc_alanlar[f"u{i}_etiket"] = r["Tarih"].strftime("%d.%m")
    uc_alanlar[f"u{i}_delta"] = round(float(r["d"]), 1)
    uc_alanlar[f"u{i}_delta_tarih"] = r["Tarih"].strftime("%d.%m.%Y")

# --- Akım: son geçerli gün + son beş işlem günü + içinde bulunulan ay -------
# Bütün ak_* TARİHLERİ HAM etikettir (akımın başladığı gün) — bkz. yukarıdaki
# hiza notu; bu, ölçülmüş olarak referans tabloların da kullandığı konvansiyon.
ak = g.dropna(subset=["net_doviz_alimi"])
aks = ak.iloc[-1] if len(ak) else None
ak_etiket = aks["Tarih"] if aks is not None else None
son5 = ak.tail(5)
# Aynı ayrım (bkz. yukarıdaki etiket/saat notu): `ak_g1` değer, `ak_g1_tarih`
# onun saati — TAM yazımla, çünkü sayfadaki canlı değer bileşeni bu alanı
# `ak_g1`in saati olarak okuyor; `ak_g1_etiket` sayfada basılan kısa gün.
son5_alanlar = {}
for i, (_, r) in enumerate(son5.iterrows(), start=1):
    son5_alanlar[f"ak_g{i}_etiket"] = r["Tarih"].strftime("%d.%m")
    son5_alanlar[f"ak_g{i}_tarih"] = r["Tarih"].strftime("%d.%m.%Y")
    son5_alanlar[f"ak_g{i}"] = round(float(r["net_doviz_alimi"]), 1)

# Aylık toplam ETİKET bazlıdır: etiketi o takvim ayına düşen akımların toplamı.
# Ölçüldü (Haziran 2026): etiket bazlı 22,26 — referans 22,3; kapanış bazlı
# 21,3. Yani ayın son etiketinin ertesi aya taşan hareketi AY İÇİNDE sayılır,
# çünkü referans da öyle sayıyor.
ay_toplam, ay_ad, ay_n = None, None, 0
if ak_etiket is not None:
    maske = ((ak["Tarih"].dt.year == ak_etiket.year)
             & (ak["Tarih"].dt.month == ak_etiket.month))
    ay_toplam = round(float(ak.loc[maske, "net_doviz_alimi"].sum()), 1)
    ay_ad = AYLAR[ak_etiket.month - 1]
    ay_n = int(maske.sum())

# --- Akım seviyenin kaç seans gerisinde? -------------------------------------
# Sayfada seviye grafiği 31.08'i, akım grafiği 26.08'i gösterdiğinde okur haklı
# olarak "neden" diye sorar. Etiket farkı (bir iş günü) YAPISALDIR ve cevap
# değildir: akım L → L+1'i taşır, yani son etiketin ölçtüğü KAPANIŞ zaten
# seviyenin son günüdür. Doğru ölçü bu yüzden etiketler arasında değil,
# `ak_tarih_kapanis` ile seviyenin son günü arasında kurulur — besleme
# yetişiyorsa bu fark SIFIRDIR. Sıfırdan büyükse ölçülemeyen seans var demektir
# ve tek sebebi altın fiyatının ilerlememesidir: fiyat farkı olmadan Γ, onsuz
# da net alım hesaplanamaz. Cümle kendi durumunu söyler; besleme yetiştiğinde
# kendiliğinden "aynı güne kadar geliyor" hâline döner.
_ak_kapanis = (_gunler[_gunler.index(ak_etiket) + 1]
               if ak_etiket is not None
               and _gunler.index(ak_etiket) + 1 < len(_gunler) else None)
_ak_gecikme = (len(_gunler) - 1 - _gunler.index(_ak_kapanis)
               if _ak_kapanis is not None else 0)
_fiyat_son_gercek = g.loc[g["altin_fiyat_kaynak"].astype(str) != "ffill", "Tarih"]
if _ak_gecikme <= 0:
    _ak_gecikme_cumle = ("Akım serisi seviye serisiyle aynı kapanışa kadar "
                         "geliyor; ölçülemeyen seans yok.")
else:
    _seans = "bir seans" if _ak_gecikme == 1 else f"{_ak_gecikme} seans"
    _ak_gecikme_cumle = (
        f"Akım serisi seviye serisinin {_seans} gerisinde: altın fiyatı "
        + (f"{_fiyat_son_gercek.iloc[-1]:%d.%m.%Y} tarihinden beri ilerlemedi"
           if len(_fiyat_son_gercek) else "ilerlemedi")
        + ". Fiyat farkı ölçülemeyen günde fiyat etkisi de net alım da boş "
          "bırakılır; sıfır yazılmaz.")

# Birikimli serinin ilk geçerli günü = çıpa (altin_etkisi.CIPA_TARIHI ya da
# --capa ile verilen tarih). Sabiti burada TEKRAR YAZMIYORUZ: veriden okunur.
# Birikim, çıpa gününün KENDİ akımını da içerir; yani gerçek başlangıç noktası
# çıpanın bir önceki iş gününün KAPANIŞIDIR. Etiket bunu söylesin diye
# `ak_cipa` o güne yazılır (hesap değişmiyor, etiket dürüstleşiyor).
bir = g.dropna(subset=["net_doviz_alimi_birikimli"])
cipa = (_onceki_isgunu(bir.iloc[0]["Tarih"]).strftime("%d.%m.%Y")
        if len(bir) else "-")
cipa_ham = bir.iloc[0]["Tarih"].strftime("%d.%m.%Y") if len(bir) else "-"

# --- Altın tanısı: yayımlanan altın değeri / yayımlanan ons = ima edilen
# değerleme fiyatı. Piyasa serisinden sistematik biraz düşük olması BEKLENİR
# (TCMB haftanın son iş günü Londra kotasyonuyla değerler).
ima_fiyat, ima_sapma = None, None
goz_yol = os.path.join(BASE, "irfcl_gozlem.csv")
if os.path.exists(goz_yol):
    gz = pd.read_csv(goz_yol, parse_dates=["tarih"]).set_index("tarih")
    if {"altin_M", "mn_ons"} <= set(gz.columns):
        gz = gz.dropna(subset=["altin_M", "mn_ons"])
        if len(gz):
            t = gz.index[-1]
            ima_fiyat = float(gz.iloc[-1]["altin_M"]) / float(gz.iloc[-1]["mn_ons"])
            piyasa = g.set_index("Tarih")["altin_fiyat"].reindex([t]).iloc[0]
            if pd.notna(piyasa) and piyasa:
                ima_sapma = round((ima_fiyat / float(piyasa) - 1.0) * 100, 1)
            ima_fiyat = round(ima_fiyat, 0)

# --- Denetim sonucu (net_rezerv.py yazar) ----------------------------------
# ASIL TEHLİKE DOSYANIN YOK OLMASI DEĞİL, ESKİ OLMASIDIR: net_rezerv.py çökse
# ya da hiç koşmasa, önceki koşudan kalan uyarilar.json sonsuza kadar
# "uyari_sayisi: 0 / uyari_metni: yok" yayımlar ve sayfa sağlıklı görünür.
# Üç şey birden sınanır: dosya var mı, veri tarihi ozet'inkiyle uyuşuyor mu,
# denetimin KOŞTUĞU gün bugüne yakın mı.
uyari_yol = os.path.join(BASE, "uyarilar.json")
tani: dict = {}
veri_tarihi = gs["Tarih"].date()
if not os.path.exists(uyari_yol):
    uyari_sayisi, uyari_metni = None, "denetim çıktısı bulunamadı"
else:
    with open(uyari_yol, encoding="utf-8") as f:
        _d = json.load(f)
    _u = _d.get("uyarilar", [])
    tani = _d.get("tani", {}) or {}
    _dt = pd.to_datetime(_d.get("tarih"), errors="coerce")
    _kosum = pd.to_datetime(_d.get("kosum"), errors="coerce")
    _fark = None if pd.isna(_dt) else abs((_dt.date() - veri_tarihi).days)
    _kosum_yas = (None if pd.isna(_kosum)
                  else (dt.date.today() - _kosum.date()).days)
    if _fark is None or _fark > 1:
        uyari_sayisi = None
        uyari_metni = (f"denetim çıktısı bayat ({_d.get('tarih', '?')} "
                       f"tarihli; seri {veri_tarihi:%d.%m.%Y})")
    elif _kosum_yas is not None and _kosum_yas > BAYAT_GUN:
        uyari_sayisi = None
        uyari_metni = (f"denetim {_kosum_yas} gün önce koştu "
                       f"({_kosum.date():%d.%m.%Y}); sonuç güncel olmayabilir")
    else:
        uyari_sayisi = len(_u)
        uyari_metni = "yok" if not _u else " · ".join(_u)

# Girdi CSV'leri bayatsa bu, uyarı sayısından bağımsız olarak söylenir.
if _bayat:
    uyari_metni = ("GİRDİ BAYAT: " + " · ".join(_bayat) + " · " + uyari_metni)
    uyari_sayisi = None

ozet = {
    "_tarih": gs["Tarih"].strftime("%d.%m.%Y"),
    "pencere_gun": PENCERE,
    **uc_alanlar,
    # Grafikteki gerçek IRFCL gözlem işaretçisi sayısı (günlük seri penceresinde)
    "irfcl_nokta": int(len(gozlem)),

    # --- Eski anahtarlar (MDX bunları kullanıyor; içerikleri artık PİYASA
    # tanımıdır, eski tanım eski_* altında durur) ---
    "g_tarih": gs["Tarih"].strftime("%d.%m.%Y"),
    "g_net": _yuvarla(gs["net_rezerv_usd"]),
    "g_swap_haric_tarih": gsh["Tarih"].strftime("%d.%m.%Y"),
    "g_swap_haric": _yuvarla(gsh["swap_haric_net_rezerv_usd"]),
    "g_kur": _yuvarla(gs["usdtry"], 2),
    "h_tarih": hs["Tarih"].strftime("%d.%m.%Y"),
    "h_brut": _yuvarla(hs["brut_rezerv_usd"]),
    "h_net": _yuvarla(hs["net_rezerv_usd"]),
    "h_swap_haric": _yuvarla(hsh["swap_haric_net_rezerv_usd"]),
    "swap_duzeltme": _yuvarla(gsh["swap_duzeltme_usd"]),
    "irfcl_tarih": (gozlem.iloc[-1]["Tarih"].strftime("%d.%m.%Y")
                    if len(gozlem) else "-"),

    # --- Piyasa tanımı ---
    "p_tarih": gs["Tarih"].strftime("%d.%m.%Y"),
    "p_brut": _yuvarla(gs["brut_usd"]),
    "p_altin": _yuvarla(gs["altin_usd"]),
    # Altının brüt rezerv içindeki payı (%): rezerv "kalitesi" tartışmasının tek sayısı.
    "p_altin_pay": _yuvarla(100 * gs["altin_usd"] / gs["brut_usd"]),
    "p_doviz": _yuvarla(gs["doviz_usd"]),
    "p_net_dis": _yuvarla(gs["net_dis_varlik_usd"]),
    "p_swap": _yuvarla(gs["swap_toplam_usd"]),
    "p_swap_haric": _yuvarla(gs["swap_haric_usd"]),
    "p_swap_yerli": _yuvarla(gs["swap_yerli_usd"]),
    "p_swap_yabanci": _yuvarla(gs["swap_yabanci_usd"]),
    "p_swap_capa_tarih": (pd.Timestamp(gs["swap_capa_tarih"]).strftime("%d.%m.%Y")
                          if pd.notna(gs["swap_capa_tarih"]) else "-"),
    "p_swap_capa_tipi": (str(gs["swap_capa_tipi"])
                         if pd.notna(gs["swap_capa_tipi"]) else "-"),
    # Serinin ne kadarı YÜKSEK hassasiyetli haftalık çapaya dayanıyor?
    # Son günün çapa tipi tek başına yanıltıcı: son gün haftalık çapaya
    # otururken tarihçenin büyük kısmı aylık çapaya dayanabiliyor.
    "p_swap_haftalik_oran": (
        round(float((g["swap_capa_tipi"] == "haftalık").mean()) * 100, 0)
        if "swap_capa_tipi" in g.columns else None),
    # Ölçülmüş hata bandı, çapa tipine göre (mlr USD)
    "p_swap_bant_haftalik": 0.02,
    "p_swap_bant_aylik": 0.20,
    # Çapa yenilendiğinde akıma giren revizyon (TCMB işlemi DEĞİL)
    "p_swap_revizyon": (_yuvarla(aks["swap_capa_revizyon"], 2)
                        if aks is not None and "swap_capa_revizyon" in g.columns
                        else None),

    # --- Akım (altın fiyat etkisi hariç net döviz alımı/satımı) ---
    # TARİHLER akımın BAŞLADIĞI gündür (ham etiket); değer o günün
    # kapanışından bir sonraki iş gününün kapanışına kadarki harekettir.
    "ak_tarih": (ak_etiket.strftime("%d.%m.%Y") if ak_etiket is not None
                 else "-"),
    "ak_tarih_kapanis": (_gunler[_gunler.index(ak_etiket) + 1].strftime("%d.%m.%Y")
                         if ak_etiket is not None
                         and _gunler.index(ak_etiket) + 1 < len(_gunler)
                         else "-"),
    "ak_gunluk": (_yuvarla(aks["net_doviz_alimi"]) if aks is not None else None),
    "ak_gunluk_altin_haric": (_yuvarla(aks["net_doviz_alimi_altin_haric"])
                              if aks is not None else None),
    **son5_alanlar,
    "ak_son5": (round(float(son5["net_doviz_alimi"].sum()), 1)
                if len(son5) else None),
    "ak_ay_ad": ay_ad,
    "ak_ay": ay_toplam,
    "ak_ay_gun": ay_n,
    "ak_cipa": cipa,
    "ak_cipa_etiket": cipa_ham,
    "ak_birikimli": (_yuvarla(aks["net_doviz_alimi_birikimli"])
                     if aks is not None else None),
    "ak_gecikme_isgunu": _ak_gecikme,
    "ak_gecikme_cumle": _ak_gecikme_cumle,

    # --- Belirsizlik bantları (raporlama kuralı: nokta tahmin tek başına
    # yayımlanmaz). Kaynak: altin_etkisi.py'deki adlandırılmış hata bütçesi;
    # bir kontrol setinden ÖLÇÜLMÜŞ sayılar değil, hata kalemlerinin
    # mertebelerinden türetilmiş 1σ tahminleridir.
    "ak_gunluk_bant": altin_etkisi.AKIM_BANT_GUNLUK,
    "ak_son5_bant": altin_etkisi.AKIM_BANT_HAFTALIK,
    "ak_ay_bant": altin_etkisi.AKIM_BANT_AYLIK,
    "ak_birikimli_bant": altin_etkisi.AKIM_BANT_BIRIKIMLI_6AY,
    # Arındırılmayan faiz geliri yanlılığı — İŞARETİ POZİTİF, sistematik.
    "ak_faiz_yanlilik_yillik": altin_etkisi.FAIZ_GELIRI_YILLIK_MLR,

    # --- Altın girdileri ve tanıları ---
    "alt_fiyat": _yuvarla(gs["altin_fiyat"], 0),
    "alt_fiyat_kaynak": str(gs["altin_fiyat_kaynak"]),
    "alt_ons": _yuvarla(gs["ons"], 2),
    "alt_ons_kaynak": str(gs["ons_kaynak"]),
    "alt_fiyat_etkisi_gunluk": (_yuvarla(aks["altin_fiyat_etkisi"], 2)
                                if aks is not None else None),
    "alt_fiyat_etkisi_birikimli": (_yuvarla(aks["altin_fiyat_etkisi_birikimli"])
                                   if aks is not None else None),
    "alt_ima_fiyat": ima_fiyat,
    "alt_ima_sapma": ima_sapma,
    # Miktar (ons) çapasının son tarihi. Bu günden SONRAKİ akım değerleri
    # GEÇİCİDİR: yeni bir haftalık gözlem geldiğinde Q(t), dolayısıyla Γ(t) ve
    # yayımlanmış net alım rakamı revize olur.
    "alt_son_capa": (pd.to_datetime(tani["son_ons_capa"]).strftime("%d.%m.%Y")
                     if tani.get("son_ons_capa") else "-"),
    "alt_gecici_gun": (int(g["akim_gecici"].astype(str).str.lower()
                           .isin(["true", "1"]).sum())
                       if "akim_gecici" in g.columns else None),
    # Laspeyres zincirleme sapması D_T (tanı; yayımlanan bir büyüklük değil)
    "alt_zincirleme_dt": tani.get("zincirleme_dt"),
    # Alış/satış kuru tercihinin seviyeye etkisi — sayfadaki "kapatılmamış
    # tanım farkı" cümlesi bu ÖLÇÜLEN sayıyı kullanır, elle yazılmış bir
    # mertebe tahminini değil (bkz. net_rezerv.kur_varyanti_farki).
    "p_kur_varyant_fark": tani.get("kur_varyant_fark"),

    # --- Karşılaştırma serisi ---
    "eski_net": _yuvarla(gs["eski_net_rezerv_usd"]),
    "eski_fark": _yuvarla(gs["tanim_farki"]),

    # --- Denetim ---
    "uyari_sayisi": uyari_sayisi,
    "uyari_metni": uyari_metni,
}

with open(os.path.join(BASE, "ozet.json"), "w", encoding="utf-8") as f:
    json.dump(ozet, f, ensure_ascii=False, indent=1)
print(json.dumps(ozet, ensure_ascii=False))
