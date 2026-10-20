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

Süzgeçler kapanışta bilinir. Sıra önemlidir: haber okumayı kapatır, dilim yönü değiştirir. İki dönemde aynı yöne bakan
fark okumadır, tek dönemde görülen uyarıdır, hiç ayırmayan süzgeç okunmaz.

{{# karar sira }}

Merdivenin en altına inen bir mumun kalan okuması 6. dersin ortalamasıdır ve o ortalama da maliyetin altındadır
(6. ders, Dilim dilim okuma).

## Dokuz süzgeç

Her süzgeç büyük mum kapandığı anda bilinir; hiçbiri mumdan sonraki fiyatı kullanmaz.

- **Büyüklük.** Mumun aralığı önceki ATR'nin kaç katı: 2–3, 3–4, 4–5, 5 ve üstü.
- **Kapanışın yeri.** Kapanış mumun yönündeki ucuna ne kadar yakın: aralığın son çeyreğinde ("uca yakın"), son yarısının
  geri kalanında ("ortada") ya da yarısının gerisinde ("geri verilmiş", uzun fitil).
- **Seans.** Mumun başladığı saat, Londra ve New York saatiyle tanımlı. TSİ karşılıkları ikisi yaz saatindeyken
  verildi; ikisi kış saatindeyken bir saat sonradır, ara haftalarda sınırlardan biri bir saat kayar. **Asya**: New York 17:00 ile Londra 07:00 arası (TSİ
  00:00–09:00). **Londra**: Londra 07:00 – New York 08:00 (TSİ 09:00–15:00). **Örtüşme**:
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

**Kapanış ucundaysa geri verme.** Kapanışı ucuna yakın büyük mum yarısına aynadan sık dönüyor (nedeni bu derste
ölçülmedi). Ölçülen şey mumun yarısına kadar geri çekilmenin aynadan sık gelmesidir;
mumun öbür ucuna dönüş değil. Fitili uzun, kapanışı yarısının gerisinde kalan mumda yarısına dönüş ölçüsü anlamsızdır: kapanış zaten
yarının gerisinde olduğu için gerçek yol da ayna da yarıya "dönmüş" sayılır. O mumun 24 mum sonraki yolu iki dönemde de
eksi ({{ S.5.kapanis.geri.ic.net }} · {{ S.5.kapanis.geri.dis.net }} ATR), yani hafif geri verme orada da sürüyor.

**Asya'da geri verme belirgin, Londra'da küçük.** Asya seansında ±1 ATR'den önce tersindeki seviye daha sık görülüyor ve
yarısına dönüş aynadan belirgin sık ({{ S.5.seans.asya.ic.geri_fark }} · {{ S.5.seans.asya.dis.geri_fark }} puan);
ince likiditenin payı ölçülmedi. Londra seansında aynı ölçüler yarı yarıya küçük (yarısına dönüş aynadan {{ S.5.seans.londra.ic.geri_fark }} ·
{{ S.5.seans.londra.dis.geri_fark }} puan sık) ve 24 mum sonraki yol sıfırın yakınında.

**Kümelenme geri vermeyi büyütüyor.** Önceki 4–24 mumda başka büyük mum varsa 24 mum sonraki ortalama yol iki dönemde de
eksi ve aralığı sıfırın altında. Arka arkaya gelen büyük mumların bir haberin ya da bir akışın sonu olup olmadığı ayrıca
ölçülmedi.

Büyüklük kovaları iki dönemde aynı yöne bakmıyor: 4–5 ATR'lik mum 2018–2023'te belirgin geri verdi, 2024 sonrasında
vermedi. "Mum ne kadar büyükse dönüş o kadar yakın" okuması bu veride yok.

### Masada: Asya'da ve ucunda kapanan mum

İki süzgeç ekranda aynı resmi verir: dar mumların arasından çıkan, uç çeyrekte kapanan uzun gövdeli mum. Kovalayan
biri biraz daha sık geri çekilmenin içine girer; yarıya dönüş öbür uca dönüş değildir ve 24 mum sonraki yol ATR'nin
onda birkaçıdır.

{{# sema asya-uc }}

{{# kart asya-uc }}

{{# ornek asya-uc }}

İkisi de Asya'da, haber yokken ucunda kapanmış aşağı yönlü büyük mumdur. Üstteki ① TSİ 08:00'de (Londra 05:00), bir
saatlik düşüşün sonunda geldi (2–3 ATR). Fiyat sonraki dört mumda ucun ötesine indi, TSİ 08:26'da ② yarıya döndü (③),
yeniden ucun ötesine indi ve TSİ 09:45'te öbür ucu kırdı; ④'te mumun tersindeydi. Yarıdaki satış limiti TSİ 08:25
mumunda doldu; stopu 2 ATR olan işlem 1 R hedefini TSİ 08:40'ta gördü, 2 R hedefiyle TSİ 09:45'te stopa gitti. Alttaki
① TSİ 02:00'de (Londra 23:00, önceki gün) dar mumların arasından çıktı (4–5 ATR). Fiyat yarıya hiç gelmedi (③ yok) ve
④'te ucun mum boyunun birkaç katı ötesindeydi; çeyrekteki limit ilk mumda doldu ve iki hedefi de gördü, yarıdaki limit
dolmadı. Limitin derinliği hangi olayların işlem olacağını seçer; tek gün kuralı ne doğrular ne yanlışlar (8. ders,
Limit neden ucuz görünür: ters seçim).

### Masada: arka arkaya büyük mum

Sezgi ikinci büyük mumu "ikinci itiş" diye okur; bu veride iki dönemde de tersi görüldü, nedeni ölçülmedi.

{{# sema kume }}

{{# kart kume }}

## 15 dakika

{{# suzgec 15 kapanis seans trend kova }}

15 dakikada yalnız Asya seansı iki ölçüde iki dönemde aynı yöne bakıyor: ±1 ATR'den önce mumun yönündeki seviye
{{ S.15.seans.asya.ic.sim }} ve {{ S.15.seans.asya.dis.sim }}, yarısına dönüş aynadan {{ S.15.seans.asya.ic.geri_fark }}
ve {{ S.15.seans.asya.dis.geri_fark }} puan sık. 24 mum sonraki yolun işareti ise dönemden döneme değişiyor
({{ S.15.seans.asya.ic.net }} · {{ S.15.seans.asya.dis.net }} ATR). Öbür hücrelerde büyük sayılar var (3–4 ATR'lik mum
2018–2023'te 24 mumda {{ S.15.kova.3-4.ic.net }} ATR, 2024 sonrasında {{ S.15.kova.3-4.dis.net }}), ama aynı işaret öbür
dönemde ya kayboluyor ya da aralık sıfırı rahatça kapsıyor.

### Masada: 15 dakikada süzgeç az şey söyler

15 dakika en okunaklı dilim gibi görünür, ama okuma çıkan tek süzgeç Asya'dır ve orada da 24 mum sonraki yolun işareti
değişir.

{{# kart on-bes }}

## 1 saat

{{# suzgec 60 trend kapanis kosu seans gun_ucu }}

1 saatte ortalama yol mumun yönünde: 2018–2023'te aralığıyla ({{ D.60.ic.net_24 }} ATR, {{ Y.95 }} aralık
{{ D.60.ic.net_24_alt }} … {{ D.60.ic.net_24_ust }}), 2024 sonrasında yalnız nokta tahmini olarak
({{ D.60.dis.net_24 }}; {{ D.60.dis.net_24_alt }} … {{ D.60.dis.net_24_ust }}). Süzgeçlerin çoğu bunu değiştirmiyor; üç
okuma dikkat çekiyor.

**Trendin yönündeki büyük mum: yalnız bir dönemde.** Günlük trendle aynı yöndeki 1 saatlik büyük mum 2018–2023'te 24
saatte ortalama {{ S.60.trend.trendle.ic.net }} ATR yol aldı ({{ Y.95 }} aralık {{ S.60.trend.trendle.ic.net_alt }} …
{{ S.60.trend.trendle.ic.net_ust }}), trende karşı olan {{ S.60.trend.karsi.ic.net }}. 2024 → döneminde iki taraf aynı
yerde ({{ S.60.trend.trendle.dis.net }} · {{ S.60.trend.karsi.dis.net }}). Trendin yatay olduğu günlerde devam iki
dönemde de kayboluyor ({{ S.60.trend.yatay.ic.net }} · {{ S.60.trend.yatay.dis.net }}).

**Londra seansı.** Londra seansında başlayan 1 saatlik büyük mum iki dönemde de mumun yönünde gitti
({{ S.60.seans.londra.ic.net }} · {{ S.60.seans.londra.dis.net }} ATR). 2018–2023'te aralık sıfıra değiyor
({{ S.60.seans.londra.ic.net_alt }} … {{ S.60.seans.londra.ic.net_ust }}), 2024 sonrasında sıfırın üstünde. Günün
yeni ucunu yapmayan büyük mum aynı durumda: iki dönemde artı ({{ S.60.gun_ucu.hayir.ic.net }} ·
{{ S.60.gun_ucu.hayir.dis.net }} ATR), aralığı yalnız 2024 sonrasında sıfırın üstünde. Trend okuması gibi bunlar da tek
bir dönemde aralığıyla tutuyor; yetmiş sekiz hücrenin içinden birkaçının tek dönemde böyle görünmesi beklenen şeydir.

**Fitili uzun büyük mum.** Kapanışı yarısının gerisinde kalan 1 saatlik büyük mum 24 saatte eksi kaldı
({{ S.60.kapanis.geri.ic.net }}; 2024 → {{ S.60.kapanis.geri.dis.net }}), öbür kapanışlarda artı. Olay az ve aralıklar
geniş, ama işaret iki dönemde aynı.

9. dersin seçtiği iki 1 saatlik girişten birinin dayandığı süzgeç "mumdan önceki 12 mum"dur; tablodaki satırları, o
süzgecin 24 mumluk yolu kendi başına ayırmadığını gösteriyor.

{{# sekil 02_yarisi "Fiyat önce hangi yöne gidiyor" }}

### Masada: trendin yönündeki saatlik mum

"Trend yönünde, devam eder" okuması yalnız 2018–2023'te görüldü, yani bir uyarıdır. 1 saatte tersine girmenin dayanağı
yok; mumun yönündeki ortalama yol da 2024 sonrasında yalnız nokta tahmini, yani o da uyarıdır (6. ders, Dilim dilim
okuma). Süzgeç ekrandaki mumlara değil bir önceki günün
kapanışına ve EMA20'ye bakar.

{{# sema saat-trend }}

{{# kart saat-trend }}

{{# ornek saat-trend }}

İkisi de günlük trendin yönünde, haber yokken ucunda kapanmış ve önceki birkaç saatin hareketini tersine çeviren 1
saatlik büyük mumdur. Üstteki ① aşağı yönlü, Londra seansında (TSİ 11:00, Londra 09:00): fiyat yarıya hiç dönmedi (③
yok) ve ertesi gün TSİ 12:00'deki ④'te ucun mum boyunun birkaç katı ötesindeydi. Alttaki ① yukarı yönlü, örtüşme
seansında (TSİ 16:00, New York 08:00): fiyat bir saat daha yükseldi, TSİ 21:00 mumunda ② yarıya döndü (③) ve aynı mumda
öbür ucu kırdı; ertesi gün TSİ 17:00'deki ④'te öbür ucun hemen üstündeydi. İki gün de trend ayrımının görüldüğü
2018–2023'ten; tek gün kuralı ne doğrular ne yanlışlar.

## Haber mumu

Takvimdeki büyük bir haberin (ABD istihdam ve enflasyon verisi, Fed, ECB, BoE kararı) saati mumun içine düşüyorsa, bu
dersin öbür süzgeçleri o mumda okunmaz. 5 dakikada 2018–2023'te {{ S.5.haber.haber.ic.n }} olay var, büyük mumların
küçük bir parçası, ve 24 mum sonraki yolun aralığı sıfırın iki yanına geniş açılıyor; okuma tablosunda bu satır
"ölçülemiyor" diye durur. 9. dersin seçim kuralı iki girişini tam buradan, haber mumunu ucundan tersine alan
limitlerden seçti ve ikisi de 2024 sonrasında tutmadı (9. ders, Seçilen girişler). Küçük bir alt küme, şansın en kolay
şişirdiği yerdir. Haber anlarının ilk mumunu kendi tanımıyla ayrı ölçen ders 4. derstir ve orada da haber mumu tek
başına bir yön sinyali değildir (4. ders, Plan tek cümlede).

### Masada: masadan kalkış

Kalkış haber saatinden önce başlar (masa uygulaması; ölçülmedi); saatler kontrol listesinin 2. maddesinde. 1 saatte
haber saatini içeren bütün saatlik mum haber mumudur.

{{# sema haber-kalk }}

{{# kart haber }}

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

Fade, mumun tersine girmektir (6. ders, Bu sonuç nasıl okunmalı). Bu dersin hiçbir okuması fade'i desteklemiyor;
tersine girmenin 5 dakikadaki küçük artısı maliyetten sonra eksidir (8. ders, 5 dakika). Masadaki asıl seçim "kovalar
mıyım, beklerim mi, kalkar mıyım"dır. Tablonun "iki dönemde aynı yönde" satırları kovalamamayı söyler (15 dakikada
Asya'da yalnız yarıya dönüşün sıklığını, yön değil); "yalnız 2018–2023'te" ve "aralık yalnız 2024 sonrasında"
satırları uyarıdır; "ayrım yok" ve "ölçülemiyor" satırları kalkmayı söyler. 1 saatte bütün büyük mumlar için de aynı
uyarı geçerli: tersine girmezsin, mumun yönünü de kenar sanmazsın.

## İyi hikâyesi olan süzgeç: masadaki tuzak

Üç hikâye sık anlatılır ve üçü de tutmadı: "beş ATR'lik mum döner" (büyüklük kovaları iki dönemde aynı yöne bakmıyor),
"trende karşı büyük mum tuzaktır" ve "günün yeni ucunu yapan mum tükenmiştir" (1 saatte ikisi de iki dönemde mumun
yönünde gitti) (7. ders, 5 dakika; 7. ders, 1 saat).

{{# sema asiri }}

Yetmiş sekiz hücrede birkaçının tek dönemde anlamlı görünmesi şanstan beklenir; hikâyeyi kurala çeviren tek şey ikinci
dönemdir.

## Emri nereye koyarsın

Emir biçimlerinin ölçülmüş sonuçları 8. dersin aynı adlı bölümündedir (8. ders, Emri nereye koyarsın); süzgeç emrin
biçimini ve yerini değiştirir, beklenen sonucunu değiştirmez. Bu dersin ekledikleri:

- **Giriş.** 5 dakikada ucunda kapanan ya da Asya'daki büyük mumda kapanışta piyasa emriyle girmezsin; mumun yönünde
  gireceksen limit çeyrek ya da yarı geri çekilmeye konur. Tutan süzgeçler geri çekilmenin sık geldiği yerleri
  gösterir; oralarda limit sık dolar ve dolması iyi haber değildir (8. ders, Limit neden ucuz görünür: ters seçim). 1
  saatte tersine girişler 2018–2023'te maliyetten önce de eksiydi, 2024 sonrasında sıfır çevresinde.
- **Stop.** Girişten (limitle giriyorsan limitin fiyatından) 2 ATR; ölçülen stoplar 1 ve 2 ATR. Mumun öbür ucunun
  ötesine konan stop bu seride ölçülmedi; 2–3 ATR'lik mumda o yer girişe 1 ATR kadar yakındır (8. ders, Stop uzaklığı
  ve maliyet). Asya'da dar ATR'nin makası R cinsinden büyütüp büyütmediği ölçülmedi.
- **Hedef.** 1 ya da 2 R; trend ya da Londra okumasına dayanarak uzatmazsın. 1 saatte hedefi 2 R olan geri çekilme
  limitleri ızgaranın sıfıra en yakın hücreleridir (2018–2023'te {{ G.60.ic.devam:limit_0.25:s2:h2.R }} ve
  {{ G.60.ic.devam:limit_0.5:s2:h2.R }} R, 2024 sonrasında {{ G.60.dis.devam:limit_0.25:s2:h2.R }} ve
  {{ G.60.dis.devam:limit_0.5:s2:h2.R }} R); büyüklükleri sıfırdan ayırt edilemez (8. ders, 15 dakika ve 1 saat).
- **Emrin ömrü.** Altı mum; dolmazsa çekilir. Süreye seans geçişi (Londra 07:00; TSİ İngiltere yaz saatinde 09:00, kış
  saatinde 10:00) ya da takvimdeki büyük haberin penceresi (açıklamadan iki dakika önce – on beş dakika sonra) düşüyorsa
  emri o andan önce çekersin: ölçülmemiş bir ek kural, bir disiplin kuralı. O pencerede piyasa ve stop emirlerine
  {{ ON.haber_kayma_pip }} pip ek kayma varsayıldı (8. dersin açılış paragrafı, maliyet varsayımı); haber anındaki makas
  ve emri çekmenin etkisi ölçülmedi.

## Sık yapılan hatalar

- **Süzgeçleri üst üste yığmak.** "Asya, ucunda kapanış ve kümelenme birlikte geldiyse daha güçlüdür" ölçülmedi; iki
  süzgeçli bileşimler bu derste yok ve küçük alt kümeler şansın en kolay şişirdiği yerdir (7. ders, Ölçülmeyenler;
  9. ders, Seçilen girişler).
- **5 dakikanın okumasını 1 saate taşımak.** 5 dakikada hafif geri verme, 1 saatte hafif devam var; 1 saatte Asya'nın
  işareti dönemden döneme değişiyor (6. ders, Dilim dilim okuma; 7. ders, 1 saat).

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
5. **Mum Asya seansında mı başladı?** Asya: New York 17:00 ile Londra 07:00 arası (TSİ ikisi yaz saatindeyken
   00:00–09:00, ikisi kış saatindeyken 01:00–10:00). 5 dakikada Asya'ysa kovalamazsın; 15 dakikada yarıya dönüş
   aynadan sık, 24 mumda yön yok (7. ders, 5 dakika; 7. ders, 15 dakika).
6. **Önceki 4–24 mumda başka büyük mum var mı?** 5 dakikada yaklaşık yirmi dakika ile iki saat geriye bakarsın; varsa
   ikinci mumu kovalamazsın (7. ders, 5 dakika).
7. **Okuman iki dönemde tutan bir süzgece mi dayanıyor?** Büyüklük ya da oynaklıksa okuma yok; 1 saatte trend ya da
   Londra ise yalnız uyarı (7. ders, Fade mi, devam mı: okuma tablosu).
8. **Gireceksen emir yazılı mı?** Emrin türü, stopun girişten uzaklığı (2 ATR; bir ATR'ye yaklaştırmadan), hedef ve
   emrin iptal anı (altı mum) (8. ders, Stop uzaklığı ve maliyet).
9. **Emrin altı mumluk süresine bir haber penceresi ya da seans geçişi düşüyor mu?** Düşüyorsa emri o andan önce
   çekersin; disiplin kuralıdır, etkisi ölçülmedi (7. ders, Emri nereye koyarsın).

## Grafik okuma alıştırmaları

**1.** 5 dakikalık EUR/USD grafiğinde, Londra 04:00'te (TSİ İngiltere yaz saatinde 06:00, kış saatinde 07:00) başlayan
bir büyük mum kapandı. Önceki iki saat sakindi, takvimde haber yok, mumun aralığı önceki ATR'nin üç katı kadar ve
kapanış aralığın en üst çeyreğinde (Asya şemasındaki gibi). Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Mum Asya seansında ve ucunda kapandı: 5 dakikanın iki dönemde tutan iki okuması birden. Okuma şudur: kovalamazsın.
Mumun yönünde başka bir gerekçeyle gireceksen limiti çeyrek ya da yarı geri çekilmeye koyarsın; limit dolarsa fiyatın
geri çekildiği olaydasın ve bu olaylarda piyasa girişi çoğunlukla kaybederdi. Tersine girmezsin, çünkü ölçülen geri
çekilme yarıya kadardır ve tersine girişin küçük artısı maliyetten sonra eksidir. İki süzgecin birlikte gelmesi
okumayı güçlendirmez; bileşim ölçülmedi. Emir altı mum (yarım saat) bekler ve Londra açılışından (Londra 07:00; TSİ
İngiltere yaz saatinde 09:00, kış saatinde 10:00) çok önce düşer; dolmazsa çekersin (7. ders, 5 dakika; 8. ders,
Limit neden ucuz görünür: ters seçim).

</details>

**2.** 1 saatlik GBP/USD grafiğinde günlük trend yukarı (dünkü kapanış EMA20'nin üstünde ve ortalama yükseliyor) ve
Londra seansında yukarı bir büyük mum kapandı. Masadaki biri "trend yönünde ve Londra'da: hedefi uzağa koy" diyor. Ne
yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

1 saatte tersine girmezsin: ortalama yol mumun yönünde (2024 sonrasında yalnız nokta tahmini). Ama "hedefi uzağa koy" iki tek dönemlik okumaya dayanıyor.
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
Süresine bu pencere düşen bekleyen bir emrin varsa onu açıklamadan önce çekersin; bu bir disiplin kuralıdır, etkisi
ölçülmedi (7. ders, Haber mumu; 9. ders, Seçilen girişler).

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

İyi hikâyesi olan ayrımlar ("5 ATR'lik mum döner", "trende karşı büyük mum tuzaktır") bu veride tutmadı; tutan okumalar
daha sıkıcı ve hepsi küçük: kapanışın yeri, Asya seansı, kümelenme.

## Ölçülmeyenler

- **İkili süzgeçler.** İki süzgecin birlikte uygulandığı bileşimler (ör. Asya ve kapanış ucunda) bu derste yok. Hücre
  sayısı kat kat büyür ve bir dönemde "anlamlı" görünen bileşim sayısı da onunla büyür.
- **Pariteye göre ayrım.** Tablolar dört paritenin toplamıdır.
- **Haberin içeriği.** Haber mumu yalnız "var/yok"; beklentiye göre sürpriz ölçülmedi.
