---
title: 'FX Gün İçi Oyun Planı 1: İlk Mumu Okumak'
description: "Açılışlar, fiksingler, ABD verileri ve merkez bankası kararları: fiyat bu anlarda ilk mumdan sonra genelde ne yapıyor, ve bunun ne kadarı gerçekten bir şey söylüyor? İlk mumu dört sınıfa ayırıp 2018–2023'teki {{ olay_ic }} olayda okuyan, şansın vereceği payla kıyaslayan ve 2024 sonrasında sınanan bir oyun planı."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Bir gün içi işlemci için günün belirli anları vardır: açılış, fiksing, veri, karar. Bu ders o anların ilk mumunu dört sınıfa ayırır, fiyatın her sınıftan sonra ne yaptığını gösterir ve bunun ne kadarının şansın, yani mumun kendi şeklinin vereceği pay olduğunu ayırır. Serinin oyun planı bu ayrımın üstüne kurulur."
seviye: 'giris'
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';
import Diyagram from '../../components/Diyagram.astro';

Bir gün içi işlemcinin günü saatlere değil anlara bölünür. Tokyo açılır, Londra açılır, New York açılır; Tokyo ve
Londra'da kur fiksingleri yapılır; ayın belirli günlerinde ABD istihdam ve enflasyon verisi gelir; altı haftada bir
merkez bankaları karar açıklar. Bu anların her birinde fiyat kısa bir süre içinde bir şey söyler. O ilk söz, yani **ilk
mum**, çoğu işlemcinin günün geri kalanını okuduğu yerdir.

Bu seri o anları anlatır; bir kural listesi değildir. Her anın ilk mumunu bir sınıfa koyar, fiyatın o sınıftan sonra
genelde ne yaptığını gösterir ve üstüne bir **oyun planı** yazar: ne beklenir, ne beklenmez, nerede sabırlı olunur.
Plan 2018–2023 verisinden yazıldı; tepkileri 2024 sonrası veride hiç koşturulmadan kaydedildi ve sonra 2024 →
döneminde, gerçek alış-satış fiyatları ve maliyetle sınandı.

## Kısaca

- **Açılışta ilk mum yön söylemiyor.** Güçlü bir açılış mumu çoğu zaman devam ediyor gibi görünür
  ({{ Y.ic.acilis.guclu.devam }} devam, {{ Y.ic.acilis.guclu.donus }} dönüş), ama fiyatın yönü rastgele olsaydı da
  aynı pay çıkardı ({{ Y.ic.acilis.guclu.devam_ayna }} ve {{ Y.ic.acilis.guclu.donus_ayna }}): güçlü mum ucunda
  kapandığı için "devam" eşiği zaten yakındadır. Açılış mumunun yarısına dönmesi de
  ({{ Y.ic.acilis.normal.orta }}) şansın verdiği payla aynı ({{ Y.ic.acilis.normal.orta_ayna }}).
- **Fiksingde gerçek bir davranış var.** Fiksinge güçlü koşan fiyat koşunun yarısını {{ Y.ic.fiksing.guclu.orta }}
  geri verdi; şansla beklenen {{ Y.ic.fiksing.guclu.orta_ayna }}. Koşunun sürme payı ise şansın altında
  ({{ Y.ic.fiksing.guclu.devam }} ve {{ Y.ic.fiksing.guclu.devam_ayna }}). İki fark 2024 → döneminde de aynı yönde.
- **ABD verisinden sonra normal ilk mum şanstan az sürüyor.** Normal bir veri mumunun devam payı 2018–2023'te
  {{ Y.ic.veri.normal.devam }} (şansla {{ Y.ic.veri.normal.devam_ayna }}), 2024 → döneminde
  {{ Y.dis.veri.normal.devam }} ({{ Y.dis.veri.normal.devam_ayna }}); güçlü veri mumunun devamı aynayla aynı. Bu
  bir okuma; bu yönde bir tepki önceden yazılmadığı için sınanmadı.
- **Merkez bankası kararlarında olay az.** Planın artı sonuç veren tek tepkileri burada, ama işlem sayıları bir hüküm
  kurmaya yetmiyor.
