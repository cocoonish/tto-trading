#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Günlük bülten — İZLEM ve EŞİK ayarları.

Bültenin "kayda değer" tanımı burada durur. Tek dosya, düz veri: eşikleri
değiştirmek için kod okumak gerekmez.

Her izlem bir hattın ozet.json'undaki BİR anahtarı izler. Karşılaştırma bir
önceki ANLIK GÖRÜNTÜYE göre yapılır (bulten/gecmis/<hat>.jsonl); yani "dün
neredeydi, bugün nerede".

Eşik iki kademeli:
  dikkat  → bültenin "not düşülenler" bölümüne girer
  onemli  → bültenin başındaki "öne çıkanlar" bölümüne girer

Eşikler bilinçli olarak GENİŞ tutulmuştur: her gün on madde üreten bir bülten
okunmaz. Bir eşik ayda birkaç kez tetikleniyorsa doğru yerdedir.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Izlem:
    hat: str                     # hangi hattın ozet.json'u (site slug'ı)
    anahtar: str
    ad: str                      # bültende görünecek Türkçe ad
    birim: str = ""
    ondalik: int = 1
    tip: str = "delta"           # delta | yuzde | akim | seviye | degisim
    dikkat: float | None = None
    onemli: float | None = None
    # seviye tipinde: eşik aşıldığında olay (mutlak değere bakılır)
    yon_iyi: str = ""            # "artis" | "azalis" | "" (nötr)
    aciklama: str = ""           # neden izliyoruz — bültende dipnot
    grup: str = ""               # bültende hangi başlık altında toplanacak
    # Bu anahtarın KENDİ veri tarihini tutan alan. Boş bırakılırsa önce
    # `<anahtar>_tarih` geleneği, o da yoksa hattın ana saati (`_tarih`)
    # kullanılır. Yalnız gelenek dışı kalan anahtarlarda doldurulur:
    # tcmb-net-rezerv'in haftalık serisi h_net/h_brut'tur ama saati h_tarih'tir.
    tarih_alani: str = ""
    # BAĞLAM ANAHTARI — tek günlük okumanın yanına yazılan ikinci ölçü.
    #
    # Bazı göstergeler tanımı gereği tek bir günün gürültüsünü büyütür:
    # yıllıklandırma bir günlük fiyat farkını 365'e ölçekler, yani kotasyondaki
    # küçük bir kayma (valör farkı, tatil, TCMB'nin ertesi gün kurunu bir gün
    # önce ilan etmesi) orana büyük yansır. 08.09.2026 bülteninde bir aylık
    # devalüasyon hızı tek günde 4,5 puan "arttı"; ölçüldü, %0,5'lik sahte bir
    # kotasyon sıçraması o oranı 7,8 puan oynatıyor, aynı ölçünün beş günlük
    # ortalamasını yalnız 1,6 puan (4,9× söndürme).
    #
    # Bağlam AYNI ÖLÇÜNÜN penceresi olmak zorunda: bir aylık hızın yanına bir
    # HAFTALIK oranın ortalamasını yazmak iki farklı pencereyi aynı cümlede
    # kıyaslamak olurdu. (hattaki anahtar, okura yazılacak etiket)
    baglam: tuple[str, str] | None = None


# Hatların OKURA görünen adları. Olay cümleleri ("hazine-ihrac: veri gecikti")
# ve sayfadaki kaynak notları eskiden slug basıyordu — okurun elinde slug yok.
HAT_ADI = {
    "usdtry-deval": "USD/TRY devalüasyon hızı",
    "tcmb-net-rezerv": "TCMB net rezerv",
    "yabanci-pozisyon": "Yabancı pozisyonu",
    "fonlama-likidite": "TCMB fonlama ve likidite",
    "kredi-parasal": "Kredi ve parasal büyüklükler",
    "enflasyon": "Enflasyon panosu",
    "try-reer": "TL reel efektif kur",
    "yiyecek-hizmetleri-marj": "Yiyecek hizmetleri marjı",
    "hazine-ihrac": "Hazine ihraç",
    "fx-haber-endeksi": "FX haber endeksi",
    "dibs-verim-egrisi": "DİBS verim eğrisi",
    "odemeler-dengesi": "Ödemeler dengesi",
    "butce-borc": "Bütçe ve borç stoku",
    "tl-tasima": "TL taşıma defteri",
    "tufex-basabas": "TÜFEX ve başabaş enflasyon",
    "makroihtiyati": "Makroihtiyatinin izi",
    "reel-sektor-fx": "Reel sektörün döviz pozisyonu",
    "buyume": "Büyüme",
    "el-nino": "El Niño ve gıda enflasyonu",
    "ovp": "Orta Vadeli Program ve ima edilen kur",
    "yp-mevduat": "Yurt içi yerleşiklerin YP mevduatı",
}

