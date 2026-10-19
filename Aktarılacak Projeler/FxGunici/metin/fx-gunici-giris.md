---
title: 'FX Gün İçi Stratejiler 1: Giriş — Veri, Saat, İşlem Mekaniği ve Sonuçların Okunuşu'
description: "Dört majör paritede (EUR/USD, GBP/USD, USD/JPY, AUD/USD) kural tabanlı gün içi stratejilerin sınandığı ders serisinin giriş dersi: 1 dakikalık bid/ask verisi ve denetimi, Londra–New York–TSİ saat haritası ve saat değişimi haftaları, sinyalden girişe ve çıkışa işlem mekaniği, maliyet, R birimi ve bir stratejinin 'çalışıyor' ya da 'çalışmıyor' hükmünün neye göre verildiği."
pubDate: 2026-10-17
tags: ['fx', 'gun-ici', 'backtest', 'strateji', 'ders']
durum: 'arsiv'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · BLS, Fed, ECB, BoE resmî takvimleri · önceden kayıt'
ozet: "Serinin bütün derslerinin dayandığı makineyi anlatır: veri nereden geliyor ve ne kadar temiz, saatler TSİ'de nereye düşüyor, bir işlem nasıl açılıp kapanıyor, maliyet nasıl ölçülüyor ve bir stratejiye 'çalışıyor' demek için hangi üç şartın birlikte tutması gerekiyor. Serinin sonucu baştan: hiçbir kural, hiçbir paritede bu üç şartı birlikte sağlamıyor.{{! ay_sonu_istisna }}{{? T.hukum_say.oos.calisiyor == 0 }}"
seviye: 'giris'
---

<div class="not gezinme"><span class="etiket">Arşiv</span> Bu ders gün içi FX kurallarının ayrıntılı sınamasındandır ve arşivdedir. Gün içi seri şimdi açılış, fiksing ve haber anlarının oyun planı olarak beş derste: [1 · İlk mumu okumak](/arastirma/fx-oyun-okuma/) · [2 · Açılışlar](/arastirma/fx-oyun-acilislar/) · [3 · Fiksingler](/arastirma/fx-oyun-fiksingler/) · [4 · Haber mumları](/arastirma/fx-oyun-haberler/) · [5 · Backtest](/arastirma/fx-oyun-backtest/).</div>

Bu seri, profesyonel FX masalarında adı sıkça geçen gün içi stratejileri tek bir makineyle sınar: Londra açılış
aralığı kırılımı, Asya aralığı, New York'un ilk dengesi, iç mum ve sıkışma kırılımları, önceki günün tepe ve dibi,
başarısız kırılımlar, VWAP, klasik (salon) pivotları, WM/R 16:00 fiksingi, gün içi momentum ve beş haber
stratejisi. Her
strateji aynı veriyle, aynı maliyetle, aynı yürütme kurallarıyla ve aynı hüküm kuralıyla ölçülür: kuralın şartları
sonuç görülmeden yazıldı; şartların asgari işlem sayıları ön kayıtta yoktur ve ilk sonuçlardan önce sabitlenmiş
uygulamada durur; hüküm penceresi ve "ölçülemedi"nin eşiği ilk sonuçlardan sonra belirlendi (metodoloji dersinde
adıyla). Amaç bir stratejiyi önermek değil; bir stratejinin ne olduğunu, nasıl kullanıldığını, ne kadar iyi
çalıştığını ve ne zaman çalışmadığını göstermektir. Çalışmayan stratejiye çalışmıyor denir.

Sonuç baştan: {{ T.birim | n }} kural ve {{ T.bilesim | n }} kural–parite bileşiminde varsayılanın hükmü, serinin
birincil penceresinde (2024 →; pencere ilk sonuçlardan sonra seçildi) {{ T.hukum_say.oos.calisiyor | n }} çalışıyor,
{{ T.hukum_say.oos.zayif | n }} zayıf, {{ T.hukum_say.oos.calismiyor | n }} çalışmıyor; ön kaydın istediği bütün
dönemde {{ T.hukum_say.tum.calisiyor | n }} çalışıyor, {{ T.hukum_say.tum.zayif | n }} zayıf,
{{ T.hukum_say.tum.calismiyor | n }} çalışmıyor{% if T.hukum_say.oos.calisiyor == 0 and T.hukum_say.tum.calisiyor == 0 %}: iki
pencerede de maliyetten sonra kanıtlanmış bir kenar bırakan kural yok{% endif %}.{{! ay_sonu_istisna }} "Zayıf" bir sınama değildir, yalnız
net ortalamanın artı olduğunu söyler; kural kural dökümü karşılaştırma dersinde. Sayıma New York ilk denge
kırılımının iki sürümü de girer, 08:00 ve 09:30 New York ({{! tsi "ve" "New York 08:00" "New York 09:30" }}); 08:00
sürümünün varsayılanı ön kayıtta yok, 09:30 sürümününkinden yalnız başlangıç saati değiştirilerek türetildi{{! turetilmis_hukum nyib_0800 }}.