- **Yüksek kazanma oranı kurmak kolay, kâr etmek değil.** Açılışta ilk mumun yarısına limitle girip yarım R hedefleyen
  tepkiler 2024 → döneminde işlemlerin {{ B.referans.acilis.normal.dis.kazanma }}–{{ B.referans.acilis.guclu.dis.kazanma }}
  kadarını kazandı; başa baş için {{ B.referans.acilis.guclu.dis.basabas }} gerekiyordu.

## Bu dersi masada nasıl kullanırsın

Bu ders bir işlem kuralı vermez; masadaki ilk dakikaları düzenler. Bir an geldiğinde, örneğin Londra açıldığında
(Londra 08:00; TSİ İngiltere yaz saatinde 10:00, kış saatinde 11:00), ilk mum kapanana kadar beklersin, mumu dört
sınıftan birine koyarsın ve tek soru sorarsın: bu mumdan sonra gördüğüm şey yönü olmayan bir fiyatta da aynı sıklıkta
görülür müydü? Cevap çoğu anda "evet"tir; o zaman iş işlem değil işaretlemedir: iki uç, yarı ve günün bir sonraki
anının saati. Şema bu sırayı beş soruya indirir; her sorunun dayanağı serinin bir dersindedir ve hiçbir dal işlem
önermez.