# Hatların yayım ritmi — "veri gecikti" uyarısı için. Gün cinsinden azami sessizlik.
RITIM = {
    "usdtry-deval": 4,          # günlük (hafta sonu boşluğu payı)
    # Hattın ANA saati `_tarih`tir; bu hatta o saat GÜNLÜK analitik bilançodur
    # (her iş günü 14:30, bir gün gecikmeli). Haftalık resmî seri ayrı bir
    # saattir ve RITIM_ALAN'da denetlenir — eskiden buradaki 10 gün haftalık
    # ritim için yazılmıştı ama günlük saatle ölçüldüğü için hiç tetiklenmiyordu.
    "tcmb-net-rezerv": 6,       # günlük analitik bilanço (fonlama ile aynı kaynak)
    "yabanci-pozisyon": 11,     # haftalık (Cuma, 1 hafta gecikmeli)
    "fonlama-likidite": 6,      # günlük/haftalık karışık
    "kredi-parasal": 11,        # haftalık
    "enflasyon": 40,            # aylık (ayın 3'ü)
    "try-reer": 40,             # aylık
    "yiyecek-hizmetleri-marj": 45,
    # İhale ritmi düzensiz: aynı strateji ayında ihaleler arası boşluk üç
    # haftayı bulur (18.08 → 14.09). 12 günlük eşik 03–08.09 arası altı sayıda
    # sahte "veri gecikti" bastı (09.09.2026'da ölçüldü).
    "hazine-ihrac": 25,
    "fx-haber-endeksi": 5,
    "dibs-verim-egrisi": 6,     # iş günü (eğri günlük kurulur)
    "odemeler-dengesi": 45,     # aylık, 6-8 hafta gecikmeli
    "butce-borc": 45,           # aylık (bütçe ayın 15'i)
    # Türev hatlar: kendi kaynaklarına gitmezler, başka hatların depoya yazdığı
    # CSV'lerden hesaplanırlar ve her koşuda çalışırlar. Ritimleri besleyen
    # hattınkidir — TÜFEX ve taşıma DİBS'ten (iş günü), makroihtiyati krediden
    # (haftalık, Perşembe, bir hafta gecikmeli).
    # Eklenmelerinin sebebi kayda değer: dördü de 26.08'de siteye girdi ve
    # bültenin ölçüm katmanı onları HİÇ görmüyordu — sayfa üretiyor ama
    # tazeliğini kimse denetlemiyordu.
    "tl-tasima": 6,
    "tufex-basabas": 6,
    "makroihtiyati": 11,
    # Aylık, TCMB ~2 ay gecikmeli yayımlar; 75 gün bir yayım kaymasını taşır.
    # (Hat ilk çekimini yaptı ve özet gerçek veri taşıyor; önceki "yer tutucu"
    # gerekçesi düştü.)
    "reel-sektor-fx": 75,
    # Ana saati canlı bacakların EN YENİSİ, yani kur: her iş günü ilerler.
    # Aylık enflasyon bacağı ayrı bir saattir ve RITIM_ALAN'da denetlenir —
    # buraya aylık bir tolerans yazmak kurun donmasını görünmez yapardı.
    "ovp": 6,
    # AŞAĞIDAKİ ÜÇÜ 07.09.2026'DA EKLENDİ ve eklenme sebebi kayda değer: kütükte
    # (guncelle.HATLAR) ve sitede ozet.json'u olan 21 hattın 18'i buradaydı.
    # Eksik üçü, RITIM'i dolaşan SEKİZ çağrı yerinin hepsinden birden düşüyordu
    # (uret · olay×2 · denetim×2 · bulten · gozlem · duman): panoları üretiliyor
    # ama bayatlıklarını soran kimse yok. En görünür sonucu, üç aylık GSYH
    # yayımının bültende HİÇ duyurulamamasıydı (olay.yeni_veri_olaylari listeyi
    # buradan alıyor). Bugün üçü de tazeydi — kapatılan şey bugünkü bir hasar
    # değil, GELECEKTEKİ körlük.
    #
    # DEĞERLER en_gec'ten KOPYALANMADI ve kopyalanamaz: RITIM "bu sürüme
    # geçileli kaç gün", Tetik.en_gec "son KOŞUMDAN kaç gün" ölçer ve depo
    # ikisini bilerek ayırmış (fx 5↔9, reel-sektor-fx 75↔30). Mekanik kopya
    # reelfx eşiğini 30'a düşürür ve ~2 ay gecikmeli aylık bir seride her ay
    # yanlış "veri gecikti" olayı üretirdi.
    "yp-mevduat": 11,           # kredi ile AYNI yayım (haftalık para-banka, Perşembe)
    "buyume": 100,              # üç aylık GSYH, TÜİK ~60 gün gecikmeli
    "el-nino": 35,              # aylık ONI + aylık TÜFE
}

# Bir hattın ozet.json'u birden fazla SAAT taşıyabilir: aynı dosyada günlük bir
# seri ile haftalık bir seri yan yana durur. RITIM yalnız ana saati (`_tarih`)
# denetler; ana saat her iş günü ilerlediği için içindeki haftalık serinin
# donması ona görünmez. Buradaki kayıtlar o alanları doğrudan izler.
#   (hat, tarih alanı) → (azami sessizlik günü, bültende görünecek ad)
# Ölçü "veri tarihinin yaşı" değil, "bu sürüme geçileli kaç gün oldu"dur:
# haftalık seri Perşembe yayımlanıp ertesi koşuda görülür, yani normalde 7 gün
# donuk kalır; 10 gün üç günlük gecikme payı bırakır.
RITIM_ALAN = {
    ("tcmb-net-rezerv", "h_tarih"): (10, "haftalık resmî seri"),
    # Programın enflasyon karşılaştırması kardeş hattın ölçümünden besleniyor
    # ve AYLIK ritimde: kur her gün ilerlerken bu bacak sessizce donabilir ve
    # ana saate bakan denetim onu hiç görmez.
    ("ovp", "tufe_tarih"): (50, "gerçekleşen enflasyon bacağı"),
    # AŞAĞIDAKİLER 07.09.2026'DA EKLENDİ. Kütük (guncelle.Hat.tarih_anahtarlari)
    # 22 ikincil saat İLAN EDİYOR; burada yalnız BİRİNİN eşiği yazılıydı, yani
    # ilan edilmiş yirmi bir saatin donması hiçbir yerde sorulmuyordu. Bir hattın
    # ANA saati her iş günü ilerlerken içindeki haftalık ya da aylık bacağın
    # donması, ana saate bakan denetime tanımı gereği görünmez.
    # Kapsam artık ELLE tutulmuyor: `bulten/duman.py` kütükteki her ilanın burada
    # bir karşılığı olmasını ENGEL olarak sınıyor. Elle yazılan tek şey EŞİK ve
    # gerekçesi — o, kaynağın ölçülmüş yayım ritmidir, mekanik türetilemez.
    # Bugünkü ağaca karşı 22 alanın 22'si de eşiğin altında: bu kayıtlar bugün
    # tek bir uyarı üretmiyor, gelecekteki körlüğü kapatıyor.
    # Günlük bacak HAFTADA BİR yenilenir: hat yalnız Perşembe yayımıyla koşar
    # (tarif: haftalık/aylık para ve banka), günlük aile o koşunun gününde
    # kalır. 4 günlük eşik her hafta Çarşamba–Perşembe sahte "gecikti"
    # üretiyordu (09.09.2026'da ölçüldü); ölçü haftalık döngüye göre.
    ("kredi-parasal", "gun_tarih"): (11, "günlük kur/bilanço bacağı (haftalık koşuda yenilenir)"),
    ("kredi-parasal", "ay_tarih"): (45, "aylık KKM ve banka türü bacağı"),
    ("fonlama-likidite", "hafta_kisa"): (12, "haftalık fonlama bacağı"),
    # Eşik hattın KENDİ ölçümünden: Fonlama/metrik.py zorunlu karşılık tabanının
    # 13 gün gecikmeli geldiğini yazıyor ve 21 günü aşarsa ima edilen oranı hiç
    # hesaplamıyor. İkinci bir sayı uydurmak yerine o sayı buraya alındı.
    ("fonlama-likidite", "zk_taban_tarih"): (21, "zorunlu karşılık tabanı"),
    ("butce-borc", "_tarih2"): (12, "haftalık DİBS/eurobond bacağı"),
    # GSYH çeyreği ~91 günde bir ilerler (buyume RITIM 100 ile aynı ölçü);
    # 170 kaçan çeyreği ~80 gün geç gösterirdi.
    ("butce-borc", "_tarih3"): (100, "çeyreklik bacak"),
    # Akım bacağı (gelir/gider) ana saatten 3–5 gün ÖNCE ilerler (Bütçe Denge
    # Tablosu ~15–17'si, Borç Stoku ~20'si); eşik ana saatle aynı, 45.
    ("butce-borc", "akim_tarih"): (45, "aylık bütçe akım bacağı (gelir/gider)"),
    # _tarih2 üç aylık GSYH bacağıdır (cari denge/GSYH oranı), aylık değil:
    # ~91 günde bir ilerler; 75 her çeyrek 2–3 hafta sahte "gecikti" üretirdi.
    ("odemeler-dengesi", "_tarih2"): (100, "çeyreklik GSYH bacağı"),
    # Günlük kur bacağı; hat aylık tetikle koşar, bacak koşu gününde kalır.
    ("odemeler-dengesi", "_tarih4"): (45, "günlük kur bacağı (aylık koşuda yenilenir)"),
    ("odemeler-dengesi", "_tarih3"): (12, "haftalık dış borç ödeme takvimi"),
    ("dibs-verim-egrisi", "_tarih2"): (45, "aylık bacak"),
    ("enflasyon", "faiz_gun"): (40, "günlük faiz bacağı"),
    ("yp-mevduat", "stok_tarih"): (11, "haftalık stok bacağı"),
    ("yp-mevduat", "akim_tarih"): (11, "haftalık akım bacağı"),
    ("yp-mevduat", "dol_tarih"): (11, "haftalık dolarizasyon bacağı"),
    ("tcmb-net-rezerv", "ak_tarih"): (6, "günlük akım bacağı"),
    ("tl-tasima", "endeks_tarih"): (6, "TLREF endeks bacağı"),
    ("tl-tasima", "nakit_tahvil_tarih"): (6, "nakit/tahvil bacağı"),
    ("tufex-basabas", "basabas_2y_tarih"): (6, "2 yıllık başabaş bacağı"),
    # Üç aylık BKEA ÇEYREĞİN BAŞIYLA damgalanıyor (2. çeyrek anketi 01.04 tarihini
    # taşır ve temmuz ortasında yayımlanır); meşru gecikme tek başına ~135 gün.
    ("makroihtiyati", "bkea_std_isletme_tarih"): (200, "üç aylık BKEA bacağı"),
    # Rezerv bacağı tcmb hattının haftalık dosyasından gelir ama BU hat 30
    # günde bir koşuyor (takvimsiz): 12 günlük eşik her ayın 16'sından ay
    # sonuna kadar yapısal "gecikti" basardı. Ölçü hattın koşu ritmine göre;
    # hat haftalık tetiğe bağlanınca eşik 12'ye döner.
    ("reel-sektor-fx", "acik_rezerv_tarih"): (37, "haftalık rezerv bacağı (aylık koşuda yenilenir)"),
    ("ovp", "kur_tarih"): (6, "günlük kur bacağı"),
}

