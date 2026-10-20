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
import Diyagram from '../../components/Diyagram.astro';

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

## Bu dersi masada nasıl kullanırsın

Bu ders sana bir giriş kuralı vermez; hiçbir giriş biçimi maliyetten sonra kenar bulmadı. Verdiği şey bir emir
disiplinidir: büyük bir mumdan sonra başka bir gerekçeyle işleme girmeye karar verdiysen, emrin türü, yeri, bekleme
süresi, stopu ve hedefi sonucu nasıl değiştirir. Masada sırası şöyledir. Önce takvime bakarsın: emir bekleyecekse
bekleyeceği süre büyük bir haberin penceresine düşüyor mu. Sonra kendi gerekçene: büyük mumun dışında bir sebebin var mı,
yoksa yalnız mumun boyuna mı tepki veriyorsun. Sonra stopun uzaklığına ve dilime. En sonda emrin türüne. Aşağıdaki şema
bu sırayı tek sayfada toplar; her adımın dayanağı bu serinin bir dersindeki ölçümdür. Şemadan çıkan cevap "emir yok"
değilse, bundan sonraki bölümler o emrin grafikte nereye konacağını ve dolduğunda ne anlattığını gösterir.

{{# karar emir-akis }}

Şemanın son kutusu bir maliyet seçimini anlatır, bir kenarı değil. Limit girişte makas ödemez, ama yalnız fiyat
aleyhine yürüdüğünde dolar; piyasa emri her olayda girer, girişte de çıkışta da öder. Hangisinin daha az kaybettirdiği
dilime ve emrin yerine göre değişir; stop 2 ATR ve hedef 1 R ile hiçbiri maliyetten sonra artıya geçmez, ızgaranın
artıda kalan tek köşesi de (1 saatte hedefi 2 R olan geri çekilme limitleri) sıfırdan ayırt edilemiyor.

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

### Masada: emirler grafikte nerede durur

On bir biçimin her biri grafikte bir çizgidir. Büyük mum kapandığı anda masada yapılacak ilk iş, mumun iki ucunu ve
yarısını işaretlemektir: limitlerin, stop emirlerinin ve koruyucu stopların hepsi bu üç seviyeden ve ATR'den ölçülür.
Aşağıdaki şemada büyük mum yukarı yönlüdür ve boyu üç ATR kadardır; aşağı mumda her şey aynalanır. Soluk mumlar olası
bir yoldur: emirlerin hangi sırayla dolabileceğini gösterir, fiyatın ne yapacağını değil.

{{# sema yonunde-emirler }}

Şemadaki dört emir aynı mumun aynı yönüne bakar ama dört ayrı olay kümesinde dolar. Kapanışta piyasa emri her olayda
girer. Çeyrek limit, fiyatın biraz geri geldiği hemen her olayda dolar; yarı limit, hareketin yarısının geri alındığı
olaylarda; derin limit, hareketin çoğunun geri alındığı olaylarda. Uca stop emri ise yalnız fiyat yeni bir uç yaptığında
dolar. Yani emrin yeri, hangi olayların işlem olacağını seçer (8. ders, Limit neden ucuz görünür). Mumun tersine kurulan
emirler aynı mantığı ters yönden taşır:

{{# sema tersine-emirler }}

Bu iki şemada yapmayacağın üç şey var. Kapanış zaten bir limitin gerisindeyse, yani mum o kadarını kendi içinde geri
vermişse, o limiti koymazsın; bu derste o emir hiç konmadı ve geri çekilmeyi bekleyen limit, gerçekleşmiş geri çekilmeye
konmaz. Mumun yönünde ve tersine iki emri aynı anda bırakmazsın; ikisinin de dolduğu bir yolda iki zararı birden
taşırsın ve bu bileşim bu derste ölçülmedi. Ve emri bekleme süresi dolduktan sonra fiyatın peşinden taşımazsın: bu
derste her emir büyük mum kapandıktan sonra {{ SB.bekle }} mum bekledi, dolmazsa iptal edildi; peşinden taşınan bir emir
artık bu dersin ölçtüğü emir değildir.

## 5 dakika

{{# izgara 5 }}

Tablonun okunuşu: önce **maliyetsiz R** sütunu, yani aynı kuralın alış-satış ortasından, makassız ve kaymasız sonucu.
Bütün biçimler sıfırın birkaç yüzde R yakınında. Tersine piyasa girişinin artı olması 6. dersin geri verme okumasıyla
tutarlı. Sonra **net R**: aynı işlemler gerçek fiyatlarla. Fark maliyettir: piyasa ve stop emirlerinde maliyetsiz
sonucun kat kat üstünde, limitlerde iki katı civarında. 5 dakikada mumun {{ Y.25 }} geri çekilmesine limitin maliyeti
işlem başına {{ G.5.ic.devam:limit_0.25:s2:h1.maliyet }} R, kapanışta piyasa girişininki
{{ G.5.ic.devam:piyasa:s2:h1.maliyet }} R.

{{# sekil 01_izgara "On bir giriş biçimi, maliyetten önce ve sonra" }}

### Masada: 5 dakikada emir bir maliyet seçimidir

5 dakikalık grafikte büyük mumun ekrandaki görüntüsü en çok aldatan görüntüdür: mum birkaç dakika içinde kapanır, fiyat
ucun yanında titrer ve kaçan bir hareket izlenimi verir. Tablonun maliyetsiz sütunu bu izlenimin yanında ne olduğunu
söyler: bütün biçimler sıfırın çevresinde. Net sütun da girişin biçiminin neyi değiştirdiğini: kaç kez makas ve kayma
ödediğini. Bu dilimde emrin türü bir yön kararı değil, bir maliyet kararıdır.

{{# kart bes-dk-kapanis }}

Bu dilimde yapmayacağın şeyler tablonun kendisinden çıkar. Kapanışta piyasa emriyle mumun yönünde girmezsin; piyasa ve stop
emirleri maliyeti en çok ödeyen satırlardır ve kapanışta piyasa girişi maliyetten önce de artı değildir. Mumun tersine kapanışta piyasa girişinin maliyetsiz
sütundaki küçük artısını da bir kenar saymazsın: maliyetten sonra o satır da eksidir. Ve limitin daha az kaybettirmesini
limitin kazandırması diye okumazsın (8. ders, 5 dakika).

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

### Masada: dilim büyüyünce

1 saatlik grafikte aynı büyük mum başka bir şey anlatır. ATR büyüdüğü için stopun pip cinsinden uzaklığı da büyür ve
aynı makas riskin çok daha küçük bir parçası olur; maliyet satırları bu yüzden kısalır. Yön de değişir: 6. dersin
ölçtüğü hafif devam burada mumun yönündeki girişlerin maliyetten önceki sonucunda görünür, tersine girişler 2018–2023'te
maliyetten önce de eksidir (6. ders, Dilim dilim okuma). Bu iki değişiklik birlikte okunur ve ikisi de bir kenar
değildir: maliyetten sonra stop 2 ATR, hedef 1 R satırında hiçbir biçim artıda değil.

{{# kart saat-tersine }}

1 saatte yapmayacağın şey tek cümledir: uzamış görünen mumu satmazsın, uca ya da ucun ötesine tersine limit koymazsın.
15 dakikada ise dilim iki ucun arasında durur; ne 5 dakikanın maliyet sorununu bütünüyle bırakır ne 1 saatin devamını
taşır. 15 dakikalık bir mumdan sonra girmeyi düşünüyorsan, okuma sırası 5 dakikanınkiyle aynıdır: önce takvim, sonra
gerekçe, sonra stop, en son emir.

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

### Masada: limitin dolması ne anlatır

Bu bölümün masadaki karşılığı tek bir alışkanlıktır: limit dolduğunda bunu bir onay değil bir uyarı olarak okumak.
Dolum, fiyatın senin yönünün aleyhine mumun yarısı kadar yürüdüğünü söyler. Dolmayan limit ise fiyatın o kadar geri
gelmeden yürüdüğünü söyler; o olaylarda piyasadan girilen işlem çoğunlukla kazanırdı, ama limit bekleyen için o işlem
hiç yoktu. Şema aynı limitin iki ayrı günde ne yaşadığını yan yana koyar.

{{# sema ters-secim }}

İki günün ortak noktası şudur: büyük mumun kapandığı anda ikisi aynı görünür. Ayrışma ancak sonraki mumlarda başlar ve
o noktada limit ya çoktan dolmuştur ya da fiyat çoktan gitmiştir. Bunun geometri olduğunu, yani yön bilgisi taşımayan
bir yolda da aynı ayrışmanın görüleceğini unutmazsın: limitin dolduğu olayların kötü gitmesi limitin bir şey bildiğini
göstermez, limitin nerede durduğunu gösterir (8. ders, Limit neden ucuz görünür). Yarısına dönen
büyük mumların yarısında dönüş ilk bir iki mum içinde geldi (6. ders, Yarısına dönen fiyat ne kadar sürede dönüyor);
yani dolum çoğu zaman erken gelir. "Biraz daha beklesem dolardı" diye limiti uzatmak, bekleme süresinin bu derste
ölçülmemiş bir uzantısıdır.

{{# kart yariya-limit }}

Aşağıdaki iki gün aynı kuralla seçildi: 5 dakikalık EUR/USD'de, Londra seansında, takvimde büyük haber olmayan bir saatte, ucunda
kapanan, boyu iki ile üç ATR arasında bir büyük mum. Üstteki günde yarıya konan limit bekleme süresinin içinde doldu ve
fiyat sonra stopu gördü; alttaki günde fiyat yarıya hiç dönmedi ve mumun yönünde yürüdü.

{{# ornek yariya-limit }}

Üstteki günde ① büyük mum kapanır, sonraki mumlarda fiyat ② ile gösterilen yarıya iner ve ③ o ilk dokunuşun mumudur:
limit orada dolar. Ardından fiyat mumun öbür ucunu da geçer ve yarıdan alınan işlemin stopunu görür; o işlem hedefine
hiç yaklaşmaz, ④ izleme penceresinin sonudur. Alttaki günde ① aynı tipte bir mumdur, ② aynı yerde durur, ama ③ yoktur: fiyat yarıya hiç
dokunmaz ve ④'te mumun yönünde, kapanışın belirgin ötesindedir. İki günün ilk birkaç mumu birbirine benzer; hangisinin
hangi güne döneceği ancak fiyat yarıya inip inmediğinde, yani limitin kaderi belli olduğunda görünür. Grafik o andan
sonra bakıldığında "belliydi" der. Bu iki gün kuralı ne doğrular ne yanlışlar: biri dolan limitin kötü gittiği, öbürü
dolmayan limitin kaçırdığı olaydır ve ölçü ikisinin binlerce örneğinin oranıdır.

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

### Masada: stop nereye

Stopun yeri grafikte çoğu zaman "mantıklı" bir yerdir: mumun ucunun hemen ötesi, son dibin altı. Ama sonucu belirleyen
şey o yerin grafikteki anlamı değil, pip cinsinden uzaklığıdır. Makas ve kayma her işlemde aynı pip kadar ödenir; risk
küçüldükçe aynı pip R'nin daha büyük bir parçası olur. Şema aynı girişe konmuş iki stopu ve onların 1 R hedeflerini
yan yana gösterir.

{{# sema stop-uzaklik }}

Şemada iki şey birlikte görünür. Yakın stopun hedefi de yakındır: 1 R, stopun uzaklığı kadardır. Ve bant, yani çıkışta
ödenecek maliyet, iki stopta da aynı genişliktedir; yakın stopta onun riske oranı iki katıdır. 5 dakikada bu oran o
kadar büyür ki olayların önemli bir kısmında planlanan risk işlem açılamayacak kadar küçük kalır: bu derste o olaylar
hiç işleme girmedi, yani 1 ATR'lik satırın maliyeti zaten seçilmiş, ATR'si büyük olayların maliyetidir.

{{# kart stop-1atr }}

Stop konusunda yapmayacağın şeyler: stopu dolumdan sonra uzaklaştırmazsın (bu, ölçülen işlemi bu derste ölçülmemiş
başka bir işleme çevirir); ve stopu yaklaştırıp hedefi 2 R'ye taşıyarak "oran
düzeldi" demezsin. Hedefi 2 R'ye taşımak 5 ve 15 dakikada hiçbir biçimi maliyetten sonra artıya çevirmedi (8. ders,
15 dakika ve 1 saat).

## Onay mumu

"Onayı bekle" en sık verilen tavsiyelerden biridir. Ölçüm şunu söylüyor: onay mumu beklemek, olayların bir kısmında hiç
işlem açmamak demek (5 dakikada mumun yönündeki onay {{ G.5.ic.devam:onayli:s2:h1.n }} olayda geldi; büyük mum
{{ D.5.ic.n }} olaydı ve kapanışta piyasa girişi {{ G.5.ic.devam:piyasa:s2:h1.n }} işlem açtı) ve gelen onaydan sonraki girişin maliyetten önceki sonucu kapanışta piyasa
girişinden belirgin farklı değil ({{ G.5.ic.devam:onayli:s2:h1.brut }} ve {{ G.5.ic.devam:piyasa:s2:h1.brut }} R).
Onay bir mumu bekler, ama fiyat o mumda zaten yürümüş olur: giriş daha kötü bir fiyattan yapılır, ve onayın taşıdığı
bilgi kaçırılan fiyatın bedelini ancak karşılıyor. 1 saatte 2018–2023'te en az kaybeden biçim onay mumu oldu.

### Masada: onayı beklerken

Onay mumunun ekrandaki görüntüsü güven verir: büyük mumdan sonra bir mum daha aynı yöne kapanmıştır. Şema bu güvenin
bedelini gösterir. Onaylı giriş büyük mumun kapanışından değil onay mumunun kapanışından yapılır; stop aynı ATR
uzaklığında durduğu için o da aynı mesafe kadar taşınır. Risk R cinsinden aynı kalır, giriş fiyatı ise daha ileridedir.

{{# sema onay }}

{{# kart onay }}

Onay beklerken yapmayacağın iki şey var. Onay mumunu beklerken aynı anda kapanışta bir piyasa emri de vermezsin; iki
giriş aynı görüşün iki kopyasıdır ve bu bileşim bu derste ölçülmedi. Onay gelmediğinde de "demek ki dönüyor" diye
mumun tersine geçmezsin: mumun tersindeki onaylı giriş de maliyetten sonra eksi, ve gelmeyen onay yalnız işlem olmadığını
söyler. 1 saatte onayın en az kaybeden biçim olması, 2024 sonrasında tekrarlanmadı (8. ders, 15 dakika ve 1 saat).

## Ucun kırılması

Mumun ucunun kırılmasına konan stop emri, mumun yönündeki "momentum" girişidir. 5 dakikada emirlerin
{{ G.5.ic.devam:stop:s2:h1.dolum }} kadarı doldu, maliyetten önce {{ G.5.ic.devam:stop:s2:h1.brut }} R, maliyetten
sonra {{ G.5.ic.devam:stop:s2:h1.R }} R. Stop emri kaymayı öder ve fiyatın zaten yürüdüğü yerden alır. 1 saatte
maliyetten önce {{ G.60.ic.devam:stop:s2:h1.brut }} R; 2024 sonrasında {{ G.60.dis.devam:stop:s2:h1.brut }} R.

### Masada: uca stop emri

Ucun kırılmasına konan stop emri ekranda en "canlı" giriştir: fiyat ucu geçtiği anda hareket hızlanıyormuş gibi
görünür ve emir tam o anda dolar. Ama dolduğu yer, fiyatın zaten yürüdüğü yerdir ve stop emri kaymayı orada öder.
Şemadaki ⑤ işareti bu emri gösterir (yukarıda, mumun yönündeki dört emrin şeması); dolum, olası yolun en sonunda,
fiyat ucun ötesine geçtiğinde gelir.

{{# kart uc-stop }}

Aşağıdaki iki gün yine aynı kuralla seçildi: 15 dakikalık GBP/USD'de, takvimde büyük haber olmayan bir saatte, ucunda
kapanan, boyu iki ile üç ATR arasında bir büyük mum. İki günde de fiyat sonraki mumlarda mumun ucunu aştı; birinde aştıktan sonra geri verdi, öbüründe
hiç geri çekilmeden yürüdü.

{{# ornek uc-stop }}

Üstteki günde ① büyük mum kapanır ve fiyat sonraki mumlarda ucun ötesine geçer; uca konan stop emri o an dolar, bekleme
süresi ({{ SB.bekle }} mum) dolmadan kırılmışsa. Sonra fiyat geri döner, ② ile gösterilen yarıya iner (③ o ilk dokunuş)
ve ④'te ucun kırıldığı yerin belirgin gerisindedir: ucun kırılmasından giren işlem hedefine ulaşmadan fiyat geri
dönmüştür. Alttaki günde ① aynı tipte bir mumdur, uç
yine kırılır, ama fiyat mumun boyunun dörtte biri kadar bile geri gelmez ve ④'te mumun yönünde belirgin ilerdedir; bu
günde ③ yoktur. Kırılma anında iki gün aynı görünür: ikisinde de fiyat ucu geçmiştir ve ikisinde de hareket hızlanıyor
gibidir. Ayrım kırılmadan sonraki mumlarda gelir. Uç ne zaman kırılırsa kırılsın, emrin açık olduğu süre ① ile kırılma
arasındaki mumlar sayılarak figürde okunur; bekleme süresi dolduktan sonraki bir kırılma bu dersin emri için işlem
değildir. Tek bir kırılma ne momentumu kanıtlar ne çürütür; ölçü, uca stop emrinin 5 ve 15 dakikada maliyetten
önce sıfır çevresinde olmasıdır.

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
