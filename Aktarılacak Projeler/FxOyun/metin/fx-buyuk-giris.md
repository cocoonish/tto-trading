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

## Emri nereye koyarsın

Bu bölüm, büyük mumdan bağımsız bir gerekçeyle işleme girmeye karar vermiş biri içindir: bir seviye, bir haber okuması,
başka bir dilimdeki bir yapı. Büyük mum o kararı vermez; yalnız emrin nasıl yazılacağını değiştirir. Aşağıdakilerin
hiçbiri bir kenar vaadi değildir. Her biri, ölçülen bir maliyetin ya da ölçülen bir seçimin nereden geldiğini söyler.

### Giriş emri

- **Piyasa emri** her olayda girer ve makası ile kaymayı hem girişte hem çıkışta öder. Seçtiği bir olay kümesi yoktur;
  bu yüzden maliyetsiz sonucu büyük mumun kendi okumasını taşır: 6. dersteki hafif geri verme burada da görünür
  (8. ders, Kısaca). Gerekçen fiyatın hemen
  yürümesini istiyorsa ve 5 dakikalık grafikteysen, ödediğin maliyetin stopuna oranını yazmadan bu emri vermezsin.
- **Limit emir** girişte makas ve kayma ödemez, çıkışta öder. Yeri, hangi olayları seçtiğini belirler: çeyrek limit
  neredeyse her olayda, yarı limit hareketin yarısı geri alındığında, derin limit hareketin çoğu geri alındığında dolar.
  Limitin bedeli, kazanacak olayları kaçırmasıdır (8. ders, Limit neden ucuz görünür). Limiti, büyük mumun kapanışının
  zaten gerisinde kalan bir seviyeye koymazsın.
- **Stop emriyle giriş** (ucun kırılması, ya da tersine yarının kırılması) yalnız fiyat o seviyeyi geçtiğinde dolar ve
  kaymayı orada öder. Momentumu yakalamak için konur; bu derste maliyetten önce sıfır çevresinde kaldı (8. ders, Ucun
  kırılması).
- **Onay mumundan sonra piyasa** olayların bir kısmında hiç işlem açmaz, açtığında daha ileriden açar. Onayın bilgisi
  kaçırılan fiyatı ancak karşılar (8. ders, Onay mumu).

### Stop

Stop girişten ATR cinsinden ölçülür; bu derste 1 ya da 2 ATR. Grafikteki "mantıklı" yer ne olursa olsun, sorulacak
soru stopun pip uzaklığının makasa oranıdır. 5 dakikada 1 ATR'lik stopla maliyet işlem başına
{{ G.5.ic.devam:piyasa:s1:h1.maliyet }} R, 2 ATR'de {{ G.5.ic.devam:piyasa:s2:h1.maliyet }} R oldu; risk
{{ ON.en_az_risk_pip }} pipin altında kalan olaylarda bu derste işlem hiç açılmadı ve masada da aynı sınırı sorarsın
(8. ders, Stop uzaklığı ve maliyet). Aynı fikri 2 ATR'lik bir stopla 5 dakikada taşıyamıyorsan, bir üst dilimde kurmak
maliyetin payını küçültür; fikrin kendisini değiştirmez. Limitle girdiysen stop limitin fiyatından ölçülür, mumun
kapanışından değil.

### Hedef

Hedef planlanan riskin katıdır: 1 R ya da 2 R. Hedefi uzaklaştırmak kazanma oranını düşürür, kazanan işlemin
büyüklüğünü artırır; bu derste ikisinin dengesi maliyetten sonra 5 ve 15 dakikada hiçbir biçimi artıya çevirmedi. Tek
istisna 1 saatte, hedefi 2 R olan geri çekilme limitleridir ve büyüklüğü sıfırdan ayırt edilemiyor (8. ders, 15 dakika
ve 1 saat). Ne stop ne hedef görülürse pozisyon 24 mumun sonunda kapanır; bu süre dilime göre iki saat, altı saat ya da
bir gündür ve emri yazarken o kapanışın saatini de yazarsın.