# `karanlik` denetiminin hat başına eşiği (gün). Anahtarın KENDİ veri tarihi,
# hattın `_tarih`inden bu kadar günden fazla geride kalırsa seri "donmuş"
# sayılır. Öntanımlı denetim.KARANLIK_GUN (45) meşru hiçbir ritme değmez;
# buraya yalnız o öntanımlının yanlış konuştuğu hatlar yazılır.
KARANLIK_GUN: dict[str, int] = {
    # Aylık seriler aylık dosyada yan yana: aylık bir kalem, yeni ay yayımlanana
    # kadar bir öncekinin tarihinde durur. 45 gün burada dar kalır.
    "odemeler-dengesi": 75,
    # Bütçe: çeyreklik GSYH bacağı (`_tarih3`) aylık ana saatin ~123 gün
    # gerisine düşebiliyor (Ç3 GSYH 1 Aralık'ta gelene dek `_tarih` 10.2026,
    # `_tarih3` 06.2026); 75 her çeyrek ~40 gün sahte "donmuş seri" üretirdi.
    "butce-borc": 140,
    # Banka Kredileri Eğilim Anketi ÜÇ AYLIK ve değeri çeyreğin BAŞI ile
    # damgalanıyor: 2. çeyrek anketi 01.04 tarihiyle durur ve ancak Temmuz
    # ortasında yayımlanır. Meşru gecikme tek başına ~135 güne çıkar.
    "makroihtiyati": 200,
    # Aynı özette günlük kur ile AYLIK enflasyon bacağı yan yana duruyor;
    # aylık bir kalem yeni ay yayımlanana kadar bir öncekinin tarihinde durur.
    "ovp": 75,
}

# Tarih taşıyan ama TAZELİK saati OLMAYAN anahtarlar.
#
# Bir `<anahtar>_tarih` alanı iki bambaşka soruya cevap verebilir:
#   "bu değer ne zamana ait?"        → tazelik saati; donması KUSURDUR
#   "bu uç nokta ne zaman yaşandı?"  → tarihsel işaret; donması NORMALDİR
# Veride ikisini ayıran yapısal bir iz YOK — `kum_zirve_tarih` ile
# `basabas_3y_tarih` birebir aynı biçimde duruyor. Ayrım ADLANDIRMADAN okunuyor:
# aşağıdaki sözcükler bir uç noktayı, çapayı ya da başlangıcı gösterir.
# (Sınır işaretleri şart: "basabas" içindeki "bas" eşleşmemeli.)
#
# Kapsanan gerçek anahtarlar: kum_zirve, zk_enbuyuk_adim, zk_taban_birim_maks,
# dol_cipa, kimlik_maks, en_derin_cokus, endeks_bas.
# Karanlık olduğu BİLİNEN ve SEBEBİ YAZILMIŞ seriler.
#
# Neden gerekiyor: her gün tekrarlanan bir uyarı uyarı olmaktan çıkar, gürültü
# olur ve yanındaki YENİ uyarıyı da görünmez kılar. Bir karanlık seri bir kez
# araştırılıp sebebi sayfaya yazıldığında buraya taşınır; denetim onu artık
# uyarı olarak değil, sebebiyle birlikte GEÇEN ölçüt olarak yazar. Listede
# olmayan her karanlık seri uyarıdır — yani susturmak için önce anlamak gerekir.
#   (hat, anahtar) → sebep (nerede açıklandığıyla birlikte)
KARANLIK_BILINEN: dict[tuple[str, str], str] = {
    ("tufex-basabas", "basabas_3y"):
        "TÜFEX itfa boşluğu: Haz-2029'dan May-2031'e atlıyor, 3y noktası "
        "12.06.2026'da boşluğa düştü — projeler/tufex-basabas sayfasında yazılı",
    ("tufex-basabas", "prim_3y"): "aynı boşluk (başabaştan türüyor)",
    ("tufex-basabas", "reel_3y"): "aynı boşluk (başabaştan türüyor)",
}

TARIHSEL_ISARET = re.compile(
    r"(^|_)(maks|min|zirve|dip|cipa|bas|baslangic|en_derin|enbuyuk|encok|"
    r"cokus|rekor|referans)(_|$)")

# Bültende grup başlıkları ve sırası
GRUPLAR = [
    ("kur", "Kur ve rezervler"),
    ("faiz", "Faiz, fonlama ve likidite"),
    ("enflasyon", "Enflasyon"),
    ("kredi", "Kredi ve para"),
    ("borclanma", "Hazine borçlanması ve borç stoku"),
    ("dis", "Dış denge ve finansman"),
    ("akim", "Yabancı akımı"),
    ("haber", "Haber tonu"),
    ("diger", "Diğer"),
]

