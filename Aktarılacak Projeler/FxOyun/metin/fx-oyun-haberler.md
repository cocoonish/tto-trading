---
title: 'FX Gün İçi Oyun Planı 4: Haber Mumları'
description: "ABD istihdam ve enflasyon verisi, Fed, ECB ve BoE kararları: açıklamadan sonraki ilk {{ AN.nfp.tf }} dakikanın mumu ne söylüyor? Güçlü, normal, reddedilen ve küçük haber mumundan sonra fiyatın davranışı, şansın vereceği payla kıyas, iki dönemde nasıl değiştiği, ve planın 2024 sonrasında artıda kalan tepkileri."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'haber', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · resmî yayım takvimleri · önceden kayıt'
ozet: "Haber mumu serinin en oynak anıdır ve en az olayı olanıdır. ABD verisinden sonra ilk mumun sürme payı iki dönemde de şansın altında. Merkez bankası kararlarında planın üç tepkisi 2024 sonrasında artıda kaldı, ama işlem sayıları bir hüküm kurmaya yetmiyor. Ders haber anlarının oyun planını ve sınırlarını verir."
seviye: 'orta'
onkosul: ['fx-oyun-okuma']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';
import Diyagram from '../../components/Diyagram.astro';

Bir veri ya da karar açıklandığında fiyat birkaç dakika içinde yeni bilgiyi fiyatlamaya çalışır. İlk mum bu yüzden
haber anlarında genellikle açılışlardan ve fiksinglerden büyüktür (2024 sonrasında yarıya limitli tepkinin ortanca riski
ABD verisinin normal mumunda {{ B.referans.veri.normal.dis.risk_pip }} pip, açılışın normal mumunda
{{ B.referans.acilis.normal.dis.risk_pip }} pip) ve çok daha seyrek gelir: bir açılış her iş günü gelir, bir istihdam
verisi ayda bir, bir merkez bankası kararı yılda sekiz kez. Bu ders iki aileyi ayrı okur: **ABD verileri** (tarım dışı
istihdam ve tüketici fiyatları) ve **merkez bankası kararları** (Fed, ECB, BoE).

