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
başarısız kırılımlar, VWAP, klasik (salon) pivotları, WM/R 16:00 fiksingi, gün içi momentum ve beş haber
stratejisi. Her
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
| 4 · Fade (harekete karşı işlem) | kırılımın tersine, ortalamaya dönüş | başarısız kırılım (üç seviye), VWAP'a dönüş, pivot dönüşü, fiksing dönüşü |
| 5 · Haber | veri ve merkez bankası kararı anında | N1–N5, kırılım ↔ fade devam tablosu, FOMC karar ↔ basın toplantısı |
| 6 · Akış | gün içi akışın yönü | fiksing momentumu, gün içi momentum, VWAP geri çekilmesi |
| 7 · Karşılaştırma | stratejiler yan yana | sonuç, maliyet, ilinti, hangi koşulda hangisi |
| 8 · Metodoloji | sınamanın kendisi | önceden kayıt, seçim, sağlamlık, veri ve takvim denetimi, ölçülmeyenler |

Kurallar ölçtükleri bahse göre gruplandı: devam bahsi yapanlar kırılım derslerinde, dönüş bahsi yapanlar fade
dersinde, belirli bir saatin akışına bahis yapanlar akış dersinde. Bu yüzden pivot kırılımı yapı kırılımlarında,
pivot dönüşü fade'de; fiksing dönüşü fade'de, fiksing momentumu akışta durur.

Her strateji dersi aynı sırayla yazılır: **ne** (kuralın adı ve fikri), **piyasa mantığı** (neden çalışması
beklenir, neden çalışmayabilir), **kurallar** (ölçülen kural, harfiyen), **örnekler** (üç gerçek işlem: kazanan,
kaybeden ve tuzak), **sonuçlar**, **koşullar** (hangi günlerde daha iyi), **kontrol listesi** (kullanılır mı, ne
zaman, nasıl) ve **hüküm**.

## Veri

Fiyatlar Dukascopy'nin halka açık 1 dakikalık mumlarıdır: her dakika için ayrı ayrı **bid** (piyasa yapıcının
alış fiyatı) ve **ask** (piyasa yapıcının satış fiyatı) açılış, en yüksek, en düşük ve kapanış. Dönem {{ K.baslangic | tarih }} →
{{ K.bitis | tarih }}, pariteler EUR/USD, GBP/USD, USD/JPY ve AUD/USD. İki fiyattan iki türev kurulur: **orta
fiyat** (bid ile ask'ın ortalaması; sinyaller ondan okunur) ve **makas** (ask − bid; işlemin maliyetinin bir
parçası). Sinyalin orta fiyattan, yürütmenin bid/ask'tan yapılması bilinçlidir: piyasa orta fiyatla işlem yapmaz;
müşterinin alışı ask'tan, satışı bid'den dolar.

Arşivin her dakikası indirildikten sonra denetlenir: işlem günlerinin kapsamı (eksik dakikalar ve boşlukların
uzunluğu), tatiller, sıfır ya da eksi makas, sıçrama adayları (ertesi dakika geri dönen olağandışı hareketler) ve
Dukascopy'nin kendi saatlik mumlarıyla çapraz sınama. Veri değiştirilmez; denetim sonucu yazılır.

{{! veri }}