IZLEMLER: list[Izlem] = [
    # ─────────────────────────────── kur ve rezervler
    Izlem("usdtry-deval", "kur", "USD/TRY", "", 2, "yuzde", 0.6, 1.2, "",
          "Günlük yüzde değişim; %1,2 üstü TL varlıklarda gün içi fiyatlamayı değiştirir.", "kur"),
    Izlem("usdtry-deval", "d1a", "1 aylık yıllıklandırılmış devalüasyon hızı", "%", 1, "delta", 4, 8,
          "azalis", "Kurun seviyesi değil HIZI; TCMB'nin patika yönetimini bu gösterir. "
          "Tek günlük okuma valör farkına duyarlıdır; son beş iş gününün ortalaması "
          "yanında verilir.", "kur",
          baglam=("d1a_ort", "son beş iş günü ortalaması")),
    Izlem("usdtry-deval", "d3a", "3 aylık yıllıklandırılmış devalüasyon hızı", "%", 1, "delta", 3, 6,
          "azalis", "Daha yavaş ama daha güvenilir rejim göstergesi.", "kur",
          baglam=("d3a_ort", "son beş iş günü ortalaması")),
    Izlem("tcmb-net-rezerv", "h_net", "Net rezerv (haftalık, resmî)", "mlr USD", 1, "delta", 1.5, 3.0,
          "artis", "Analitik bilançodan piyasa tanımıyla; haftalık yayımlanır.", "kur", "h_tarih"),
    Izlem("tcmb-net-rezerv", "h_swap_haric", "Swap hariç net rezerv", "mlr USD", 1, "delta", 1.5, 3.0,
          "artis", "Rezervin borçlanılmamış kısmı — kalite ölçüsü.", "kur", "h_tarih"),
    Izlem("tcmb-net-rezerv", "h_brut", "Brüt rezerv", "mlr USD", 1, "delta", 2.5, 5.0,
          "artis", "", "kur", "h_tarih"),
    Izlem("tcmb-net-rezerv", "g_net", "Net rezerv (günlük tahmin)", "mlr USD", 1, "delta", 2.0, 4.0,
          "artis", "Günlük analitik bilanço vekili; haftalık resmî seriden önce hareketi gösterir.",
          "kur", "g_tarih"),
    Izlem("tcmb-net-rezerv", "p_altin", "Altın rezervi", "mlr USD", 1, "delta", 2.5, 5.0,
          "", "", "kur", "p_tarih"),
    Izlem("try-reer", "redk", "TÜFE bazlı reel efektif kur", "endeks", 1, "delta", 2.0, 4.0, "",
          "Aylık; 100 üstü TL'nin uzun dönem ortalamasına göre değerli olduğunu gösterir.", "kur"),
    # Orta Vadeli Program bir kur patikası yayımlamıyor; iki milli gelir
    # satırının oranı onu ele veriyor. İzlenen üç büyüklük de gerçekleşen kur
    # her gün ilerledikçe DEĞİŞİR — programın kendi sayıları sabit dursa bile.
    Izlem("ovp", "yil_sonu_ustel", "Programın ima ettiği yıl sonu kuru", "TL/$", 2,
          "delta", 0.5, 1.0, "",
          "Yıl ortalaması programın ima ettiğine eşitlenirse kurun yıl sonunda "
          "geleceği seviye; gerçekleşen ortalama kaydıkça oynar.", "kur"),
    Izlem("ovp", "sapma_bu_yil", "Yıl içi ortalamanın programdan sapması", "%", 1,
          "delta", 0.5, 1.0, "",
          "Eksi değer, gerçekleşen ortalamanın programın ima ettiğinin altında "
          "kaldığını söyler.", "kur"),
    Izlem("ovp", "gereken_ort", "Kalan günlerin tutturması gereken ortalama", "TL/$", 2,
          "delta", 0.5, 1.5, "",
          "Programın yıl ortalaması tutsun diye kalan işlem günlerinin ortalaması; "
          "yıl sonuna yaklaştıkça tek bir günün etkisi büyür.", "kur"),

    # ─────────────────────────────── faiz, fonlama, likidite
    Izlem("fonlama-likidite", "politika", "Politika faizi", "%", 2, "degisim", None, None, "",
          "Her değişim PPK kararıdır; koşulsuz olay.", "faiz"),
    Izlem("fonlama-likidite", "koridor_ust", "Koridor üst bandı (GLP)", "%", 2, "degisim", None, None, "", "", "faiz"),
    Izlem("fonlama-likidite", "koridor_alt", "Koridor alt bandı", "%", 2, "degisim", None, None, "", "", "faiz"),
    Izlem("fonlama-likidite", "tlref", "TLREF", "%", 2, "delta", 0.25, 0.75, "",
          "Gecelik gerçekleşen; politika faizinden sapması sıkılık göstergesi.", "faiz"),
    Izlem("fonlama-likidite", "aofm", "Ağırlıklı ortalama fonlama maliyeti", "%", 2, "delta", 0.25, 0.75, "", "", "faiz"),
    Izlem("fonlama-likidite", "spread_tlref_politika", "TLREF − politika farkı", "puan", 2, "seviye", 1.0, 2.0, "",
          "Farkın büyümesi TCMB'nin fiilî duruşunun ilan edilenden ayrıştığını söyler.", "faiz"),
    Izlem("fonlama-likidite", "net_fonlama_mlr", "TCMB net fonlaması", "mlr TL", 0, "delta", 150, 350, "",
          "Sistemin TCMB'ye net borcu; işaret değiştirmesi rejim değişimidir.", "faiz"),
    Izlem("fonlama-likidite", "swap_net_mlr_tl", "Net swap stoku", "mlr TL", 0, "delta", 100, 250, "", "", "faiz"),
    Izlem("fonlama-likidite", "zk_oran", "Ortalama zorunlu karşılık oranı", "%", 2, "delta", 0.3, 0.8, "",
          "Makroihtiyati sıkılaştırmanın sessiz kolu.", "faiz"),

    # ─────────────────────────────── enflasyon
    Izlem("enflasyon", "tufe_aylik", "Aylık TÜFE", "%", 2, "delta", 0.5, 1.0, "azalis",
          "Ayın 3'ünde gelir; bültende sürpriz olarak da ayrıca işlenir.", "enflasyon"),
    Izlem("enflasyon", "tufe_12a", "Yıllık TÜFE", "%", 2, "delta", 1.0, 2.5, "azalis", "", "enflasyon"),
    Izlem("enflasyon", "tufe_3a", "TÜFE 3 aylık yıllıklandırılmış (mevsimsellikten arındırılmış)", "%", 1,
          "delta", 3.0, 6.0, "azalis", "Panonun merkezî momentum ölçüsü.", "enflasyon"),
    Izlem("enflasyon", "tufe_3a_ham", "TÜFE 3 aylık yıllıklandırılmış (ham)", "%", 1, "delta", 3.0, 6.0,
          "azalis", "", "enflasyon"),
    Izlem("enflasyon", "b_12a", "Çekirdek B (yıllık)", "%", 2, "delta", 1.0, 2.5, "azalis", "", "enflasyon"),
    Izlem("enflasyon", "c_12a", "Çekirdek C (yıllık)", "%", 2, "delta", 1.0, 2.5, "azalis", "", "enflasyon"),
    Izlem("enflasyon", "hizmet_12a", "Hizmet enflasyonu (yıllık)", "%", 1, "delta", 1.0, 2.5, "azalis",
          "Ataleti en yüksek kalem; dezenflasyonun gerçek sınavı.", "enflasyon"),

    # ─────────────────────────────── kredi ve para
    Izlem("kredi-parasal", "g_ar_13y", "Kur etkisinden arındırılmış kredi büyümesi (13 haftalık yıllıklandırılmış)",
          "%", 1, "delta", 5.0, 10.0, "", "Makroihtiyati sınırların bağladığı asıl büyüklük.", "kredi"),
    Izlem("kredi-parasal", "g_tuketici_13y", "Tüketici kredisi büyümesi (13h yıllıklandırılmış)", "%", 1,
          "delta", 6.0, 12.0, "", "", "kredi"),
    Izlem("kredi-parasal", "g_ticari_13y", "Ticari kredi büyümesi (13h yıllıklandırılmış)", "%", 1,
          "delta", 6.0, 12.0, "", "", "kredi"),
    Izlem("kredi-parasal", "npl", "Takipteki alacak oranı", "%", 2, "delta", 0.15, 0.35, "azalis",
          "Yavaş hareket eder; sıçraması kredi döngüsünün dönüşüdür.", "kredi"),
    Izlem("kredi-parasal", "kredi_mevduat", "Kredi/mevduat oranı", "%", 1, "delta", 2.0, 4.0, "", "", "kredi"),

    # ─────────────────────────────── Hazine borçlanması
    Izlem("hazine-ihrac", "maliyet_son", "Son ihale ortalama bileşik maliyeti", "%", 2, "delta", 1.0, 2.5,
          "azalis", "Hazinenin fiilî borçlanma maliyeti.", "borclanma"),
    Izlem("hazine-ihrac", "b2c_son", "Son ihale teklif/karşılama oranı", "kat", 2, "delta", 0.4, 0.8, "artis",
          "Talebin gücü; 1,5'in altı zayıf ihale demektir.", "borclanma"),
    Izlem("hazine-ihrac", "n_ihale", "Toplam ihale sayısı", "adet", 0, "delta", 0.5, None, "",
          "Artması yeni ihale sonucu geldiği anlamına gelir.", "borclanma"),
    Izlem("hazine-ihrac", "wam_son", "Yeni ihraçların ağırlıklı ortalama vadesi", "yıl", 2, "delta", 0.5, 1.0,
          "artis", "", "borclanma"),

    # ─────────────────────────────── yabancı akımı
    Izlem("yabanci-pozisyon", "toplam_hafta", "Yabancı haftalık net akım (toplam)", "mn USD", 0, "akim",
          500, 1000, "artis", "Hisse + DİBS; stok değil AKIM (fiyat/kur etkisinden arındırılmış).", "akim"),
    Izlem("yabanci-pozisyon", "dibs_hafta", "Yabancı haftalık net akım (DİBS)", "mn USD", 0, "akim",
          400, 800, "artis", "", "akim"),
    Izlem("yabanci-pozisyon", "hisse_hafta", "Yabancı haftalık net akım (hisse)", "mn USD", 0, "akim",
          400, 800, "artis", "", "akim"),

    # ─────────────────────────────── DİBS verim eğrisi
    Izlem("dibs-verim-egrisi", "gosterge_ytm", "Gösterge tahvil bileşik getirisi", "%", 2,
          "delta", 0.75, 1.75, "azalis",
          "En likit DİBS'in vadeye kadar getirisi; TL faizinin manşet fiyatı.", "faiz"),
    Izlem("dibs-verim-egrisi", "spot_2y", "DİBS 2 yıllık spot getiri", "%", 2, "delta",
          0.75, 1.75, "azalis", "", "faiz"),
    Izlem("dibs-verim-egrisi", "spot_9y", "DİBS 9 yıllık spot getiri", "%", 2, "delta",
          0.75, 1.75, "azalis", "", "faiz"),
    Izlem("dibs-verim-egrisi", "egim_2y9y", "DİBS 2y−9y eğimi", "puan", 2, "delta",
          1.0, 2.5, "", "Negatif = ters eğri; işaret değiştirmesi rejim değişimidir.", "faiz"),
    Izlem("dibs-verim-egrisi", "carry_2y_tlref", "2 yıllık taşıma (TLREF, bileşik)", "puan", 2,
          "delta", 1.5, 3.0, "artis",
          "Tahvili gecelikten fonlamanın maliyeti; negatifse pozisyon taşımak pahalıdır.", "faiz"),
    Izlem("dibs-verim-egrisi", "basabas_2y", "2 yıllık başabaş enflasyon", "%", 2, "delta",
          1.0, 2.5, "azalis",
          "Nominal ile enflasyona endeksli tahvilin ima ettiği enflasyon.", "enflasyon"),
    Izlem("dibs-verim-egrisi", "reel_egri_2y", "2 yıllık reel getiri", "%", 2, "delta",
          1.0, 2.0, "", "", "faiz"),

    # ─────────────────────────────── ödemeler dengesi ve dış finansman
    Izlem("odemeler-dengesi", "cari12_mia", "Cari denge (12 aylık birikimli)", "mlr USD", 1,
          "delta", 3.0, 7.0, "artis", "", "dis"),
    Izlem("odemeler-dengesi", "cekirdek12_mia", "Çekirdek cari denge (altın ve enerji hariç)",
          "mlr USD", 1, "delta", 3.0, 7.0, "artis",
          "Dış dengenin yapısal kısmı; enerji ve altın dalgası dışarıda.", "dis"),
    Izlem("odemeler-dengesi", "nhn12_mia", "Net hata noksan (12 aylık)", "mlr USD", 1,
          "delta", 4.0, 9.0, "", "Büyümesi kaynağı belirsiz döviz girişine işaret eder.", "dis"),
    Izlem("odemeler-dengesi", "cari_gsyh", "Cari denge / GSYH", "%", 2, "delta", 0.5, 1.0,
          "artis", "", "dis"),

    # ─────────────────────────────── bütçe ve borç stoku
    Izlem("butce-borc", "denge_gsyh", "Bütçe dengesi / GSYH (12 aylık)", "%", 2, "delta",
          0.4, 0.8, "artis", "", "borclanma"),
    Izlem("butce-borc", "fdd_gsyh", "Faiz dışı denge / GSYH (12 aylık)", "%", 2, "delta",
          0.4, 0.8, "artis", "", "borclanma"),
    Izlem("butce-borc", "faiz_vergi", "Faiz harcaması / vergi geliri", "%", 1, "delta",
          1.5, 3.0, "azalis",
          "Borç servisinin vergi tabanını ne kadar yediğinin ölçüsü.", "borclanma"),
    Izlem("butce-borc", "doviz_pay", "Borç stokunda döviz payı", "%", 1, "delta", 1.5, 3.0,
          "azalis", "Kur şokuna duyarlılığın ölçüsü.", "borclanma"),
    Izlem("butce-borc", "yurt_disi_pay", "Borç stokunda yurt dışı yerleşik payı", "%", 1,
          "delta", 1.5, 3.0, "", "", "borclanma"),
]


