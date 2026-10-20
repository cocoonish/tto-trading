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
haber anlarında açılışlardan ve fiksinglerden çok daha büyüktür ve çok daha seyrek gelir: bir açılış her iş günü gelir,
bir istihdam verisi ayda bir, bir merkez bankası kararı yılda sekiz kez. Bu ders iki aileyi ayrı okur: **ABD verileri**
(tarım dışı istihdam ve tüketici fiyatları) ve **merkez bankası kararları** (Fed, ECB, BoE).

{{# an_tablo veri mb }}

Saatler resmî yayım takviminden alınır, tahmin edilmez. Burada **ilk mum** açıklamadan sonraki ilk {{ AN.nfp.tf }}
dakikadır. Tipik boy o anın son {{ S.haber_pencere }} olayından ölçülür. Haber anında makas açılır ve emirler kayar;
maliyet bu yüzden açıklamadan iki dakika önce ile on beş dakika sonrası arasında ek {{ ON.haber_kayma_pip }} pip
kayma içerir.

## Plan tek cümlede

**Haber mumu tek başına bir yön sinyali değildir.** ABD verisinin ilk mumu şanstan seyrek sürüyor. Merkez bankası
kararlarında güçlü ya da reddedilen ilk mumun yönünde kalmak 2024 sonrasında artıda kaldı, ama bu sonuç birkaç karar
gününe dayanıyor; bir hüküm değil, izlenecek bir aday.

## Bu dersi masada nasıl kullanırsın

Bu ders haber anında bir yön vermez; masada üç şey söyler: açıklamadan önce defterde ne bırakılmaz, ilk beş dakikalık
mum nasıl okunur, ne zaman beklenir ve ne zaman masadan kalkılır. Açıklamadan önceki dakikalar ölçülmedi; dersin bütün
sayıları ilk mumla, yani açıklamadan sonraki ilk {{ AN.nfp.tf }} dakikayla başlar ve iki saatlik izlemeyle biter.
Aşağıdaki şema bu sırayı beş soruya çevirir: bir soru seni durdurursa sağdaki sonuç geçerlidir, durdurmazsa bir alttaki
soruya inilir.

{{# karar haber-akis }}

Şema bir okuma sırasıdır, işlem kuralı değil. Son sorudaki iki saat ölçünün kendi sınırıdır: bu ders o pencerenin
ötesinde fiyatın ne yaptığını ölçmedi.

## Haberden sonra fiyat nereye gidiyor

İlk mum kapandıktan sonra ortalama fiyat, mumun yönünde ve mumun boyu cinsinden; iki aile, iki dönem.

{{# sekil 01_patika "Haber mumundan sonra ortalama fiyat yolu, ilk mumun yönünde" }}

Haber anlarında olay sayısı az olduğu için ortalama yol açılışlardaki kadar düzgün değildir; tek bir olay çizgiyi
belirgin oynatabilir. Şekil bir yön söylemek için değil, iki dönemin birbirinden ne kadar ayrıştığını görmek için.

### Masada: açıklamadan önceki dakikalar

Bu dersin sayılarının hiçbiri açıklamadan önceki dakikaları ölçmedi; buradaki kurallar sınamanın maliyet kurallarından
ve ilk mumun tanımından gelir. Maliyet: sınamada her işlem gerçek alış-satış fiyatlarından doldu, piyasa, stop ve
kırılım emirleri ayrıca açıklamadan iki dakika önce ile on beş dakika sonrası arasında {{ ON.haber_kayma_pip }} pip daha
kötü doldu. Bu ek kayma bir varsayımdır; gerçek kayma ve haber anındaki makasın büyüklüğü ayrıca ölçülmedi. İkisinin
birlikte ne yaptığı ölçüldü: küçük veri mumunun kırılımı maliyetsiz artıda, maliyetle eksideydi. Tanım: ilk mumun
sınıfı boyundan ve gövdesinin yerinden çıkar, mum kapanmadan ikisi de belli değildir; bir ucu süpürüp öbür yöne kapanan
mum (reddedilen) ilk saniyelerde güçlü bir mum gibi görünebilir.

{{# sema dar-aralik }}

{{# kart haber-oncesi }}

Bu durumda yapmazsın: açıklamadan önce yön tahminiyle girmezsin; dar aralığın kırılımına haberden önce stop emri
bırakmazsın; açık bir pozisyonun stopunu haber mumunun içinde kalacak kadar yakında unutmazsın.

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

1. **Sınıfı koyarsın.** Mumun boyu o anın tipik boyuyla kıyaslanır (son {{ S.haber_pencere }} olayın ortancası):
   büyük ve gövdesi uzunsa güçlü, bir yönde uzun fitilli ve küçük gövdeliyse reddedilen, çok küçükse küçük, kalan her
   mum normal.
2. **Üç seviye çizersin:** mumun iki ucu ve yarısı. Sonraki iki saatin okuması bu üç çizginin karşısında yapılır.
3. **Neyi beklemeyeceğini söylersin.** Normal ve reddedilen veri mumunun yönde sürmesini beklemezsin: iki dönemde de
   şanstan seyrek sürdü. Güçlü veri mumunda devam payı aynayla aynı; mumun ucunda kapanması yön bilgisi değildir.

İzleme New York 10:35'te (TSİ 17:35, ABD kış saatinde 18:35) biter; arada New York açılışı (TSİ 16:30, ABD kış
saatinde 17:30) geçer ve bu ders ikisini ayırmadı.

{{# sema veri-normal }}

{{# kart veri-normal }}

{{# kart veri-guclu }}

Bu durumda yapmazsın: mumun ucunun ötesinde mumun yönünde kovalamazsın; "sürmüyor, öyleyse dönecek" diye tersine
girmezsin, çünkü sürmemek dönmek değildir ve o tepki sınanmadı.

Aşağıdaki iki gün bir kuralla seçildi: EUR/USD'de tarım dışı istihdamın normal ilk mumuna uyan olaylardan, biri dersin
ölçtüğü eğilimle biten, öbürü ters giden en son olay.

{{# ornek nfp-normal }}

Üstteki günde ① verinin ilk mumu normal sınıfa düşer, ② mumun yarısıdır, ③ fiyatın oraya ilk döndüğü mumdur ve ④
pencerenin sonunda itiş sürmemiştir. Alttaki günde ① aynı sınıftandır ve kapandığı anda üstteki günden ayırt
edilemez; ayrım sonraki mumlarda doğar: fiyat mumun ucunu yarım mum boyu aşar ve okuma "sürdü" diye kapanır. İki günün
farkının sebebi ölçülmedi; grafikte "belli" görünmesi sonradan bakmanın sonucudur. Tek bir gün kuralı ne doğrular ne
yanlışlar: üstteki gün ölçülen eğilimin bir örneğidir, alttaki gün okumanın neden bir yön tahmini değil, bir sıklık
olduğunu gösterir.

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

Bir karar masada iki dalga olarak gelir. İlk {{ AN.nfp.tf }} dakikalık mum karar metninin fiyatıdır; ikinci dalga basın
toplantısıdır: Fed'de New York 14:30 (TSİ 21:30, ABD kış saatinde 22:30), ECB'de bugün Frankfurt 14:45 (TSİ 15:45,
Avrupa kış saatinde 16:45). BoE'de tutanak kararla birlikte gelir, yani ilk mum ikisini birden taşır. Ölçülen devam ve
dönüş payları Fed'de ve ECB'de iki dalganın toplamıdır; karar mumu kapandığında kararın okuması bitmemiştir.

Normal karar mumu çoğu zaman yarısına döner, ama yönü rastgele bir yol da aynı sıklıkta dönerdi; yarıya dönüş burada
bir şey söylemez. Reddedilen karar mumu iki dönemde de şanstan sık sürdü, güçlü karar mumu 2024 sonrasında birkaç karar
gününde sürdü; ikisinde de olay az. Masada bunları aday olarak izlersin: mumun yönünü, iki ucunu ve toplantının saatini
işaretler, toplantı boyunca fiyatın öbür uca gidip gitmediğine bakarsın. Öbür uç kırılırsa karar mumunun okuması biter.

{{# sema iki-dalga }}

{{# kart karar-guclu }}

Bu durumda yapmazsın: karar mumunun kapanışını kararın son fiyatı saymazsın; toplantı başlamadan metinden çıkardığın
yorumu pozisyona çevirmezsin; birkaç karar gününün artı sonucunu kural saymazsın.

Aşağıdaki iki gün de kuralla seçildi: EUR/USD'de Fed kararının normal ilk mumu; biri ölçülen eğilimle (öbür ucun
kırılması) biten, öbürü ters giden en son olay.

{{# ornek fomc-normal }}

Üstteki günde ① kararın ilk mumu normal sınıftadır, ② mumun yarısı, ③ fiyatın oraya ilk döndüğü mumdur. Basın
toplantısı (2019'dan beri her kararda) karar mumundan altı mum sonra başlar. Üstteki günde fiyat pencerenin içinde öbür
ucu kırar ve ④ pencerenin sonunda ilk mumun yönü geri alınmıştır; bu kırılımın toplantıya mı başka bir şeye mi bağlı
olduğu grafikten okunamaz. Alttaki günde ① yine normal bir mumdur ve karar mumu kapandığında iki gün aynı görünür; fark
ilk mumdan sonra doğar: fiyat mumun ucunu yarım mum boyu aşar. Hangi günün hangisi olacağı karar mumunun kapanışında
belli değildi. Tek bir karar kuralı ne doğrular ne yanlışlar; üstteki gün ikinci dalganın ilkini geri alabileceğini,
alttaki gün aynı yöne itebileceğini gösterir.

## Küçük haber mumu

Açıklama ilk beş dakikada fiyatı oynatmamışsa, sonra kırıldığı tarafa ne kadar gidiyor:

{{# kucuk veri mb }}

Fed kararında küçük ilk mumdan sonra kırılan tarafta bir mum boyu ilerleme {{ K.ic.fomc.ilerle }}
(2024 → {{ K.dis.fomc.ilerle }}): karar metni fiyatı oynatmamışsa, hareket çoğu zaman sonra geliyor; basın toplantısı
izlenen sürenin içinde. ABD verisinde ise küçük ilk mum 2024 → döneminde daha da az ilerliyor (enflasyon verisinde
{{ K.dis.cpi.ilerle }}). ECB ve BoE'nin olay sayıları küçük ({{ K.dis.ecb.n }} ve {{ K.dis.boe.n }}).

### Masada: fiyatı oynatmayan açıklama

Küçük ilk mum, açıklamanın fiyatı oynatmadığını söyler; yön söylemez. Okuma, iki ucun hangisinin önce kırıldığıyla
başlar. Fed kararında kırılan taraf iki dönemde de çoğu zaman bir mum boyu yol aldı; kırılımın metinden mi toplantıdan
mı geldiği ayrılmadı, bu yüzden Fed'in küçük mumunda okuma toplantının başlangıcından (TSİ 21:30, ABD kış saatinde
22:30) önce bitmiş sayılmaz. ABD verisinin küçük mumu 2024 sonrasında daha az ilerledi; ECB ve BoE'de olay az.

Küçük mumun tuzağı riskin kendisidir. Kırılan uçtan girip stopu öbür ucun ötesine koyan işlemin riski mumun boyu
kadardır; makas ve kayma mumun boyundan bağımsız olduğu için bu küçük riskin görünür bir parçası olur. Riski üç pipin
altında kalan işlem sınamada açılmadı; açılanlarda küçük veri mumunun kırılımı maliyetsiz artıyken maliyetle eksiye
döndü.

{{# sema kucuk-karar }}

{{# kart karar-kucuk }}

Bu durumda yapmazsın: küçük karar mumunu "piyasa kararı umursamadı" diye okumazsın; iki uçtan biri kırılmadan taraf
seçmezsin; dar bir stopu, makası hesaba katmadan "riskim küçük" diye kurmazsın.

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
  "{{ B.islem.veri.kucuk.hukum }}". Maliyetsiz sonucu artı ({{ B.islem.veri.kucuk.dis.brut }} R); haber anının makası
  ve kayması onu eksiye çeviriyor.

## Emri nereye koyarsın

Bu bölüm başka bir gerekçeyle işleme giren biri içindir: haber mumu bir giriş sinyali değildir, ama masada zaten bir
görüşün varsa emrini haber anına göre koyarsın. Dersin tepkileri üç emir biçimi kullandı.

- **Piyasa emri, ilk mum kapanınca.** Güçlü ve reddedilen karar mumunun işlem tepkileri böyle kuruldu. Giriş hâlâ haber
  penceresinin içindedir: makası öder ve sınamada {{ ON.haber_kayma_pip }} pip ek kayma öder. Stop öbür ucun ötesinde ve
  geniştir; güçlü karar mumunda ortanca risk {{ B.islem.mb.guclu.dis.risk_pip }} pip.
- **Limit, mumun yarısına.** Yön sınıflarının referans tepkileri böyle kuruldu. Limit girişte makas ve kayma ödemez,
  çıkışta öder, ve yalnız fiyat ilk mumun yönünün tersine yarıya geri geldiğinde dolar. 8. ders büyük mumda limitin
  dolduğu olaylarda piyasa girişinin çoğunlukla kaybettiğini ölçtü; haber mumunda bu ayrım ölçülmedi. ABD verisinde
  dolmuş bir limit, itişin sürmediğinin işaretidir.
- **Stop emri, kırılan uca.** Küçük mumun tepkileri böyle kuruldu: iki uca birer kırılım emri, önce tetiklenen geçerli.
  Stop emri kaymayı öder ve fiyatın zaten yürüdüğü yerden alır; küçük riskte aynı maliyet R cinsinden büyür.

Onay mumundan sonra giriş haber anında bu seride sınanmadı; 8. ders onu büyük mumda ölçtü ve maliyetten önceki sonucu
kapanışta piyasa girişinden belirgin farklı bulmadı. **Stop** bütün tepkilerde ilk mumun öbür ucunun ötesindedir
(referans tepkilerde mum boyunun onda biri, iki işlem tepkisinde yarısı kadar); stopu mumun içine çekmek denenmedi ve
riski üç pipin altında kalan işlem açılmadı. **Hedef** riskin yarısı, riskin kendisi ya da mumun kendi ucudur; hedef
yaklaştıkça kazanma oranı da başa baş için gereken oran da yükselir.

**Emrin iptali ve masadan kalkmak.** Sınanan tepkilerde limit ve kırılım emirleri izlemenin ilk saatinde geçerliydi,
dolmayan emir iptal edildi; dolan pozisyon ne hedefe ne stopa ulaşırsa iki saatin sonunda kapandı. Güçlü veri mumunun
tepkisinde 2024 sonrasında işlemlerin {{ B.islem.veri.guclu.dis.zaman_pay }} kadarı böyle kapandı. Basın toplantısı karar
mumunun öbür ucunu kırarsa da emir çekilir: karar mumunun okuması bitmiştir. Limit ilk saatte dolmadıysa fiyat yarıya
hiç gelmemiştir; bu, kovalamak için bir gerekçe değildir.

{{# sema emir-yerleri }}

{{# kart iki-saat }}

**Haber penceresinde ne değişir.** Açıklamadan iki dakika önce ile on beş dakika sonrası arasında makas gerçek
fiyatlardan ödenir (büyüklüğü ayrıca ölçülmedi), piyasa ve stop emirleri varsayılan bir ek kayma öder, ve ilk mum
büyük olduğu için öbür ucun ötesindeki stop pip cinsinden geniştir. Küçük haber mumu bunun tersidir: risk dardır ve
maliyet onun büyük bir parçası olur. İlk mumdan sonra on dakika daha beklemek pencereden çıkmak demektir; bunun sonuca
etkisi ölçülmedi.

## Sık yapılan hatalar

- **Haberden önce yön tahminiyle girmek.** Bu dersin ölçümü ilk mumla başlar; açıklamadan önceki dakikalar için hiçbir
  sayı yok, ve yön ilk mumla da gelmiyor. Dayanak: 4. ders, "ABD verileri".
- **Veri mumunu kovalamak.** Normal ve reddedilen veri mumunun yönü iki dönemde de şanstan seyrek sürdü. Dayanak:
  4. ders, "ABD verileri".
- **Güçlü mumun ucunda kapanmasını yön bilgisi saymak.** Güçlü mumun devam payı aynayla aynı; yakın devam eşiği mumun
  şeklinden gelir. Dayanak: 1. ders, "Şans ne verirdi: yolun aynası"; 4. ders, "ABD verileri".
- **"Sürmüyorsa döner" diye tersine girmek.** Ters yönde bir tepki önceden yazılmadı ve sınanmadı; sürmemek ile dönmek
  ayrı ölçülerdir. Dayanak: 4. ders, "ABD verileri".
- **Karar mumunu son söz saymak.** Basın toplantısı izlenen sürenin içindedir; ölçülen devam ve dönüş payları iki
  dalganın toplamıdır. Dayanak: 4. ders, "Merkez bankası kararları"; 5. ders, "Günün haritası".
- **Birkaç karar gününü kural saymak.** Güçlü karar mumunun artı sonucu {{ B.islem.mb.guclu.dis.gun_n }} karar gününe
  dayanıyor; {{ ON.hukum_en_az }} işlemin altında hüküm kurulmaz. Dayanak: 4. ders, "Bu okumaları işleme çevirmek".
- **Küçük mumda dar stopu ucuz sanmak.** Küçük risk aynı makas ve kaymayı R cinsinden büyütür; küçük veri mumunun
  kırılımı maliyetsiz artıyken maliyetle eksiye döndü. Dayanak: 4. ders, "Bu okumaları işleme çevirmek"; 8. ders,
  "Stop uzaklığı ve maliyet".
- **Kazanma oranına bakıp işlemi iyi sanmak.** Yarım R hedefle kazanma oranı yüksek kurulur; başa baş için gereken oran
  da yükselir. Dayanak: 1. ders, "Kazanma oranı ile net sonuç"; 5. ders, "Referans tepkiler".

## Masa kontrol listesi

1. Bugün takvimde hangi açıklama var ve saati TSİ kaçta? ABD verisi TSİ 15:30 (ABD kış saatinde 16:30), Fed TSİ 21:00
   (ABD kış saatinde 22:00), ECB TSİ 15:15 (Avrupa kış saatinde 16:15), BoE TSİ 14:00 (İngiltere kış saatinde 15:00).
2. Defterde açıklamadan önce bırakılmış bir emir ya da stop var mı; o anın ilk mumunun tipik boyu kadar bir hareketin
   içinde kalıyor mu?
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

Mum normaldir ("ABD verisinin normal ilk mumu" şeması). İki ucu ve yarısını işaretlersin. Mumun yönünde kalmazsın:
normal veri mumunun itişi iki dönemde de şanstan seyrek sürdü. Tersine de girmezsin: o tepki sınanmadı. Başka bir
gerekçeyle mumun yönünde gireceksen limit yarıya, stop öbür ucun ötesine; limitin dolması itişin sürmediğini söyler.
Dayanak: 4. ders, "ABD verileri"; 5. ders, "Referans tepkiler".

</details>

**2.** ABD yaz saatinde Fed kararı TSİ 21:00'de açıklandı; ilk mum küçük. TSİ 21:20'de fiyat hâlâ mumun
aralığında. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Beklersin. Basın toplantısı TSİ 21:30'da başlar ve izlenen süre onu içerir; okuma hangi ucun önce kırıldığıyla
başlar ve kırılımdan önce taraf seçmezsin. Kırılan uçtan gireceksen stop öbür ucun ötesine gider; risk küçüktür ve makas
ile kayma onun büyük bir parçası olur. Dayanak: 4. ders, "Küçük haber mumu"; 5. ders, "Maliyet nereye gidiyor".

</details>

**3.** TÜFE açıklamasına beş dakika var ve aralık dar. Aralığın iki pip üstüne bir alış, iki pip altına bir satış
stop emri bırakmayı düşünüyorsun ("Açıklamadan önce" şeması). Ne yaparsın?

<details>
<summary>Çözüm</summary>

Bırakmazsın. Emirlerden biri, mum iki yöne de giderse ikisi birden, haber mumunun ilk dakikasında tetiklenir ve dolum
seviyenin ötesinde olabilir (sınamadaki ek kayma bir varsayımdı, gerçek kayma ölçülmedi). Mum bir ucu süpürüp öbür yöne
kapanabilir; dersin her tepkisi ilk mum kapandıktan sonra başlar. Dayanak: 1. ders, "İlk mumun dört sınıfı"; 1. ders,
"Kazanma oranı ile net sonuç".

</details>

**4.** ECB kararından sonra güçlü bir aşağı mum geldi; yarım saat sonra basın toplantısı başlıyor. Biri bunun,
karar mumunun yönünde yarım R hedefli tepkinin tam örneği olduğunu söylüyor. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Bunu bir kural saymazsın. Güçlü karar mumu 2018–2023'te aynayla aynıydı; 2024 sonrasındaki artı sonuç birkaç karar
gününe dayanıyor ve "ölçülemedi" hükmü taşıyor; ECB'nin kendi güçlü mumları bir okuma kurmaya bile yetmiyor. Başka bir
gerekçeyle girersen stop öbür ucun ötesinde ve geniştir; toplantı öbür ucu kırarsa okuma biter. Dayanak: 4. ders,
"Merkez bankası kararları"; 4. ders, "Bu okumaları işleme çevirmek".

</details>

**5.** ABD ve İngiltere yaz saatindeyken, tarım dışı istihdamdan iki buçuk saat sonra (TSİ 18:00) fiyat ilk
mumun ucunun çok ötesinde. Bu, mumun yönünde girmek için bir gerekçe mi?

<details>
<summary>Çözüm</summary>

Değil. Ölçü iki saatte biter ve bu dersin o saatten sonrası için söyleyecek bir şeyi yoktur. TSİ 18:00 üstelik
Londra fiksingidir (Londra 16:00); okuma artık o anındır ve 3. dersin konusudur. Haberle açılmış bir emir hâlâ
defterdeyse çekersin. Dayanak: 1. ders, "İncelenen on an"; 4. ders, "Bu okumaları işleme çevirmek".

</details>

## Haber anları için masa kartı

- **Haber mumu yeni bilginin ilk fiyatıdır, son fiyatı değil.** Yarısına dönüş haberde de sıktır.
- **ABD verisinin ilk beş dakikasının yönü sonraki iki saatte şanstan seyrek sürer.** Veri mumunun yönüne dayanan bir
  okuma iki dönemde de zayıf; 2024 sonrasında daha da zayıf.
- **Karar metni fiyatı oynatmadıysa hareket sonra gelebilir.** Fed'de küçük ilk mumdan sonra kırılım iki dönemde de
  çoğu zaman yol aldı; üç bankanın küçük karar mumu kırılımı bir işleme çevrildiğinde ise iki dönem ayrı işaret verdi.
- **Merkez bankası kararlarındaki üç işlem tepkisi 2024 sonrasında artıda kaldı.** Hiçbirinin karar günü sayısı bir
  hüküm kurmaya yetmiyor. Bir sonraki dönemde, bugünkü kuralla, değiştirilmeden sınanmadan bir kural sayılmaz.
- **Haber anının maliyeti farklıdır.** Makas açılır, kayma artar; dar stoplu bir haber işlemi maliyete en çok
  dayanan işlemdir.