_Kapsam: hafta içi normal günlerde kotasyonu olan dakikaların payı. Tatil: hafta içine düşen 25 Aralık ve 1 Ocak
(takvimden; kapsamı %50'nin altında kalan günlerle aynı günlerdir). Boşluk: kotasyonun art arda kaç dakika
kesildiği; en uzun boşluk TSİ başlangıcıyla. Makas dakika kapanışında. Sıçrama adayı yalnız sayılır, veriden
çıkarılmaz. Çapraz sınama: dakika arşivinden kurulan saatlik mumların Dukascopy'nin kendi saatlik dosyalarıyla
birebir eşitlik oranı._

{{! sekil veri-makas "Makas: gün içinde ve devir dakikalarında" }}

Makas gün içinde sabit değildir. New York 17:00'de (FX gününün kapanışı) likidite sağlayıcılar pozisyonlarını bir
sonraki güne devrederken makas birkaç katına açılır; bu yüzden bu serideki bütün işlemler en geç 16:55 New York'ta
kapatılır. Haber dakikalarında da makas açılır; olay olay ölçüsü ve dört paritenin karşılaştırması haber
dersinde.

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

## Seanslar ve aralık

FX'in likiditesi üç seansa dağılır. **Asya** (Tokyo ve Sidney; TSİ gece yarısından sabaha) USD/JPY ve AUD/USD için
gerçek bir seanstır, EUR/USD ve GBP/USD için çoğu gün dar bir banttır. **Londra** (08:00 yerel) günün en büyük
hacmini taşır: Avrupa masaları gecenin emirlerini o saatte işler. **New York** (08:00 yerel) Londra öğleden sonrasıyla
dört saat örtüşür; ABD verisinin çoğu 08:30'da, hisse piyasası 09:30'da açılır. Bu serinin kırılım kurallarının çoğu
bir seansın başında oluşan bir **aralığa** bakar: bir zaman penceresinin en yüksek ve en düşük fiyatı (Londra'nın ilk
mumu, gecenin sekiz saati, New York'un ilk saati, dünün tamamı). Aralığın iki ucu emirlerin biriktiği yerdir; kırılım
kuralları ucun kesilmesinin hareketi hızlandıracağına, fade kuralları kesilen ucun geri alınacağına bahis yapar.

**Kapanış teyidi.** Bütün kurallar aralığın dışına taşmayı değil, dışında **kapanmayı** sinyal sayar. Sebep piyasanın
kendisindedir: ucun hemen ötesindeki stop emirleri fiyatı bir an dışarı taşır ve fiyat çoğu zaman geri döner; mum
içinde "geçti, girdim" diye kurulan bir kural bu gezintileri kırılım sayar. Kapanış o gürültünün bir kısmını ayıklar,
bedeli de girişin geç ve stop'un uzak olmasıdır. İkisinin dengesi ölçülen şeyin parçasıdır: aynı kural 5, 15 ve 60
dakikalık mumla, yani üç ayrı teyit uzunluğuyla sınanır.

## İşlem mekaniği

Bütün stratejiler aynı yürütme kurallarıyla koşar. Kuralların her biri bir yanılgıyı engellemek için oradadır.

**Sinyal mumun kapanışında, giriş sonraki dakikada.** Bir sinyal ancak mumu kapandıktan sonra bilinir. Giriş
sinyal mumundan sonraki ilk dakikanın açılışında yapılır; bir mumun içinde "fiyat aralığı geçti, hemen girdim"
türünden bir giriş yoktur. Bu kural bir sınamayla korunur: girişi sinyal mumunun kapanışından önceye düşen tek bir
işlem bile koşuyu durdurur. Ayrıca her strateji iki ayrı geleceğe bakmama sınamasından geçer (veriyi bir anda
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

**Gün sonu.** Açık pozisyon en geç {{ K.gun_sonu_et | t }} New York'ta (TSİ 23:55, ABD kış saatinde 00:55) kapatılır;
gece pozisyon taşınmaz.

**Tek pozisyon.** Bir strateji aynı paritede aynı anda en çok bir pozisyon taşır; haber stratejilerinde de bu kural
paritenin bütün olaylarına birlikte uygulanır (bir olayın pozisyonu açıkken başka bir olayın sinyali alınmaz).

**R birimi.** Her işlemin sonucu pip olarak ve **R** olarak yazılır. 1R, işlemin planlanan riskidir: yürütülen
giriş fiyatından stop seviyesine uzaklık. +2R, riskin iki katı kazanç demektir. R paritelerin pip değerlerinden ve
oynaklıklarından bağımsızdır; dört paritenin sonuçları ancak R ile toplanabilir. Stop'u olmayan stratejilerde
(fiksing kuralları ve gün içi momentum) R birimi girişteki ATR'dir: fiksingde kuralın kendi mumlarının, gün içi
momentumda 60 dakikalık mumların on dört mumluk ortalama gerçek aralığı. Orada R bir risk değil bir **ölçek
birimidir**: stop olmadığı için kayıp 1R'de durmaz ve tek bir işlem birkaç R kaybedebilir. Stop'lu kurallarda da
kayıp 1R'yi biraz aşabilir: stop'ta çıkış makas ve kaymayla stop seviyesinin ötesinde dolar, boşlukla stop daha da
ötede.

**R ve pip.** R'nin bir bedeli var. İşlem başına ortalama R, her işlemi riskine göre büyüklükleyen birinin sonucudur: stopu
dar bir işlemde 1R birkaç pip olabilir ve aynı pip hareketi o işlemde büyük bir R'ye dönüşür. Pip ortalaması ise
her işlemde aynı büyüklükle işlem yapanın sonucudur. İkisi aynı işareti taşımadığında sonucun işaretini stopu dar
işlemler belirliyor demektir; strateji dersleri bunu parite parite adıyla yazar. Hüküm ön kayıt gereği R'den
verilir.

<div class="pratik">
  <span class="etiket">Pratik — işlem mekaniği</span>

{{! pratik_islem orb "Alıştırma 1" }}

{{! pratik_islem vwap_donus "Alıştırma 2" kaybeden }}

</div>

## Maliyet

Bir işlemin maliyeti iki parçadır: girişte ve çıkışta ödenen **makas** (gerçek bid/ask'tan, dakika dakika) ve
**kayma** (makasın ötesinde kötüleşen dolum). Makas veriden gelir; kayma bir varsayımdır ve dört kademede ölçülür:
dolum başına {{ K.kayma_pip[0] | s1 }} · {{ K.kayma_pip[1] | s1 }} · {{ K.kayma_pip[2] | s1 }} ·
{{ K.kayma_pip[3] | s1 }} pip. Her strateji dersinin maliyet tablosu dört kademede net sonucu verir; **başabaş
kayma** işlem başına net R'nin sıfıra indiği dolum başına kaymadır ve iki dönemde ayrı ayrı yazılır: bütün dönem
ve örneklem dışı (2024 →). R'den ölçülür, pipten değil: pozisyon R'ye göre büyüklüklendiğinde para sonucu R'yi
izler (R ile pip ortalamasının farkı yukarıda). Başabaş kayma temel senaryonun yarım pipinin altındaysa kuralın
kenarı (varsa) o senaryonun yürütme maliyetine sığmaz. Merdivenin her kademesinde haber penceresinin ek kayması
sabit kalır; yalnız makasın kendisini görmek için ayrıca **yalnız makas** satırı var: kayma da haber kayması da
sıfır, maliyet yalnız gerçek bid/ask.

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
**varsayılan** (veriye hiç bakmadan seçilmiş) ve **seçilen** (ızgaradan yalnız örneklem içinde, en yüksek günlük
Sharpe'la, en az {{ K.secim.asgari_islem | n }} işlem şartıyla seçilmiş; haber stratejilerinde
{{ K.secim.asgari_islem_haber | n }}). Hüküm varsayılan üzerinden ve örneklem dışından (2024 →) verilir. Ön kayıt
varsayılan için bütün dönemi de örneklem dışı sayar, çünkü varsayılan hiçbir veriye bakmadan yazıldı; bütün dönemin
hükmü bu yüzden her tabloda yan sütunda durur ve iki hüküm ayrıştığında adıyla yazılır.

**Hüküm kuralı.** Bir stratejiye bir paritede "çalışıyor" demek için üç şartın birlikte tutması gerekir:
1. örneklem dışında işlem başına net ortalama R sıfırın üstünde;
2. bu ortalamanın %95 güven aralığının alt ucu da sıfırın üstünde (aralık, işlemlerin
   {{ K.hukum_kurali.bootstrap_tekrar | n }} kez yeniden örneklenmesiyle);
3. **rastgele yön sınamasında** stratejinin sonucu, dağılımın yüzdeliği olarak
   ≥ {{ K.hukum_kurali.rastgele_esik_yuzdelik | n }}.

Ortalama artı ama öbür şartlardan biri tutmuyorsa hüküm **zayıf**; ortalama sıfır ya da eksiyse **çalışmıyor**.
Örneklem dışında hiç işlem yoksa **ölçülemedi**. İki şartın kendi asgarisi var ve hüküm tablolarında görünür:
%95 aralığı en az {{ K.uygulama_esik.bootstrap | n }} işlemle kurulur, rastgele yön sınaması en az
{{ K.uygulama_esik.rastgele | n }} işlemle koşar; {{ K.uygulama_esik.az_islem | n }}'den{{? K.uygulama_esik.az_islem == 20 and K.uygulama_esik.rastgele == K.uygulama_esik.az_islem }} az işlemli bir sonuç "az işlem" diye
işaretlenir ve o sonuçta "çalışıyor" hükmü çıkamaz. Ayrıca bir bayrak var: brüt sonucun %95
aralığı sıfırın üstünde ama net sonuç sıfır ya da eksiyse **maliyet bayrağı** yanar — kuralın bir kenarı olabilir
ama makası ödemeye yetmiyor. Bayrak iki dönemde ayrı okunur (bütün dönem ve 2024 →).

**Rastgele yön sınaması.** Stratejinin her işlemi aynı giriş dakikasında, aynı risk uzaklığıyla ve aynı çıkış
kuralıyla (stop ve hedef ters yönde aynı uzaklıkta, zaman çıkışı aynı dakikada) yeniden koşturulur; yalnız yön yazı
turayla seçilir. Bu {{ K.hukum_kurali.rastgele_tekrar | n }} kez tekrarlanır. Gün içi stratejilerin çoğu saatini
seçerek bir şey kazanır: hareketin olduğu saatte piyasadadır. Bu sınama "yön bilgisi mi kazandırıyor, yoksa yalnız
zamanlama mı" sorusunu ayırır: yazı turayla aynı saatte girmek aynı sonucu veriyorsa kuralın yön söylemesinin bir
değeri yoktur.

**Çoklu sınama.** Bir ızgara onlarca kombinasyon dener; en iyisinin örneklem içi Sharpe'ı şans eseri yüksek
olabilir. **Deflated Sharpe** (Bailey ve López de Prado) en iyi kombinasyonun Sharpe'ını, aynı sayıda denemenin şansla
üreteceği en yüksek Sharpe'a göre düzeltir. Eşik iki biçimde kurulur: yalnız örnekleme gürültüsünden (her deneme
sıfır kenarlı olsaydı) ve denemelerin kendi Sharpe yayılımından (Bailey–López de Prado'nun önerisi); ikisi birlikte
yazılır. **Yürüyen pencere** her yılı yalnız önceki yılların verisiyle seçip o yılda
sınar ({{ K.saglamlik.walk_forward_ilk_test_yili | t }} → bugün).

**Koşul analizi.** Girişin olduğu anda bilinen on dört değişken{{? len(K.kosul.degiskenler) == 14 }} (aralığın ATR'ye oranı,
önceki günün yönü, oynaklık yüzdeliği, haftanın günü, büyük olay günü, saat değişimi haftası…) kovalara ayrılır.
Sürekli değişkenler örneklem içinin tercillerine (üçte birlik dilimlerine) bölünür; kova sınırları örneklem dışına
olduğu gibi taşınır. Örneklem içinde koşulsuz ortalamanın üstünde kalan kovalar (en az
{{ K.kosul.asgari_kova_islem | n }} işlemle) seçilir; örneklem dışında seçilen kovaların ortalaması (en az
{{ K.uygulama_esik.kosul_oos | n }} işlemle)
sıfırın ve öbür kovaların üstündeyse koşul **tuttu**, değilse **tutmadı**. Aynı ölçünün iki adı (Asya aralığı
kuralında "aralık" ile "Asya aralığı") tek değişken sayılır. On dört değişkenin her biri ayrı bir denemedir ve
şansla birkaçının tutması beklenir; bir koşul kontrol listesine ancak en az iki paritede aynı kovayla tutuyorsa
aday olarak girer. Şansın payını görmek için her bölüm bir de **ters seçimi** sayar: örneklem içinde ortalamanın
altında kalan kovalar seçilseydi aynı ölçüt kaç değişkende tutardı.

**Örnekler.** Her stratejinin figüründeki üç işlem örneklem dışından, sonuca bakmadan seçilir: **kazanan** (en az
yarım R kâr), **kaybeden** (en az yarım R zarar ve işlem boyunca lehine yarım R'ye ulaşmamış) ve **tuzak** (lehine en
az yarım R gidip zararla kapanmış: kırılımda sahte kırılım, dönüşte süren hareket). Uygun işlemler arasından seçim
sabit bir çekilişle yapılır ve üç örnek ayrı günlerdedir; "en iyi gün" seçilmez. Her örnek işlem ayrıca dolum başına
yarım pip daha kötü kaymayla yeniden koşturulur; alıştırmaların "dolum daha kötü olsaydı" şıkkı oradan gelir.

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
| Rastgele yön sınaması | Aynı giriş dakikası, aynı risk uzaklığı ve aynı çıkış kuralıyla, yönü yazı turayla seçen denemelerin dağılımı. |
| Deflated Sharpe | Çok sayıda kombinasyon denenmişken en iyisinin Sharpe'ının şans payından arındırılmış olasılığı; eşik iki biçimde (örnekleme gürültüsü · denemelerin yayılımı). |
| Yürüyen pencere | Her yılı yalnız önceki yıllarla seçip o yılda sınamak. |
| Makas | Ask − bid; işlemin girişte ve çıkışta ödediği gerçek maliyet. |
| Kayma | Makasın ötesinde kötüleşen dolum; bir varsayımdır, kademelerle ölçülür. |
| Başabaş kayma | İşlem başına net R'yi sıfıra indiren dolum başına kayma; bütün dönem ve 2024 → ayrı. |
| Ölçülemedi | Örneklem dışında işlem yok; hüküm verilemez. |
| Kova · tercil | Bir koşul değişkeninin dilimi; sürekli değişkende örneklem içinin üçte birlik dilimleri. |
| Welch t | İki grubun ortalamasını, varyansları eşit saymadan kıyaslayan t sınaması. |
| Benjamini–Hochberg q | Çok sayıda sınamada yanlış keşif oranını denetleyen düzeltilmiş p değeri. |
| McNemar | Aynı birimlerde iki ikili sonucun (ör. gerçek ve ters seçimin tuttu/tutmadı) farkını sınayan kesin sınama. |
| Binom sınaması | Bir olayın görülme sayısının, belirli bir olasılıkla şansın beklediğinden fazla olup olmadığı. |
| HAC (Newey–West) | Komşu gözlemlerin hataları ilintiliyken de geçerli standart hata; Bartlett çekirdeği ağırlık verir. |
| Pip | EUR/USD, GBP/USD, AUD/USD'de 0,0001; USD/JPY'de 0,01. |
| TSİ | Türkiye saati, yıl boyu UTC+3. |

## Ne değildir

Bu seri bir sinyal servisi değildir ve **yatırım tavsiyesi değildir**. Ölçülen her şey geçmişe aittir; geçmiş
sonuçlar gelecekteki sonuçların göstergesi değildir. Sınanan kurallar yayımlanmış ya da yaygın biçimleriyle,
tek tek ve mekanik olarak ölçüldü: bir masanın bu kuralları takdirle, başka bilgiyle ve başka risk yönetimiyle
kullanması ayrı bir şeydir ve burada ölçülmedi.