# ─────────────────────────────── haber kaynakları
# İki tür kaynak var ve bültende AYRI durur:
#   kurum  → TCMB/Resmî Gazete duyuruları. Bunlar haber değil OLAY'dır; hepsi gösterilir.
#   haber  → RSS akışları. Gürültülü; alaka süzgecinden geçer ve sayısı sınırlanır.
#
# TCMB duyuru listesi RSS vermiyor ama liste sayfası düz HTTP ile okunabiliyor
# (haber.tcmb_duyurulari). Faiz kararı, makroihtiyati çerçeve, TL likidite yönetimi,
# swap düzenlemesi — hepsi oradan çıkar; bu kullanıcı için en değerli tek kaynak.
RESMI_GAZETE_URL = "https://www.resmigazete.gov.tr/"
# Kurum ve konu süzgeci: Resmî Gazete günde onlarca kalem yayımlar; bültene yalnız
# finans/makro ilgisi olanlar girer.
RG_ILGILI = (r"merkez bankas|tcmb|bddk|spk|hazine|maliye|vergi|kur\b|d[öo]viz|kredi|"
             r"banka|sermaye piyasas|zorunlu kar[şs][ıi]l|faiz|tahvil|bono|kambiyo|"
             r"finansal kiralama|sigortac|emeklilik|ihracat|ithalat|g[üu]mr[üu]k|te[şs]vik")

