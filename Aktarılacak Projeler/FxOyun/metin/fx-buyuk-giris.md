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

Bu ders bir giriş kuralı değil bir emir disiplini verir: başka bir gerekçeyle girersen emrin türü, yeri, süresi, stopu
ve hedefi sonucu nasıl değiştirir. Sıra: takvim, gerekçe, stop ve dilim, en son emrin türü. Büyük mum serisinin emir
kuralları bu dersin "Emri nereye koyarsın" bölümündedir; 6., 7. ve 9. dersler oraya dayanır.

{{# karar emir-akis }}

## On bir giriş biçimi

Mumun **yönünde**:

- **Kapanışta piyasa.** Mum kapanınca, sonraki dakikanın açılışında piyasa emri.
- **Geri çekilmeye limit.** Mumun ucundan mumun boyunun {{ Y.25 }}, {{ Y.50 }} ya da {{ Y.62 }} kadarı geri çekilen
  seviyeye limit. Mum zaten o kadar geri çekilmişse (kapanış o seviyenin gerisindeyse) emir konmaz.
- **Ucun kırılmasına stop.** Mumun ucunun bir fiyat adımı (pipin onda biri) ötesine stop emri: fiyat yeni bir uç yaparsa girilir.
- **Onay mumundan sonra piyasa.** Sonraki mum, kapanışı büyük mumun kapanışının ötesinde kapanırsa onun kapanışında
  piyasa emri. Onay gelmezse işlem yok.

Mumun **tersine**:

- **Kapanışta piyasa.** Mum kapanınca, mumun tersine piyasa emri.
- **Mumun ucuna limit.** Fiyat mumun ucuna geri gelirse oradan tersine (yukarı mumda satış, aşağı mumda alış).
- **Ucun yarım ATR ötesine limit.** Uzamaya karşı girilir: fiyat mumun ucunu yarım ATR aşarsa oradan tersine.
- **Mumun yarısının kırılmasına stop.** Fiyat mumun yarısını kırarsa tersine stop emri (geri çekilme başladı onayı).
  Kapanış zaten yarının gerisindeyse emir yok.
- **Onay mumundan sonra piyasa.** Sonraki mum büyük mumun kapanışının gerisinde kapanırsa, onun kapanışında tersine.

Limit ve stop emirleri büyük mum kapandıktan sonra {{ SB.bekle }} mum boyunca bekler, dolmazsa iptal edilir. Her biçim
iki stop (girişten 1 ya da 2 ATR) ve iki hedefle (riskin 1 ya da 2 katı) koşturuldu; ne stop ne hedef görülürse pozisyon
24 mumun sonunda kapanır.

### Masada: emirler grafikte nerede durur

On bir biçimin her biri grafikte bir çizgidir. Büyük mum kapandığı anda masada yapılacak ilk iş, mumun iki ucunu ve
yarısını işaretlemektir: limitlerin, stop emirlerinin ve koruyucu stopların hepsi bu üç seviyeden ve ATR'den ölçülür.
Aşağıdaki şemada büyük mum yukarı yönlüdür ve boyu üç ATR kadardır; aşağı mumda her şey aynalanır. Soluk mumlar olası
bir yoldur: emirlerin hangi sırayla dolabileceğini gösterir, fiyatın ne yapacağını değil. Şemalarda numaralar şemanın
altındaki maddelere bağlıdır.

{{# sema yonunde-emirler }}

Emrin yeri hangi olayların işlem olacağını seçer (8. ders, Limit neden ucuz görünür: ters seçim). Tersine kurulan
emirler aynı mantığı ters yönden taşır:

{{# sema tersine-emirler }}

Bu şemalarda yapmayacağın iki şey var. Kapanış zaten bir limitin gerisindeyse, yani mum o kadarını kendi içinde geri
çekilmişse, o limiti koymazsın; bu derste o emir hiç konmadı. Mumun yönünde ve tersine iki emri aynı anda bırakmazsın;
ikisinin de dolduğu bir yolda iki zararı birden taşırsın ve bu bileşim bu derste ölçülmedi.

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

5 dakikalık grafikte büyük mum kaçan bir hareket izlenimi verir: mum birkaç dakikada kapanır, fiyat ucun yanında
titrer. Tablonun maliyetsiz sütunu bu izlenimin karşılığını verir (bütün biçimler sıfırın çevresinde), net sütun da
emrin türünün neyi değiştirdiğini: kaç kez makas ve kayma ödendiğini. Bu dilimde emrin türü bir maliyet kararıdır.

{{# kart bes-dk-kapanis }}

## 15 dakika ve 1 saat

**15 dakika**

{{# izgara 15 }}

**1 saat**

{{# izgara 60 }}

Dilim büyüdükçe iki şey değişiyor. Maliyet R cinsinden küçülüyor, çünkü ATR büyüyor ve aynı makas daha büyük bir
mesafenin parçası oluyor. Ve yön değişiyor: 2018–2023'te 1 saatte mumun yönündeki girişlerin çoğu maliyetten önce artı
({{ G.60.ic.devam:piyasa:s2:h1.brut }} R, onay mumuyla {{ G.60.ic.devam:onayli:s2:h1.brut }} R), tersine girişlerin
hepsi eksi; 2024 sonrasında tersine girişler maliyetten önce sıfırın çevresinde kaldı. Maliyetten sonra 1 saatte de bu
satırda hiçbir biçim artıda değil. 2018–2023'te sıfıra en yakın iki biçim onay mumu
({{ G.60.ic.devam:onayli:s2:h1.R }} R) ve mumun {{ Y.25 }} geri çekilmesine limitti
({{ G.60.ic.devam:limit_0.25:s2:h1.R }} R). 2024 sonrasında sıra değişti: onay mumu mumun yönündeki biçimlerin en çok
kaybedeni oldu ({{ G.60.dis.devam:onayli:s2:h1.R }} R), en az kaybeden yarıya limitti
({{ G.60.dis.devam:limit_0.5:s2:h1.R }} R).

Izgaranın öbür hücrelerinde (iki stop, iki hedef) sıfıra en yakın yer 1 saatte, hedefi 2 R olan geri çekilme
limitleri: mumun {{ Y.25 }} geri çekilmesine limit 2018–2023'te {{ G.60.ic.devam:limit_0.25:s2:h2.R }} R, 2024
sonrasında {{ G.60.dis.devam:limit_0.25:s2:h2.R }} R; yarısına limit {{ G.60.ic.devam:limit_0.5:s2:h2.R }} ve
{{ G.60.dis.devam:limit_0.5:s2:h2.R }} R. Izgarada maliyetten sonra artıya geçen hücreler yalnız bu ikisidir ve yalnız
2024 sonrasında; büyüklükleri sıfırdan ayırt edilemeyecek kadar küçük. Aynı emir biçiminin stopu 1 ATR'lik, koşu
süzgeçli bir hâli 9. dersin planına seçildi ve 2024 sonrasında tutmadı (9. ders, Seçilen girişler).

### Masada: dilim büyüyünce

1 saatte aynı makas riskin daha küçük bir parçasıdır ve 6. dersin ölçtüğü hafif devam mumun yönündeki girişlerin
maliyetsiz sonucunda görünür (6. ders, Dilim dilim okuma); ikisi de kenar değildir.

{{# kart saat-tersine }}

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
küçük geri verme kenarını yok ediyor, çünkü fiyatın ucuna geri döndüğü olaylar tam da geri çekilmenin sürmediği
olaylardır.

{{# sekil 02_ters_secim "Limit doldu mu, dolmadı mı" }}

Pratik ders: "geri çekilmeyi bekle, limitle gir" tavsiyesi maliyeti düşürür, kenar yaratmaz. Limitin dolum oranı
yüksekse (5 dakikada {{ Y.25 }} geri çekilmeye limit {{ G.5.ic.devam:limit_0.25:s2:h1.dolum }} doluyor) bu iyi haber
değildir: emir, fiyatın kolayca geri geldiği olayların neredeyse tamamında doluyor demektir.

### Masada: limitin dolması ne anlatır

Bu bölümün masadaki karşılığı tek bir alışkanlıktır: limitin dolmasını bir onay değil bir uyarı olarak okumak. Dolum,
fiyatın senin yönünün aleyhine mumun yarısı kadar yürüdüğünü söyler; dolmayan limit, fiyatın geri gelmeden yürüdüğünü.
Şema aynı limitin iki ayrı günde ne yaşadığını yan yana koyar.

{{# sema ters-secim }}

İki gün kapanışta aynıdır; ayrışma limitin kaderiyle gelir ve geometridir. Yarısına dönen büyük mumların yarısında
dönüş ilk bir iki mumdadır (6. ders, Yarısına dönen fiyat ne kadar sürede dönüyor); limiti bekleme süresinin ötesine
uzatmak bu derste ölçülmemiş bir emirdir.

{{# kart yariya-limit }}

Aşağıdaki iki gün aynı kuralla seçildi: 5 dakikalık EUR/USD'de, Londra seansında, takvimde büyük haber olmayan bir
saatte, ucunda kapanan, boyu iki ile üç ATR arasında yukarı yönlü bir büyük mum. Gerçek grafiklerde numaralar sabittir:
① olay mumu, ② mumun yarısı, ③ fiyatın yarıya ilk dokunduğu mum, ④ izleme penceresinin sonu.

{{# ornek yariya-limit }}

Üstteki günde ① TSİ 11:10'da kapanır ve fiyat sonraki ilk dakikada ② yarıya iner; ③ kapanıştan sonraki ilk mumdur ve
yarıya konan limit orada dolar. Aynı beş dakikalık mumun içinde fiyat büyük mumun dibini de kırar ve limitin 2 ATR
altındaki stopu görür; kapanışta piyasadan giren de aynı mumda stopa giderdi. İşlem hedefine hiç yaklaşmaz ve ④'te fiyat
mumun dibinin belirgin altındadır. Alttaki günde ① TSİ 11:00'da kapanır ve ③ yoktur: ilk mumda fiyat yarıya bir fiyat
adımından az kala döner ve mumun ucunu aşar; yarıdaki limit dolmaz, çeyrek geri çekilmeye konmuş bir limit ise ilk
dakikada dolardı. Fiyat sonra mumun yönünde yürür; kapanışta piyasadan giren 1 R hedefini ikinci mumda görürdü ve ④'te
fiyat kapanışın belirgin ötesindedir. Biri dolan limitin kötü gittiği, öbürü dolmayan limitin kaçırdığı olaydır; ölçü
ikisinin binlerce örneğinin oranıdır.

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

Grafikte en "mantıklı" görünen stop mumun öbür ucunun hemen ötesidir. Bu seride o yer ölçülmedi: ölçülen stop girişten
1 ya da 2 ATR uzaktır ve sonucu belirleyen yerin anlamı değil pip cinsinden uzaklığıdır. 2–3 ATR'lik bir mumda yarıdaki
limitten öbür uca mesafe bir ile bir buçuk ATR'dir; yani öbür ucun ötesi yakın stopa yakın bir yerdir. Şema aynı girişe
konmuş iki stopu ve onların 1 R hedeflerini gösterir.

{{# sema stop-uzaklik }}

{{# kart stop-1atr }}

Stopu dolumdan sonra uzaklaştırmazsın (bu, ölçülen işlemi bu derste ölçülmemiş başka bir işleme çevirir); stopu
yaklaştırıp hedefi 2 R'ye taşıyarak "oran düzeldi" de demezsin: hedefi 2 R'ye taşımak 5 ve 15 dakikada hiçbir biçimi
maliyetten sonra artıya çevirmedi (8. ders, 15 dakika ve 1 saat).

## Onay mumu

"Onayı bekle" en sık verilen tavsiyelerden biridir. Ölçüm şunu söylüyor: onay mumu beklemek, olayların bir kısmında hiç
işlem açmamak demek (5 dakikada mumun yönündeki onay {{ G.5.ic.devam:onayli:s2:h1.n }} olayda geldi; büyük mum
{{ D.5.ic.n }} olaydı ve kapanışta piyasa girişi {{ G.5.ic.devam:piyasa:s2:h1.n }} işlem açtı) ve gelen onaydan sonraki girişin maliyetten önceki sonucu kapanışta piyasa
girişinden belirgin farklı değil ({{ G.5.ic.devam:onayli:s2:h1.brut }} ve {{ G.5.ic.devam:piyasa:s2:h1.brut }} R).
Onay bir mumu bekler, ama fiyat o mumda zaten yürümüş olur: giriş daha kötü bir fiyattan yapılır, ve onayın taşıdığı
bilgi kaçırılan fiyatın bedelini ancak karşılıyor. 1 saatte 2018–2023'te en az kaybeden biçim onay mumu oldu; 2024
sonrasında mumun yönündeki biçimlerin en çok kaybedeniydi.

### Masada: onayı beklerken

Onay mumu güven verir: büyük mumdan sonra bir mum daha aynı yöne kapanmıştır. Şema bu güvenin bedelini gösterir: giriş
onay mumunun kapanışından, yani daha ileriden yapılır ve stop da aynı mesafe kadar taşınır.

{{# sema onay }}

{{# kart onay }}

Onayı beklerken aynı anda kapanışta bir piyasa emri de vermezsin; iki giriş aynı görüşün iki kopyasıdır ve bu bileşim
bu derste ölçülmedi.

## Ucun kırılması

Mumun ucunun kırılmasına konan stop emri, mumun yönündeki "momentum" girişidir. 5 dakikada emirlerin
{{ G.5.ic.devam:stop:s2:h1.dolum }} kadarı doldu, maliyetten önce {{ G.5.ic.devam:stop:s2:h1.brut }} R, maliyetten
sonra {{ G.5.ic.devam:stop:s2:h1.R }} R. Stop emri kaymayı öder ve fiyatın zaten yürüdüğü yerden alır. 1 saatte
maliyetten önce {{ G.60.ic.devam:stop:s2:h1.brut }} R; 2024 sonrasında {{ G.60.dis.devam:stop:s2:h1.brut }} R.

### Masada: uca stop emri

Ucun kırılmasına konan stop emri ekranda en "canlı" giriştir: fiyat ucu geçtiği anda hareket hızlanıyormuş gibi
görünür ve emir tam o anda dolar. Dolduğu yer fiyatın zaten yürüdüğü yerdir ve kayma orada ödenir;
{{# atif sema yonunde-emirler }}'deki ⑤ bu emirdir.

{{# kart uc-stop }}

Aşağıdaki iki gün yine aynı kuralla seçildi: 15 dakikalık GBP/USD'de, takvimde büyük haber olmayan bir saatte, ucunda
kapanan, boyu iki ile üç ATR arasında bir büyük mum; iki günde de uç bekleme süresinin içinde kırıldı.

{{# ornek uc-stop }}

Üstteki gün aşağı yönlü bir mumdur (TSİ 16:30, Londra–New York örtüşmesi). Fiyat kapanıştan birkaç dakika sonra önce
② yarıya döner (③), sonra yeniden iner ve kapanıştan sonraki dördüncü mumda dibi kırar: uca konan satış stop emri orada
dolar. Fiyat bir mum daha ilerler, ama TSİ 18:00 mumunda geri döner, girişin 2 ATR üstündeki stopu görür ve aynı mumda
büyük mumun tepesini de aşar; ④'te fiyat tepenin belirgin üstündedir. Alttaki gün yukarı yönlü, tepesinde kapanmış bir
mumdur (TSİ 12:30, Londra seansı): uç ilk mumda kırılır, fiyat mumun boyunun dörtte biri kadar bile geri gelmez ve uçtan
giren işlem 1 R hedefini ikinci mumda görüp kapanır. Fiyatın asıl yürüyüşü sonra, ABD istihdam raporuyla (New York
08:30, TSİ ABD yaz saatinde 15:30) gelir: emrin bekleme süresinin dışında, izleme penceresinin içinde; ④'te fiyat
kapanışın çok ötesindedir. Emrin dolup dolmadığını figürde ① ile kırılma arasındaki mumları sayarak okursun: emir
{{ SB.bekle }} mum açıktır ve süre dolduktan sonraki bir kırılma bu dersin emri için işlem değildir. Tek bir kırılma ne
momentumu kanıtlar ne çürütür.

## Emri nereye koyarsın

Bu bölüm, büyük mumdan bağımsız bir gerekçeyle işleme girmeye karar vermiş biri içindir: bir seviye, bir haber okuması,
başka bir dilimdeki bir yapı. Büyük mum o kararı vermez; yalnız emrin nasıl yazılacağını değiştirir. Büyük mum
serisinin (6–9. dersler) emir kuralları burada durur. Aşağıdakilerin hiçbiri bir kenar vaadi değildir; her biri ölçülen
bir maliyetin ya da bir seçimin nereden geldiğini söyler.

### Giriş emri

- **Piyasa emri** her olayda girer, makası ve kaymayı girişte de çıkışta da öder; maliyetsiz sonucu büyük mumun kendi
  okumasını taşır (8. ders, Kısaca). 5 dakikada bu emri, maliyetin stopa oranını yazmadan vermezsin.
- **Limit emir** girişte makas ve kayma ödemez, çıkışta öder; yeri hangi olayları seçtiğini belirler, bedeli kazanacak
  olayları kaçırmasıdır (8. ders, Limit neden ucuz görünür: ters seçim). Kapanışın zaten gerisinde kalan bir seviyeye
  konmaz. 5 dakikada mumun yönünde gireceksen limiti mumun çeyrek ya da yarı geri çekilmesine koyarsın; "yarıyı bekle"
  tek başına bir kural değildir: çeyrek limit daha sık dolar, yarı limit daha derin bir geri çekilmeyi bekler ve ikisi
  de maliyetten sonra eksidir (8. ders, 5 dakika). Dolum bir uyarıdır.
- **Stop emriyle giriş** yalnız fiyat seviyeyi geçtiğinde dolar ve kaymayı orada öder; maliyetten önce sıfır
  çevresinde (8. ders, Ucun kırılması).
- **Onay mumundan sonra piyasa** olayların bir kısmında işlem açmaz, açtığında daha ileriden açar (8. ders, Onay mumu).

### Stop

Stop girişten 2 ATR uzaktadır; limitle giriyorsan limitin fiyatından. Bu seride ölçülen stoplar 1 ve 2 ATR'dir; 1 ATR'de
maliyetin payı büyür: 5 dakikada işlem başına {{ G.5.ic.devam:piyasa:s1:h1.maliyet }} R, 2 ATR'de
{{ G.5.ic.devam:piyasa:s2:h1.maliyet }} R (8. ders, Stop uzaklığı ve maliyet). Mumun öbür ucunun ötesine konan stop bu
seride ölçülmedi: 2–3 ATR'lik bir mumda o yer yarıdaki limite bir ile bir buçuk ATR uzaklıktadır, yani yakın stopun
maliyetini taşır; mumun tersine kapanışta girerken mumun ucu girişin hemen yanındadır. 2 ATR'lik stop büyük bir mumda
mumun içinde de kalabilir; ölçülen budur. Risk {{ ON.en_az_risk_pip }} pipin altında kalan olaylarda işlem hiç
açılmadı; masada da aynı sınırı sorarsın. Fikri 2 ATR'lik bir stopla taşıyamıyorsan bir üst dilimde kurmak maliyetin
payını küçültür; fikrin kendisini değiştirmez.

### Hedef

Hedef planlanan riskin katıdır: 1 R ya da 2 R. Hedef uzaklaştıkça ona daha az işlem ulaşır, ulaşan daha çok kazanır;
bu derste ikisinin dengesi 5 ve 15 dakikada hiçbir biçimi maliyetten sonra artıya çevirmedi (8. ders, 15 dakika ve
1 saat). Ne stop ne hedef görülürse pozisyon 24 mumun sonunda kapanır; emri yazarken o kapanışın saatini de yazarsın.
1 saatte bu pencere bir günü kapsar; perşembe akşamından sonra açılan 1 saatlik mumların penceresi hafta sonuna
taştığı için bu mumlar ölçüye girmedi (6. ders, Büyük mum nasıl tanımlandı).

### Bekleme süresi ve iptal

Limit ve stop emri büyük mum kapandıktan sonra {{ SB.bekle }} mum bekler, dolmazsa iptal edilir; ölçülen emir budur ve
süre mumla sayıldığı için dilimle uzar. Süreye seans geçişi düşüyorsa (Londra açılışı Londra 07:00, TSİ İngiltere yaz
saatinde 09:00, kış saatinde 10:00) emri geçişten önce çekmek bu seride ölçülmemiş bir ek kuraldır; haber penceresi için
aşağıdaki kural geçerlidir. Emri süre dolmadan şu iki durumda da çekersin, çünkü ikisinde de emrin ölçülen hâli artık
yoktur (masa uygulaması; ölçülmedi): fiyat yeni bir uç yapar ve limiti peşinden taşımak istersen (taşınan limit başka
bir emirdir); emrin dayandığı gerekçe o sürede geçersiz olursa. Farklı bekleme süreleri bu derste ölçülmedi.

### Haber penceresinde

Bekleyen bir emrin süresine takvimdeki büyük bir haberin penceresi (açıklamadan iki dakika önce – on beş dakika sonra)
düşüyorsa emri açıklamadan önce çekersin. Bu bir disiplin kuralıdır, ölçüm sonucu değil: o pencerede piyasa ve stop
emirlerine {{ ON.haber_kayma_pip }} pip ek kayma varsayıldı, haber anındaki makas ve gerçek kayma ölçülmedi, limit emir
o pencerede de kaymasız sayıldı ve emri çekmenin sonuca etkisi bu seride ölçülmedi. Saatler: ABD istihdam ve enflasyon
verisi New York 08:30 (TSİ ABD yaz saatinde 15:30, kış saatinde 16:30), FOMC kararı New York 14:00 (TSİ ABD yaz
saatinde 21:00, kış saatinde 22:00), ECB kararı Frankfurt 14:15 (TSİ Avrupa yaz saatinde 15:15, kış saatinde 16:15),
BoE kararı Londra 12:00 (TSİ İngiltere yaz saatinde 14:00, kış saatinde 15:00). Haberin kendi mumu ayrıca okundu ve bir
okuma çıkarmadı: az sayıdadır ve sonraki yolu bir yön söyleyemeyecek kadar dağınıktır (7. ders, Haber mumu). Haber
olmayan bir mumun bekleyen emrine sonradan haber düşmesi ayrıca ölçülmedi.

## Sık yapılan hatalar

1. **"Limitin dolum oranı yüksek, limit iyi çalışıyor."** Çeyrek limit fiyatın kolayca geri geldiği olayların neredeyse
   hepsinde dolar; seçici değildir (8. ders, Limit neden ucuz görünür: ters seçim).
2. **"Limit dolmadı, fiyat kaçıyor, piyasadan girerim."** Kaçırılan kazanç kapanıştaki piyasa girişinindir ve o fiyat
   geride kalmıştır. Geç piyasa girişi bu derste ölçülmedi; kapanıştaki giriş de maliyetten sonra eksidir (8. ders,
   5 dakika).
3. **"Hedefi 2 R yaparsam oran düzelir."** 5 ve 15 dakikada hiçbir biçimi maliyetten sonra artıya çevirmedi (8. ders,
   15 dakika ve 1 saat).

## Masa kontrol listesi

Büyük mum kapandıktan sonra, emir vermeden önce sırayla:

1. Hangi seanstayım? Asya New York 17:00 ile Londra 07:00 arası (TSİ ikisi yaz saatindeyken 00:00–09:00), Londra seansı
   Londra 07:00 ile New York 08:00 arası (TSİ ikisi yaz saatindeyken 09:00–15:00), örtüşme New York 08:00 ile Londra
   16:30 arası (TSİ ikisi yaz saatindeyken 15:00–18:30); ikisi kış saatindeyken TSİ karşılıkları bir saat sonra.
2. Emrin bekleme süresine ({{ SB.bekle }} mum) büyük bir haberin penceresi düşüyor mu? ABD verisi New York 08:30 (TSİ
   ABD yaz saatinde 15:30, kış saatinde 16:30), FOMC New York 14:00 (TSİ ABD yaz saatinde 21:00, kış saatinde 22:00),
   ECB Frankfurt 14:15 (TSİ Avrupa yaz saatinde 15:15, kış saatinde 16:15), BoE Londra 12:00 (TSİ İngiltere yaz
   saatinde 14:00, kış saatinde 15:00). Düşüyorsa emri açıklamadan önce çekersin (disiplin kuralı; ölçülmedi).
3. FX gününün devrine yakın mıyım? New York 16:50–17:10 (TSİ ABD yaz saatinde 23:50–00:10, kış saatinde 00:50–01:10)
   makas sıçrar; o mumlar bu serinin ölçülerine girmedi.
4. Büyük mumun dışında bir gerekçem var mı? Yoksa emir yok.
5. Mumun iki ucunu ve yarısını işaretledim mi; kapanış hangi seviyenin gerisinde?
6. Dilim kaç, ATR kaç pip; stop girişten 2 ATR mi ve risk makasın kaç katı?
7. Emrin türü hangi olay kümesini seçiyor, hangi maliyeti ödüyor?
8. Limit dolarsa ne düşüneceğimi, dolmazsa kovalamayacağımı yazdım mı?
9. Hedef 1 R mi 2 R mi; ne stop ne hedef görülürse pozisyon hangi saatte kapanır?

## Grafik okuma alıştırmaları

**Alıştırma 1.** 5 dakikalık EUR/USD'de Londra 08:40'ta (TSİ İngiltere yaz saatinde 10:40, kış saatinde 11:40) yukarı
yönlü, boyu üç ATR kadar bir mum ucunda kapanıyor; takvimde haber yok. Masadaki biri "kaçıyor" deyip kapanışta
piyasadan alıyor. Senin başka bir gerekçen yok. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Emir vermezsin: tek gerekçe büyük mumun kendisi ve hiçbir giriş biçimi bunu maliyetten sonra artıya çevirmedi (8. ders,
5 dakika). Mumun uçlarını ve yarısını işaretleyip izlersin. Gerekçen olsaydı bile kapanışta piyasa emri vermezdin; 5
dakikada piyasa ve stop emirleri maliyeti en çok ödeyen satırlardır.

</details>

**Alıştırma 2.** Başka bir gerekçeyle 5 dakikalık yukarı bir büyük mumdan sonra yarıya alış limiti koydun. Üçüncü mumda
limit doldu; dolum mumu uzun ve kırmızı. Ucuzdan almış gibisin ve ikinci bir limitle ortalamayı düşürmek aklından
geçiyor. Ne yaparsın, ne yapmazsın? ({{# atif sema ters-secim }}, A günü.)

<details>
<summary>Çözüm</summary>

Stopu ve hedefi baştan yazdığın yerde bırakırsın ve dolumu bir uyarı olarak okursun: limitin dolduğu olaylarda aynı
anda piyasadan giren işlem çoğunlukla kaybederdi (8. ders, Limit neden ucuz görünür: ters seçim). İkinci limitle
pozisyonu büyütmezsin; bu bileşim bu derste ölçülmedi. Stopu da "fiyat ucuzladı" diye uzaklaştırmazsın.

</details>

**Alıştırma 3.** 1 saatlik GBP/USD'de New York 10:00'da (TSİ ABD yaz saatinde 17:00, kış saatinde 18:00) başlayan aşağı
yönlü büyük bir mum önceki mumların birkaç katı boyunda kapanıyor. "Fazla gitti, ucuna limit koyup alırım" diye
düşünüyorsun. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Mumun tersine girmezsin: 1 saatte tersine girişler 2018–2023'te maliyetten önce de eksiydi, uca konan limit dahil;
2024 sonrasında maliyetten önce sıfırın çevresinde kaldılar ve maliyetten sonra hepsi eksi (8. ders, 15 dakika ve
1 saat; 6. ders, Dilim dilim okuma). Mumun yönünde başka bir gerekçen varsa çeyrek ya da yarı geri çekilmeye limit
koyarsın, stop limitin fiyatından 2 ATR. Onay mumunu daha güvenli bir seçenek saymazsın: 2018–2023'te en az kaybeden
biçimdi, 2024 sonrasında mumun yönündeki biçimlerin en çok kaybedeni oldu. Bunların hiçbirinin stop 2 ATR, hedef 1 R
satırında maliyetten sonra artıda olmadığını bilirsin.

</details>

**Alıştırma 4.** 5 dakikalık USD/JPY'de New York 08:20'de (TSİ ABD yaz saatinde 15:20, kış saatinde 16:20) yukarı bir
büyük mum kapanıyor; New York 08:30'da (TSİ ABD yaz saatinde 15:30, kış saatinde 16:30) ABD istihdam raporu var. Başka
bir gerekçeyle ucun kırılmasına stop emri koymayı düşünüyorsun. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Emri koymazsın, koyduysan açıklamadan önce çekersin: {{ SB.bekle }} mumluk bekleme süresine haber penceresi düşüyor.
Bu bir disiplin kuralıdır, ölçüm sonucu değil: o pencerede stop emrine bu derste {{ ON.haber_kayma_pip }} pip ek kayma
varsayıldı, haber anındaki makas ve gerçek kayma ölçülmedi, emri çekmenin etkisi de ölçülmedi (8. ders, Emri nereye
koyarsın). Uca stop emri haber dışında da maliyetten önce sıfır çevresindeydi (8. ders, Ucun kırılması).

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
- **Değişken kayma ve haber anındaki makas.** Kayma sabit bir varsayımdır (haber penceresinde artan); hızlı piyasadaki
  gerçek kayma ve haber anındaki makas ölçülmedi.
- **Mumun ucuna göre stop.** Stop girişten 1 ya da 2 ATR uzakta ölçüldü; mumun öbür ucunun ötesine konan stop ölçülmedi.
- **Emri haberden ya da seans geçişinden önce çekmek.** Ölçülen emir {{ SB.bekle }} mumun sonuna kadar bekledi; erken
  çekmenin sonuca etkisi ölçülmedi.
- **Dinamik çıkış.** Stop ve hedef sabit; iz süren stop, kısmi kâr alma ölçülmedi.
- **Stop emriyle girişin dolum dakikası.** Dakika verisinde stop emrinin dolduğu dakikanın içindeki sıra görünmez: fiyat
  önce koruyucu stopa uğrayıp sonra girişi tetiklemiş olabilir. Bu derste o dakikada koruyucu stop yalnız dakika stopun
  ötesinde kapandıysa sayıldı ve çıkış stop seviyesinden yazıldı; dakikanın içindeki gerçek sıra ölçülmedi. Bu kural
  2024 sınamasından sonra konuldu; değiştirdiği yalnız stop emirli hücrelerin sonucudur, seçilen ve sınanan girişlerin
  hiçbiri stop emirli değil.