### Bekleme süresi ve iptal

Bu derste limit ve stop emirleri büyük mum kapandıktan sonra {{ SB.bekle }} mum bekledi; süre mumla sayıldığı için
dilimle birlikte uzar, 1 saatlik grafikte aynı sayıda mum 5 dakikalığın on iki katı süredir. Dolmayan emir iptal edildi. Masada üç durumda emri süre
dolmadan da çekersin, çünkü üçünde de emrin bu derste ölçülen hâli artık yoktur: bekleme süresinin içine takvimde büyük
bir haber girerse; mumun yönündeki bir limit beklenirken fiyat yeni bir uç yapar ve sen limiti yukarı taşımak
istersen (taşınan limit başka bir emirdir); ve emrin dayandığı gerekçe o sürede geçersiz olursa. Farklı bekleme süreleri
bu derste ölçülmedi.

### Haber penceresinde

Bu derste takvimdeki büyük bir haberin iki dakika öncesinden on beş dakika sonrasına kadar piyasa ve stop emirleri
{{ ON.haber_kayma_pip }} pip daha kötü doldu; bu bir varsayımdır, hızlı piyasadaki gerçek kayma ölçülmedi. Limit emir
bu pencerede de kaymasız sayıldı; gerçek bir defterde bunun doğru olduğu ölçülmedi. Saatler: ABD istihdam ve enflasyon
verisi New York 08:30 (TSİ ABD yaz saatinde 15:30, kış saatinde 16:30), FOMC kararı New York 14:00 (TSİ ABD yaz
saatinde 21:00, kış saatinde 22:00), ECB kararı Frankfurt 14:15 (TSİ Avrupa yaz saatinde 15:15, kış saatinde 16:15),
BoE kararı Londra 12:00 (TSİ İngiltere yaz saatinde 14:00, kış saatinde 15:00). Haber mumunun kendisi bir okuma
taşımaz: az sayıdadır ve sonraki yolu bir yön söyleyemeyecek kadar dağınıktır (7. ders, Kısaca; 9. ders, Büyük
mum için oyun planı). Bu yüzden masadaki kural sadedir: büyük mumdan sonra bekleyen bir emrin süresi haber penceresine
düşüyorsa emri bırakmazsın.

## Sık yapılan hatalar

1. **"Limit doldu, demek ki doğru yerden aldım."** Dolum, fiyatın aleyhine mumun yarısı kadar yürüdüğünü söyler; o
   olaylarda aynı anda piyasadan giren işlem çoğunlukla kaybederdi. Dolum bir uyarıdır (8. ders, Limit neden ucuz
   görünür).
2. **"Limitin dolum oranı yüksek, demek ki limit iyi çalışıyor."** Çeyrek limitin neredeyse her olayda dolması, fiyatın
   kolayca geri geldiği olayların neredeyse tamamını işleme çevirdiği anlamına gelir; seçici değildir (8. ders, Limit
   neden ucuz görünür).
3. **"Limit dolmadı, fiyat kaçıyor, piyasadan girerim."** Dolmayan limitin kaçırdığı kazanç, kapanışta piyasa girişinin
   kazancıdır ve o fiyat bekleme süresi içinde geride kalmıştır. Geç bir piyasa girişi bu derste ölçülmedi; kapanıştaki
   piyasa girişinin kendisi maliyetten sonra eksidir (8. ders, 5 dakika).
4. **"Stopu yakın koyarsam kaybım küçük olur."** Pip olarak küçülen kayıp, R cinsinden büyüyen maliyetle gelir; 5
   dakikada 1 ATR'lik stopla maliyet 2 ATR'dekinden belirgin büyük (8. ders, Stop uzaklığı ve maliyet).
5. **"Onay mumunu beklersem güvenli girerim."** Onaylı giriş daha ileriden girer ve maliyetten önce kapanıştaki piyasa
   girişinden belirgin farklı değildir (8. ders, Onay mumu).
6. **"Uç kırıldı, momentum başladı."** Uca stop emri kaymayı fiyatın zaten yürüdüğü yerde öder ve maliyetten önce sıfır
   çevresindedir (8. ders, Ucun kırılması).