Bu ders makinenin kendisidir. Sonraki dersler buradaki tanımları tekrar etmez: bir strateji dersinde "net R",
"örneklem dışı" ya da "rastgele yön yüzdeliği" geçtiğinde tanımı buradadır.

## Serinin haritası

| Ders | Konu | Stratejiler |
| :--- | :--- | :--- |
| 1 · Giriş | veri, saat, işlem mekaniği, sonuçların okunuşu | — |
| 2 · Seans kırılımları | bir seansın açılış aralığının kırılması | Londra açılış aralığı, Asya aralığı, New York ilk dengesi (iki çıpa: masaların sabahı, hisse açılışı) |
| 3 · Yapı kırılımları | bir fiyat yapısının ya da seviyenin kırılması | iç mum, Bollinger–Keltner sıkışması, önceki gün tepe/dip, pivot kırılımı |
| 4 · Fade (harekete karşı işlem) | kırılımın tersine, ortalamaya dönüş | başarısız kırılım (üç seviye), VWAP'a dönüş, pivot dönüşü, fiksing dönüşü |
| 5 · Haber | veri ve merkez bankası kararı anında | N1–N5, kırılım ↔ fade devam tablosu, FOMC karar ↔ basın toplantısı |
| 6 · Akış | gün içi akışın yönü | fiksing momentumu, gün içi momentum, VWAP geri çekilmesi |
| 7 · Karşılaştırma | stratejiler yan yana | sonuç, maliyet, ilinti, hangi koşulda hangisi |
| 8 · Metodoloji | sınamanın kendisi | önceden kayıt, seçim, sağlamlık, veri ve takvim denetimi, ölçülmeyenler |
| 9 · Neden başarısız oluyorlar | kayıp nereden geliyor, bir kural hangi şartla kullanılabilir | başabaş isabeti, kaybın ayrışımı, ölçek, şans ve seçim, başabaş maliyeti, ay sonu fiksingi, güç ve sınama planı |

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
{{ K.bitis | tarih }}, pariteler {{ K.ciftler | pariteler }}. İki fiyattan iki türev kurulur: **orta
fiyat** (bid ile ask'ın ortalaması; sinyaller ondan okunur) ve **makas** (ask − bid; işlemin maliyetinin bir
parçası). Sinyalin orta fiyattan, yürütmenin bid/ask'tan yapılması bilinçlidir: piyasa orta fiyatla işlem yapmaz;
müşterinin alışı ask'tan, satışı bid'den dolar.

Arşivin her dakikası indirildikten sonra denetlenir: işlem günlerinin kapsamı (eksik dakikalar ve boşlukların
uzunluğu), tatiller, sıfır ya da eksi makas, sıçrama adayları (ertesi dakika geri dönen olağandışı hareketler) ve
Dukascopy'nin kendi saatlik mumlarıyla çapraz sınama. Veri değiştirilmez; denetim sonucu yazılır.

{{! veri }}

_Kapsam: hafta içi normal günlerde kotasyonu olan dakikaların payı. Tatil: hafta içine düşen 25 Aralık ve 1 Ocak
(takvimden; kapsamı {{! kalite_esik tatil in }} altında kalan günlerle aynı günlerdir). İngiltere banka tatilleri ve ABD federal tatilleri
işlem günüdür ve kurallar o günlerde de işlem açar; üçüncü tablo o günlerin kotasyon kapsamını verir (ortalama ve en
düşük gün; kapsamı {{! kalite_esik normal in }} altında kalan gün sayısı). Boşluk: kotasyonun art arda kaç dakika
kesildiği; en uzun boşluk TSİ başlangıcıyla. Makas dakika kapanışında. Sıçrama adayı yalnız sayılır, veriden
çıkarılmaz. Çapraz sınama: dakika arşivinden kurulan saatlik mumların Dukascopy'nin kendi saatlik dosyalarıyla
birebir eşitlik oranı; {{! capraz_kapsam }}._

