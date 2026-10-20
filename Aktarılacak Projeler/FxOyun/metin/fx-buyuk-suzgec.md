---
title: 'FX Gün İçi Oyun Planı 7: Büyük Mum — Süzgeçler: Ne Zaman Tersine, Ne Zaman Mumun Yönünde'
description: "Büyük mumdan sonra tersine mi girmeli (fade), mumun yönünde mi kalmalı? Kapanışın yeri, seans, takvimdeki haber, günlük trend, önceki koşu, günün ucu, oynaklık ve yakın geçmişteki büyük mumlar: dokuz süzgeç, üç dilim, iki dönem. Hangi süzgeç gerçekten ayırıyor, hangisi yalnız iyi bir hikâye anlatıyor."
pubDate: 2026-10-20
tags: ['fx', 'gun-ici', 'oyun-plani', 'buyuk-mum', 'suzgec', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Dokuz süzgeçten çoğu büyük mumdan sonraki yolu ayırmıyor. İki dönemde aynı yöne bakan okumalar az ve küçük: 5 dakikada ucunda kapanan ve Asya seansındaki büyük mum geri vermeye daha yatkın, arka arkaya büyük mum gelen piyasada geri verme belirgin; 1 saatte günlük trendin yönündeki büyük mum 2018–2023'te biraz daha uzağa gitti, 2024 sonrasında bu ayrım kayboldu. Hiçbiri maliyeti karşılayacak büyüklükte değil."
seviye: 'orta'
onkosul: ['fx-buyuk-mum']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';
import Diyagram from '../../components/Diyagram.astro';

Önceki ders büyük mumdan sonra fiyatın ortalama davranışını ölçtü: 5 dakikada hafif bir geri verme, 15 dakikada daha
zayıf bir geri verme, 1 saatte hafif bir devam. Ortalama, farklı koşulların karışımıdır. İşlemcinin asıl sorusu şudur: **hangi büyük
mumda** tersine girmek, hangisinde mumun yönünde kalmak daha haklı? Bu ders o soruyu dokuz süzgeçle sorar.

Dokuz süzgeç ve değerleri 2018–2023 gözlemiyle birlikte, 2024 sonrasının fiyatları hiçbir hesaba girmeden tanımlandı;
2024 sınamasından sonra hiçbiri değiştirilmedi. Her süzgeç için iki dönem yan yana durur. Bir süzgeçten okuma çıkarmanın kuralı basittir: **fark iki
dönemde de aynı yöne bakmalı.** Dokuz süzgeç, yirmi altı değer ve üç dilim yetmiş sekiz hücre eder. Hiçbir şey
olmasa da bunların birkaçı tek bir dönemde "anlamlı" görünür; ikinci dönem o şansı eler.

## Kısaca

- **Süzgeçlerin çoğu ayırmıyor.** Seansa, trende, oynaklığa ya da büyüklüğe göre ayrılan büyük mumların 24 mum
  sonraki ortalama yolu çoğu hücrede birbirinin aralığı içinde kalıyor (Şekil 01).
- **5 dakikada geri verme iki yerde yoğunlaşıyor.** Ucunda kapanan mumda yarısına dönüş aynadan
  {{ S.5.kapanis.uc.ic.geri_fark }} puan sık (2024 → {{ S.5.kapanis.uc.dis.geri_fark }}). Asya seansındaki büyük mumda
  ±1 ATR'den önce mumun yönündeki seviyenin görülme payı {{ S.5.seans.asya.ic.sim }} (2024 → {{ S.5.seans.asya.dis.sim }});
  Londra seansında {{ S.5.seans.londra.ic.sim }}.
- **Arka arkaya büyük mum, 5 dakikada geri verme işareti.** Önceki 4–24 mumda (5 dakikada yaklaşık iki saat) başka
  büyük mum olan piyasada 24 mum sonra ortalama {{ S.5.ardisik.evet.ic.net }} ATR (2024 → {{ S.5.ardisik.evet.dis.net }}); olmayanda
  {{ S.5.ardisik.hayir.ic.net }} ({{ S.5.ardisik.hayir.dis.net }}).
- **1 saatte trend ayrımı yalnız bir dönemde.** Günlük trendle aynı yöndeki 1 saatlik büyük mum 2018–2023'te 24 mum
  sonra ortalama {{ S.60.trend.trendle.ic.net }} ATR yol aldı, trende karşı olan {{ S.60.trend.karsi.ic.net }}. 2024
  sonrasında iki taraf aynı ({{ S.60.trend.trendle.dis.net }} · {{ S.60.trend.karsi.dis.net }}).
- **Haber mumu ayrı bir durum.** Takvimdeki büyük bir haberin mumu az (5 dakikada 2018–2023'te
  {{ S.5.haber.haber.ic.n }} olay) ve 24 mum sonraki yolun aralığı sıfırın iki yanına geniş açılıyor.

## Bu dersi masada nasıl kullanırsın

Süzgeçlerin hepsi büyük mum kapandığı anda bilinir, yani masada mum kapanır kapanmaz sorulabilir. Sorulma sırası
önemlidir, çünkü bazı cevaplar okumayı tamamen kapatır (haber mumu), bazıları dilime göre yönünü değiştirir (5 dakikada
hafif geri verme, 1 saatte hafif devam). Aşağıdaki merdiven bu sırayı yazar. Her basamak dersin bir bulgusuna dayanır
ve her basamağın sonucu bir işlem değil, bir yasaktır ya da bir bekleme: nerede kovalanmaz, nerede tersine girilmez,
nerede masadan kalkılır. Okumanın kuralı dersin kendi kuralıdır: iki dönemde aynı yöne bakan bir fark okuma sayılır,
tek dönemde görülen bir fark yalnız uyarıdır, hiç ayırmayan süzgeç okunmaz.

{{# karar sira }}

Merdivende "evet" dalı seni durdurur, "hayır" dalı bir sonraki soruya indirir. Sıranın bir mantığı var: önce okumayı
kapatan soru (haber), sonra yönü belirleyen soru (dilim), sonra yalnız 5 ve 15 dakikada iki dönemde tutan süzgeçler
(kapanışın yeri, seans, kümelenme), en sonda da hikâyesi güçlü ama ayırmayan süzgeçler. Merdivenin en altına
inen bir mumun kalan okuması 6. dersin ortalamasıdır ve o ortalama da maliyetin altındadır (6. ders, Dilim dilim okuma).

## Dokuz süzgeç

Her süzgeç büyük mum kapandığı anda bilinir; hiçbiri mumdan sonraki fiyatı kullanmaz.

- **Büyüklük.** Mumun aralığı önceki ATR'nin kaç katı: 2–3, 3–4, 4–5, 5 ve üstü.
- **Kapanışın yeri.** Kapanış mumun yönündeki ucuna ne kadar yakın: aralığın son çeyreğinde ("uca yakın"), son yarısının
  geri kalanında ("ortada") ya da yarısının gerisinde ("geri verilmiş", uzun fitil).
- **Seans.** Mumun başladığı saat, Londra ve New York saatiyle tanımlı; TSİ karşılıkları İngiltere ve ABD yaz
  saatindeyken verildi, ikisi kış saatindeyken bir saat sonradır; Mart'taki ve Ekim–Kasım'daki ara haftalarda iki
  ülkenin saati ayrıştığı için sınırlardan biri bir saat kayar. **Asya**: Londra 07:00'den önce (TSİ 09:00'dan önce;
  New York 17:00'den, yani TSİ 00:00'dan sonraki saatler dahil). **Londra**: Londra 07:00 – New York 08:00 (TSİ 09:00–15:00). **Örtüşme**:
  New York 08:00 – Londra 16:30 (TSİ 15:00–18:30). **New York öğleden sonra**: Londra 16:30 – New York 17:00 (TSİ
  18:30–00:00).
- **Takvimdeki büyük haber.** ABD istihdam ve enflasyon verisi, Fed, ECB ve BoE kararı; olayın saati mumun başlangıcından
  iki dakika önce ile mumun sonu arasındaysa "var".
- **Günlük trend.** Bir önceki günün kapanışı 20 günlük üstel ortalamanın (EMA20) üstünde ve ortalama beş günde
  yükselmişse yukarı, tersi aşağı, öbür hâller yatay. Mumun yönü trendle aynıysa "trend yönünde".
- **Mumdan önceki 12 mum.** Büyük mumdan önceki 12 mumda fiyat mumun yönünde en az 2 ATR yürümüşse "aynı yönde koşu",
  tersine 2 ATR yürümüşse "ters yönde koşu", öbür hâller "sakin".
- **Günün yeni ucu.** Mum, FX gününün (New York 17:00'de, TSİ ABD yaz saatinde 00:00, kış saatinde 01:00 başlayan
  gün) o ana kadarki ucunu aştı mı.
- **Günlük oynaklık.** Son 20 günün ortalama günlük aralığının, son 250 güne göre yüzdelik sırası: alt üçte bir düşük,
  orta üçte bir orta, üst üçte bir yüksek.
- **Yakın geçmişte başka büyük mum.** Önceki 4–24 mumda başka bir büyük mum var mı (önceki üç mum zaten kümenin
  devamı sayılıp dışarıda bırakıldı).

Her hücrede üç ölçü var: ±1 ATR'den önce mumun yönündeki görülme payı (yazı turada {{ Y.50 }}), mumun yarısına dönüşün
aynadan farkı (puan) ve 24 mum sonraki ortalama yol (ATR, mumun yönünde).

{{# sekil 01_net "Süzgeçler 24 mum sonrasını ayırıyor mu" }}

Aşağıdaki tablolar her dilimde öne çıkan süzgeçleri verir; dokuz süzgecin bütün değerleri iki dönemiyle Şekil 01'de
ve Şekil 02'de. Tablolarda "önce +1 ATR (mumun yönü)", kapanışın 1 ATR mumun yönündeki seviyesinin, 1 ATR tersindekinden
önce görülme payıdır.

## 5 dakika

{{# suzgec 5 kapanis seans ardisik kova }}

5 dakikada üç okuma iki dönemde de tutuyor. (24 mum sonraki yolu iki dönemde de sıfırın altında kalan öbür hücreler,
örneğin sakin geçmişten gelen mum ve 2–3 ATR kovası, olayların çoğunu taşıdıkları için ortalamanın kendisini
tekrarlıyor.)

**Kapanış ucundaysa geri verme.** Kapanışı ucuna yakın büyük mum yarısına aynadan sık dönüyor. Olası bir açıklama
(bu derste ölçülmedi): ucunda kapanan mum, alıcının ya da satıcının son dakikaya kadar bastırdığı mumdur ve son
dakikadaki baskı çoğu zaman geçicidir. Ama "geri verme" burada mumun yarısına kadar geri çekilmedir; mumun öbür ucuna
dönüş değil. Fitili uzun, kapanışı yarısının gerisinde kalan mumda yarısına dönüş ölçüsü anlamsızdır: kapanış zaten
yarının gerisinde olduğu için gerçek yol da ayna da yarıya "dönmüş" sayılır. O mumun 24 mum sonraki yolu iki dönemde de
eksi ({{ S.5.kapanis.geri.ic.net }} · {{ S.5.kapanis.geri.dis.net }} ATR), yani hafif geri verme orada da sürüyor.

**Asya'da geri verme belirgin, Londra'da küçük.** Asya seansında ±1 ATR'den önce tersindeki seviye daha sık görülüyor ve
yarısına dönüş aynadan belirgin sık ({{ S.5.seans.asya.ic.geri_fark }} · {{ S.5.seans.asya.dis.geri_fark }} puan). Olası
bir açıklama (ölçülmedi): Asya'da likidite incedir ve ince piyasadaki büyük mum daha kolay geri verilir. Londra
seansında aynı ölçüler yarı yarıya küçük (yarısına dönüş aynadan {{ S.5.seans.londra.ic.geri_fark }} ·
{{ S.5.seans.londra.dis.geri_fark }} puan sık) ve 24 mum sonraki yol sıfırın yakınında.

**Kümelenme geri vermeyi büyütüyor.** Önceki 4–24 mumda başka büyük mum varsa 24 mum sonraki ortalama yol iki dönemde de
eksi ve aralığı sıfırın altında. Arka arkaya gelen büyük mumların bir haberin ya da bir akışın sonu olup olmadığı ayrıca
ölçülmedi.

Büyüklük kovaları iki dönemde aynı yöne bakmıyor: 4–5 ATR'lik mum 2018–2023'te belirgin geri verdi, 2024 sonrasında
vermedi. "Mum ne kadar büyükse dönüş o kadar yakın" okuması bu veride yok.

### Masada: Asya'da ve ucunda kapanan mum

5 dakikanın iki dönemde tutan iki süzgeci ekranda aynı resmi verir: dar, sakin mumların arasından çıkan uzun gövdeli
bir mum, kapanışı aralığının en uç çeyreğinde. Asya seansı Londra 07:00'den öncedir (TSİ İngiltere yaz saatinde
09:00'dan, kış saatinde 10:00'dan önce) ve New York 17:00'den sonraki saatleri de kapsar (TSİ ABD yaz saatinde 00:00,
kış saatinde 01:00). Bu resimde okuma şudur: mumun yarısına dönüş aynadan biraz sık gelir, yani kapanışta mumun
yönünde kovalayan biri, yön bilgisi olmayan bir yola göre biraz daha sık geri çekilmenin içine girer. Okumanın
söylemediği şey de aynı derecede önemli: yarıya dönüş mumun öbür ucuna dönüş değildir, ve 24 mum sonraki ortalama yol
ATR'nin onda birkaçıdır.

{{# sema asya-uc }}

{{# kart asya-uc }}

Bu durumda yapmazsın: kapanışta mumun yönünde piyasa emriyle kovalamazsın; mumun tersine yalnız "Asya'da geri verir"
diye girmezsin, çünkü tersine girmenin maliyetten önceki küçük artısı maliyetten sonra eksidir (8. ders, 5 dakika);
iki süzgeç birlikte geldi diye okumayı iki kat güçlü saymazsın, çünkü iki süzgecin birlikte ne verdiği bu derste
ölçülmedi (Ölçülmeyenler). Londra açılışıyla (Londra 07:00; TSİ İngiltere yaz saatinde 09:00, kış saatinde 10:00)
seans değişir ve Londra'daki aynı okuma yarı yarıya küçüktür; Asya'da kurulan bir okumayı Londra'ya taşımazsın.

{{# ornek asya-uc }}

Üstteki günde ① Asya'da ucunda kapanan büyük mum, ② onun yarısı: fiyat birkaç mum içinde ③'te yarıya dokundu ve ④'e
kadar mumun tersinde kaldı. Alttaki günde ① ve ② masada aynı görünüyordu: mum ucunda kapandı, öncesi sakindi, takvimde
haber yoktu, kartın "Ne görürsün" satırına iki gün de birebir uyar. Ama alttaki günde fiyat yarıya hiç gelmedi (③
işareti bu yüzden yok) ve ④'te mumun yönünde uzaktaydı. Üstteki günde mumun yönünde yarıya konan limit dolardı ve o
işlem kaybederdi; alttaki günde limit dolmazdı ve en iyi hareket kaçardı. 8. dersin ters seçimi tek bir çiftte böyle
görünür. İki günün farkı ancak sonraki mumlarda belli olur; sonradan bakınca "belli" görünmesi, kararın o anda
verildiği bilgiyle ilgisizdir. Tek bir örnek kuralı ne doğrular ne yanlışlar: okuma binlerce mumun ortalamasıdır ve
o ortalama aynadan yalnız birkaç puan uzaktadır (7. ders, 5 dakika).

### Masada: arka arkaya büyük mum

Kümelenme süzgeci ekranda iki büyük mum olarak görünür: biri dört ile yirmi dört mum önce (5 dakikada yaklaşık yirmi
dakika ile iki saat), öbürü şimdi. Sezgi çoğu zaman ikinci mumu "ikinci itiş" diye okur ve devamını bekler. Bu
veride iki dönemde de tersi görüldü: önceki 4–24 mumda başka büyük mum olan piyasada 24 mum sonraki ortalama yol
mumun tersinde ve aralığı sıfırın altında. Bu ölçülen bir eğilimdir, ama nedeni (bir haberin ya da bir akışın sonu
mu) bu derste ölçülmedi.

{{# sema kume }}

{{# kart kume }}

Bu durumda yapmazsın: ikinci mumu kovalamazsın; "iki büyük mum geldi, akış bitti" diye tersine de girmezsin, çünkü
24 mumdaki eksi yol yine ATR'nin onda birkaçıdır ve maliyetten küçüktür (6. ders, Makas büyük mumda açılıyor mu); ilk mumun
neden geldiğini bilmeden ikinci muma okuma kurmazsın, ilk mum takvimdeki bir haberse ikinci mum da haber penceresinin
içinde olabilir (bkz. Haber mumu).

## 15 dakika

{{# suzgec 15 kapanis seans trend kova }}

15 dakikada yalnız Asya seansı iki ölçüde iki dönemde aynı yöne bakıyor: ±1 ATR'den önce mumun yönündeki seviye
{{ S.15.seans.asya.ic.sim }} ve {{ S.15.seans.asya.dis.sim }}, yarısına dönüş aynadan {{ S.15.seans.asya.ic.geri_fark }}
ve {{ S.15.seans.asya.dis.geri_fark }} puan sık. 24 mum sonraki yolun işareti ise dönemden döneme değişiyor
({{ S.15.seans.asya.ic.net }} · {{ S.15.seans.asya.dis.net }} ATR). Öbür hücrelerde büyük sayılar var (3–4 ATR'lik mum
2018–2023'te 24 mumda {{ S.15.kova.3-4.ic.net }} ATR, 2024 sonrasında {{ S.15.kova.3-4.dis.net }}), ama aynı işaret öbür
dönemde ya kayboluyor ya da aralık sıfırı rahatça kapsıyor.

### Masada: 15 dakikada süzgeç az şey söyler

15 dakikalık grafik masada çoğu zaman en "okunaklı" görünen dilimdir: mumlar 5 dakikadakinden düzgün, 1 saattekinden
sık. Bu ders o okunaklılığın bir okuma vermediğini söylüyor. 15 dakikada okuma çıkan tek süzgeç Asya seansı;
tablodaki büyük sayılar (3–4 ATR kovası gibi) öbür dönemde ya kayboluyor ya da aralıkları sıfırı kapsıyor.
Asya'da bile okuma yalnız yarıya dönüşün ve ±1 ATR payının yönüdür; 24 mum sonraki yolun işareti dönemden döneme
değişiyor.

{{# kart on-bes }}

Bu durumda yapmazsın: büyüklük kovasına bakıp yön okumazsın; 5 dakikada tutan "kapanış ucunda" okumasını 15 dakikaya
taşımazsın, çünkü bu ders 15 dakikada o süzgeçten bir okuma çıkarmadı (15 dakika); Asya'daki 15 dakikalık mumda yarıya dönüşü bir
yön sinyali saymazsın, çünkü 24 mumun sonunda fiyatın nerede olduğunu söylemiyor.

## 1 saat

{{# suzgec 60 trend kapanis kosu seans gun_ucu }}

1 saatte ortalama yol zaten mumun yönünde ve süzgeçlerin çoğu bunu değiştirmiyor. İki okuma dikkat çekiyor.

**Trendin yönündeki büyük mum: yalnız bir dönemde.** Günlük trendle aynı yöndeki 1 saatlik büyük mum 2018–2023'te 24
saatte ortalama {{ S.60.trend.trendle.ic.net }} ATR yol aldı ({{ Y.95 }} aralık {{ S.60.trend.trendle.ic.net_alt }} …
{{ S.60.trend.trendle.ic.net_ust }}), trende karşı olan {{ S.60.trend.karsi.ic.net }}. 2024 → döneminde iki taraf aynı
yerde ({{ S.60.trend.trendle.dis.net }} · {{ S.60.trend.karsi.dis.net }}). Trendin yatay olduğu günlerde devam iki
dönemde de kayboluyor ({{ S.60.trend.yatay.ic.net }} · {{ S.60.trend.yatay.dis.net }}).

**Londra seansı.** Londra seansında başlayan 1 saatlik büyük mum iki dönemde de mumun yönünde gitti
({{ S.60.seans.londra.ic.net }} · {{ S.60.seans.londra.dis.net }} ATR). 2018–2023'te aralık sıfıra değiyor
({{ S.60.seans.londra.ic.net_alt }} … {{ S.60.seans.londra.ic.net_ust }}), 2024 sonrasında sıfırın üstünde. Trend
okuması gibi bu da tek bir dönemde aralığıyla tutuyor; yetmiş sekiz hücrenin içinden birkaçının tek dönemde böyle
görünmesi beklenen şeydir.

**Fitili uzun büyük mum.** Kapanışı yarısının gerisinde kalan 1 saatlik büyük mum 24 saatte eksi kaldı
({{ S.60.kapanis.geri.ic.net }}; 2024 → {{ S.60.kapanis.geri.dis.net }}), öbür kapanışlarda artı. Olay az ve aralıklar
geniş, ama işaret iki dönemde aynı.

9. dersin seçtiği 1 saatlik girişin dayandığı süzgeç "mumdan önceki 12 mum"dur; tablodaki satırları, o süzgecin
24 mumluk yolu kendi başına ayırmadığını gösteriyor.

{{# sekil 02_yarisi "Fiyat önce hangi yöne gidiyor" }}

### Masada: trendin yönündeki saatlik mum

1 saatlik grafikte masaya en sık gelen hikâye şudur: birkaç gündür aynı yöne giden bir piyasada trendin yönünde büyük
bir saatlik mum, ve "trend yönünde, devam eder" okuması. Bu derste o okuma 2018–2023'te görüldü ve 2024 sonrasında
kayboldu: iki dönemden yalnız birinde tutan bir fark, okuma kuralına göre bir uyarıdır. Asıl iki dönemde tutan şey
daha düz: 1 saatte büyük mumun tersine girmenin dayanağı yok, ortalama yol mumun yönünde (6. ders, Dilim dilim okuma).
Günlük trend süzgeci grafiğe değil bir önceki günün kapanışına bakar: kapanış EMA20'nin üstünde ve ortalama beş günde
yükselmişse yukarı. Ekrandaki son birkaç saatlik mumun yönü bu süzgeç değildir.

{{# sema saat-trend }}

{{# kart saat-trend }}

Bu durumda yapmazsın: trendin yönünde diye hedefi uzatmazsın; trende karşı büyük mumu "tuzak" sayıp tersine girmezsin,
çünkü 1 saatte trende karşı büyük mum da iki dönemde mumun yönünde gitti; fitili uzun, kapanışı yarısının gerisinde
kalan saatlik mumu mumun yönündeki bir devam diye okumazsın, çünkü o mumun 24 saatlik yolu iki dönemde de eksi (olay
az, aralık geniş). Londra seansındaki saatlik mumun devamı da iki dönemde artı ama aralığı yalnız 2024 sonrasında
sıfırın üstünde: bir uyarıdır, kural değil.

{{# ornek saat-trend }}

Üstteki günde ① günlük trendin yönünde 1 saatlik büyük mum, ② yarısı: fiyat yarıya dönmedi (③ işareti yok) ve ④'te,
bir gün sonra, mumun yönünde uzaktaydı. Bu, trend okumasının anlattığı hikâyenin ta kendisi. Alttaki gün masada
aynıydı: trend aynı yöndeydi, mum aynı biçimde kapandı, takvimde haber yoktu; fiyat ③'te yarıya döndü ve ④'te mumun
tersindeydi. İki gün de 2018–2023'ten, yani trend ayrımının görüldüğü dönemden; o dönemde bile iki son da sıradandı.
Mum kapandığında hangisinin geleceğini söyleyen bir işaret yoktu; sonradan bakınca üstteki gün "trendin gücü",
alttaki gün "yorgun trend" diye kolayca anlatılır. Üstteki gün trend okumasını doğrulamaz, alttaki onu yanlışlamaz;
ikisi birlikte, tek dönemde tutan bir okumanın neden kural olmadığını gösterir: her okuma için hikâyesi hazır bir gün
bulunur (7. ders, 1 saat).

## Haber mumu

Takvimdeki büyük bir haberin (ABD istihdam ve enflasyon verisi, Fed, ECB, BoE kararı) saati mumun içine düşüyorsa, bu
dersin öbür süzgeçleri o mumda okunmaz. 5 dakikada 2018–2023'te {{ S.5.haber.haber.ic.n }} olay var, büyük mumların
küçük bir parçası, ve 24 mum sonraki yolun aralığı sıfırın iki yanına geniş açılıyor; okuma tablosunda bu satır
"ölçülemiyor" diye durur. 9. dersin seçim kuralı iki girişini tam buradan, haber mumunu ucundan tersine alan
limitlerden seçti ve ikisi de 2024 sonrasında tutmadı (9. ders, Seçilen girişler). Küçük bir alt küme, şansın en kolay
şişirdiği yerdir. Haber anlarının ilk mumunu kendi tanımıyla ayrı ölçen ders 4. derstir ve orada da haber mumu tek
başına bir yön sinyali değildir (4. ders, Plan tek cümlede).

### Masada: masadan kalkış

Haber mumunda masadan kalkmak bir işlem kararı değil, bir okuma kararıdır: bu dersin süzgeçleri o mumda bir şey
söylemiyor. Kalkış mum kapanınca değil, haber saatinden önce başlar. Bugünkü saatleriyle: ABD istihdam ve TÜFE New
York 08:30 (TSİ ABD yaz saatinde 15:30, kış saatinde 16:30), Fed kararı New York 14:00 (TSİ ABD yaz saatinde 21:00,
kış saatinde 22:00), ECB kararı Frankfurt 14:15 (TSİ Avrupa yaz saatinde 15:15, kış saatinde 16:15), BoE kararı
Londra 12:00 (TSİ İngiltere yaz saatinde 14:00, kış saatinde 15:00). Süzgeç olayın saati mumun başlangıcından iki
dakika önce ile mumun sonu arasındaysa mumu haber mumu sayar; 1 saatlik grafikte bu, haber saatini içeren bütün
saatlik mumdur.

{{# sema haber-kalk }}

{{# kart haber }}

Bu durumda yapmazsın: haber mumunun kapanış yerine, seansına ya da büyüklüğüne bakıp okuma kurmazsın; ilk dakikaların
sert hareketini kovalamazsın, uzun fitili "reddedildi" diye tersine de okumazsın; haber saatinden önce bekleyen bir
limiti ya da stop emrini haber penceresine taşımazsın. Haber mumundan sonra gelen ikinci bir büyük mumda kümelenme
okumasına da yaslanmazsın: önceki büyük mum bir haber mumuyken ikinci mumun ne yaptığı bu derste ayrıca ölçülmedi.

## Fade mi, devam mı: okuma tablosu

| Durum | Okuma | Ne kadar güvenilir |
|---|---|---|
| 5 dakika, kapanış ucunda | Mumun yarısına dönüş şanstan biraz sık. Kovalamak yerine geri çekilmeyi beklemek daha iyi fiyat verir, ama geri çekilme bir tersine işlem sinyali değil. | İki dönemde aynı yönde; birkaç puan. |
| 5 dakika, Asya seansı | Geri verme eğilimi en belirgin burada; Londra'da yarı yarıya küçük. | İki dönemde aynı yönde. |
| 5 dakika, önceki 4–24 mumda başka büyük mum | 24 mumda ortalama geri verme. | İki dönemde aynı yönde, aralık sıfırın altında. |
| 5 dakika, kapanış geri verilmiş (uzun fitil) | Hafif geri verme sürüyor. | İki dönemde eksi; olay az. |
| 15 dakika, Asya seansı | Hafif geri verme; 24 mumda işaret kararsız. | İki ölçüde aynı yönde. |
| 15 dakika, öbür koşullar | Ayrım yok. | — |
| 1 saat, günlük trendle aynı yönde | Mumun yönünde biraz daha yol. | Yalnız 2018–2023'te; 2024 sonrasında ayrım yok. |
| 1 saat, Londra seansı | Mumun yönünde yol. | İki dönemde artı; aralık yalnız 2024 sonrasında sıfırın üstünde. |
| 1 saat, kapanış geri verilmiş | Mumun yönü korunmuyor. | İki dönemde eksi; olay az. |
| Takvimdeki büyük haberin mumu | Okuma yok: olay az, dağılım çok geniş. | Ölçülemiyor. |

Bu tablonun hiçbir satırı bir işlem kuralı değildir. 6. dersin sonucu burada da geçerli: en belirgin okumaların büyüklüğü
24 mumda ATR'nin onda birkaçı. 8. ders bu büyüklüğün girişin maliyetiyle nasıl karşılaştığını, 9. ders de bu
okumalardan seçilen girişlerin 2024 sonrasında ne verdiğini gösterir.

### Masada: fade mi, bekle mi — süzgece göre okunuş

Fade, mumun tersine işleme girmektir (6. ders, Bu sonuç nasıl okunmalı). Bu dersin hiçbir okuması fade'i bir karar
olarak desteklemiyor: geri verme okumaları kovalamamayı ve beklemeyi söyler, tersine girmenin 5 dakikadaki küçük
artısı ise maliyetten sonra eksidir (8. ders, 5 dakika). Masadaki asıl seçim "fade mi devam mı" değil, "kovalar mıyım,
beklerim mi, kalkar mıyım"dır. Tablonun satırları bu üç cevaba şöyle dağılır.

**İki dönemde tutan okumalar (okuma kuralı):**

- **5 dakika, kapanış ucunda.** Kovalamazsın; mumun yönünde gireceksen geri çekilmeyi beklersin. Tersine girmezsin:
  geri çekilme mumun yarısına kadardır, öbür ucuna değil (7. ders, 5 dakika).
- **5 dakika, Asya seansı.** Aynı okuma, daha belirgin. Londra açılışıyla küçülür; okumayı seans geçişinin ötesine
  taşımazsın (7. ders, 5 dakika).
- **5 dakika, önceki 4–24 mumda başka büyük mum.** İkinci mumu kovalamazsın; ikinci mum devamın işareti değil
  (7. ders, 5 dakika).
- **5 dakika ve 1 saat, kapanış geri verilmiş.** Mumun yönüne yaslanmazsın; 1 saatte olay az ve aralık geniş
  (7. ders, 5 dakika; 7. ders, 1 saat).
- **15 dakika, Asya seansı.** Kovalamazsın; ama 24 mumda işaret kararsız, yani beklemek bir yön söylemez
  (7. ders, 15 dakika).

**Tek dönemde tutan okumalar (uyarıyla):**

- **1 saat, bütün büyük mumlar.** Ortalama yol mumun yönünde: 2018–2023'te aralığıyla, 2024 sonrasında yalnız nokta
  tahmini olarak (6. ders, Dilim dilim okuma). Uyarı olarak okunur: tersine girmezsin, ama mumun yönünü de bir kenar
  sanmazsın.
- **1 saat, günlük trendin yönünde.** Biraz daha yol yalnız 2018–2023'te; 2024 sonrasında trende karşı mum da aynı
  yolu aldı. Trend diye hedefi uzatmazsın (7. ders, 1 saat).
- **1 saat, Londra seansı.** İki dönemde artı, ama aralık yalnız 2024 sonrasında sıfırın üstünde (7. ders, 1 saat).

**Okuma yok:** büyüklük kovaları (dönemden döneme yön değiştiriyor), günlük oynaklık, 15 dakikada Asya dışındaki
süzgeçler, 1 saatte mumdan önceki koşu ve takvimdeki haber mumu (7. ders, Kısaca; 7. ders, Haber mumu).

## İyi hikâyesi olan süzgeç: masadaki tuzak

Masada bir süzgeç seçmenin en kolay yolu hikâyesine bakmaktır, ve en sık yapılan hata da budur. Üç hikâye her masada
anlatılır. "Beş ATR'lik mum aşırıdır, döner": büyüklük kovaları iki dönemde aynı yöne bakmıyor, 4–5 ATR'lik mum
2018–2023'te belirgin geri verdi, 2024 sonrasında vermedi (7. ders, 5 dakika; 6. ders, Büyüklük değişince). "Trende
karşı büyük mum tuzaktır": 1 saatte trende karşı büyük mum iki dönemde de mumun yönünde gitti (7. ders, 1 saat).
"Günün yeni ucunu yapan mum tükenmiştir, döner": 1 saatte günün yeni ucunu yapan büyük mum iki dönemde de ortalama
mumun yönünde gitti; "döner" hikâyesi tabloda görünmüyor (7. ders, 1 saat).

{{# sema asiri }}

Hikâyenin tuzağı şudur: üç gözlemden kurulmuş her örüntünün bir açıklaması bulunur, ve açıklama ne kadar iyiyse onu
sınamadan kabul etme eğilimi o kadar güçlüdür. Bu derste yetmiş sekiz hücre var; hiçbir şey olmasa da birkaçı tek bir
dönemde "anlamlı" görünür ve her birine bir hikâye yazılabilir. Hikâyeyi kurala çeviren tek şey ikinci dönemdir. Masada
bunun pratik karşılığı basit: bir süzgeç sana bir şey söylüyorsa önce "bu iki dönemde tuttu mu" diye sorarsın; cevap
hayırsa hikâye ne kadar ikna edici olursa olsun okuma yoktur. Tutan okumaların sıkıcı olması (kapanışın yeri, Asya
seansı, kümelenme) bir kusur değil, sınanmış olmanın görüntüsüdür.

## Emri nereye koyarsın

Bu bölüm bu derse bir giriş kuralı eklemez. Başka bir gerekçeyle (kendi okuman, bir seviye, bir haber) büyük mumdan
sonra işleme gireceksen, süzgecin söylediği şey emrin biçimini ve yerini değiştirir, işlemin beklenen sonucunu
değiştirmez. Aşağıdakilerin hepsi 8. dersin ölçtüğü giriş biçimlerine dayanır.

**Giriş emri.**

- **Kapanışta piyasa emri.** Mumun yönünde en pahalı biçimdir: makası ve kaymayı girişte de, çıkışta da öder
  (8. ders, 5 dakika). 5 dakikada ucunda kapanan ya da Asya'daki büyük mumda bu emirle girmezsin.
- **Geri çekilmeye limit** (mumun ucundan mumun boyunun dörtte biri, yarısı ya da daha derini). Girişte makas ve kayma
  ödemez, çıkışta öder. Ama limit, fiyat piyasa girişinin aleyhine yürüdüğünde dolar: dolduğu olaylarda aynı anda
  piyasadan girilseydi işlemlerin çoğu kaybederdi (8. ders, Limit neden ucuz görünür: ters seçim). Bu dersin tutan
  süzgeçleri tam da geri çekilmenin sık geldiği yerleri gösterir; oralarda limit sık dolar ve dolması iyi haber
  değildir. Limit maliyeti düşürür, kenar yaratmaz.
- **Ucun kırılmasına stop emri.** Mumun yönündeki momentum girişidir; kaymayı öder ve fiyatın zaten yürüdüğü yerden
  alır, maliyetten sonra eksidir (8. ders, Ucun kırılması).
- **Onay mumu.** Onay gelmeyen olaylarda emir hiç açılmaz, gelenlerde fiyat bir mum kötüleşmiş olur; onayın taşıdığı
  bilgi kaçırılan fiyatın bedelini ancak karşılıyor (8. ders, Onay mumu).
- **Tersine giriş.** Mumun ucuna konan tersine limit, 5 dakikadaki küçük geri verme kenarını yok eder, çünkü fiyatın
  uca geri döndüğü olaylar tam da geri vermenin olmadığı olaylardır (8. ders, Limit neden ucuz görünür: ters seçim).
  1 saatte tersine girmezsin (9. ders, Büyük mum için oyun planı).

**Stop.** 8. ders stopu girişten bir ya da iki ATR uzağa koyar. Bir ATR'de makas ve kayma R'nin daha büyük bir kısmını
yer ve riski çok küçük kalan olayların bir kısmında işlem hiç açılmaz; stopu iki ATR'ye taşımak maliyeti küçültür ama
kenar yaratmaz (8. ders, Stop uzaklığı ve maliyet). Mumun öbür ucunun ötesine konan stop bu derste ayrı bir seçenek
olarak ölçülmedi. Asya'da ATR'nin dar olmasının aynı makası R cinsinden büyütüp büyütmediği de bu derste ayrıca
ölçülmedi.

**Hedef.** 8. dersin hedefleri riskin bir ya da iki katıdır. Trend ya da Londra okumasına dayanarak hedefi uzatmazsın;
ikisi de tek dönemde tutan okumalardır. 1 saatte hedefi iki R olan geri çekilme limitleri ızgaranın sıfıra en yakın
hücreleridir, ama büyüklükleri sıfırdan ayırt edilemeyecek kadar küçük (8. ders, 15 dakika ve 1 saat).

**Emrin iptali.** 8. dersin limit ve stop emirleri büyük mum kapandıktan sonra altı mum bekler, dolmazsa iptal edilir;
bu bir seçim değil, ölçümün kuralıdır. Bekleme süresinde seans değişiyorsa (Asya'dan Londra'ya geçiş Londra 07:00, TSİ
İngiltere yaz saatinde 09:00, kış saatinde 10:00) emrin dayandığı okuma da değişir: Asya'daki geri verme Londra'da
yarı yarıya küçük (7. ders, 5 dakika). Bu yüzden seans geçişinde bekleyen emri çekersin; çekmenin sonucu bu derste
ölçülmedi, gerekçesi okumanın kendisinin seansla değişmesidir.

**Haber penceresinde.** 8. dersin maliyet varsayımı takvimdeki büyük bir haberin iki dakika öncesinden on beş dakika
sonrasına kadar piyasa ve stop emirlerine ek kayma ekler (8. dersin giriş paragrafı). Bekleyen bir limit ya da stop
emri o pencerede dolabilir ve dolduğu mum bir haber mumudur, yani bu dersin okuması o anda kalkar. Haber saati bekleme
süresinin içine düşüyorsa emri saatten önce çekersin (bu derste ölçülmedi). Pozisyondaysan dar stop haber penceresinde
maliyete en çok dayanan stoptur (4. ders, Haber anları için masa kartı).

## Sık yapılan hatalar

- **İyi hikâyesi olan süzgeci ölçmeden kural yapmak.** "Beş ATR'lik mum döner" gibi bir hikâyenin mekanizması
  anlatılabilir, ama büyüklük kovaları dönemden döneme yön değiştiriyor (7. ders, 5 dakika; 6. ders, Büyüklük
  değişince).
- **Tek dönemde tutan okumayı kural saymak.** 1 saatte trendin yönündeki büyük mumun fazladan yolu yalnız 2018–2023'te
  görüldü; 2024 sonrasında trende karşı mum da aynı yolu aldı (7. ders, 1 saat).
- **Geri vermeyi tersine işlem sanmak.** Ölçülen geri verme mumun yarısına kadardır; tersine girmenin küçük artısı
  maliyetten sonra eksi (7. ders, 5 dakika; 8. ders, 5 dakika).
- **Süzgeçleri üst üste yığmak.** "Asya, ucunda kapanış ve kümelenme birlikte geldiyse daha güçlüdür" ölçülmedi; iki
  süzgeçli bileşimler bu derste yok ve küçük alt kümeler şansın en kolay şişirdiği yerdir (7. ders, Ölçülmeyenler;
  9. ders, Seçilen girişler).
- **Haber mumunda süzgeç aramak.** Haber mumu az ve dağılımı geniş; 9. dersin buradan seçtiği iki giriş 2024 sonrasında
  tutmadı (7. ders, Haber mumu; 9. ders, Seçilen girişler).
- **Limitin dolmasını okumanın teyidi saymak.** Limit, fiyat piyasa girişinin aleyhine yürüdüğünde dolar; dolmasının
  büyük kısmı geometridir, teyit değil (8. ders, Limit neden ucuz görünür: ters seçim).
- **5 dakikanın okumasını 1 saate taşımak.** 5 dakikada hafif geri verme, 1 saatte hafif devam var; 1 saatte Asya'nın
  işareti dönemden döneme değişiyor (6. ders, Dilim dilim okuma; 7. ders, 1 saat).
- **Stopu yaklaştırmak.** Bir ATR'lik stopla makas ve kayma R'nin önemli bir kısmını yer (8. ders, Stop uzaklığı ve
  maliyet).

## Masa kontrol listesi

Büyük mum kapandığında masada sırayla sorulan sorular. Bir "evet" seni durdurabilir; durmadıysan bir sonrakine geçersin.

1. **Mum kapandı mı?** Süzgeçler kapanışta bilinir; açık mumda kapanışın yeri de büyüklük de değişir (7. ders, Dokuz
   süzgeç).
2. **Takvimdeki büyük bir haberin saati mumun içinde mi?** ABD istihdam ve TÜFE New York 08:30 (TSİ ABD yaz saatinde
   15:30, kış saatinde 16:30); Fed New York 14:00 (TSİ ABD yaz saatinde 21:00, kış saatinde 22:00); ECB Frankfurt 14:15
   (TSİ Avrupa yaz saatinde 15:15, kış saatinde 16:15); BoE Londra 12:00 (TSİ İngiltere yaz saatinde 14:00, kış
   saatinde 15:00). Evetse masadan kalkarsın (7. ders, Haber mumu).
3. **Dilim hangisi?** 1 saatse tersine girmezsin (6. ders, Dilim dilim okuma).
4. **Kapanış nerede?** Aralığın son çeyreğinde mi, ortasında mı, yarısının gerisinde mi (7. ders, 5 dakika)?
5. **Mum hangi seansta başladı?** Asya: Londra 07:00'den önce (TSİ İngiltere yaz saatinde 09:00'dan, kış saatinde
   10:00'dan önce) ya da New York 17:00'den sonra (TSİ ABD yaz saatinde 00:00'dan, kış saatinde 01:00'den sonra).
   Londra: Londra 07:00 ile New York 08:00 arası (TSİ ikisi yaz saatindeyken 09:00–15:00, ikisi kış saatindeyken 10:00–16:00). 5 ya da 15 dakikada Asya'ysa
   kovalamazsın (7. ders, 5 dakika; 7. ders, 15 dakika).
6. **Önceki 4–24 mumda başka büyük mum var mı?** 5 dakikada yaklaşık yirmi dakika ile iki saat geriye bakarsın; varsa
   ikinci mumu kovalamazsın (7. ders, 5 dakika).
7. **Okuman iki dönemde tutan bir süzgece mi dayanıyor?** Büyüklük ya da oynaklıksa okuma yok; 1 saatte trend ya da
   Londra ise yalnız uyarı (7. ders, Fade mi, devam mı: okuma tablosu).
8. **Gireceksen emir yazılı mı?** Emrin türü, stopun girişten uzaklığı (bir ATR'ye yaklaştırmadan), hedef ve emrin
   iptal anı (8. ders, Stop uzaklığı ve maliyet).
9. **Emrin bekleme süresinde bir haber saati ya da seans geçişi var mı?** Varsa emri o andan önce çekersin
   (bu derste ölçülmedi).

## Grafik okuma alıştırmaları

**1.** 5 dakikalık EUR/USD grafiğinde, Londra 04:00'te (TSİ İngiltere yaz saatinde 06:00, kış saatinde 07:00) başlayan
bir büyük mum kapandı. Önceki iki saat sakindi, takvimde haber yok, mumun aralığı önceki ATR'nin üç katı kadar ve
kapanış aralığın en üst çeyreğinde (Asya şemasındaki gibi). Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Mum Asya seansında ve ucunda kapandı: 5 dakikanın iki dönemde tutan iki okuması birden. Okuma şudur: kovalamazsın.
Mumun yönünde başka bir gerekçeyle gireceksen geri çekilmeye limit koyarsın ve limit dolarsa geri vermenin başladığı
olayda olduğunu bilirsin. Tersine girmezsin, çünkü ölçülen geri verme yarıya kadardır ve tersine girişin küçük artısı
maliyetten sonra eksidir. İki süzgecin birlikte gelmesi okumayı güçlendirmez; bileşim ölçülmedi. Londra açılışıyla
(Londra 07:00; TSİ İngiltere yaz saatinde 09:00, kış saatinde 10:00) okuma küçülür; bekleyen emri o saatten önce çekersin (7. ders, 5 dakika; 8. ders,
Limit neden ucuz görünür: ters seçim).

</details>

**2.** 1 saatlik GBP/USD grafiğinde günlük trend yukarı (dünkü kapanış EMA20'nin üstünde ve ortalama yükseliyor) ve
Londra seansında yukarı bir büyük mum kapandı. Masadaki biri "trend yönünde ve Londra'da: hedefi uzağa koy" diyor. Ne
yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

1 saatte tersine girmezsin: ortalama yol mumun yönünde. Ama "hedefi uzağa koy" iki tek dönemlik okumaya dayanıyor.
Trend ayrımı yalnız 2018–2023'te görüldü (o dönemde trendle aynı yöndeki mum {{ S.60.trend.trendle.ic.net }} ATR,
trende karşı olan {{ S.60.trend.karsi.ic.net }}); 2024 sonrasında iki taraf aynı yerde ({{ S.60.trend.trendle.dis.net }}
· {{ S.60.trend.karsi.dis.net }}). Londra okumasının aralığı yalnız 2024 sonrasında sıfırın üstünde. İkisi de uyarıdır;
hedefi bunlara dayanarak uzatmazsın (7. ders, 1 saat; 8. ders, 15 dakika ve 1 saat).

</details>

**3.** 5 dakikalık grafikte New York 08:30'da (TSİ ABD yaz saatinde 15:30, kış saatinde 16:30) başlayan mum, ABD
istihdam verisinin mumu. Aralığı önceki ATR'nin altı katı, kapanışı ucunda, seans Londra–New York örtüşmesi (haber mumu
şemasına bak). Kapanış ucunda olduğu için yarıyı beklemeyi düşünüyorsun. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

İlk soru haberdir ve cevabı evet: masadan kalkarsın. Kapanışın yeri, seans ve büyüklük bu mumda okunmaz; "kapanış
ucunda" okumasının haber mumunda da geçerli olup olmadığı bu derste ayrıca ölçülmedi, çünkü iki süzgecin birlikte
ne verdiği yok. Haber mumu az ve dağılımı geniş; 9. dersin haber mumundan seçtiği iki giriş 2024 sonrasında tutmadı.
Bekleyen bir emrin varsa saatten önce çekmiş olman gerekirdi (7. ders, Haber mumu; 9. ders, Seçilen girişler).

</details>

**4.** 5 dakikalık AUD/USD grafiğinde, Londra–New York örtüşmesinde, yarım saat önceki bir büyük mumun ardından aynı
yönde ikinci bir büyük mum kapandı; kapanışı aralığının ortasında, takvimde haber yok (kümelenme şemasındaki gibi). Biri "ikinci
itiş geldi, devam eder" diyor, öbürü "iki büyük mum geldi, akış bitti, tersine girilir" diyor. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Kümelenme süzgeci iki dönemde aynı yöne bakıyor: önceki 4–24 mumda başka büyük mum olan piyasada 24 mum sonraki
ortalama yol mumun tersinde ({{ S.5.ardisik.evet.ic.net }} · {{ S.5.ardisik.evet.dis.net }} ATR). Yani "ikinci itiş
devam eder" okuması bu veride yok ve ikinci mumu kovalamazsın. Ama "akış bitti" de bir tersine işlem gerekçesi değil:
eksi yol ATR'nin onda birkaçı, maliyetten küçük, ve kümenin bir akışın sonu olup olmadığı ölçülmedi. Kapanışın ortada
olması kendi başına bir okuma vermiyor. Masada kalırsın ama işlem yoktur (7. ders, 5 dakika; 8. ders, 5 dakika).

</details>

## Bu sonuç nasıl okunmalı

Süzgeçler hakkında en sık yapılan hata, iyi bir hikâyesi olan bir ayrımı ölçmeden kabul etmektir. "5 ATR'lik mum
aşırıdır, döner" ve "trende karşı büyük mum tuzaktır" cümlelerinin ikisinin de bir mekanizması anlatılabilir. Bu veride
ikisi de tutmadı: büyüklük kovaları dönemden döneme yön değiştiriyor, 1 saatte trende karşı büyük mum da iki dönemde
mumun yönünde gitti. Tutan okumalar daha sıkıcı: kapanışın yeri, Asya seansı ve kümelenme. Hepsi küçük.

## Ölçülmeyenler

- **İkili süzgeçler.** İki süzgecin birlikte uygulandığı bileşimler (ör. Asya ve kapanış ucunda) bu derste yok. Hücre
  sayısı kat kat büyür ve bir dönemde "anlamlı" görünen bileşim sayısı da onunla büyür.
- **Pariteye göre ayrım.** Tablolar dört paritenin toplamıdır.
- **Haberin içeriği.** Haber mumu yalnız "var/yok"; beklentiye göre sürpriz ölçülmedi.