7. **"Mum çok uzadı, uçtan satarım."** 5 dakikadaki küçük geri verme kenarını uca konan tersine limit yok eder, çünkü
   fiyatın uca geri döndüğü olaylar geri vermenin olmadığı olaylardır; 1 saatte tersine girişler 2018–2023'te maliyetten
   önce de eksidir (8. ders, Limit neden ucuz görünür; 8. ders, 15 dakika ve 1 saat).
8. **"Hedefi 2 R yaparsam oran düzelir."** Hedefi uzaklaştırmak 5 ve 15 dakikada hiçbir biçimi maliyetten sonra artıya
   çevirmedi (8. ders, 15 dakika ve 1 saat).

## Masa kontrol listesi

Büyük mum kapandıktan sonra, emir vermeden önce sırayla:

1. Saat kaç ve hangi seanstayım? Asya Londra 07:00'den önce (TSİ İngiltere yaz saatinde 09:00'dan önce, kış saatinde
   10:00'dan önce), Londra seansı Londra 07:00 ile New York 08:00 arası (TSİ ikisi yaz saatindeyken 09:00–15:00),
   örtüşme New York 08:00 ile Londra 16:30 arası (TSİ ikisi yaz saatindeyken 15:00–18:30); ikisi kış saatindeyken TSİ
   karşılıkları bir saat sonradır.
2. Emrin bekleme süresi ({{ SB.bekle }} mum) takvimdeki büyük bir haberin penceresine düşüyor mu? ABD verisi New York
   08:30 (TSİ ABD yaz saatinde 15:30, kış saatinde 16:30), FOMC New York 14:00 (TSİ ABD yaz saatinde 21:00, kış saatinde
   22:00). Düşüyorsa emir yok.
3. FX gününün devrine yakın mıyım? New York 16:50–17:10 (TSİ ABD yaz saatinde 23:50–00:10, kış saatinde 00:50–01:10)
   makas sıçrar; o mumlar bu serinin ölçülerine girmedi.
4. Büyük mumun dışında bir gerekçem var mı? Yoksa emir yok.
5. Mumun iki ucunu ve yarısını işaretledim mi? Kapanış hangi seviyenin gerisinde?
6. Dilim kaç, ATR kaç pip? Stop 1 ATR mi 2 ATR mi, ve planlanan risk makasın kaç katı?
7. Emrin türü ne: piyasa, limit, stop, onay? Hangi olay kümesini seçiyor ve hangi maliyeti ödüyor?
8. Limit dolarsa bunun ne anlattığını yazdım mı? Dolmazsa fiyatı kovalamayacağımı?
9. Hedef 1 R mi 2 R mi; ne stop ne hedef görülürse pozisyon hangi saatte kapanır?
10. Emri hangi koşulda süre dolmadan çekerim: haber, taşınmak istenen limit, geçersizleşen gerekçe?

## Grafik okuma alıştırmaları

**Alıştırma 1.** 5 dakikalık EUR/USD grafiğinde, Londra 08:40'ta (TSİ İngiltere yaz saatinde 10:40) yukarı yönlü, boyu
üç ATR kadar bir mum ucunda kapanıyor. Takvimde o saatlerde bir haber yok. Masadaki bir arkadaşın "kaçıyor" deyip
kapanışta piyasadan alıyor. Senin başka bir gerekçen yok. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Emir vermezsin: tek gerekçe büyük mumun kendisi ve hiçbir giriş biçimi bunu maliyetten sonra artıya çevirmedi (8. ders,
5 dakika). Mumun iki ucunu ve yarısını işaretleyip izlersin. Başka bir gerekçen olsaydı bile kapanışta piyasa emri
vermezdin; 5 dakikada piyasa ve stop emirleri maliyeti en çok ödeyen satırlardır. Arkadaşının işlemi bir kenar değil,
bu dersin en pahalı satırlarından biridir.

</details>