{{! sekil veri-makas "Makas: gün içinde ve devir dakikalarında" }}

Makas gün içinde sabit değildir. New York 17:00'de (FX gününün kapanışı; {{! tsi "" "New York 17:00" }}) likidite sağlayıcılar pozisyonlarını bir
sonraki güne devrederken makas birkaç katına açılır; bu yüzden bu serideki bütün işlemler en geç
{{ K.gun_sonu_et | t }} New York'ta ({{! gun_sonu_tsi }}) kapatılır. Haber dakikalarında da makas açılır; olay olay ölçüsü ve dört paritenin karşılaştırması haber
dersinde.

**Hacim üzerine bir uyarı.** FX'te merkezî bir borsa ve merkezî bir işlem hacmi yoktur. Dukascopy'nin mumlarındaki
"hacim", kendi platformundaki kotasyonların en iyi fiyattaki likidite miktarıdır, gerçekleşmiş işlem hacmi değildir.
VWAP stratejileri bu hacmi ağırlık olarak kullanır ve derste bu sınır açıkça yazılır.

## Saat

Arşiv UTC'de tutulur ve bütün seans saatleri yerel saatlerinden (Londra, New York, Tokyo, Frankfurt) IANA saat
dilimi veritabanının kurallarıyla hesaplanır; hiçbir saat elle kaydırılmaz. **FX işlem günü** New York 17:00'de
({{! tsi "" "New York 17:00" }}) başlar ve ertesi gün aynı saatte biter: pazartesinin işlem günü pazar akşamı New
York'ta açılır. Derslerde bütün saatler ayrıca
**TSİ** olarak yazılır. Türkiye 2016'dan beri yıl boyu UTC+3'tür ve saat değiştirmez; bu yüzden Londra ya da New York
saat değiştirdiğinde onların TSİ karşılığı kayar.

Avrupa ile ABD saati aynı gün değiştirmez: ABD mart ayının ikinci pazarı ileri, kasımın ilk pazarı geri alır;
Avrupa mart ve ekimin son pazarı. Aradaki birkaç hafta Londra ile New York arasındaki fark beş değil dört saattir.
Dört rejimde olayların TSİ saati:

{{! zaman }}

{{! zaman_diger }}

Ara dönemler, yıl yıl:

{{! dst }}

İki pratik sonuç var. Birincisi takvim: bir olayın TSİ saati yalnız kendi şehrinin saatine bağlıdır. Londra
açılışı TSİ'de İngiltere yaz saatindeyken 10:00, değilken 11:00; ABD verisi ABD yaz saatindeyken 15:30, değilken
16:30. Ara dönemde ikisi farklı rejimdedir ve iki ara dönemde de aynı şey olur: Londra açılışı TSİ 11:00'de, ABD
verisi 15:30'da — Londra ile New York arasındaki fark bir saat kısalır. İkincisi ölçü: saat değişimi haftası ve ara dönemin kendisi koşul analizinde ayrı birer
değişkendir; bir stratejinin bu haftalarda farklı davranıp davranmadığı her strateji dersinde ayrıca sorulur.

## Seanslar ve aralık