{{# an_tablo veri mb }}

Saatler resmî yayım takviminden alınır, tahmin edilmez. Burada **ilk mum** açıklamadan sonraki ilk {{ AN.nfp.tf }}
dakikadır. Tipik boy o anın son {{ S.haber_pencere }} olayından ölçülür. Sınamada açıklamadan iki dakika önce ile on
beş dakika sonrası arasında piyasa, stop ve kırılım emirlerine ek {{ ON.haber_kayma_pip }} pip kayma varsayıldı; makas
gerçek alış-satış fiyatlarından ödendi, haber anındaki büyüklüğü ayrıca ölçülmedi.

## Plan tek cümlede

**Haber mumu tek başına bir yön sinyali değildir.** ABD verisinin normal ve reddedilen ilk mumu şanstan seyrek
sürüyor. Merkez bankası kararlarında güçlü ya da reddedilen ilk mumun yönünde kalmak 2024 sonrasında artıda kaldı, ama
bu sonuç birkaç karar gününe dayanıyor; bir hüküm değil, izlenecek bir aday.

## Bu dersi masada nasıl kullanırsın

Bu ders haber anında bir yön vermez; masada üç şey söyler: açıklamadan önce defterde ne bırakılmaz, ilk beş dakikalık
mum nasıl okunur, ne zaman beklenir ve ne zaman masadan kalkılır. Dersin bütün sayıları ilk mumla başlar ve iki saatlik
izlemeyle biter. Aşağıdaki şema bu sırayı beş soruya çevirir: bir soru seni durdurursa sağdaki sonuç geçerlidir,
durdurmazsa bir alttaki soruya inilir.

{{# karar haber-akis }}

## Haberden sonra fiyat nereye gidiyor

İlk mum kapandıktan sonra ortalama fiyat, mumun yönünde ve mumun boyu cinsinden; iki aile, iki dönem.

{{# sekil 01_patika "Haber mumundan sonra ortalama fiyat yolu, ilk mumun yönünde" }}

Haber anlarında olay sayısı az olduğu için ortalama yol açılışlardaki kadar düzgün değildir; tek bir olay çizgiyi
belirgin oynatabilir. Şekil bir yön söylemek için değil, iki dönemin birbirinden ne kadar ayrıştığını görmek için.

### Masada: açıklamadan önceki dakikalar

Açıklamadan önceki dakikalar ölçülmedi; buradaki kurallar sınamanın maliyet kurallarından ve ilk mumun tanımından
gelir. Süresine haber penceresi düşen bekleyen bir emri açıklamadan önce çekersin. Bu bir disiplin kuralıdır, ölçüm
sonucu değil: penceredeki ek kayma bir varsayımdı, haber anındaki makas ve gerçek kayma ölçülmedi, emri çekmenin
sonuca etkisi de ölçülmedi. Mumun sınıfı kapanışta verilir: bir ucu süpürüp öbür yöne kapanan mum (reddedilen) ilk
saniyelerde güçlü bir mum gibi görünebilir.

{{# sema dar-aralik }}

{{# kart haber-oncesi }}

## ABD verileri

Yarısına dönüş, devam ve dönüş payı; yanında yolun aynasında (yön rastgele olsaydı) aynı payın değeri:

{{# ayna veri }}

Normal ve reddedilen veri mumunda sürme payı iki dönemde de aynanın altında. Normal mumda 2018–2023'te
{{ Y.ic.veri.normal.devam }} (ayna {{ Y.ic.veri.normal.devam_ayna }}), 2024 → döneminde {{ Y.dis.veri.normal.devam }}
({{ Y.dis.veri.normal.devam_ayna }}). Veri ilk beş dakikada fiyatı bir yöne itiyor, ve o itiş sonraki iki saatte şanstan
seyrek sürüyor. 2024 → döneminde fark büyüdü. Güçlü veri mumunda ise devam payı aynayla aynı
({{ Y.ic.veri.guclu.devam }} ve {{ Y.ic.veri.guclu.devam_ayna }}).

Bu bir okuma. İlk mumun tersine giren bir tepki ABD verisi için önceden yazılmadığı için sınanmadı; sınanmadan bir
kural sayılmaz. Her veri tek tek:

{{# davranis veri }}

2024 → döneminde güçlü veri mumu yalnız {{ D.dis.veri.guclu.n }} olay. İki dönemin farkının sebebi bu derste ölçülmedi:
bir piyasa değişimi de (veriden sonraki ilk dakikalarda fiyatlamanın daha hızlı bitmesi), küçük örneklemin dalgalanması
da olabilir.

### Masada: verinin ilk beş dakikası

Tarım dışı istihdam ve TÜFE New York 08:30'da (TSİ 15:30, ABD kış saatinde 16:30) gelir; ilk mum New York 08:35'te
(TSİ 15:35, ABD kış saatinde 16:35) kapanır. Masadaki okuma o kapanışla başlar ve üç adımdır.

1. **Sınıfı koyarsın,** o anın son {{ S.haber_pencere }} olayının tipik boyuna göre (1. ders, İlk mumun dört sınıfı).
2. **Üç seviye çizersin:** mumun iki ucu ve yarısı. Sonraki iki saatin okuması bu üç çizginin karşısında yapılır.
3. **Neyi beklemeyeceğini söylersin.** Normal ve reddedilen veri mumunun yönünde sürmesini beklemezsin: iki dönemde de
   şanstan seyrek sürdü. Güçlü veri mumunda devam payı aynayla aynı; mumun ucunda kapanması yön bilgisi değildir.

İzleme New York 10:35'te (TSİ 17:35, ABD kış saatinde 18:35) biter; arada New York açılışı (New York 09:30, TSİ
16:30, ABD kış saatinde 17:30) geçer ve bu ders ikisini ayırmadı.

{{# sema veri-normal }}

{{# kart veri-normal }}

Aşağıdaki iki gün bir kuralla seçildi: EUR/USD'de tarım dışı istihdamın normal ilk mumuna uyan olaylardan, biri
yarıya dönüp itişi sürdürmeyen, öbürü itişi sürdüren en son olay.

{{# ornek nfp-normal }}

Üstteki gün 1 Eylül 2023'tür. ① verinin yukarı ilk mumudur (TSİ 15:30–15:35), normal sınıftadır ve ucuna yakın
kapanır. Fiyat ucu bir pipten az aşar, yedi dakika sonra ② yarıya geri çekilir (③, TSİ 15:42), TSİ 16:30'da mumun
ucuna kadar yeniden çıkar ama onu aşamaz; TSİ 17:00'de öbür ucu kırar ve ④'te (TSİ 17:35) mumun dibinin belirgin
altındadır: ilk mumun yükselişi tamamen geri alınmıştır. Alttaki gün 3 Kasım 2023'tür. ① aynı sınıftan, aşağı yukarı
aynı boyda ve yine ucuna yakın kapanmış bir yukarı mumdur; kapandığı anda üstteki günden ayırt edilemez. Fiyat yarıya
hiç dönmez, kapanıştan sonraki ilk mumda ucu aşar, TSİ 17:00'de ucun neredeyse bir mum boyu ötesine gider ve ④'te ucun
biraz ötesinde biter. Tek bir gün kuralı ne doğrular ne yanlışlar; okuma bir yön tahmini değil, bir sıklıktır.

## Merkez bankası kararları

{{# ayna mb }}

Kararlarda reddedilen ilk mum iki dönemde de şanstan sık sürüyor: 2018–2023'te {{ Y.ic.mb.reddedilen.devam }}
(ayna {{ Y.ic.mb.reddedilen.devam_ayna }}), 2024 → döneminde {{ Y.dis.mb.reddedilen.devam }}
({{ Y.dis.mb.reddedilen.devam_ayna }}). Ama olay sayısı küçük ({{ D.ic.mb.reddedilen.n }} ve
{{ D.dis.mb.reddedilen.n }}). Güçlü karar mumu 2018–2023'te aynayla aynıydı ({{ Y.ic.mb.guclu.devam }} ve
{{ Y.ic.mb.guclu.devam_ayna }}); 2024 → döneminde {{ D.dis.mb.guclu.n }} olayda {{ Y.dis.mb.guclu.devam }} sürdü ve
tersine dönen olmadı. Her karar tek tek:

{{# davranis mb }}

Kararın ilk beş dakikası karar metnidir; BoE'de toplantı tutanağı da aynı anda yayımlanır. Fed'de basın toplantısı
karardan yarım saat sonra başlar (2019'dan beri her kararda; 2018'de yalnız çeyrek sonu toplantılarında), ECB'de
bugün yarım saat sonra (2022 ortasına kadar üç çeyrek saat sonra), ve izlenen {{ AN.fomc.pencere }} dakika onu da
içerir. Yani bir karar mumunun "devam etmesi", metnin ve basın toplantısının aynı yöne bakması anlamına gelebilir.
Basın toplantısının ayrı etkisi bu derste ölçülmedi.

### Masada: karar metni ve basın toplantısı

İlk {{ AN.nfp.tf }} dakikalık mum karar metninin fiyatıdır; ikinci dalga basın toplantısıdır: Fed New York 14:30 (TSİ
21:30, ABD kış saatinde 22:30), ECB Frankfurt 14:45 (TSİ 15:45, Avrupa kış saatinde 16:45); BoE'de tutanak kararla
gelir. Ölçülen paylar Fed'de ve ECB'de iki dalganın toplamıdır, yani karar mumu kapandığında kararın okuması
bitmemiştir. Normal karar mumu çoğu zaman yarısına döner, ama yönü rastgele bir yol da aynı sıklıkta dönerdi. Reddedilen
karar mumu iki dönemde de şanstan sık sürdü, güçlü karar mumu 2024 sonrasında birkaç karar gününde sürdü; ikisinde de
olay az. Masada işlem açmazsın: mumun iki ucunu ve toplantının saatini işaretler, toplantıyı izler ve adayı deftere
yazarsın. Öbür uç kırılırsa karar mumunun okuması biter.

{{# sema iki-dalga }}

{{# kart karar-guclu }}

Aşağıdaki iki gün de kuralla seçildi: EUR/USD'de Fed kararının normal ilk mumu; biri öbür ucu kırarak, öbürü mumun
yönünde sürerek biten en son olay.

{{# ornek fomc-normal }}

Üstteki gün 3 Mayıs 2023'tür. ① kararın yukarı ilk mumudur (TSİ 21:00–21:05); uzun bir üst fitili vardır ve yarısının
hemen üstünde kapanır, bu yüzden fiyat ② yarıya hemen sonraki mumda dokunur (③). Öbür uç basın toplantısının ilk
mumunda (TSİ 21:30) kırılır; fiyat pencerenin geri kalanında o ucun çevresinde dolaşır ve ④'te (TSİ 23:05) mumun alt
yarısında, açılışının biraz üstündedir: yükselişin çoğu geri alınmıştır. Alttaki gün 20 Mart 2019'dur. ① yine normal
sınıftadır ama biçimi farklıdır: gövdesi neredeyse mumun tamamıdır ve ucunda kapanır. Fiyat yarıya hiç dönmez,
kapanıştan sonraki ilk mumda ucu aşar, basın toplantısı başladıktan sonra (TSİ 21:30) ucun üç çeyrek mum boyu kadar
ötesine gider ve ④'te ucun yaklaşık yarım mum boyu ötesindedir. İki mumun biçim farkı sınıfın içinde ölçülmedi; tek bir
karar günü hangi biçimin hangi sonu verdiğini söylemez.

## Küçük haber mumu

Açıklama ilk beş dakikada fiyatı oynatmamışsa, sonra kırıldığı tarafa ne kadar gidiyor:

{{# kucuk veri mb }}

Fed kararında küçük ilk mumdan sonra kırılan tarafta bir mum boyu ilerleme {{ K.ic.fomc.ilerle }}
(2024 → {{ K.dis.fomc.ilerle }}): karar metni fiyatı oynatmamışsa, hareket çoğu zaman sonra geliyor; basın toplantısı
izlenen sürenin içinde. ABD verisinde ise küçük ilk mum 2024 → döneminde daha da az ilerliyor (enflasyon verisinde
{{ K.dis.cpi.ilerle }}). ECB ve BoE'nin olay sayıları küçük ({{ K.dis.ecb.n }} ve {{ K.dis.boe.n }}).

### Masada: fiyatı oynatmayan açıklama

Küçük ilk mum fiyatın oynamadığını söyler, yön söylemez; okuma önce kırılan uçla başlar. Fed'de kırılımın metinden mi
toplantıdan mı geldiği ayrılmadı, bu yüzden okuma toplantının başlangıcından (TSİ 21:30, ABD kış saatinde 22:30) önce
bitmiş sayılmaz. Sınanan biçim iki uca birer kırılım emridir: biri dolunca öbürü iptal olur, stop öbür ucun mum boyunun
onda biri ötesindedir, hedef yarım R. Bunu "sıkışma patlar" diye bir kenar saymazsın. ABD verisinin küçük mumunda
kırılım maliyetten önce küçük bir artı, maliyetle iki dönemde de eksiydi (2018–2023'te
{{ B.referans.veri.kucuk.ic.brut }} → {{ B.referans.veri.kucuk.ic.R }} R, 2024 → {{ B.referans.veri.kucuk.dis.brut }} →
{{ B.referans.veri.kucuk.dis.R }} R). Karar mumunda 2018–2023'te eksi ({{ B.referans.mb.kucuk.ic.R }} R), 2024
sonrasında artı ama zayıf ({{ B.referans.mb.kucuk.dis.R }} R); maliyetin payı {{ B.referans.mb.kucuk.ic.maliyet }} ve
{{ B.referans.mb.kucuk.dis.maliyet }} R (5. ders, Maliyet nereye gidiyor). Bir R hedefli biçimler karar mumunda
2018–2023'te denendi ve hiçbiri maliyetten sonra artıda kalmadı (en iyisi {{ I.mb.kucuk.R }} R); 2024 sonrasında
sınanmadı.

{{# sema kucuk-karar }}

{{# kart karar-kucuk }}

## Trend

Haber anlarında olay sayısı trend ayrımı için yetmiyor: bir sınıfı üçe bölünce hücrelerin çoğunda birkaç düzine,
kararlarda birkaç olay kalıyor. Plan haber anlarında trendi kullanmaz.

## Bu okumaları işleme çevirmek

Haber anlarında planın iki tür tepkisi var. **Referans tepkiler** açılış ve fiksinglerle aynı kuralla kuruldu: yarısına
limit, yarım R hedef; küçük mumda kırılım. 2024 → dönemindeki sonuç:

{{# kisa referans veri mb }}

**İşlem tepkileri** önceden yazılmış seçim kuralıyla seçildi: 2018–2023'te denenen adayların içinden maliyetten sonra
artıda kalan en iyisi. Kural artıyı şart koştuğu için seçilen tepkilerin 2018–2023 sonucu kendiliğinden artıdır; kanıt
yalnız 2024 → sonucudur.

{{# bacaklar islem veri mb }}

{{# sekil 02_bacaklar "Haber anlarında işlem tepkileri: 2024 sonrasında net sonuç ve güven aralığı" }}

- **Güçlü karar mumu, kapanışta mumun yönünde, yarım R hedef.** 2024 → döneminde {{ B.islem.mb.guclu.dis.n }}
  işlemin {{ B.islem.mb.guclu.dis.kazanma }} kadarı kazandı, net {{ B.islem.mb.guclu.dis.R }} R; hiçbiri stopta
  bitmedi. Ama bu {{ B.islem.mb.guclu.dis.n }} işlem yalnız {{ B.islem.mb.guclu.dis.gun_n }} karar gününe düşüyor; aynı
  kararda paritelerin işlemleri birlikte hareket eder. Karar günlerinden yeniden örneklenen aralık
  {{ B.islem.mb.guclu.dis.gun_alt }} … {{ B.islem.mb.guclu.dis.gun_ust }} R. {{ ON.hukum_en_az }} işlemin altında hüküm
  kurulmaz ("{{ B.islem.mb.guclu.hukum }}"). Stop geniş: ortanca risk {{ B.islem.mb.guclu.dis.risk_pip }} pip.
- **Reddedilen karar mumu, kapanışta reddin yönünde, bir R hedef.** {{ B.islem.mb.reddedilen.dis.n }} işlem
  ({{ B.islem.mb.reddedilen.dis.gun_n }} karar günü), net {{ B.islem.mb.reddedilen.dis.R }} R; ölçülemedi.
- **Normal karar mumu, yarısına limit, bir R hedef.** {{ B.islem.mb.normal.dis.n }} işlemde
  ({{ B.islem.mb.normal.dis.gun_n }} karar günü) net {{ B.islem.mb.normal.dis.R }} R; aralık
  {{ B.islem.mb.normal.dis.alt }} … {{ B.islem.mb.normal.dis.ust }}, hüküm "{{ B.islem.mb.normal.hukum }}".
- **Güçlü veri mumu, yarısına limit, hedef mumun ucu.** 2024 → döneminde {{ B.islem.veri.guclu.dis.n }} işlemde
  {{ B.islem.veri.guclu.dis.R }} R. İşlemlerin {{ B.islem.veri.guclu.dis.zaman_pay }} kadarı ne hedefe ne stopa ulaşıp
  sürenin sonunda kapandı: verinin ilk mumundan sonraki itişin sürmemesi burada da görünüyor.
- **Küçük veri mumu, kırılımda, bir R hedef.** 2018–2023'te işlem başına {{ B.islem.veri.kucuk.ic.R3 }} R ile
  seçildi; 2024 → döneminde {{ B.islem.veri.kucuk.dis.n }} işlemde net {{ B.islem.veri.kucuk.dis.R }} R, hüküm
  "{{ B.islem.veri.kucuk.hukum }}". Maliyetsiz sonucu artı ({{ B.islem.veri.kucuk.dis.brut }} R); makas ve
  varsayılan ek kayma onu eksiye çeviriyor.

## Emri nereye koyarsın

Emrin genel kuralları (giriş türleri, emrin ömrü, haber penceresinde bekleyen emir) 1. dersin "Emri nereye koyarsın"
bölümündedir; burada yalnız haber anına özgü olanlar var. Haber mumu bir giriş sinyali değildir; bu bölüm başka bir
gerekçeyle girecek olan içindir.

- **Piyasa emri, ilk mum kapanınca.** Güçlü ve reddedilen karar mumunun işlem tepkileri böyle kuruldu. Giriş hâlâ haber
  penceresinin içindedir: makası ve sınamada varsayılan {{ ON.haber_kayma_pip }} pip ek kaymayı öder. Stop öbür ucun
  ötesinde ve geniştir; güçlü karar mumunda ortanca risk {{ B.islem.mb.guclu.dis.risk_pip }} pip.
- **Limit, mumun yarısına.** Yön sınıflarının referans tepkileri böyle kuruldu. Limit yalnız fiyat yarıya geri
  geldiğinde dolar; dolum, mumun yönündeki itişin yarısının geri alındığını söyler. Büyük mumda bu olaylarda piyasa
  girişi çoğunlukla kaybetti (8. ders, Limit neden ucuz görünür: ters seçim); haber mumunda bu ayrım ölçülmedi.
- **Stop emri, kırılan uca.** Küçük mumun tepkileri iki uca birer kırılım emriyle kuruldu; biri dolunca öbürü iptal.

**Stop** referans tepkilerde öbür ucun mum boyunun onda biri, iki işlem tepkisinde yarısı kadar ötesindedir; mumun
içine konan stop denenmedi ve riski üç pipin altında kalan işlem açılmadı. **Hedef** yarım R, bir R ya da mumun kendi
ucudur. Onay mumundan sonra giriş haber anında ölçülmedi; büyük mumda onayın bilgisi kaçırılan fiyatın bedelini ancak
karşıladı (8. ders, Onay mumu).

**Emrin ömrü.** Limit ve kırılım emri ilk mum kapandıktan bir saat sonra düşer (ön kayıttaki süre, ölçülerek
seçilmedi); dolan pozisyon ne hedefe ne stopa ulaşırsa iki saatlik izlemenin sonunda kapanır. Güçlü veri mumunun
tepkisinde 2024 sonrasında işlemlerin {{ B.islem.veri.guclu.dis.zaman_pay }} kadarı böyle kapandı. Basın toplantısı
karar mumunun öbür ucunu kırarsa bekleyen emri çekersin, çünkü karar mumunun okuması bitmiştir (masa uygulaması;
ölçülmedi). Limit bir saatte dolmadıysa fiyat yarıya hiç gelmemiştir; bu kovalamak için bir gerekçe değildir. İlk mumdan
sonra on dakika daha beklemek ek kayma penceresinden çıkmaktır; bunun sonuca etkisi ölçülmedi.

{{# sema emir-yerleri }}

{{# kart iki-saat }}

## Sık yapılan hatalar

- **"Sürmüyorsa döner" diye tersine girmek.** Ters yönde bir tepki önceden yazılmadı ve sınanmadı; sürmemek ile dönmek
  ayrı ölçülerdir. Dayanak: 4. ders, "ABD verileri".
- **Karar mumunu son söz saymak.** Basın toplantısı izlenen sürenin içindedir; ölçülen devam ve dönüş payları iki
  dalganın toplamıdır. Dayanak: 4. ders, "Merkez bankası kararları"; 5. ders, "Günün haritası".
- **Birkaç karar gününü kural saymak.** Güçlü karar mumunun artı sonucu {{ B.islem.mb.guclu.dis.gun_n }} karar gününe
  dayanıyor; {{ ON.hukum_en_az }} işlemin altında hüküm kurulmaz. Dayanak: 4. ders, "Bu okumaları işleme çevirmek".

## Masa kontrol listesi

1. Bugün takvimde hangi açıklama var ve saati TSİ kaçta? ABD verisi TSİ 15:30 (ABD kış saatinde 16:30), Fed TSİ 21:00
   (ABD kış saatinde 22:00), ECB TSİ 15:15 (Avrupa kış saatinde 16:15), BoE TSİ 14:00 (İngiltere kış saatinde 15:00).
2. Defterde süresine haber penceresi düşen bir emir var mı? Varsa açıklamadan önce çekiyor muyum? Açık pozisyonun
   stopu o anın ilk mumunun tipik boyu kadar bir hareketin içinde kalıyor mu?
3. Açıklamadan iki dakika önce ile on beş dakika sonrası arasındaki her piyasa ve stop emrinin seviyesinden kötü
   dolabileceğini hesaba kattım mı?
4. İlk beş dakikalık mum kapandı mı? ABD verisinde TSİ 15:35 (ABD kış saatinde 16:35), Fed'de TSİ 21:05 (ABD kış
   saatinde 22:05).
5. Mumun sınıfı ne: güçlü, normal, reddedilen, küçük? Sınıfı o anın tipik boyuna göre mi koydum?
6. Mumun iki ucu ve yarısı çizili mi?
7. ABD verisiyse: mumun yönünde sürmesini bir beklenti gibi taşıyor muyum?
8. Kararsa: basın toplantısı ne zaman? Fed TSİ 21:30 (ABD kış saatinde 22:30), ECB TSİ 15:45 (Avrupa kış saatinde
   16:45); BoE'de tutanak kararla birlikte gelir.
9. Başka bir gerekçeyle giriyorsam: stop mumun öbür ucunun ötesinde mi, risk pip cinsinden ne kadar, makas bu riskin ne
   kadarı?
10. İlk mumdan bu yana iki saat geçti mi? ABD verisinde TSİ 17:35 (ABD kış saatinde 18:35), Fed'de TSİ 23:05 (ABD kış
    saatinde ertesi gün 00:05). Geçtiyse haber okuması bitmiştir.

## Grafik okuma alıştırmaları

**1.** Tarım dışı istihdam açıklandı. EUR/USD'de ilk beş dakikalık mum yukarı; boyu tipik boya yakın, kapanışı
ortasına yakın. Sonraki iki mum ucun hemen altında, hafifçe yukarı. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Mum normaldir ({{# atif sema veri-normal }}). İki ucu ve yarısını işaretlersin. Mumun yönünde kalmazsın:
normal veri mumunun itişi iki dönemde de şanstan seyrek sürdü. Tersine de girmezsin: o tepki sınanmadı. Başka bir
gerekçeyle mumun yönünde gireceksen limit yarıya, stop öbür ucun ötesine; limitin dolması itişin yarıya kadar geri
alındığını söyler. Dayanak: 4. ders, "ABD verileri"; 5. ders, "Referans tepkiler".

</details>

**2.** ABD yaz saatinde Fed kararı TSİ 21:00'de açıklandı; ilk mum küçük. TSİ 21:20'de fiyat hâlâ mumun
aralığında. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Beklersin. Basın toplantısı TSİ 21:30'da başlar ve izlenen süre onu içerir; okuma hangi ucun önce kırıldığıyla
başlar ve kırılımdan önce taraf seçmezsin. Sınanan biçim iki uca birer kırılım emridir: stop öbür ucun mum boyunun onda
biri ötesinde, hedef yarım R. Makas ve kayma bu riskin görünür bir parçasıdır: maliyetin payı 2018–2023'te
{{ B.referans.mb.kucuk.ic.maliyet }} R, 2024 sonrasında {{ B.referans.mb.kucuk.dis.maliyet }} R'ydi. Dayanak: 4. ders,
"Küçük haber mumu"; 5. ders, "Maliyet nereye gidiyor".

</details>

**3.** ECB kararından sonra güçlü bir aşağı mum geldi; yarım saat sonra basın toplantısı başlıyor. Biri bunun,
karar mumunun yönünde yarım R hedefli tepkinin tam örneği olduğunu söylüyor. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Bunu bir kural saymazsın. Güçlü karar mumu 2018–2023'te aynayla aynıydı; 2024 sonrasındaki artı sonuç birkaç karar
gününe dayanıyor ve "ölçülemedi" hükmü taşıyor; ECB'nin kendi güçlü mumları bir okuma kurmaya bile yetmiyor. İşlem
açmadan toplantıyı izler, sonucu adayın satırı olarak deftere yazarsın. Başka bir gerekçeyle girersen stop öbür ucun
ötesinde ve geniştir; toplantı öbür ucu kırarsa okuma biter. Dayanak: 4. ders, "Merkez bankası kararları"; 4. ders, "Bu
okumaları işleme çevirmek".

</details>

**4.** ABD ve İngiltere yaz saatindeyken, tarım dışı istihdamdan iki buçuk saat sonra (TSİ 18:00) fiyat ilk
mumun ucunun çok ötesinde. Bu, mumun yönünde girmek için bir gerekçe mi?

<details>
<summary>Çözüm</summary>

Değil. Ölçü iki saatte biter ve bu dersin o saatten sonrası için söyleyecek bir şeyi yoktur. TSİ 18:00 üstelik
Londra fiksingidir (Londra 16:00); okuma artık o anındır ve 3. dersin konusudur. Haberle açılmış pozisyon hâlâ açıksa
kapatırsın; bekleyen emir bir saat önce zaten düşmüştür. Dayanak: 1. ders, "İncelenen on an"; 4. ders, "Bu okumaları
işleme çevirmek".

</details>

## Haber anları için masa kartı

- **Haber mumu yeni bilginin ilk fiyatıdır, son fiyatı değil.** Yarısına dönüş haberde de sıktır.
- **ABD verisinin normal ve reddedilen ilk mumunun yönü sonraki iki saatte şanstan seyrek sürer.** Güçlü veri mumunun
  devamı aynayla aynıdır; 2024 sonrasında veri mumunun yönüne dayanan okuma daha da zayıf.
- **Karar metni fiyatı oynatmadıysa hareket sonra gelebilir.** Fed'de küçük ilk mumdan sonra kırılım iki dönemde de
  çoğu zaman yol aldı; üç bankanın küçük karar mumu kırılımı bir işleme çevrildiğinde ise iki dönem ayrı işaret verdi.
- **Merkez bankası kararlarındaki üç işlem tepkisi 2024 sonrasında artıda kaldı.** Hiçbirinin karar günü sayısı bir
  hüküm kurmaya yetmiyor. Bir sonraki dönemde, bugünkü kuralla, değiştirilmeden sınanmadan bir kural sayılmaz.
- **Haber anının maliyeti bir varsayımla hesaplandı.** Pencerede piyasa ve stop emirlerine ek kayma varsayıldı; haber
  anındaki makas ve gerçek kayma ölçülmedi. Süresine bu pencere düşen emri açıklamadan önce çekersin: bu bir disiplin
  kuralıdır, ölçüm sonucu değil.