# ABD Hazinesi basın duyuruları — borç yönetimi operasyonlarının BİRİNCİL kaynağı.
# Bu kaynak eksikken sistem 19 Ağustos 2026'daki geri alım (buyback) büyüklüğü
# artırımını tamamen kaçırdı; oysa o duyuru haftanın dolar ve uzun vadeli faiz
# hareketinin ana sebebiydi. Merkez bankası odaklı aramalar bunu YAKALAYAMAZ:
# geri alım, refinansman ve ihale takvimi para politikası değil BORÇ YÖNETİMİDİR.
ABD_HAZINE_URL = "https://home.treasury.gov/news-data/press-releases/search/{yil}.json"
# Piyasayı ilgilendiren duyuru başlıkları (geri kalan: yaptırım, vergi, atama…).
ABD_HAZINE_ILGILI = (r"buyback|refunding|auction|debt|borrowing|financing|bill|note|bond|"
                     r"yield|treasury international capital|tic data|cash balance|"
                     r"quarterly|issuance|maturit|liquidity")

TCMB_DUYURU_URL = "https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB+TR/Main+Menu/Duyurular/Basin/{yil}"

HABER_KAYNAKLARI = [
    # bolge: "tr" | "global" | "karisik"    alan: "makro" | "politika" | "piyasa" | "karisik"
    # Kaynağın alanı VARSAYILANDIR; başlık/özetteki kalıplar bunu ezebilir.
    #
    # Sıra bilinçli: önce DOĞRUDAN YAYINCI akışları. Onların açıklama alanı gerçek
    # bir özet taşıyor ve bağlantıları doğrudan habere gidiyor; Google News
    # bağlantıları ise yayıncıya JS ile yönlendirdiği için ne özet ne de gövde
    # okunabiliyor. Google aramaları yalnız yayıncı akışlarının kapsamadığı
    # konularda, boşluk doldurucu olarak kalır.

    # ── Türkiye
    {"ad": "Anadolu Ajansı — Ekonomi", "bolge": "tr", "alan": "makro",
     "url": "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"},
    {"ad": "Anadolu Ajansı — Politika", "bolge": "tr", "alan": "politika",
     "url": "https://www.aa.com.tr/tr/rss/default?cat=politika"},
    {"ad": "Bloomberg HT", "bolge": "tr", "alan": "piyasa",
     "url": "https://www.bloomberght.com/rss"},
    {"ad": "Dünya Gazetesi", "bolge": "tr", "alan": "makro",
     "url": "https://www.dunya.com/rss?dunya"},
    {"ad": "Ekonomim", "bolge": "tr", "alan": "makro",
     "url": "https://www.ekonomim.com/rss"},
    {"ad": "Hürriyet Ekonomi", "bolge": "tr", "alan": "makro",
     "url": "https://www.hurriyet.com.tr/rss/ekonomi"},
    {"ad": "Investing", "bolge": "tr", "alan": "piyasa",
     "url": "https://tr.investing.com/rss/news_285.rss"},

    # ── Global
    {"ad": "BBC Business", "bolge": "global", "alan": "makro",
     "url": "https://feeds.bbci.co.uk/news/business/rss.xml"},
    {"ad": "BBC World", "bolge": "global", "alan": "politika",
     "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"ad": "The Guardian — Business", "bolge": "global", "alan": "makro",
     "url": "https://www.theguardian.com/uk/business/rss"},
    {"ad": "Al Jazeera", "bolge": "global", "alan": "politika",
     "url": "https://www.aljazeera.com/xml/rss/all.xml"},
    {"ad": "CNBC — dünya ekonomisi", "bolge": "global", "alan": "makro",
     "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100727362"},
    {"ad": "CNBC — piyasalar", "bolge": "global", "alan": "piyasa",
     "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258"},
    {"ad": "CNBC — finans", "bolge": "global", "alan": "makro",
     "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664"},
    {"ad": "MarketWatch", "bolge": "global", "alan": "piyasa",
     "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"ad": "Financial Times", "bolge": "global", "alan": "karisik",
     "url": "https://www.ft.com/rss/home"},
    {"ad": "OilPrice", "bolge": "global", "alan": "piyasa",
     "url": "https://oilprice.com/rss/main"},
    {"ad": "Euronews Türkçe", "bolge": "karisik", "alan": "karisik",
     "url": "https://tr.euronews.com/rss"},

    # ── Hedefli aramalar (boşluk doldurucu; özet taşımazlar)
    {"ad": "Arama — TCMB ve faiz", "bolge": "tr", "alan": "makro", "ozet_yok": True,
     "url": "https://news.google.com/rss/search?q=(TCMB+OR+%22Merkez+Bankas%C4%B1%22+OR+PPK+OR+enflasyon)+when:2d&hl=tr&gl=TR&ceid=TR:tr"},
    {"ad": "Arama — Türkiye ekonomi politikası", "bolge": "tr", "alan": "politika", "ozet_yok": True,
     "url": "https://news.google.com/rss/search?q=(%22ekonomi+program%C4%B1%22+OR+%22orta+vadeli+program%22+OR+%22maliye+politikas%C4%B1%22+OR+%22asgari+%C3%BCcret%22+OR+vergi+d%C3%BCzenleme)+when:2d&hl=tr&gl=TR&ceid=TR:tr"},
    {"ad": "Arama — Türkiye (yabancı basın)", "bolge": "tr", "alan": "karisik", "ozet_yok": True,
     "url": "https://news.google.com/rss/search?q=(%22Turkish+lira%22+OR+CBRT+OR+%22Turkey+economy%22+OR+%22Turkey+inflation%22)+when:2d&hl=en-US&gl=US&ceid=US:en"},
    {"ad": "Arama — ABD borç yönetimi ve tahvil arzı", "bolge": "global", "alan": "makro",
     "ozet_yok": True,
     "url": "https://news.google.com/rss/search?q=(%22Treasury+buyback%22+OR+%22quarterly+refunding%22+OR+%22Treasury+auction%22+OR+%22debt+ceiling%22+OR+%22bond+supply%22+OR+%22term+premium%22)+when:3d&hl=en-US&gl=US&ceid=US:en"},
    {"ad": "Arama — Fed ve ECB", "bolge": "global", "alan": "makro", "ozet_yok": True,
     "url": "https://news.google.com/rss/search?q=(%22Federal+Reserve%22+OR+ECB+OR+%22Bank+of+Japan%22)+(rates+OR+inflation+OR+policy)+when:1d&hl=en-US&gl=US&ceid=US:en"},
]

