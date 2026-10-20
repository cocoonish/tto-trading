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

## 15 dakika

{{# suzgec 15 kapanis seans trend kova }}

15 dakikada yalnız Asya seansı iki ölçüde iki dönemde aynı yöne bakıyor: ±1 ATR'den önce mumun yönündeki seviye
{{ S.15.seans.asya.ic.sim }} ve {{ S.15.seans.asya.dis.sim }}, yarısına dönüş aynadan {{ S.15.seans.asya.ic.geri_fark }}
ve {{ S.15.seans.asya.dis.geri_fark }} puan sık. 24 mum sonraki yolun işareti ise dönemden döneme değişiyor
({{ S.15.seans.asya.ic.net }} · {{ S.15.seans.asya.dis.net }} ATR). Öbür hücrelerde büyük sayılar var (3–4 ATR'lik mum
2018–2023'te 24 mumda {{ S.15.kova.3-4.ic.net }} ATR, 2024 sonrasında {{ S.15.kova.3-4.dis.net }}), ama aynı işaret öbür
dönemde ya kayboluyor ya da aralık sıfırı rahatça kapsıyor.

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