{{# karar ilk-mum }}

## İncelenen on an

Seri {{ an_sayi }} anı inceler; hepsi {{ pariteler }} paritelerinde. Saatler yerel saat ve Türkiye saati (TSİ) olarak
verilir. İngiltere, Avrupa ve ABD yaz saatine geçtiğinde TSİ karşılığı bir saat erkene kayar; Tokyo yaz saati
uygulamaz.

{{# an_tablo }}

**İlk mum** açılışlarda açılıştan sonraki ilk {{ AN.londra_acilis.tf }} dakikadır. Fiksinglerde ilk mum fiksinge
giden {{ AN.wmr.tf }} dakikadır, yani fiyatın fiksinge kadar yaptığı koşu; plan fiksingden sonrasını okur. Veri ve
kararlarda ilk mum açıklamadan sonraki ilk {{ AN.nfp.tf }} dakikadır. **İzlenen süre**, ilk mumdan sonra fiyatın
ne yaptığına bakılan penceredir.

## İlk mumun dört sınıfı

Bir mumun büyük mü küçük mü olduğu, o anın kendi geçmişine göre söylenir: Londra açılışının sıradan mumu Tokyo
açılışının sıradan mumundan büyüktür. Her anın **tipik boyu**, o anın son {{ S.tipik_pencere }} olayındaki ilk
mum boylarının ortancasıdır (en az {{ S.tipik_en_az }} olay); veri ve kararlarda son {{ S.haber_pencere }} olay
(en az {{ S.haber_en_az }}). Hesap yalnız geçmiş olaylardan yapılır, o günün mumu kendi ölçüsüne girmez.

- **Güçlü.** Boyu tipik boyun en az {{ S.guclu_aralik }} katı ve gövdesi boyunun en az {{ S.guclu_govde.yuzde }}
  kadarı. Fiyat bir yöne gitmiş ve o yönde kapanmış. Yönü mumun yönüdür.
- **Reddedilen.** Gövdesi boyunun en çok {{ S.red_govde.yuzde }} kadarı, fitillerinden biri boyunun en az
  {{ S.red_fitil.yuzde }} kadarı ve boyu tipik boyun en az {{ S.red_aralik }} katı. Fiyat bir yöne gitmiş, orada
  satıcı ya da alıcı bulmuş ve geri itilmiş. Yönü reddin yönüdür: üstte uzun fitil aşağı, altta uzun fitil yukarı.
- **Küçük.** Boyu tipik boyun {{ S.kucuk_aralik }} katından küçük. Piyasa o anda bir şey söylememiş. Yönü yoktur;
  plan hangi tarafın önce kırıldığına bakar.
- **Normal.** Kalan her mum. Yönü gövdesinin yönüdür.

Aynı açılışın dört sınıftan dört örneği (EUR/USD, Londra açılışı; her şeklin altında günü ve TSİ saati):

{{# sekil 01_siniflar "İlk mumun dört sınıfı: aynı açılış, dört gün" }}

Şekildeki kesikli çizgi ilk mumun **yarısıdır** (orta noktası). Bu seride en çok bakılan seviye odur.

### Masada: mumu sınıflandırmak

Sınıf kapanışta verilir; on beş dakikalık mum onuncu dakikada güçlü görünüp reddedilen olarak kapanabilir. Masada
sırayla mumun boyuna, gövdenin ve en uzun fitilin boya oranına bakarsın. Boy ekrandaki komşu mumlarla değil, aynı
anın geçmiş ilk mumlarıyla kıyaslanır (son {{ S.tipik_pencere }} olay; veri ve kararlarda son {{ S.haber_pencere }});
başka bir defterle okunan sınıf bu derste ölçülmedi.

{{# sema siniflar }}

{{# kart reddedilen-acilis }}

## Trend

Her ilk mum bir de günlük trendle karşılaştırılır. Trend, bir önceki günün kapanışının {{ S.ema_n }} günlük üssel
ortalamaya göre yeridir: kapanış ortalamanın üstünde ve ortalama son {{ S.ema_egim }} günde yükselmişse trend yukarı,
ikisi de tersi ise aşağı, başka her durumda yatay. İlk mumun yönü trendle aynıysa mum **trend yönünde**, tersse
**trende karşı** sayılır.

Haber anlarında olay sayısı böyle bir ayrım için yetmiyor. Masada trendi bir satır not olarak yazarsın, süzgeç olarak
kullanmazsın. Trend yönündeki güçlü bir açılış mumu
trende karşı olanından daha sık devam etmedi (2. ders, Trend bir şey değiştiriyor mu); fiksinge güçlü koşunun sürme
payı da trendle değişmedi (3. ders, Trend). "Trendle aynı yönde, öyleyse bu kez sürer" cümlesi bu derslerin ölçtüğü
bir şey değildir.

## İlk mumdan sonra ne olabilir

İlk mum kapandıktan sonra izlenen süre içinde dört şeye bakılır. Hepsi ilk mumun **boyu** cinsinden ölçülür:

- **Yarısına döndü.** Fiyat mumun orta noktasına geri geldi. (Fiksingde: fiyat koşunun yarısına geri çekildi.)
- **Devam etti.** Fiyat, mumun öbür ucunu görmeden, kendi ucunu yarım mum boyu aştı.
- **Tersine döndü.** Fiyat, kendi ucunu yarım mum boyu aşmadan, mumun öbür ucunu kırdı.
- **Geri çekilip devam etti.** Fiyat önce yarısına döndü, sonra öbür uca gitmeden kendi ucuna ulaştı.

Aynı dakikada iki seviye birden görülürse hangisinin önce geldiği bilinemez; o olay iki sonuçta da "olmadı" sayılır.

## Şans ne verirdi: yolun aynası

Bir payın bir şey söyleyip söylemediği, şansın aynı ölçüde ne vereceği bilinmeden kurulamaz. Burada şansın payı
mumun **şeklinden** gelir. Güçlü bir mum ucuna yakın kapanır. Kapanıştan "devam" eşiği (kendi ucunun yarım mum boyu
ötesi) yakın, "dönüş" eşiği (öbür uç) uzaktır. Fiyat yazı tura atsa bile devam dönüşten sık görünür. Normal bir mum
ise ortasına yakın kapanır, yani "yarısına dönüş" zaten bir adım ötededir.

Bu payı ayırmak için her olayda ilk mumdan sonraki fiyat yolu, ilk mumun kapanışına göre **aynalanır**: yukarı giden
her hareket aşağı, aşağı giden her hareket yukarı yazılır, ve aynı dört ölçü aynalanmış yolda yeniden hesaplanır. Yol
ile aynası, yönü olmayan bir fiyatta eşit olasıdır. Gerçek pay ile aynanın payı aynıysa ilk mum yön bilgisi
taşımıyordur. Fark varsa, fark ilk mumun söylediği şeydir.

Açılış, fiksing ve ABD verisinde, üç yönlü sınıfta, iki dönemde bu farkın kendisi (gerçek pay eksi aynadaki pay,
puan). Merkez bankası kararlarında olay az olduğu için fark birkaç olayla onlarca puan oynar; o aile haber dersinde
kendi tablosuyla verilir.

{{# sekil 02_yarisi "Gerçek pay eksi şansın payı: açılışta sıfır, fiksingde geri verme" }}

Şekil serinin özetidir. Açılışlarda üç ölçünün farkı da sıfır çevresinde: açılış mumunun söylediği her şey kendi
şeklinin sonucudur. Fiksinglerde koşunun yarısını geri verme payı iki dönemde de şansın üstünde, sürme payı altında.
ABD verisinin normal ve reddedilen mumunda devam payı iki dönemde de şansın altında.

### Masada: aynayı kendi gözünle sormak

"Bak, devam etti" ya da "bak, yarısına döndü" dediğin her an aynı cümleyi aynalanmış yol için de kurarsın: fiyat tam
tersine aynı adımları atsaydı, aynı şeyi görür müydün? Güçlü bir mumda cevap çoğu zaman evettir, çünkü eşiklerin
kapanışa uzaklığı mumun şeklinden gelir.

{{# sema ayna-esik }}

Güçlü açılış mumunda devamın dönüşten sık çıkması bu yüzden aynada da aynen çıkar
({{ Y.ic.acilis.guclu.devam_ayna }} ve {{ Y.ic.acilis.guclu.donus_ayna }}); masada sayıyı değil mesafeyi okursun.

{{# sema ayna-yol }}

Gözle sorulan aynanın yararı, "bu sefer farklı" duygusunun çoğu zaman mumun şeklinden geldiğini fark ettirmesidir.

Gerçek grafiklerde numaralar her derste aynıdır: ① olay mumu (fiksingde koşu), ② mumun ya da koşunun yarısı, ③ fiyatın
yarıya ilk dokunduğu mum, ④ izleme penceresinin sonu; şemalarda ise numaralar şemanın altındaki maddelere bağlıdır.

{{# ornek londra-guclu }}

Üstteki günde (28.09.2023, TSİ 10:00) ① ucunda kapanan güçlü bir yukarı açılış mumudur. Fiyat sonraki saatte geri
çekilir ama yarıya inmez, bu yüzden ③ yoktur; TSİ 11:15'te kendi ucunu yarım mum boyu aşar ve ④'te ucunun bir buçuk
mum boyundan fazla ötesindedir. Alttaki günde (17.11.2023, TSİ 11:00) ① aynı sınıftan bir aşağı mumdur, ama ucunda
değil yarısının hemen ötesinde kapanmıştır. Yarı kapanışa bu kadar yakın olduğu için ③ iki dakika sonra gelir: bu,
aynanın ölçtüğü geometrinin kendisidir. Fiyat TSİ 11:30'da öbür ucu kırar, sonraki üç saat boyunca yükselir ve ④'te mumun
tepesinin iki mum boyundan fazla üstündedir. Kapanışta iki ekranı ayıran şey kapanışın mumun içindeki yeridir; bu
yer sınıfın ölçütü değildir ve ayrıca ölçülmedi. Geriye bakınca biri "açıkça devam", öbürü "açıkça
tuzak" görünür. İki gün ne devamı ne dönüşü kanıtlar; tek gün bir kuralı ne doğrular ne yanlışlar. Ölçü binlerce
günden gelir: güçlü açılış mumunda iki sonuç aynadaki paylarla aynı sıklıkta gelir.

Fiksingde ayna başka bir şey söyler: güçlü koşunun yarısını geri vermesi aynadakinden sık
({{ Y.ic.fiksing.guclu.orta }} ve {{ Y.ic.fiksing.guclu.orta_ayna }}), sürmesi seyrek. Fiksingden sonra koşunun
yönünde yeni bir hareket beklemezsin; ama koşunun tersine girmek kenar değildir, fark maliyetin altında kaldı (3. ders,
Bu okumaları işleme çevirmek).

{{# kart fiksing-kosu }}

{{# ornek wmr-guclu }}

Üstteki günde (15.11.2023, fiksing TSİ 19:00) ① fiksinge giden yarım saatlik yukarı koşudur ve ucuna yakın biter.
Fiyat fiksingden sonraki çeyrek saatte biraz daha yükselir ama yarım koşu boyuna varmaz; TSİ 19:30'dan sonra geri
çekilir, ③ fiksingden kırk bir dakika sonra koşunun yarısına dokunur ve ④'te fiyat yarının hemen altındadır; koşunun
başı görülmez. Alttaki günde (27.07.2023, fiksing TSİ 18:00) ① aynı sınıftan, yine ucuna yakın biten bir yukarı
koşudur; fiyat fiksingden sonraki ilk beş dakikada yarım koşu boyunu aşar, yarıya hiç dönmez ve ④'te ucun koşu
boyunun dörtte üçünden fazla üstündedir. Fiksing anında iki koşu ayırt edilemez; geri verme payı aynadakinden yalnız
biraz yüksek.

ABD verisinde ayna üçüncü bir şey gösterir: normal ve reddedilen veri mumunun devam payı iki dönemde de aynadakinin
altında, güçlü veri mumununki aynayla aynı (4. ders, ABD verileri). Bu bir uyarıdır, işaret değil. Masada: güçlü
açılış mumunun devamını yön saymazsın; fiksingden sonra koşuyu kovalamazsın, geri vermeyi de kenar saymazsın; veri
mumunun yönünü sürecek bir hareket saymazsın.

## Kazanma oranı ile net sonuç

Planın her okuması bir **tepkiye** çevrilip sınandı: ilk mumun yarısına limitle mumun yönünde girmek, küçük mumun
kırılan ucundan girmek, fiksingde koşunun tersine girmek gibi. Her tepkinin bir stopu ve bir hedefi var.

Sonuç **R** cinsinden yazılır. R, riske edilen mesafedir: giriş ile stop arası. Hedef girişten riskin yarısı kadar
uzaktaysa ("hedef yarım R") kazanan işlem yarım R kazanır, stopa gelen işlem bir R kaybeder. Böyle bir tepkinin başa
baş kalması için işlemlerin üçte ikisini kazanması gerekir: üç işlemin ikisi kazanıp biri kaybederse toplam sıfırdır.

Kazanma oranı tek başına hiçbir şey söylemez. Hedef yaklaştıkça kazanma oranı yükselir, ama kazanan işlemin getirdiği
de küçülür. Açılışlarda güçlü ilk mumun yarısına limitle girip yarım R hedefleyen tepki 2024 → döneminde işlemlerin
{{ B.referans.acilis.guclu.dis.kazanma }} kadarını kazandı. Ortalama kazanç {{ B.referans.acilis.guclu.dis.kazanc }} R,
ortalama kayıp {{ B.referans.acilis.guclu.dis.kayip }} R, başa baş için gereken kazanma oranı
{{ B.referans.acilis.guclu.dis.basabas }}. İşlemlerin {{ B.referans.acilis.guclu.dis.stop_pay }} kadarı tam bir R'lik
stopla kapandı ve yarım R'lik kazançlar bunu karşılamadı. Sonuç işlem başına {{ B.referans.acilis.guclu.dis.R }} R.

Net sonuç maliyetten sonradır. Her işlem gerçek alış-satış farkını (makas) öder: alış emri satış fiyatından, satış
emri alış fiyatından dolar, stop ve hedef de çıkış tarafının fiyatından sorulur. Piyasa, stop ve kırılım emirleri
ayrıca {{ ON.kayma_pip }} pip kayma öder; veri ve karar anında (açıklamadan iki dakika önce ile on beş dakika sonrası
arası) ek {{ ON.haber_kayma_pip }} pip. Kayma sınamanın varsayımıdır; gerçek kayma ve haber anındaki makasın
büyüklüğü ölçülmedi. Limit emir kendi fiyatından dolar, kayma ödemez. Riski {{ ON.en_az_risk_pip }}
pipten küçük işlem açılmaz. Her tepkinin bir de **maliyetsiz** sonucu var: aynı kurallar orta fiyatla, makas ve kayma
olmadan. İkisinin farkı maliyetin payıdır.

### Masada: yarım R hedefin hesabı

Bir tepkinin ilk sorusu kazanma oranı değil başa baş oranıdır. Yarıya limitli girişte maliyet kazancı küçültmez:
giriş makas ödemez, hedef çıkış tarafının fiyatından sorulur ve dolduğunda tam yarım R getirir. Kaybı büyütür: stopta
makas ve kayma ödenir. Başa baş bu yüzden üçte ikinin üstüne çıkar ({{ B.referans.acilis.guclu.dis.basabas }}) ve
gerçekleşen kazanma oranı onun altında kalır.

{{# sema yarim-r }}

Şemadaki hedef kapanışın altında duruyor: yarıya konan limit ile yarım R'lik hedef, mumun zaten gittiği yolun bir
kısmını geri almayı hedefler.

{{# kart guclu-acilis }}

## Emri nereye koyarsın

Bu ders işlem önermez. Başka bir gerekçeyle (kendi modelin, bir akış bilgisi) ilk mumdan sonra işleme gireceksen,
ilk mum emrin geometrisini, bu derste ölçülen maliyet kuralları da bedelini verir. Bu bölüm oyun derslerinin (1–5)
ortak emir kurallarıdır; öbür dersler yalnız kendi anına özgü olanı ekler.

- **Giriş.** Piyasa emri hemen dolar, makası ve {{ ON.kayma_pip }} pip kaymayı öder. Yarıya limit girişte makas ve
  kayma ödemez, çıkışta öder; yalnız fiyat yarıya geri geldiğinde dolar, yani dolum mumun yönündeki hareketin
  yarısının geri alındığını söyler. Kırılan uca stop emri fiyatı yürüdüğü yerden alır ve kayma öder.
- **Büyük mumun ölçüleri.** Limit dolumunun piyasa girişinin kaybettiği olayları seçmesi (ters seçim) ve onay mumunun
  bilgisinin kaçırılan fiyatın bedelini ancak karşılaması 8. dersin büyük mum ölçüleridir (8. ders, Limit neden ucuz
  görünür: ters seçim; 8. ders, Onay mumu). Anların ilk mumu için ikisi de ölçülmedi; onay mumundan sonra giriş bu
  anlarda sınanmadı.
- **Stop.** Sınanan tepkilerde stop öbür ucun mum boyunun onda biri ötesindedir; fiksingde koşunun ucunun koşu boyunun
  onda biri ötesinde. Mumun içine konan stop ölçülmedi. Açılış mumu küçüktür, stop da: maliyetin payı normal mumun
  limit tepkisinde {{ B.referans.acilis.normal.dis.maliyet }} R, küçük mumun kırılımında
  {{ B.referans.acilis.kucuk.dis.maliyet }} R (2. ders, Bu okumaları işleme çevirmek). Stopu daraltmak riski
  küçültmez, aynı makası daha büyük bir R yapar.
- **Hedef.** Yarım R hedef kazanma oranını da başa baş eşiğini de yükseltir. Açılışlarda daha uzak hedefler
  2018–2023'te denendi ve hiçbiri maliyetten sonra artıda kalmadı; 2024 sonrasında sınanmadı (2. ders, Bu okumaları
  işleme çevirmek).
- **Emrin ömrü.** Limit ve kırılım emri ilk mum kapandıktan (fiksingde fiksing anından) 60 dakika sonra düşer. Süre
  ön kayıtta yazılıydı, ölçülerek seçilmedi; başka bir süre sınanmadı. Dolan pozisyon ne hedefe ne stopa ulaşırsa
  izlenen sürenin sonunda kapanır. Fiyat limit dolmadan devam eşiğine giderse emri taşımazsın; taşınan emir başka bir
  emirdir ve ölçülmedi.
- **Haber penceresi.** Bekleyen bir emrin süresine takvimdeki büyük bir haberin penceresi (açıklamadan iki dakika önce
  – on beş dakika sonra) düşüyorsa emri açıklamadan önce çekersin. Bu bir disiplin kuralıdır, ölçüm sonucu değil:
  sınamada o pencerede piyasa ve stop emirlerine {{ ON.haber_kayma_pip }} pip ek kayma varsayıldı, haber anındaki makas
  ölçülmedi ve emri çekmenin sonuca etkisi bu seride ölçülmedi (1. ders, Kazanma oranı ile net sonuç).

{{# kart kucuk-mum }}

## Sık yapılan hatalar

- **Devam payını yön sanmak.** Güçlü mum ucuna yakın kapanır, devam eşiği yakındır; aynada da aynı pay çıkar (1. ders,
  Şans ne verirdi: yolun aynası; 2. ders, Güçlü ilk mum).
- **Kazanma oranına bakıp kâr beklemek.** Yarım R hedefte başa baş maliyetle üçte ikinin üstündedir; açılışın referans tepkileri
  işlemlerin yarısından çoğunu kazanıp kaybettirdi (1. ders, Kazanma oranı ile net sonuç).

## Masa kontrol listesi

1. Hangi an ve TSİ kaçta? Tokyo açılışı 03:00, Tokyo fiksingi 03:55, Londra açılışı 10:00 (İngiltere kış saatinde
   11:00), ABD verisi 15:30 ve New York açılışı 16:30 (ABD kış saatinde 16:30 ve 17:30), Londra fiksingi 18:00
   (İngiltere kış saatinde 19:00).
2. Bekleyen emrin süresine bir veri ya da karar penceresi (açıklamadan iki dakika önce – on beş dakika sonra) düşüyor
   mu? Düşüyorsa emri açıklamadan önce çekersin.
3. İlk mum kapandı mı? Kapanmadıysa sınıf yok.
4. Boy, aynı anın geçmiş ilk mumlarının ortancasına göre ne kadar; gövde ve en uzun fitil boyun ne kadarı? Sınıf hangisi?
5. İki uç, yarı ve kendi ucunun yarım mum ötesi işaretli mi?
6. Gördüğüm şey aynada da aynı sıklıkta görülür müydü?
7. Fiksingse: koşu güçlü mü, ayın son Londra iş günü mü? Geri verme beklenir, koşunun sürmesi beklenmez.
8. Başka bir gerekçeyle girersem: başa baş oranı ne, maliyet riskin ne kadarı? Emir ilk mum kapandıktan 60 dakika
   sonra düşer.

## Grafik okuma alıştırmaları

**1.** Londra açılışı (Londra 08:00; TSİ İngiltere yaz saatinde 10:00, kış saatinde 11:00). İlk mum onuncu dakikada
uzun bir gövdeyle yukarıda; on beşinci dakikada geri itilmiş, üst fitili uzun, gövdesi küçük kapanıyor. Onuncu
dakikada mumu "güçlü" diye not etmiştin. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Sınıf kapanışta verilir: mum reddedilen olarak kapandı ve yönü aşağıdır ({{# atif sema siniflar }}'nin üçüncü mumu). Onuncu dakikadaki
not geçersizdir. Reddedilen açılış mumunda devam ile dönüş aynadakiyle aynı; yön okuması kurmazsın, iki ucu ve yarıyı
işaretlersin (1. ders, İlk mumun dört sınıfı; 2. ders, Normal ve reddedilen ilk mum).

</details>

**2.** Londra fiksingi (Londra 16:00; TSİ İngiltere yaz saatinde 18:00, kış saatinde 19:00). Fiyat fiksinge güçlü
yukarı koşmuş; fiksingden sonraki on dakikada koşunun üçte biri kadar geri çekilmiş. Ne beklersin, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Güçlü koşunun yarısını geri verme payı şanstan sık, sürme payı seyrek; üçte birlik bir geri çekilmeden sonraki koşullu
pay ise bu derste ölçülmedi. Koşunun yönünde yeni işlem açmazsın, geri vermeye koşunun tersine katılmayı da kenar
saymazsın: fark maliyetin altında kaldı (1. ders, Şans ne verirdi: yolun aynası; 3. ders, Bu okumaları işleme
çevirmek).

</details>

**3.** Tarım dışı istihdam verisi (New York 08:30; TSİ ABD yaz saatinde 15:30, kış saatinde 16:30). İlk beş dakikalık
mum normal ve aşağı; makas açılmış. Elinde dar bir stopla mumun tersine girme fikri var. Ne yaparsın?

<details>
<summary>Çözüm</summary>

Normal veri mumunun yönünün şanstan seyrek sürmesi iki dönemde görülen bir okumadır; bu yönde tepki önceden
yazılmadığı için sınanmadı ve kural değildir. Başka bir gerekçeyle girersen giriş hâlâ haber penceresindedir: ekranda
gördüğün makası girişte ödersin, sınama da bu pencerede {{ ON.haber_kayma_pip }} pip ek kayma varsaydı (haber anındaki
makas ölçülmedi). Dar stop aynı maliyeti R cinsinden büyütür (1. ders, Kısaca; 1. ders, Emri nereye koyarsın).

</details>

**4.** New York açılışı (New York 09:30; TSİ ABD yaz saatinde 16:30, kış saatinde 17:30). İlk mum küçük; yirmi dakika
sonra fiyat üst ucu kırıyor. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Küçük açılış mumunun kırılımı bir sinyal değildir: kırılan tarafta bir mum boyu ilerleme yazı turaya yakın, kırılıma
girmek maliyetten önce sıfıra yakın, sonra eksi. Kırılan tarafı izlersin, kovalamazsın (2. ders, Küçük ilk mum; 2.
ders, Bu okumaları işleme çevirmek).

</details>

## Bu planın dürüstlük kuralları

- **Plan 2018–2023'ten yazıldı.** Gözlem ({{ olay_ic }} olay) ve tepkilerin seçimi yalnız o dönemin verisiyle
  yapıldı; gözlem sırasında 2024 sonrasının verisine bakılmadı.
- **Seçim kuralı önceden yazıldı.** Bir an ailesi ve ilk mum sınıfı için "işlem" tepkisi, 2018–2023'te en az
  {{ ON.secim_en_az }} işlemi olan ve maliyetten sonra artıda kalan adaylardan en iyisidir. Hiçbir aday artıda
  değilse o hücrede plan "izle, işlem açma" der. Bu kural gereği seçilen her tepkinin 2018–2023 sonucu artıdır; o
  sonuç kanıt değildir, kanıt 2024 → sonucudur.
- **Hüküm 2024 → döneminden verilir.** İşlem başına net sonucun güven aralığı (işlemlerden yeniden örnekleme,
  {{ ON.bootstrap }} tekrar) tamamen sıfırın üstündeyse **çalışıyor**, ortalama artı ama aralık sıfırı kapsıyorsa
  **zayıf**, ortalama eksiyse **çalışmıyor**. {{ ON.hukum_en_az }} işlemin altında hüküm **ölçülemedi**dir; sonuç
  yine yazılır.
- **Bilinen sınırlar.** Referans tepkilerin 2018–2023 sonucu plan yazılırken biliniyordu. Aynı verinin 2024 sonrası
  dönemiyle daha önce yirmi iki gün içi kural sınanıp yayımlanmıştı ve çoğu maliyetten sonra eksi kalmıştı; bu planın
  kendi tepkilerinin 2024 sonrası sonucu ise hiç ölçülmemişti. Yolun aynası ölçüsü
  iki dönem de görüldükten sonra eklendi; bir betimlemedir, hüküm değildir.

Veri: Dukascopy bir dakikalık alış ve satış fiyatları, 2018 başından {{ veri_bitis }} tarihine kadar.

## Serinin dersleri

1. **İlk mumu okumak** (bu ders): anlar, sınıflar, ölçüler.
2. [**Açılışlar**](/arastirma/fx-oyun-acilislar/): Tokyo, Londra ve New York açılışlarının oyun planı.
3. [**Fiksingler**](/arastirma/fx-oyun-fiksingler/): Tokyo fiksingi ve Londra'nın WM/R fiksingi; ay sonu.
4. [**Haber mumları**](/arastirma/fx-oyun-haberler/): ABD istihdam ve enflasyon verisi, Fed, ECB ve BoE kararları.
5. [**Backtest**](/arastirma/fx-oyun-backtest/): planın bütün tepkileri iki dönemde, maliyetle; günün haritası.
