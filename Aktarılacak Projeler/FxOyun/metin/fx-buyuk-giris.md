---
title: 'FX Gün İçi Oyun Planı 8: Büyük Mum — Nasıl Girilir: Piyasa, Limit, Stop, Onay'
description: "Büyük mumdan sonra kapanışta piyasadan mı girmeli, geri çekilmeye limit mi koymalı, ucun kırılmasını mı beklemeli, onay mumunu mu? Mumun yönünde ve tersine on bir giriş biçimi, iki stop ve iki hedefle: dolum oranı, kazanma oranı, maliyetten önce ve sonra işlem başına sonuç, limit emrin ters seçimi."
pubDate: 2026-10-20
tags: ['fx', 'gun-ici', 'oyun-plani', 'buyuk-mum', 'emir', 'limit', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Giriş biçimi sonucu değiştirir ama kenar yaratmaz. Maliyetten önce bütün biçimler sıfır çevresinde; stop 2 ATR ve hedef 1 R ile maliyetten sonra hepsi eksi. Limit girişte makası ve kaymayı ödemediği için 5 ve 15 dakikada en az kaybeden biçim, ama maliyetten önce piyasa emrinden kötü: limit, fiyat aleyhine yürüdüğünde dolar ve kazanacak işlemi kaçırır. Stopu yaklaştırmak maliyeti R cinsinden büyütür."
seviye: 'orta'
onkosul: ['fx-buyuk-mum', 'fx-buyuk-suzgec']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';

Önceki iki ders büyük mumdan sonra fiyatın ne yaptığını okudu. Bu ders o okumanın **işlem hâlini** ölçer: aynı büyük
mumdan sonra, aynı stop ve hedefle, farklı biçimde giren on bir işlemci ne kazanır? Sorunun iki yarısı var. Biri yöndür
(mumun yönünde mi, tersine mi); öbürü girişin kendisidir (hemen mi, geri çekilmede mi, kırılımda mı, onay gelince mi).

Bütün işlemler gerçek alış ve satış fiyatlarından simüle edildi. Alış ask'tan, satış bid'den dolar. Piyasa ve stop
emirleri {{ ON.kayma_pip }} pip kötü dolar; takvimdeki büyük bir haberin iki dakika öncesinden on beş dakika sonrasına
kadar buna {{ ON.haber_kayma_pip }} pip daha eklenir. Limit emir kendi fiyatına kaymasız dolar. Aynı dakikada hem stop
hem hedef görülürse stop sayılır; dolum dakikasında hedef sayılmaz. Planlanan risk {{ ON.en_az_risk_pip }} pipin
altındaysa işlem açılmaz. Tablolar 2018–2023'ün ve 2024 sonrasının sonucunu yan yana verir. Girişlerin 2024 sonrası
sonucu planın seçiminde kullanılmadı (seçim 9. dersin konusu ve yalnız 2018–2023'ten yapıldı); burada betimleme olarak
duruyor.

İki ölçü bütün ders boyunca aynı anlamda kullanılır. **R**, planlanan risktir: girişten stopa olan mesafe; işlemin
sonucu bu mesafenin katı olarak yazılır. **Maliyetsiz R** (maliyetten önce), aynı kuralın alış ile satışın ortasından,
makassız ve kaymasız sonucudur; **net R** (maliyetten sonra) aynı işlemlerin gerçek alış-satış fiyatlarıyla sonucudur.
Aradaki fark maliyettir. Aşağıdaki üç tablonun bütün satırları stop 2 ATR, hedef 1 R ile hesaplandı.

## Kısaca

- **Maliyetten önce kenar yok.** 5 dakikada mumun yönünde kapanışta piyasadan giren, stop 2 ATR ve hedef 1 R ile, işlem
  başına {{ G.5.ic.devam:piyasa:s2:h1.brut }} R; tersine giren {{ G.5.ic.ters:piyasa:s2:h1.brut }} R aldı. 6. dersteki
  hafif geri verme burada da görünüyor, büyüklüğü R'nin yüzde birkaçı.
- **Maliyetten sonra her biçim eksi** (stop 2 ATR, hedef 1 R). Aynı iki giriş maliyetten sonra {{ G.5.ic.devam:piyasa:s2:h1.R }} ve
  {{ G.5.ic.ters:piyasa:s2:h1.R }} R. Maliyet (makas ve kayma) işlem başına {{ G.5.ic.devam:piyasa:s2:h1.maliyet }} R.
- **Limit en az kaybeden, ama kenarı yok.** Limit girişte makası ve kaymayı ödemez, çıkışta öder. Mumun yarısına
  limitle giren 5 dakikada maliyetten sonra {{ G.5.ic.devam:limit_0.5:s2:h1.R }} R aldı; maliyetten önce
  {{ G.5.ic.devam:limit_0.5:s2:h1.brut }} R, yani piyasa emrinden kötü.
- **Limit, piyasa girişinin kaybettiği olaylarda dolar.** 5 dakikada mumun yarısına konan limitin dolduğu olaylarda
  aynı anda piyasadan girilseydi işlemlerin {{ T.ic.5.devam:limit_0.5:s2:h1.dolan_kaz }} kadarı kazanırdı; dolmadığı
  olaylarda {{ T.ic.5.devam:limit_0.5:s2:h1.kacan_kaz }}. Bunun büyük kısmı geometridir: limit, fiyat piyasa
  girişinin aleyhine yürüdüğünde dolar.
- **Stop yakınsa maliyet büyür.** 5 dakikada stop 1 ATR'de maliyet işlem başına
  {{ G.5.ic.devam:piyasa:s1:h1.maliyet }} R, 2 ATR'de {{ G.5.ic.devam:piyasa:s2:h1.maliyet }} R, 1 saatte 2 ATR'de
  {{ G.60.ic.devam:piyasa:s2:h1.maliyet }} R.

## On bir giriş biçimi

Mumun **yönünde**:

- **Kapanışta piyasa.** Mum kapanınca, sonraki dakikanın açılışında piyasa emri.
- **Geri çekilmeye limit.** Mumun ucundan mumun boyunun {{ Y.25 }}, {{ Y.50 }} ya da {{ Y.62 }} kadarı geri çekilen
  seviyeye limit. Mum zaten o kadar geri vermişse (kapanış o seviyenin gerisindeyse) emir konmaz.
- **Ucun kırılmasına stop.** Mumun ucunun bir fiyat adımı (pipin onda biri) ötesine stop emri: fiyat yeni bir uç yaparsa girilir.
- **Onay mumundan sonra piyasa.** Sonraki mum, kapanışı büyük mumun kapanışının ötesinde kapanırsa onun kapanışında
  piyasa emri. Onay gelmezse işlem yok.

Mumun **tersine**:

- **Kapanışta piyasa.** Mum kapanınca, mumun tersine piyasa emri.
- **Mumun ucuna limit.** Fiyat mumun ucuna geri gelirse oradan tersine (yukarı mumda uçtan sat).
- **Ucun yarım ATR ötesine limit.** Uzama satılır: fiyat mumun ucunu yarım ATR aşarsa oradan tersine.
- **Mumun yarısının kırılmasına stop.** Fiyat mumun yarısını kırarsa tersine stop emri (geri verme başladı onayı).
  Kapanış zaten yarının gerisindeyse emir yok.
- **Onay mumundan sonra piyasa.** Sonraki mum büyük mumun kapanışının gerisinde kapanırsa, onun kapanışında tersine.

Limit ve stop emirleri büyük mum kapandıktan sonra {{ SB.bekle }} mum boyunca bekler, dolmazsa iptal edilir. Her biçim
iki stop (girişten 1 ya da 2 ATR) ve iki hedefle (riskin 1 ya da 2 katı) koşturuldu; ne stop ne hedef görülürse pozisyon
24 mumun sonunda kapanır.

## 5 dakika

{{# izgara 5 }}

Tablonun okunuşu: önce **maliyetsiz R** sütunu, yani aynı kuralın alış-satış ortasından, makassız ve kaymasız sonucu.
Bütün biçimler sıfırın birkaç yüzde R yakınında. Tersine piyasa girişinin artı olması 6. dersin geri verme okumasıyla
tutarlı. Sonra **net R**: aynı işlemler gerçek fiyatlarla. Fark maliyettir: piyasa ve stop emirlerinde maliyetsiz
sonucun kat kat üstünde, limitlerde iki katı civarında. 5 dakikada mumun {{ Y.25 }} geri çekilmesine limitin maliyeti
işlem başına {{ G.5.ic.devam:limit_0.25:s2:h1.maliyet }} R, kapanışta piyasa girişininki
{{ G.5.ic.devam:piyasa:s2:h1.maliyet }} R.

{{# sekil 01_izgara "On bir giriş biçimi, maliyetten önce ve sonra" }}

## 15 dakika ve 1 saat

**15 dakika**

{{# izgara 15 }}

**1 saat**

{{# izgara 60 }}

Dilim büyüdükçe iki şey değişiyor. Maliyet R cinsinden küçülüyor, çünkü ATR büyüyor ve aynı makas daha büyük bir
mesafenin parçası oluyor. Ve yön değişiyor: 2018–2023'te 1 saatte mumun yönündeki girişlerin çoğu maliyetten önce artı
({{ G.60.ic.devam:piyasa:s2:h1.brut }} R, onay mumuyla {{ G.60.ic.devam:onayli:s2:h1.brut }} R), tersine girişlerin
hepsi eksi. Yine de bu satırda maliyetten sonra 1 saatte de hiçbir biçim artıda değil. 2018–2023'te sıfıra en yakın iki
biçim onay mumu ({{ G.60.ic.devam:onayli:s2:h1.R }} R) ve mumun {{ Y.25 }} geri çekilmesine limit
({{ G.60.ic.devam:limit_0.25:s2:h1.R }} R); 2024 sonrasında ikisi {{ G.60.dis.devam:onayli:s2:h1.R }} ve
{{ G.60.dis.devam:limit_0.25:s2:h1.R }} R.

Izgaranın öbür hücrelerinde (iki stop, iki hedef) maliyetten sonra sıfırın üstüne çıkan tek yer 1 saatte, hedefi 2 R
olan geri çekilme limitleri: mumun {{ Y.25 }} geri çekilmesine limit 2018–2023'te
{{ G.60.ic.devam:limit_0.25:s2:h2.R }} R, 2024 sonrasında {{ G.60.dis.devam:limit_0.25:s2:h2.R }} R; yarısına limit
{{ G.60.ic.devam:limit_0.5:s2:h2.R }} ve {{ G.60.dis.devam:limit_0.5:s2:h2.R }} R. Büyüklükler sıfırdan ayırt
edilemeyecek kadar küçük; bu hücrenin süzgeçli hâli 9. dersin planında sınandı.

## Limit neden ucuz görünür: ters seçim

Limit emir üç şeyi birden yapar. Girişte makas ödemez (fiyat sana gelir), girişte kayma ödemez, ve **yalnız fiyat
aleyhine yürüdüğünde dolar.** Çıkışta (stopta ya da süre dolunca) makas ve kayma yine ödenir. Üçüncüsü ilk ikisini
dengeler. Yukarı bir büyük mumdan sonra yarıya konan alış limiti, fiyat mumun yarısına
indiğinde dolar; yani tam da büyük mumun hareketinin geri alındığı olaylarda. Fiyat hiç geri gelmeden yükselmeye devam
ederse limit dolmaz ve en iyi işlem kaçar.

Bunu ölçmek için her olayda iki soru birlikte soruldu: limit doldu mu, ve aynı anda piyasadan girilseydi (aynı stop ve
hedefle) işlem kazanır mıydı?

{{# ters_secim }}

Limitin dolduğu olaylarda piyasa girişi çoğunlukla kaybediyor; dolmadığı olaylarda çoğunlukla kazanıyor. Fark büyük ve
iki dönemde aynı. Farkın büyük kısmı geometridir: limit, fiyat piyasa girişinin aleyhine mumun yarısı kadar yürüdüğünde
dolar, ve yön bilgisi taşımayan bir yolda da piyasa girişi o olaylarda çoğunlukla kaybederdi. Tablo limitin iyi ya da
kötü bir süzgeç olduğunu söylemez; limitin dolmasının hangi olaylarla birlikte geldiğini gösterir. Limitin net sonucu
5 dakikada piyasa emrinden iyi çıkıyor, çünkü daha iyi bir fiyattan giriyor ve girişte makas ödemiyor. Ama maliyetten
önce piyasa emrinden kötü: 5 dakikada mumun yönünde, yarıya limit {{ G.5.ic.devam:limit_0.5:s2:h1.brut }} R, piyasa
{{ G.5.ic.devam:piyasa:s2:h1.brut }} R. Mumun tersine aynı durum daha da belirgin: kapanışta piyasa maliyetten önce
{{ G.5.ic.ters:piyasa:s2:h1.brut }} R, mumun ucuna limit {{ G.5.ic.ters:limit_uc:s2:h1.brut }} R. Limit, 5 dakikadaki
küçük geri verme kenarını yok ediyor, çünkü fiyatın ucuna geri döndüğü olaylar tam da geri vermenin olmadığı olaylar.

{{# sekil 02_ters_secim "Limit doldu mu, dolmadı mı" }}

Pratik ders: "geri çekilmeyi bekle, limitle gir" tavsiyesi maliyeti düşürür, kenar yaratmaz. Limitin dolum oranı
yüksekse (5 dakikada {{ Y.25 }} geri çekilmeye limit {{ G.5.ic.devam:limit_0.25:s2:h1.dolum }} doluyor) bu iyi haber
değildir: emir, fiyatın kolayca geri geldiği olayların neredeyse tamamında doluyor demektir.

## Stop uzaklığı ve maliyet

Makas ve kayma pip cinsinden sabittir; R cinsinden, stopun uzaklığına bölünür. Stop yaklaştıkça aynı maliyet daha büyük
bir R olur.

{{# sekil 03_maliyet "Stop yakınsa maliyet büyür" }}

5 dakikalık bir ATR'nin medyanı {{ D.5.ic.A_pip }} pip. Stop 1 ATR'deyse planlanan risk birkaç pip ve tek bir makas
bunun önemli bir parçası: 5 dakikada kapanışta piyasa girişinin maliyeti işlem başına {{ G.5.ic.devam:piyasa:s1:h1.maliyet }}
R. Üstelik 1 ATR'de 5 dakikalık olayların {{ G.5.taban_pay }} kadarında risk {{ ON.en_az_risk_pip }} pipin altında
kaldı ve işlem hiç açılmadı (kalanların medyan riski {{ G.5.ic.devam:piyasa:s1:h1.risk }} pip); yani 1 ATR'lik
maliyet yalnız ATR'si büyük olan olayların maliyeti, gerçek fark daha da büyük. Stopu 2 ATR'ye taşımak maliyeti {{ G.5.ic.devam:piyasa:s2:h1.maliyet }} R'ye, 1 saatlik grafiğe geçmek
{{ G.60.ic.devam:piyasa:s2:h1.maliyet }} R'ye indiriyor. Ama hiçbiri kenar yaratmıyor; yalnız kaybı küçültüyor.

## Onay mumu

"Onayı bekle" en sık verilen tavsiyelerden biridir. Ölçüm şunu söylüyor: onay mumu beklemek, olayların bir kısmında hiç
işlem açmamak demek (5 dakikada mumun yönündeki onay {{ G.5.ic.devam:onayli:s2:h1.n }} olayda geldi; büyük mum
{{ D.5.ic.n }} olaydı ve kapanışta piyasa girişi {{ G.5.ic.devam:piyasa:s2:h1.n }} işlem açtı) ve gelen onaydan sonraki girişin maliyetten önceki sonucu kapanışta piyasa
girişinden belirgin farklı değil ({{ G.5.ic.devam:onayli:s2:h1.brut }} ve {{ G.5.ic.devam:piyasa:s2:h1.brut }} R).
Onay bir mumu bekler, ama fiyat o mumda zaten yürümüş olur: giriş daha kötü bir fiyattan yapılır, ve onayın taşıdığı
bilgi kaçırılan fiyatın bedelini ancak karşılıyor. 1 saatte 2018–2023'te en az kaybeden biçim onay mumu oldu.

## Ucun kırılması

Mumun ucunun kırılmasına konan stop emri, mumun yönündeki "momentum" girişidir. 5 dakikada emirlerin
{{ G.5.ic.devam:stop:s2:h1.dolum }} kadarı doldu, maliyetten önce {{ G.5.ic.devam:stop:s2:h1.brut }} R, maliyetten
sonra {{ G.5.ic.devam:stop:s2:h1.R }} R. Stop emri kaymayı öder ve fiyatın zaten yürüdüğü yerden alır. 1 saatte
maliyetten önce {{ G.60.ic.devam:stop:s2:h1.brut }} R; 2024 sonrasında {{ G.60.dis.devam:stop:s2:h1.brut }} R.

## Bu sonuç nasıl okunmalı

Giriş biçimi üç şeyi değiştirir: kaç işlem açıldığını, işlemin hangi fiyattan açıldığını ve ne kadar maliyet ödendiğini.
Yön bilgisini değiştirmez; o, mumun kendisinden gelir ve 6. ders onun küçük olduğunu gösterdi. 5 ve 15 dakikada en az
kaybeden biçim (limit) maliyeti en az ödeyen biçimdir, en çok bilgiyi kullanan biçim değil. "Hangi emirle girmeliyim"
sorusunun dürüst cevabı: kenar yoksa en ucuz emir bile kaybettirir; hiç girmemek ondan da ucuzdur.

## Ölçülmeyenler

- **Kısmi dolum ve kuyruk sırası.** Limit emir, fiyatı ona dokunduğu dakikada tam doldu sayıldı; gerçek bir defterde
  sırada beklemek ve kısmen dolmak vardır, bu da limitin sonucunu tablodakinden kötü yapar.
- **Komisyon.** Yalnız makas ve kayma; komisyon eklenmedi.
- **Değişken kayma.** Kayma sabit bir varsayımdır (haber penceresinde artan); hızlı piyasadaki gerçek kayma ölçülmedi.
- **Dinamik çıkış.** Stop ve hedef sabit; iz süren stop, kısmi kâr alma ölçülmedi.
- **Stop emriyle girişin dolum dakikası.** Dakika verisinde stop emrinin dolduğu dakikanın içindeki sıra görünmez: fiyat
  önce koruyucu stopa uğrayıp sonra girişi tetiklemiş olabilir. Bu derste o dakikada koruyucu stop yalnız dakika stopun
  ötesinde kapandıysa sayıldı ve çıkış stop seviyesinden yazıldı; dakikanın içindeki gerçek sıra ölçülmedi. Bu kural
  2024 sınamasından sonra konuldu; değiştirdiği yalnız stop emirli hücrelerin sonucudur, seçilen ve sınanan girişlerin
  hiçbiri stop emirli değil.