# ─────────────────────────── haber sınıflandırma
# Kaynağın varsayılan bölge/alanı yeterli değil: AA Dünya'da bir ABD enflasyon
# haberi çıkabilir, Bloomberg HT'de bir seçim haberi. Başlık + özet metni bu
# kalıplarla taranır ve varsayılan EZİLİR.
ALAN_KALIPLARI = {
    "politika": (r"se[çc]im|meclis|kabine|bakan\b|cumhurba[şs]kan|yasa|kanun|teklif|"
                 r"diploma|savaş|sava[şs]|ate[şs]kes|yaptırım|yaptırım|tarife|g[üu]mr[üu]k vergi|"
                 r"nato|avrupa birli[ğg]i|m[üu]zakere|zirve|anla[şs]ma|protesto|referandum|"
                 r"koalisyon|parlamento|sanction|tariff|election|parliament|summit|ceasefire|"
                 r"peace talk|trade war|geopolit"),
    "makro": (r"enflasyon|b[üu]y[üu]me|istihdam|i[şs]sizlik|cari a[çc]|b[üu]t[çc]e|faiz|"
              r"para politikas|resesyon|pmi|gsyh|t[üu]ketici g[üu]ven|sanayi [üu]retim|"
              r"inflation|growth|employment|unemployment|deficit|rate cut|rate hike|"
              r"monetary policy|recession|gdp|payroll"),
    "piyasa": (r"borsa|endeks|hisse|tahvil|getiri|kur\b|dolar|euro|alt[ıi]n|petrol|brent|"
               r"kripto|bitcoin|cds|bist|stocks|bond|yield|oil|gold|currency|equit"),
}
BOLGE_KALIPLARI = {
    "tr": r"t[üu]rkiye|tcmb|merkez bankas|lira|bist|istanbul|ankara|turkish|turkey",
    "global": (r"\bfed\b|federal reserve|ecb|avrupa merkez|[çc]in\b|china|abd\b|"
               r"amerika|washington|brussels|japonya|japan|almanya|germany|rusya|russia|"
               r"opec|imf|d[üu]nya bankas|world bank"),
}

# Bülten bölümleri: (id, başlık, bölge, alan) — sıra sayfadaki sıradır.
HABER_BOLUMLERI = [
    ("kilit", "Kilit gelişmeler", None, "kilit"),
    ("kurum", "Kurum duyuruları — Türkiye", None, "kurum"),
    ("kurum_global", "Kurum duyuruları — ABD Hazinesi ve borç yönetimi", None, "kurum_global"),
    ("tr_makro", "Türkiye — makro ve veri", "tr", "makro"),
    ("tr_politika", "Türkiye — politika ve düzenleme", "tr", "politika"),
    ("tr_piyasa", "Türkiye — piyasa", "tr", "piyasa"),
    ("global_makro", "Global — makro ve merkez bankaları", "global", "makro"),
    ("global_politika", "Global — jeopolitik ve ticaret", "global", "politika"),
    ("global_piyasa", "Global — piyasa ve emtia", "global", "piyasa"),
]
# ─────────────────────────── haber ÖNEM puanlaması
# Sorun: bülten haberleri bölümlere dağıtıyor ama hepsini eşit ağırlıkta gösteriyordu.
# ABD Hazinesi'nin geri alım büyüklüğünü ikiye katlaması ile "ECB başkanı WEF'e aday"
# haberi yan yana, aynı puntoda duruyordu. Haftanın ana sürücüsü bu yüzden gözden kaçtı.
#
# Puan üç kaynaktan gelir:
#   1. Konu ağırlığı — aşağıdaki kalıplar (piyasayı fiilen hareket ettiren olaylar).
#   2. Kaynak itibarı — KAYNAK_PUANI (0-10) beşte bir ağırlıkla.
#   3. Kümedeki kaynak sayısı — aynı öyküyü kaç yayın yazdı; yayılma önemin ölçüsüdür.
# Kurum duyurusu ayrıca sabit bonus alır: birincil kaynaktır, haber değil OLAYdır.
ONEM_KALIPLARI = [
    # (ağırlık, kalıp) — sıra önemsiz, en yüksek eşleşen ağırlık alınır
    (6, r"buyback|geri al[ıi]m|quarterly refunding|refinansman duyuru|debt ceiling|"
        r"bor[çc] tavan|m[üu]dahale|intervention|emergency|ola[ğg]an[üu]st[üu] toplant|"
        r"moratoryum|default|temerr[üu]t|devalu|peg|kur [çc]apas"),
    (5, r"faiz karar|rate decision|rate cut|rate hike|policy decision|ppk karar|"
        r"zorunlu kar[şs][ıi]l|makroihtiyati|sermaye kontrol|capital control|"
        r"not indirim|downgrade|not art[ıi]r|upgrade|kredi notu"),
    (4, r"tarife|tariff|yapt[ıi]r[ıi]m|sanction|ticaret sava|trade war|ambargo|"
        r"ihale|auction|tahvil ihrac|bond sale|issuance|arz|supply|"
        r"bilan[çc]o k[üu][çc]|quantitative|qt|qe|swap hatt|swap line"),
    (3, r"t[üu]fe|cpi|enflasyon veri|inflation data|tar[ıi]m d[ıi][şs][ıi] istihdam|"
        r"payroll|i[şs]sizlik|unemployment|gsyh|gdp|b[üu]y[üu]me veri|pmi|"
        r"tutanak|minutes|enflasyon raporu|projeksiyon|dot plot"),
    (2, r"opec|petrol|oil price|alt[ıi]n|gold|repo|likidite|liquidity|"
        r"cari a[çc]|b[üu]t[çc]e a[çc]|rezerv|reserve"),
]
# Bu puanın üstündeki maddeler "Kilit gelişmeler" bölümüne çıkar ve ayrıntılı işlenir.
KILIT_ESIK = 6.0
# Kilit bölümünde gösterilecek azami madde.
KILIT_SINIRI = 6

# Bölüm başına azami madde (kurum duyuruları sınırsız).
BOLUM_SINIRI = 10

# Haber listesi OLMAYAN, yalnız yazıdan ibaret gündem bölümleri. Bunlar piyasa
# tablolarını ve takvimi okuyup yorumlayan bölümlerdir; kural tabanlı koşu
# bunları boş bırakır, yorum katmanı doldurur.
GUNDEM_YAZI_BOLUMLERI = [
    ("faiz_fx_surucu", "Faiz ve döviz piyasasının sürücüleri"),
    ("emtia_surucu", "Emtia ve enerji: fiyat hareketinin sebebi"),
    ("risk_firsat", "Riskler ve fırsatlar"),
    ("beklenti", "Yaklaşan veriler: beklentiler ve ne izlenmeli"),
]