FX'in likiditesi üç seansa dağılır. **Asya** (Tokyo ve Sidney; TSİ gece yarısından sabaha) USD/JPY ve AUD/USD için
gerçek bir seanstır, EUR/USD ve GBP/USD için çoğu gün dar bir banttır. **Londra** (yerel 08:00;
{{! tsi "" "Londra 08:00" }}) günün en büyük hacmini taşır: Avrupa masaları gecenin emirlerini o saatte işler.
**New York** masaları 08:00 New York'ta ({{! tsi "" "New York 08:00" }}) devralır ve Londra öğleden sonrasıyla dört
saat örtüşür; ABD verisinin çoğu New York 08:30'da ({{! tsi "" "New York 08:30" }}), hisse piyasası New York
09:30'da ({{! tsi "" "New York 09:30" }}) açılır. Bu serinin kırılım kurallarının çoğu
bir seansın başında oluşan bir **aralığa** bakar: bir zaman penceresinin en yüksek ve en düşük fiyatı (Londra'nın ilk
mumu, gecenin sekiz saati, New York'un ilk saati, dünün tamamı). Aralığın iki ucu emirlerin biriktiği yerdir; kırılım
kuralları ucun kesilmesinin hareketi hızlandıracağına, fade kuralları kesilen ucun geri alınacağına bahis yapar.

**Kapanış teyidi.** Bütün kurallar aralığın dışına taşmayı değil, dışında **kapanmayı** sinyal sayar. Sebep piyasanın
kendisindedir: ucun hemen ötesindeki stop emirleri fiyatı bir an dışarı taşır ve fiyat çoğu zaman geri döner; mum
içinde "geçti, girdim" diye kurulan bir kural bu gezintileri kırılım sayar. Kapanış o gürültünün bir kısmını ayıklar,
bedeli de girişin geç ve stopun uzak olmasıdır. İkisinin dengesi ölçülen şeyin parçasıdır: aynı kural 5, 15 ve 60
dakikalık mumla, yani üç ayrı teyit uzunluğuyla sınanır.

## İşlem mekaniği

Bütün stratejiler aynı yürütme kurallarıyla koşar. Kuralların her biri bir yanılgıyı engellemek için oradadır.

**Sinyal mumun kapanışında, giriş sonraki dakikada.** Bir sinyal ancak mumu kapandıktan sonra bilinir. Kural kendi
giriş saatini tanımlamıyorsa giriş, sinyal mumundan sonraki ilk dakikanın açılışında yapılır; gün içi momentum 12:00
New York'ta ({{! tsi "" "New York 12:00" }}), fiksing dönüşünün gecikmeli biçimi bir mum sonra girer. Bir mumun içinde "fiyat aralığı geçti, hemen
girdim" türünden bir giriş yoktur. Bu kural bir sınamayla korunur: girişi sinyal mumunun kapanışından önceye düşen tek
bir işlem bile koşuyu durdurur. Ayrıca her strateji iki ayrı geleceğe bakmama sınamasından geçer: veri bir anda
kesilir ya da o andan sonrası değiştirilir ve kararı kesimden önce verilen sinyallerin değişmediği sınanır; kesim
anlarının bir kısmı gerçek bir sinyalin karar anının hemen ardındadır, yani bir iki mum sonrasına bakan bir kural da
yakalanır (kapsamı metodoloji dersinde).

**Yürütülebilir fiyat.** Alış ask'tan, satış bid'den dolar; dolum başına ayrıca **kayma** eklenir (temel senaryoda
{{ K.temel_kayma_pip | s1 }} pip). Haber penceresinde (olaydan önceki iki dakikadan sonraki on beş dakikaya
kadar){{? K.haber_pencere_dk[0] == -2 and K.haber_pencere_dk[1] == 15 }} ek {{ K.haber_kayma_pip | s1 }} pip kayma eklenir.

**Stop.** "Sert" stop emir tarafında dakika dakika izlenir (alışta bid stop seviyesine değdiğinde dolar). "Kapanış"
stopu yalnız mumun orta fiyattan kapanışı stopun ötesindeyse tetiklenir ve bir sonraki mumun açılışında doldurulur.
Sert stopta bir dakika stopun ötesinde açılırsa (önceki dakikanın kapanışıyla arasında sıçrama olduğunda da, bir veri boşluğundan sonra da) dolum o açılış fiyatındadır (boşlukla stop); hedefin ötesinde açılan dakikada da dolum açılıştır.

**Hedef.** Limit emirdir ve kaymaz: hedef seviyesine değen dakika hedefte doldurur. Aynı dakikada hem stop hem hedef
değerse **stop sayılır**: dakikanın içinde hangisinin önce geldiği 1 dakikalık veriden bilinemez ve belirsizlikte
iyimser seçim yapılmaz. **Zaman hedefi** ("zaman") bir fiyat değil bir süredir: işlem girişten
{{ ON.genel.desen_zaman_mum | n }} mum sonra{% if ON.haber.zaman_mum != ON.genel.desen_zaman_mum %} (haber kurallarında {{ ON.haber.zaman_mum | n }} mum){% endif %}, o mumun açılışında
piyasa emriyle kapanır; stop o ana kadar açık kalır ve çıkış gün sonunu aşmaz.

**Gün sonu.** Açık pozisyon en geç {{ K.gun_sonu_et | t }} New York'ta ({{! gun_sonu_tsi }}) kapatılır; gece
pozisyon taşınmaz.

**Tek pozisyon.** Bir strateji aynı paritede aynı anda en çok bir pozisyon taşır; haber stratejilerinde de bu kural
paritenin bütün olaylarına birlikte uygulanır (bir olayın pozisyonu açıkken başka bir olayın sinyali alınmaz).

**Alınmayan emir.** Açık pozisyonun dışında üç durumda daha emir alınmaz: giriş dakikasında emrin tarafının açılışı
(alışta ask, satışta bid) stopun ötesinde ya da tam üstündeyse; seviye hedefi yürütülen girişin (kayma dahil)
gerisinde ya da tam üstündeyse; giriş gün sonunda ({{ K.gun_sonu_et | t }} New York; {{! gun_sonu_tsi }}) ya da sonrasındaysa.
Stopta kayma hesaba katılmaz, çünkü kayma bir işlem yaratmamalıdır; hedefte katılır, çünkü hedefi aşan bir dolumun
kazancı yoktur. Hızlı bir mumda giriş anında stopa ya da hedefe varmış ya da onu geçmiş emir bu yüzden örneklemden çıkar;
kural kural sayısı strateji derslerinde.

**R birimi.** Her işlemin sonucu pip olarak ve **R** olarak yazılır. 1R, işlemin planlanan riskidir: yürütülen
giriş fiyatından stop seviyesine uzaklık. +2R, riskin iki katı kazanç demektir. R paritelerin pip değerlerinden ve
oynaklıklarından bağımsızdır; dört paritenin sonuçları ancak R ile toplanabilir. Stopu olmayan stratejilerde
(fiksing kuralları ve gün içi momentum) R birimi girişteki ATR'dir: fiksingde kuralın kendi mumlarının, gün içi
momentumda 60 dakikalık mumların on dört mumluk ortalama gerçek aralığı. Orada R bir risk değil bir **ölçek
birimidir**: stop olmadığı için kayıp 1R'de durmaz ve tek bir işlem birkaç R kaybedebilir. Stoplu kurallarda da
kayıp 1R'yi aşabilir. Sert stopta çıkış, stop seviyesinden yalnız kayma kadar öteden dolar (haber penceresinde haber
kayması dahil); makas stop emir tarafında sorulduğu için tetiklenmeyi öne alır, dolum uzaklığına girmez. Boşlukla stop
daha ötede dolar. Kapanış stopunda mum stopun ötesinde kapandıktan sonra sonraki açılışta çıkıldığı için kayıp 1R'yi
belirgin aşabilir. {{! stop_cikis }}