**Alıştırma 2.** Başka bir gerekçeyle 5 dakikalık yukarı bir büyük mumdan sonra yarıya alış limiti koydun. Üçüncü mumda
limit doldu; dolum mumu uzun ve kırmızı. Ekranda ucuz bir fiyattan almış gibisin ve aklından ikinci bir limitle
ortalamayı düşürmek geçiyor. Ne yaparsın, ne yapmazsın? (Yarıya alış limiti şemasındaki A gününe bak.)

<details>
<summary>Çözüm</summary>

Stopu ve hedefi emri koyarken yazdığın yerde bırakırsın. Dolumu bir uyarı olarak okursun: limitin dolduğu olaylarda
aynı anda piyasadan giren işlem çoğunlukla kaybederdi (8. ders, Limit neden ucuz görünür). İkinci bir limitle pozisyonu
büyütmezsin; bu bileşim bu derste ölçülmedi ve dolum zaten fiyatın aleyhine yürüdüğünün işaretidir. Stopu da "fiyat
ucuzladı" diye uzaklaştırmazsın.

</details>

**Alıştırma 3.** 1 saatlik GBP/USD grafiğinde New York 10:00'da (TSİ ABD yaz saatinde 17:00) başlayan aşağı yönlü büyük
bir mum, önceki mumların birkaç katı boyunda kapanıyor. Günlük grafikte de göze batıyor. "Fazla gitti, ucuna limit
koyup alırım" diye düşünüyorsun. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Mumun tersine girmezsin: 1 saatte tersine girişler 2018–2023'te maliyetten önce de eksiydi, uca ve ucun yarım ATR
ötesine konan tersine limitler dahil (8. ders, 15 dakika ve 1 saat; 6. ders, Dilim dilim okuma). Mumun yönünde başka
bir gerekçen varsa çeyrek ya da yarı geri çekilmeye limit ya da onay mumundan sonra piyasa emri, stop 2 ATR; bunların da
maliyetten sonra stop 2 ATR, hedef 1 R satırında artıda olmadığını bilirsin.

</details>

**Alıştırma 4.** 5 dakikalık USD/JPY'de New York 08:20'de (TSİ ABD yaz saatinde 15:20) yukarı bir büyük mum kapanıyor.
Takvimde New York 08:30'da (TSİ ABD yaz saatinde 15:30) ABD istihdam raporu var. Başka bir gerekçeyle ucun kırılmasına stop emri
koymayı düşünüyorsun. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Emri bırakmazsın: {{ SB.bekle }} mumluk bekleme süresi haber penceresine düşüyor. O pencerede stop emri bu derste
{{ ON.haber_kayma_pip }} pip daha kötü dolduruldu ve gerçek kayma ölçülmedi; haber mumunun kendisi de bir yön okuması
taşımıyor (7. ders, Kısaca; 9. ders, Büyük mum için oyun planı). Uca stop emri haber dışında da maliyetten önce
sıfır çevresindeydi (8. ders, Ucun kırılması).

</details>

**Alıştırma 5.** 5 dakikalık AUD/USD'de ATR birkaç pip. Bir büyük mumdan sonra stopu mumun ucunun hemen ötesine,
girişten bir ATR'ye koymak istiyorsun; grafikte çok makul görünüyor. Ne yaparsın, ne yapmazsın? (Aynı makas, iki stop
şemasına bak.)

<details>
<summary>Çözüm</summary>

Riski pip olarak yazar, makasla yan yana koyarsın. Bu derste risk {{ ON.en_az_risk_pip }} pipin altında kalan olayda
işlem açılmadı; 5 dakikada 1 ATR'de olayların {{ G.5.taban_pay }} kadarı bu yüzden işlem dışı kaldı. Kalan olaylarda da
maliyet 1 ATR'de 2 ATR'dekinden belirgin büyük (8. ders, Stop uzaklığı ve maliyet). Stopu 2 ATR'ye koyarsın ya da aynı
fikri 15 dakika veya 1 saatte kurarsın. Hedefi 2 R yaparak yakın stopu "telafi etmezsin".

</details>

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