# ─────────────────────────── alaka ve gürültü süzgeçleri
# BAŞLIKTA bu terimlerden biri geçmelidir. Özette geçmesi yetmez: özet çoğu akışta
# haberin ilk cümlesidir ve "ekonomi" gibi bir kelime rastgele düşebilir; başlık ise
# haberin ne hakkında olduğunu söyler.
HABER_ILGILI = (r"enflasyon|t[üu]fe|[üu]fe\b|faiz|tcmb|merkez bankas|kur\b|dolar|euro\b|"
                r"rezerv|swap|tahvil|bono|hazine|ihale|bor[çc]lan|kredi|mevduat|bddk|spk|"
                r"imf\b|moody|fitch|s&p|cds\b|bist|borsa|fed\b|ecb\b|ppk|b[üu]t[çc]e|"
                r"cari a[çc]|[öo]demeler dengesi|istihdam|i[şs]sizlik|b[üu]y[üu]me|gsyh|"
                r"resesyon|durgunluk|lira\b|asgari [üu]cret|vergi d[üu]zenle|vergi paketi|"
                r"orta vadeli program|ekonomi program|petrol|brent|do[ğg]al gaz|alt[ıi]n fiyat|"
                r"ons alt[ıi]n|yapt[ıi]r[ıi]m|tarife|g[üu]mr[üu]k vergi|ticaret sava|ate[şs]kes|"
                r"se[çc]im|zirve|m[üu]zakere|"
                r"inflation|interest rate|rate cut|rate hike|central bank|monetary polic|"
                r"treasury|bond|yield|deficit|recession|payroll|unemployment|gdp\b|"
                r"tariff|sanction|trade war|ceasefire|opec|oil price|gold price|"
                r"currenc|devalu|default|downgrade|upgrade|imf\b")

# Bunlardan biri geçiyorsa alınmaz — alaka terimi de geçse.
HABER_GURULTU = r"emekli zamm|emekli maa|ev kadın|arazi sat|kiraya ver|burç|ma[çc] [öo]zeti|transfer bombas|hava durumu|piyango|çekili[şs]|indirim kampanya|astroloji|promosyon|convert [0-9]|bybit|binance|coin fiyat|how much is|gong .{0,20}çaldı|ya[şs] g[üu]n[üu]|falc|tur[şs]u|lezzet|festival|g[ıi]da denetim|taksit f[ıi]rsat|72 taksit|ka[çc] para|ne kadar oldu|^about .{0,90}reuters|quote page|stock quote|hisse [öo]nerisi|katlanabilir|iphone|nvidia earnings|burcunuz|ma[çc] sonucu|teknik direkt[öo]r|cricket|nightclub|premier lig|şampiyonlar ligi|futbol|basketbol|oyuncu kadrosu"

# Kaynak itibar sıralaması: aynı öyküyü birden çok yer yazdığında bülten hangisini
# gösterecek? Yüksek puanlı kaynak temsilci olur. Puanı olmayan kaynak 0 sayılır;
# içerik çiftlikleri ve toplayıcılar böylece kendiliğinden geri düşer.
KAYNAK_PUANI = {
    "reuters": 10, "financial times": 10, "ft.com": 10, "bloomberg": 9, "wall street journal": 9,
    "wsj": 9, "economist": 9, "cnbc": 8, "bbc": 8, "associated press": 8, "ap news": 8,
    "anadolu ajansı": 7, "aa.com.tr": 7, "bloomberg ht": 7, "dünya": 6, "dunya": 6,
    "investing": 5, "euronews": 5, "hürriyet": 4, "milliyet": 4, "sözcü": 4, "sozcu": 4,
    "cumhuriyet": 4, "t24": 4, "ekonomim": 4, "patronlardunyasi": 3, "borsagundem": 3,
}

# Bültende gösterilecek azami haber sayısı (kurum duyuruları bu sınırın dışında).
HABER_SINIRI = 12


# ─────────────────────────── ekonomik takvim: önem filtresi
# TÜİK "Ulusal Veri Yayımlama Takvimi" günde onlarca kayıt içerir (günlük SPK fon
# istatistiği, EFT işlem hacmi…). Bülten hepsini yazsa okunmaz. Aşağıdaki kalıplar
# NELERİN bültene gireceğini belirler; eşleşmeyen kayıt DÜŞER.
#   onem 1 = kritik (bültenin başında, saatiyle)
#   onem 2 = önemli (takvim tablosunda)
#   onem 3 = takip (yalnız haftalık genişletilmiş görünümde)
# Kalıplar büyük/küçük harf duyarsız düzenli ifadelerdir; sıra önemlidir (ilk eşleşen kazanır).
TAKVIM_KURALLARI: list[tuple[str, int, str]] = [
    (r"Tüketici Fiyat Endeksi", 1, "TÜFE"),
    (r"Yurt İçi Üretici Fiyat", 1, "Yİ-ÜFE"),
    (r"Ödemeler Dengesi", 1, "Ödemeler dengesi"),
    (r"Merkezi Yönetim Bütçe", 1, "Bütçe dengesi"),
    (r"Gayrisafi Yurt İçi Hasıla", 1, "GSYH"),
    (r"İşgücü İstatistikleri", 1, "İşgücü"),
    (r"Uluslararası Rezervler ve Döviz Likiditesi", 1, "IRFCL rezerv"),
    (r"Haftalık Para ve Banka", 2, "Haftalık para-banka"),
    (r"Menkul Kıymet İstatistikleri", 2, "Menkul kıymet ist."),
    (r"Sanayi Üretim", 2, "Sanayi üretimi"),
    (r"Dış Ticaret", 2, "Dış ticaret"),
    (r"Kapasite Kullanım", 2, "Kapasite kullanımı"),
    (r"Reel Kesim Güven|İktisadi Yönelim", 2, "Reel kesim güveni"),
    (r"Tüketici Güven", 2, "Tüketici güveni"),
    (r"Merkezi Yönetim Borç", 2, "Borç stoku"),
    (r"Konut Satış", 3, "Konut satışları"),
    (r"Hizmet.*Güven|Perakende.*Güven", 3, "Sektörel güven"),
    (r"Finansal Hizmetler", 3, "Finansal hizmetler"),
    (r"Bankacılık Sektörü", 3, "BDDK bankacılık"),
    (r"Tarım Ürünleri Üretici", 3, "Tarım ÜFE"),
    (r"Yurt Dışı Üretici Fiyat", 3, "YD-ÜFE"),
    (r"Ciro Endeks", 3, "Ciro endeksleri"),
    (r"Perakende Satış", 3, "Perakende satış"),
]

# Bültenin takvim bölümünde gösterilecek asgari önem (3 = hepsi).
TAKVIM_ASGARI_ONEM = 2
# Haftalık genişletilmiş görünümde (Pazartesi bülteni) asgari önem.
TAKVIM_HAFTALIK_ASGARI_ONEM = 3
# Takvim ufku (gün).
TAKVIM_UFKU = 21
