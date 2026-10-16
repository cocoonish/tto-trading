---
title: 'FX Gün İçi Stratejiler 1: Giriş — Veri, Saat, İşlem Mekaniği ve Sonuçların Okunuşu'
description: "Dört majör paritede (EUR/USD, GBP/USD, USD/JPY, AUD/USD) kural tabanlı gün içi stratejilerin sınandığı ders serisinin giriş dersi: 1 dakikalık bid/ask verisi ve denetimi, Londra–New York–TSİ saat haritası ve saat değişimi haftaları, sinyalden girişe ve çıkışa işlem mekaniği, maliyet, R birimi ve bir stratejinin 'çalışıyor' ya da 'çalışmıyor' hükmünün neye göre verildiği."
pubDate: 2026-10-16
tags: ['fx', 'gun-ici', 'backtest', 'strateji', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · BLS, Fed, ECB, BoE resmî takvimleri · önceden kayıt'
ozet: "Serinin bütün derslerinin dayandığı makineyi anlatır: veri nereden geliyor ve ne kadar temiz, saatler TSİ'de nereye düşüyor, bir işlem nasıl açılıp kapanıyor, maliyet nasıl ölçülüyor ve bir stratejiye 'çalışıyor' demek için hangi üç şartın birlikte tutması gerekiyor."
seviye: 'giris'
---

Bu seri, profesyonel FX masalarında adı sıkça geçen gün içi stratejileri tek bir makineyle sınar: Londra açılış
aralığı kırılımı, Asya aralığı, New York'un ilk dengesi, iç mum ve sıkışma kırılımları, önceki günün tepe ve dibi,
başarısız kırılımlar, VWAP, taban pivotları, WM/R 16:00 fiksingi, gün içi momentum ve beş haber stratejisi. Her
strateji aynı veriyle, aynı maliyetle, aynı yürütme kurallarıyla ve sonuç görülmeden yazılmış aynı hüküm kuralıyla
ölçülür. Amaç bir stratejiyi önermek değil; bir stratejinin ne olduğunu, nasıl kullanıldığını, ne kadar iyi
çalıştığını ve ne zaman çalışmadığını göstermektir. Çalışmayan stratejiye çalışmıyor denir.

Bu ders makinenin kendisidir. Sonraki dersler buradaki tanımları tekrar etmez: bir strateji dersinde "net R",
"örneklem dışı" ya da "rastgele yön yüzdeliği" geçtiğinde tanımı buradadır.

## Serinin haritası

| Ders | Konu | Stratejiler |
| :--- | :--- | :--- |
| 1 · Giriş | veri, saat, işlem mekaniği, sonuçların okunuşu | — |
| 2 · Seans kırılımları | bir seansın açılış aralığının kırılması | Londra açılış aralığı, Asya aralığı, New York ilk dengesi (08:00 ve 09:30) |
| 3 · Yapı kırılımları | bir fiyat yapısının ya da seviyenin kırılması | iç mum, Bollinger–Keltner sıkışması, önceki gün tepe/dip, pivot kırılımı |
| 4 · Fade | kırılımın tersine, ortalamaya dönüş | başarısız kırılım (üç seviye), VWAP'a dönüş, pivot dönüşü, fiksing dönüşü |
| 5 · Haber | veri ve merkez bankası kararı anında | N1–N5, kırılım ↔ fade devam tablosu, FOMC karar ↔ basın toplantısı |
| 6 · Akış | gün içi akışın yönü | fiksing momentumu, gün içi momentum, VWAP geri çekilmesi |
| 7 · Karşılaştırma | stratejiler yan yana | sonuç, maliyet, ilinti, hangisi ne zaman |
| 8 · Metodoloji | sınamanın kendisi | önceden kayıt, seçim, sağlamlık, veri ve takvim denetimi, ölçülmeyenler |

Her strateji dersi aynı sırayla yazılır: **ne** (kuralın adı ve fikri), **piyasa mantığı** (neden çalışması
beklenir, neden çalışmayabilir), **kurallar** (ölçülen kural, harfiyen), **örnekler** (iki gerçek gün), **sonuçlar**,
**koşullar** (hangi günlerde daha iyi), **kontrol listesi** ve **hüküm**.

## Veri

Fiyatlar Dukascopy'nin halka açık 1 dakikalık mumlarıdır: her dakika için ayrı ayrı **bid** (alış kotasyonu) ve
**ask** (satış kotasyonu) açılış, en yüksek, en düşük ve kapanış. Dönem {{ K.baslangic | tarih }} →
{{ K.bitis | tarih }}, pariteler EUR/USD, GBP/USD, USD/JPY ve AUD/USD. İki fiyattan iki türev kurulur: **orta
fiyat** (bid ile ask'ın ortalaması; sinyaller ondan okunur) ve **makas** (ask − bid; işlemin maliyetinin bir
parçası). Sinyalin orta fiyattan, yürütmenin bid/ask'tan yapılması bilinçlidir: piyasa orta fiyatla işlem yapmaz,
alış ask'tan, satış bid'den dolar.

Arşivin her dakikası indirildikten sonra denetlenir: işlem günlerinin kapsamı (eksik dakikalar ve boşlukların
uzunluğu), tatiller, sıfır ya da eksi makas, sıçrama adayları (ertesi dakika geri dönen olağandışı hareketler) ve
Dukascopy'nin kendi saatlik mumlarıyla çapraz sınama. Veri değiştirilmez; denetim sonucu yazılır.

{{! veri }}

_Kapsam: hafta içi normal günlerde kotasyonu olan dakikaların payı. Tatil: kapsamı %50'nin altında kalan işlem günü
(Noel, yılbaşı). Sıçrama adayı yalnız sayılır, veriden çıkarılmaz. Çapraz sınama: dakika arşivinden kurulan saatlik
mumların Dukascopy'nin kendi saatlik dosyalarıyla birebir eşitlik oranı._

{{! sekil veri-makas "Makas ve hacim — saat saat" }}

Makas gün içinde sabit değildir. New York 17:00'de (FX gününün kapanışı) likidite sağlayıcılar pozisyonlarını bir
sonraki güne devrederken makas birkaç katına açılır; bu yüzden bu serideki bütün işlemler en geç 16:55 New York'ta
kapatılır. Haber dakikalarında da makas açılır. {{! haber_makas_cumle }} Olay olay tablosu ve dört paritenin
karşılaştırması haber dersinde.

**Hacim üzerine bir uyarı.** FX'te merkezî bir borsa ve merkezî bir işlem hacmi yoktur. Dukascopy'nin mumlarındaki
"hacim", kendi platformundaki kotasyonların en iyi fiyattaki likidite miktarıdır, gerçekleşmiş işlem hacmi değildir.
VWAP stratejileri bu hacmi ağırlık olarak kullanır ve derste bu sınır açıkça yazılır.

## Saat

Arşiv UTC'de tutulur ve bütün seans saatleri yerel saatlerinden (Londra, New York, Tokyo, Frankfurt) `zoneinfo`
saat dilimi kurallarıyla hesaplanır; hiçbir saat elle kaydırılmaz. **FX işlem günü** New York 17:00'de başlar ve ertesi
gün 17:00'de biter: pazartesinin işlem günü pazar akşamı 17:00 New York'ta açılır. Derslerde bütün saatler ayrıca
**TSİ** olarak yazılır. Türkiye 2016'dan beri yıl boyu UTC+3'tür ve saat değiştirmez; bu yüzden Londra ya da New York
saat değiştirdiğinde onların TSİ karşılığı kayar.

Avrupa ile ABD saati aynı gün değiştirmez: ABD mart ayının ikinci pazarı ileri, kasımın ilk pazarı geri alır;
Avrupa mart ve ekimin son pazarı. Aradaki birkaç hafta Londra ile New York arasındaki fark beş değil dört saattir.
Dört rejimde olayların TSİ saati:

{{! zaman }}

Ara dönemler, yıl yıl:

{{! dst }}

İki pratik sonuç var. Birincisi takvim: bir olayın TSİ saati yalnız kendi şehrinin saatine bağlıdır. Londra
açılışı İngiltere yaz saatindeyken 10:00, değilken 11:00; ABD verisi ABD yaz saatindeyken 15:30, değilken 16:30.
Ara dönemde ikisi farklı rejimdedir ve iki ara dönemde de aynı şey olur: Londra açılışı 11:00'de, ABD verisi
15:30'da — Londra ile New York arasındaki fark bir saat kısalır. İkincisi ölçü: saat değişimi haftası ve ara dönemin kendisi koşul analizinde ayrı birer
değişkendir; bir stratejinin bu haftalarda farklı davranıp davranmadığı her strateji dersinde ayrıca sorulur.

## İşlem mekaniği

Bütün stratejiler aynı yürütme kurallarıyla koşar. Kuralların her biri bir yanılgıyı engellemek için oradadır.

**Sinyal mumun kapanışında, giriş sonraki dakikada.** Bir sinyal ancak mumu kapandıktan sonra bilinir. Giriş
sinyal mumundan sonraki ilk dakikanın açılışında yapılır; bir mumun içinde "fiyat aralığı geçti, hemen girdim"
türünden bir giriş yoktur. Bu kural kodda bir sınamayla korunur: girişi sinyal mumunun kapanışından önceye düşen tek
bir işlem bile koşuyu durdurur. Ayrıca her strateji iki ayrı geleceğe bakmama sınamasından geçer (veriyi bir anda
kesip ya da o andan sonrasını değiştirip, kesimden önceki sinyallerin değişmediği sınanır).

**Yürütülebilir fiyat.** Alış ask'tan, satış bid'den dolar; dolum başına ayrıca **kayma** eklenir (temel senaryoda
{{ K.temel_kayma_pip | s1 }} pip). Haber penceresinde (olaydan önceki iki dakikadan sonraki on beş dakikaya
kadar){{? K.haber_pencere_dk[0] == -2 and K.haber_pencere_dk[1] == 15 }} ek {{ K.haber_kayma_pip | s1 }} pip kayma eklenir.

**Stop.** "Sert" stop emir tarafında dakika dakika izlenir (alışta bid stop seviyesine değdiğinde dolar). "Kapanış"
stop'u yalnız mumun orta fiyattan kapanışı stop'un ötesindeyse tetiklenir ve bir sonraki mumun açılışında doldurulur.
Bir veri boşluğundan sonra fiyat stop'un ötesinde açılırsa dolum açılış fiyatındadır (boşlukla stop); hedefte de aynı.

**Hedef.** Limit emirdir ve kaymaz: hedef seviyesine değen dakika hedefte doldurur. Aynı dakikada hem stop hem hedef
değerse **stop sayılır**: dakikanın içinde hangisinin önce geldiği 1 dakikalık veriden bilinemez ve belirsizlikte
iyimser seçim yapılmaz.

**Gün sonu.** Açık pozisyon en geç {{ K.gun_sonu_et | t }} New York'ta (TSİ yazın 23:55, kışın 00:55) kapatılır; gece
pozisyon taşınmaz.

**Tek pozisyon.** Bir strateji aynı paritede aynı anda en çok bir pozisyon taşır.

**R birimi.** Her işlemin sonucu pip olarak ve **R** olarak yazılır. 1R, işlemin planlanan riskidir: yürütülen
giriş fiyatından stop seviyesine uzaklık. +2R, riskin iki katı kazanç demektir. R paritelerin pip değerlerinden ve
oynaklıklarından bağımsızdır; dört paritenin sonuçları ancak R ile toplanabilir. Stop'u olmayan stratejilerde
(fiksing, gün içi momentum) R birimi girişteki ATR'dir (son on dört mumun ortalama gerçek aralığı).

<div class="pratik">
  <span class="etiket">Pratik — işlem mekaniği</span>

{{! pratik_islem orb "Alıştırma 1" }}

{{! pratik_islem vwap_donus "Alıştırma 2" }}

</div>

## Maliyet

Bir işlemin maliyeti iki parçadır: girişte ve çıkışta ödenen **makas** (gerçek bid/ask'tan, dakika dakika) ve
**kayma** (makasın ötesinde kötüleşen dolum). Makas veriden gelir; kayma bir varsayımdır ve dört kademede ölçülür:
dolum başına {{ K.kayma_pip[0] | s1 }}, {{ K.kayma_pip[1] | s1 }}, {{ K.kayma_pip[2] | s1 }} ve
{{ K.kayma_pip[3] | s1 }} pip. Her strateji dersinin maliyet tablosu dört kademede net sonucu verir; **başabaş
kayma** net sonucun sıfıra indiği kaymadır. Başabaş kayma yarım pipin altındaysa kuralın kenarı (varsa) bir kurumsal
masanın bile yürütme maliyetine sığmaz.

Aynı işlem iki ayrı sayı taşır: **brüt** (orta fiyattan orta fiyata, maliyetsiz) ve **net** (yürütülebilir
fiyatlarla, makas ve kayma dahil). Brüt sonuç kuralın bir şey yakalayıp yakalamadığını, net sonuç bundan para
kalıp kalmadığını söyler. İkisi arasındaki fark, kısa işlemlerde ve yakın stop'larda büyür.

## Sonuçların okunuşu

**Örneklem içi ve dışı.** Dönem ikiye bölünür: {{ K.baslangic | tarih }} → {{ K.ic_bitis | tarih }} örneklem içi,
{{ K.dis_baslangic | tarih }} → {{ K.bitis | tarih }} örneklem dışı. Parametre seçimi yalnız örneklem içinde yapılır;
örneklem dışı yalnız sınar. Bir stratejinin geçmişe iyi uyması kolaydır; asıl soru seçimden sonra gelen veride ne
yaptığıdır.

**Önceden kayıtlı varsayılan ve seçilen.** Her stratejinin parametre ızgarası ve "ders kitabı" varsayılanı hiçbir
sonuç görülmeden yazılıp kayda geçirildi (metodoloji dersinde tarihçesiyle). İki sonuç birlikte raporlanır:
**varsayılan** (veriye hiç bakmadan seçilmiş; bütün dönem onun için örneklem dışıdır) ve **seçilen** (ızgaradan
yalnız örneklem içinde, en yüksek günlük Sharpe'la, en az {{ K.secim.asgari_islem | n }} işlem şartıyla seçilmiş).
Hüküm varsayılan üzerinden verilir.

**Hüküm kuralı.** Bir stratejiye bir paritede "çalışıyor" demek için üç şartın birlikte tutması gerekir:
1. örneklem dışında işlem başına net ortalama R sıfırın üstünde;
2. bu ortalamanın %95 güven aralığının alt ucu da sıfırın üstünde (aralık, işlemlerin
   {{ K.hukum_kurali.bootstrap_tekrar | n }} kez yeniden örneklenmesiyle);
3. **rastgele yön sınamasında** stratejinin sonucu, dağılımın {{ K.hukum_kurali.rastgele_esik_yuzdelik | n }}.
   yüzdeliğinin üstünde.

Ortalama artı ama öbür şartlardan biri tutmuyorsa hüküm **zayıf**; ortalama sıfır ya da eksiyse **çalışmıyor**.
Ayrıca bir bayrak var: brüt sonucun aralığı sıfırın üstünde ama net sonuç eksiyse **maliyet yiyor** — kuralın bir
kenarı olabilir ama makası ödemeye yetmiyor.

**Rastgele yön sınaması.** Stratejinin işlemleri aynı giriş ve çıkış dakikalarında, yönü yazı turayla seçilerek
{{ K.hukum_kurali.rastgele_tekrar | n }} kez yeniden koşturulur. Gün içi stratejilerin çoğu saatini seçerek bir şey
kazanır: hareketin olduğu saatte piyasadadır. Bu sınama "yön bilgisi mi kazandırıyor, yoksa yalnız zamanlama mı"
sorusunu ayırır: yazı turayla aynı saatte girmek aynı sonucu veriyorsa kuralın yön söylemesinin bir değeri yoktur.

**Çoklu sınama.** Bir ızgara onlarca kombinasyon dener; en iyisinin örneklem içi Sharpe'ı şans eseri yüksek
olabilir. **Deflated Sharpe** (Bailey ve López de Prado) en iyi kombinasyonun Sharpe'ını, aynı sayıda denemenin şansla
üreteceği en yüksek Sharpe'a göre düzeltir. **Yürüyen pencere** her yılı yalnız önceki yılların verisiyle seçip o yılda
sınar ({{ K.saglamlik.walk_forward_ilk_test_yili | t }} → bugün).

**Koşul analizi.** Girişin olduğu anda bilinen on dört değişken{{? len(K.kosul.degiskenler) == 14 }} (aralığın ATR'ye oranı,
önceki günün yönü, oynaklık yüzdeliği, haftanın günü, büyük olay günü, saat değişimi haftası…) kovalara ayrılır.
Örneklem içinde koşulsuz ortalamanın üstünde kalan kovalar (en az {{ K.kosul.asgari_kova_islem | n }} işlemle) seçilir;
örneklem dışında seçilen kovaların ortalaması sıfırın ve tamamlayanının üstündeyse koşul **tuttu**, değilse **tutmadı**.
On dört değişkenin her biri ayrı bir denemedir ve şansla birkaçının tutması beklenir; bir koşul kontrol listesine
ancak başka paritelerde de aynı yönde duruyorsa aday olarak girer.

**Havuz.** Aynı kural dört paritede birlikte koşturulduğunda işlem başına ortalama, bütün işlemlerin ortalamasıdır;
Sharpe ve düşüş dört paritenin günlük R toplamından hesaplanır.

## Sözlük

| Terim | Anlamı |
| :--- | :--- |
| ATR | Ortalama gerçek aralık (*average true range*): son on dört mumun (ya da günün) aralığının, boşlukları da sayan, Wilder ortalaması. |
| R | İşlemin planlanan riski: yürütülen girişten stop'a uzaklık. Sonuçlar R'nin katı olarak yazılır. |
| Net / brüt | Net: yürütülebilir fiyatlarla, makas ve kayma dahil. Brüt: orta fiyattan orta fiyata. |
| İsabet | Kazanan işlemlerin payı. Tek başına bir şey söylemez: %30 isabetle de para kazanılır, %70 isabetle de kaybedilir. |
| Kâr çarpanı | Kazanılan pip toplamının kaybedilen pip toplamına oranı; 1'in altı kaybettirir. |
| Sharpe | Günlük R serisinin ortalamasının standart sapmasına oranı, yıllıklandırılmış (×√252). |
| MAE / MFE | İşlem açıkken gidilen en kötü (*maximum adverse excursion*) ve en iyi (*maximum favorable excursion*) nokta, R biriminde. |
| Azami düşüş | Birikimli R eğrisinin bir tepeden sonraki en derin çukuru. |
| Örneklem içi / dışı | Parametrenin seçildiği dönem / seçimin sınandığı dönem. |
| Önceden kayıt | Kuralın, ızgaranın ve hüküm ölçütünün sonuç görülmeden yazılıp kayda geçirilmesi. |
| Rastgele yön sınaması | Aynı giriş ve çıkış dakikalarında yönü yazı turayla seçen denemelerin dağılımı. |
| Deflated Sharpe | Çok sayıda kombinasyon denenmişken en iyisinin Sharpe'ının şans payından arındırılmış olasılığı. |
| Yürüyen pencere | Her yılı yalnız önceki yıllarla seçip o yılda sınamak. |
| Başabaş kayma | Net beklentiyi sıfıra indiren dolum başına kayma. |
| Pip | EUR/USD, GBP/USD, AUD/USD'de 0,0001; USD/JPY'de 0,01. |
| TSİ | Türkiye saati, yıl boyu UTC+3. |

## Ne değildir

Bu seri bir sinyal servisi değildir ve **yatırım tavsiyesi değildir**. Ölçülen her şey geçmişe aittir; geçmiş
sonuçlar gelecekteki sonuçların göstergesi değildir. Sınanan kurallar yayımlanmış ya da yaygın biçimleriyle,
tek tek ve mekanik olarak ölçüldü: bir masanın bu kuralları takdirle, başka bilgiyle ve başka risk yönetimiyle
kullanması ayrı bir şeydir ve burada ölçülmedi.