**R ve pip.** R'nin bir bedeli var. İşlem başına ortalama R, her işlemi riskine göre ölçekleyen birinin sonucudur: stopu
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
ve örneklem dışı (2024 →). R'den ölçülür, pipten değil: pozisyon R'ye göre ölçeklendiğinde para sonucu R'yi
izler (R ile pip ortalamasının farkı yukarıda). Başabaş kayma temel senaryonun {{ K.temel_kayma_pip | s1 }} pip'inin
altındaysa kuralın kenarı (varsa) o senaryonun yürütme maliyetine sığmaz. Merdivenin her kademesinde haber
penceresinin ek kayması sabit kalır; yalnız makasın kendisini görmek için ayrıca **yalnız makas** satırı var: kayma da
haber kayması da sıfır, maliyet yalnız gerçek bid/ask. Başabaşın dört özel hâli tabloda adıyla yazılır. Brüt sonuç
artı değilse hiçbir kayma kademesi başabaş değildir: "orta fiyattan bile eksi". Brüt artı ama yalnız makasla bile
eksiyse başabaş bir kayma değil bir makastır: sonucun sıfıra indiği makas, bu verinin makasının payı olarak ("makas ≤
%X": makas bu verininkinin en çok %X'i olmalı; makasın maliyeti makasla doğrusal ölçeklenir varsayımıyla). Yalnız
makasla artı ama temel kayma sıfırken de haber penceresinin {{ K.haber_kayma_pip | s1 }} pip'i sonucu eksiye
çeviriyorsa: "{{= "0,0" }} pip kademesinde bile eksi". Merdivenin en yüksek kademesinde de artı kalan sonuçta başabaş
merdivenin dışındadır: "2 pip'te bile artı".{{? len(K.kayma_pip) == 4 and K.kayma_pip[0] == 0.0 and K.kayma_pip[3] == 2.0 }}

Aynı işlem iki ayrı sayı taşır: **brüt** (orta fiyattan orta fiyata, maliyetsiz) ve **net** (yürütülebilir
fiyatlarla, makas ve kayma dahil). Brüt sonuç kuralın bir şey yakalayıp yakalamadığını, net sonuç bundan para
kalıp kalmadığını söyler. İkisi arasındaki fark, kısa işlemlerde ve yakın stoplarda büyür.

## Sonuçların okunuşu

**Örneklem içi ve dışı.** Dönem ikiye bölünür: {{ K.baslangic | tarih }} → {{ K.ic_bitis | tarih }} örneklem içi,
{{ K.dis_baslangic | tarih }} → {{ K.bitis | tarih }} örneklem dışı. Parametre seçimi yalnız örneklem içinde yapılır;
örneklem dışı yalnız sınar. Bir stratejinin geçmişe iyi uyması kolaydır; asıl soru seçimden sonra gelen veride ne
yaptığıdır.

**Önceden kayıtlı varsayılan ve seçilen.** Her strateji ailesinin parametre ızgarası ve "ders kitabı" varsayılanı
hiçbir sonuç görülmeden yazılıp kayda geçirildi (metodoloji dersinde tarihçesiyle; New York ilk denge kırılımının
08:00 New York ({{! tsi "" "New York 08:00" }}) başlangıçlı sürümünün varsayılanı, 09:30
({{! tsi "" "New York 09:30" }}) başlangıçlı sürümününkinden yalnız başlangıç saati değiştirilerek türetildi). İki sonuç birlikte raporlanır:
**varsayılan** (veriye hiç bakmadan seçilmiş) ve **seçilen** (ızgaradan yalnız örneklem içinde, en yüksek günlük
Sharpe'la, en az {{ K.secim.asgari_islem | n }} işlem şartıyla seçilmiş; haber stratejilerinde
{{ K.secim.asgari_islem_haber | n }}). Ön kayıt varsayılanın hükmünü bütün dönemden kurar: varsayılan hiçbir veriye bakmadan yazıldığı
için bütün dönem onun örneklem dışıdır. Bu seri iki sonucu aynı pencerede kıyaslamak için birincil hükmü 2024 →
penceresinden verir; bütün dönemin hükmü her tabloda yan sütunda durur ve iki hüküm ayrıştığında adıyla yazılır
(gerekçesi ve ayrışan bileşimler metodoloji dersinde).

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
olabilir. **Deflated Sharpe** (Bailey ve López de Prado, 2014) en iyi kombinasyonun Sharpe'ını, aynı sayıda denemenin şansla
üreteceği en yüksek Sharpe'a ve günlük getirilerin çarpıklık ve basıklığına göre düzeltir. Eşik iki biçimde kurulur: yalnız örnekleme gürültüsünden (her deneme
sıfır kenarlı olsaydı) ve denemelerin kendi Sharpe yayılımından (Bailey–López de Prado'nun önerisi); ikisi birlikte
yazılır. **Yürüyen pencere** her yılı yalnız önceki yılların verisiyle seçip o yılda
sınar ({{ K.saglamlik.walk_forward_ilk_test_yili | t }} → bugün; seçim şartını sağlayan kombinasyonu olmayan yıl sınanmaz,
sınanan yıllar strateji derslerinde adıyla yazılır).

**Koşul analizi.** Girişin olduğu anda bilinen on dört değişken{{? len(K.kosul.degiskenler) == 14 }} (aralığın ATR'ye oranı,
önceki günün yönü, oynaklık yüzdeliği, haftanın günü, büyük olay günü, saat değişimi haftası…) kovalara ayrılır.
Sürekli değişkenler örneklem içinin tercillerine (üçte birlik dilimlerine) bölünür; kova sınırları örneklem dışına
olduğu gibi taşınır. Örneklem içinde koşulsuz ortalamanın üstünde kalan kovalar (en az
{{ K.kosul.asgari_kova_islem | n }} işlemle) seçilir; örneklem dışında seçilen kovaların ortalaması (en az
{{ K.uygulama_esik.kosul_oos | n }} işlemle)
sıfırın ve seçilmeyen kovaların birlikte ortalamasının (tamamlayanın) üstündeyse koşul **tuttu**, değilse **tutmadı**;
seçilen kova seçilmeyenlerden birinin altında kalsa da koşul tutabilir. Aynı ölçünün iki adı (Asya aralığı
kuralında "aralık" ile "Asya aralığı") tek değişken sayılır. On dört değişkenin her biri ayrı bir denemedir ve
şansla birkaçının tutması beklenir. Bir koşul, en az iki paritede aynı kova seçimiyle tutuyorsa kontrol listesine aday
olarak girer. İkinci paritedeki tutuş şansı ayıklamaz: {{! aday_taban }}. Şansın payını görmek için her bölüm ters
seçimi de sayar.

Değişkenlerin tanımı aşağıdaki tabloda. Günlük ATR, önceki on dört FX işlem gününün Wilder ATR'sidir: bugünü
içermez, tatil günü atlanır. Üç değişken işlemin yönüne göre işaret alır (önceki günün yönü, açılış farkı, 60 dk trend);
aynı gün alışta bir kovaya, satışta karşı kovaya düşer. Her strateji bölümünün koşul kısmı, ana paritede her kovanın
sınırını, örneklem içi ve dışı işlem sayısını, net R'sini ve isabetini katlanır bir tabloda verir.

{{! kosul_tanim }}

**Örnekler.** Her stratejinin figüründeki üç işlem örneklem dışından, sonuca bakmadan seçilir: **kazanan** (en az
yarım R kâr), **kaybeden** (en az yarım R zarar ve işlem boyunca lehine yarım R'ye ulaşmamış) ve **tuzak** (lehine en
az yarım R gidip zararla kapanmış: kırılımda sahte kırılım, dönüşte süren hareket). Uygun işlemler arasından seçim
sabit bir çekilişle yapılır ve üç örnek ayrı günlerdedir; "en iyi gün" seçilmez. Her örnek işlem ayrıca dolum başına
yarım pip daha kötü kaymayla yeniden koşturulur; alıştırmaların "dolum daha kötü olsaydı" şıkkı oradan
gelir.{{? K.ornek.esik == 0.5 and K.ornek.ek_kayma == 0.5 }}

**Havuz.** Aynı kural dört paritede birlikte koşturulduğunda işlem başına ortalama, bütün işlemlerin ortalamasıdır;
Sharpe ve düşüş dört paritenin günlük R toplamından hesaplanır. Havuzun %95 aralığı gün kümelidir: aynı günün
bütün paritelerdeki işlemleri birlikte yeniden örneklenir, çünkü dört paritenin aynı günkü sonuçları ortak dolar
hareketiyle birbirine bağlıdır.

## Sözlük

| Terim | Anlamı |
| :--- | :--- |
| ATR | Ortalama gerçek aralık (*average true range*): son on dört mumun (ya da günün) aralığının, boşlukları da sayan, Wilder ortalaması. |
| R | İşlemin planlanan riski: yürütülen girişten stopa uzaklık. Sonuçlar R'nin katı olarak yazılır. |
| Net / brüt | Net: yürütülebilir fiyatlarla, makas ve kayma dahil. Brüt: orta fiyattan orta fiyata. |
| İsabet | Kazanan işlemlerin payı. Tek başına bir şey söylemez: %30 isabetle de para kazanılır, %70 isabetle de kaybedilir. |
| Başabaş isabeti | İşlem başına beklentiyi sıfırlayan isabet: ortalama kaybın büyüklüğü / (ortalama kazanç + ortalama kaybın büyüklüğü). İsabetin ondan uzaklığı beklentinin işaretini taşır. |
| Kâr çarpanı (R) | Kazanılan R toplamının kaybedilen R toplamına oranı; hükmün birimi. 1'in altı, her işlemi riskine göre ölçekleyen birine kaybettirir. |
| Kâr çarpanı (pip) | Aynı oran pip ile; her işlemde aynı büyüklükle işlem yapanın sonucu. İkisi ayrışabilir (yukarıda, "R ve pip"). |
| Sharpe | Günlük R serisinin ortalamasının standart sapmasına oranı, yıllıklandırılmış (×√252). Seri dönemin bütün tatil dışı FX işlem günlerini taşır; işlem açılmayan gün sıfırdır, bu yüzden seyrek işlem açan kuralların (haber kuralları) Sharpe'ı çoğunlukla sıfır günlerden oluşan bir seriden gelir. |
| MAE / MFE | İşlem açıkken gidilen en kötü (*maximum adverse excursion*) ve en iyi (*maximum favorable excursion*) nokta, R biriminde. |
| Azami düşüş | Birikimli R eğrisinin bir tepeden sonraki en derin çukuru. |
| Örneklem içi / dışı | Parametrenin seçildiği dönem / seçimin sınandığı dönem. |
| Önceden kayıt | Kuralın, ızgaranın ve hüküm ölçütünün sonuç görülmeden yazılıp kayda geçirilmesi. |
| Rastgele yön sınaması | Aynı giriş dakikası, aynı risk uzaklığı ve aynı çıkış kuralıyla, yönü yazı turayla seçen denemelerin dağılımı. |
| Ayna işlem | Gerçek işlemle aynı dakikada ters yönde açılan, stopu ve hedefi girişe aynı R uzaklığında duran işlem; rastgele yön sınamasının ters yönlü yarısı. Kaybı yön, zamanlama ve maliyet paylarına ayırır. |
| Deflated Sharpe | Çok sayıda kombinasyon denenmişken en iyisinin Sharpe'ının şans payından ve getirilerin normal olmamasından arındırılmış olasılığı; eşik iki biçimde (örnekleme gürültüsü · denemelerin yayılımı). |
| Yürüyen pencere | Her yılı yalnız önceki yıllarla seçip o yılda sınamak. |
| Makas | Ask − bid; işlemin girişte ve çıkışta ödediği gerçek maliyet. |
| Kayma | Makasın ötesinde kötüleşen dolum; bir varsayımdır, kademelerle ölçülür. |
| Başabaş maliyeti | Kuralın işlem başına kaldırabildiği en yüksek gidiş-dönüş maliyeti (pip): ortalama brüt R / ortalama (1 / R'nin pip karşılığı). |
| Başabaş kayma | İşlem başına net R'yi sıfıra indiren dolum başına temel kayma (haber penceresinin ek kayması sabit); bütün dönem ve 2024 → ayrı. Brüt artı değilse yoktur ("orta fiyattan bile eksi"); yalnız makasla bile eksiyse makasın payıyla yazılır ("makas ≤ %X"). |
| Ölçülemedi | Örneklem dışında işlem yok; hüküm verilemez. |
| Zaman hedefi | Girişten sabit sayıda mum sonra piyasa emriyle çıkış (stop açık kalır, gün sonunu aşmaz). |
| Kümeli bootstrap | Bağımsız olmayan gözlemlerin birlikte yeniden örneklenmesi: havuzda aynı günün bütün paritelerdeki işlemleri (gün kümeli), haber tablolarında aynı olayın bütün paritelerdeki işlemleri (olay kümeli). |
| Kova · tercil | Bir koşul değişkeninin dilimi; sürekli değişkende örneklem içinin üçte birlik dilimleri. |
| Welch t | İki grubun ortalamasını, varyansları eşit saymadan kıyaslayan t sınaması. |
| Benjamini–Hochberg q | Çok sayıda sınamada yanlış keşif oranını denetleyen düzeltilmiş p değeri. |
| McNemar | Aynı gözlemlerde (ör. aynı kural–parite bileşimlerinde) iki ikili sonucun (ör. gerçek ve ters seçimin tuttu/tutmadı) farkını sınayan kesin sınama. |
| Binom sınaması | Bir olayın görülme sayısının, belirli bir olasılıkla şansın beklediğinden fazla olup olmadığı. |
| Güvenilirlik | Bileşimler arasındaki farkların örnekleme gürültüsü olmayan payı: (gözlenen varyans − ortalama örnekleme varyansı) / gözlenen varyans. |
| Kazananın laneti | Bir eşikten geçtiği için seçilen bir etkinin gerçek büyüklüğünden büyük ölçülmesi; seçilen sonuç gelecekte ortalamaya doğru döner. |
| Güç | Gerçek bir etki varken sınamanın onu görme olasılığı. |
| En küçük görülebilir etki | Belirli bir işlem sayısıyla, belirli bir düzey ve güçle sıfırdan ayrılabilecek en küçük etki. |
| HAC (Newey–West) | Komşu gözlemlerin hataları ilintiliyken de geçerli standart hata; Bartlett çekirdeği ağırlık verir. |
| Pip | {{! pip_tanimi }}. |
| TSİ | Türkiye saati, yıl boyu UTC+3. |

## Ne değildir

Bu seri bir sinyal servisi değildir ve **yatırım tavsiyesi değildir**. Ölçülen her şey geçmişe aittir; geçmiş
sonuçlar gelecekteki sonuçların göstergesi değildir. Sınanan kurallar yayımlanmış ya da yaygın biçimleriyle,
tek tek ve mekanik olarak ölçüldü: bir masanın bu kuralları takdirle, başka bilgiyle ve başka risk yönetimiyle
kullanması ayrı bir şeydir ve burada ölçülmedi.

## Kaynaklar

{{! kaynaklar fx-gunici-giris }}
