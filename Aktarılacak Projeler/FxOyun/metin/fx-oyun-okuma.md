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

Bu seri o anları anlatır. Bir kural listesi değildir: "fiyat şu seviyeyi kırarsa al" demez. Her anın ilk mumunu bir
sınıfa koyar, o sınıftan sonra fiyatın genelde ne yaptığını gösterir ve bunun üstüne bir **oyun planı** yazar: bu
anda ne beklenir, ne beklenmez, nerede sabırlı olunur, nerede masadan kalkılır. Plan 2018–2023 verisinden yazıldı;
planın tepkileri 2024 sonrası veride hiç koşturulmadan kaydedildi ve sonra 2024 → döneminde, gerçek alış-satış
fiyatları ve maliyetle sınandı.

## Kısaca

- **Açılışta ilk mum yön söylemiyor.** Güçlü bir açılış mumu çoğu zaman devam ediyor gibi görünür
  ({{ Y.ic.acilis.guclu.devam }} devam, {{ Y.ic.acilis.guclu.donus }} dönüş), ama fiyatın yönü rastgele olsaydı da
  aynı pay çıkardı ({{ Y.ic.acilis.guclu.devam_ayna }} ve {{ Y.ic.acilis.guclu.donus_ayna }}): güçlü mum ucunda
  kapandığı için "devam" eşiği zaten yakındadır. Açılış mumunun yarısına dönmesi de
  ({{ Y.ic.acilis.normal.orta }}) şansın verdiği payla aynı ({{ Y.ic.acilis.normal.orta_ayna }}).
- **Fiksingde gerçek bir davranış var.** Fiksinge güçlü koşan fiyat koşunun yarısını {{ Y.ic.fiksing.guclu.orta }}
  geri verdi; şansla beklenen {{ Y.ic.fiksing.guclu.orta_ayna }}. Koşunun sürme payı ise şansın altında
  ({{ Y.ic.fiksing.guclu.devam }} ve {{ Y.ic.fiksing.guclu.devam_ayna }}). İki fark 2024 → döneminde de aynı yönde.
- **ABD verisinden sonra ilk mum şanstan az sürüyor.** Normal bir veri mumunun devam payı 2018–2023'te
  {{ Y.ic.veri.normal.devam }} (şansla {{ Y.ic.veri.normal.devam_ayna }}), 2024 → döneminde
  {{ Y.dis.veri.normal.devam }} ({{ Y.dis.veri.normal.devam_ayna }}). Bu bir okuma; bu yönde bir tepki önceden
  yazılmadığı için sınanmadı.
- **Merkez bankası kararlarında olay az.** Planın artı sonuç veren tek tepkileri burada, ama işlem sayıları bir hüküm
  kurmaya yetmiyor.
- **Yüksek kazanma oranı kurmak kolay, kâr etmek değil.** Açılışta ilk mumun yarısına limitle girip yarım R hedefleyen
  tepkiler 2024 → döneminde işlemlerin {{ B.referans.acilis.normal.dis.kazanma }}–{{ B.referans.acilis.guclu.dis.kazanma }}
  kadarını kazandı; başa baş için {{ B.referans.acilis.guclu.dis.basabas }} gerekiyordu.

Bu sonuç ilk bakışta kafa karıştırır: işlemlerin çoğu kazanıyorsa nasıl kaybedilir? Cevap aşağıda, "Kazanma oranı
ile net sonuç" başlığında.

## Bu dersi masada nasıl kullanırsın

Bu ders bir işlem kuralı vermez; masadaki ilk dakikaları düzenler. Bir an geldiğinde, örneğin Londra açıldığında
(Londra 08:00; TSİ İngiltere yaz saatinde 10:00, kış saatinde 11:00), ilk mum kapanana kadar beklersin. Sonra mumu
dört sınıftan birine koyarsın ve tek bir soru sorarsın: bu mumdan sonra gördüğüm şey, yönü olmayan bir fiyatta da aynı
sıklıkta görülür müydü? Cevap çoğu anda "evet"tir. O zaman yapılacak iş işlem değil, işaretlemedir: iki uç, yarı ve
günün bir sonraki anının saati. Aşağıdaki şema bu sırayı beş soruya indirir; her sorunun dayanağı serinin bir
dersinde ölçülmüş bir sonuçtur ve hiçbir dal bir işlem önermez.

{{# karar ilk-mum }}

Son kutu bilerek dar yazıldı: ABD verisinden sonra ilk mumun yönü şanstan seyrek sürdü, ama bu yönde bir tepki önceden
yazılmadığı için sınanmadı. Veri mumunun yönüne güvenmezsin, tersine girmeyi de bir kural saymazsın.

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

Sınıf bir kapanış ölçüsüdür: on beş dakikalık bir açılış mumu onuncu dakikada güçlü görünüp reddedilen olarak
kapanabilir. Masada sırayla üç şeye bakarsın: mumun boyu, gövdenin boya oranı, en uzun fitilin boya oranı.

Boyu neyle kıyasladığın sınıfın kendisidir. Kıyas ekrandaki önceki mumlar değil, aynı anın geçmiş günlerdeki ilk
mumlarıdır; Asya seansının sakin mumlarıyla kıyaslanınca neredeyse her Londra açılış mumu güçlü görünür. Pratikte her
an için bir defter tutarsın: o anın son olaylarındaki ilk mum boyları ve ortancası. Defter bu dersin tanımıyla aynıysa
(son {{ S.tipik_pencere }} olay; veri ve kararlarda son {{ S.haber_pencere }}) okuduğun sınıf da bu dersin sınıfıdır;
başka bir defterle okunan sınıf bu derste ölçülmedi.

{{# sema siniflar }}

Şemadaki dört mum aynı anın dört ayrı gününden. Birinciyi güçlü yapan yalnız boyu değil, gövdenin mumu doldurmasıdır.
Üçüncüde yön sezgiye terstir: mum yukarı uzanmış ama yönü aşağıdır. Dördüncüde yön sorulmaz; iki ucu işaretleyip
hangisinin önce kırıldığını beklersin.

{{# kart reddedilen-acilis }}

Bu durumda yapmazsın: mum kapanmadan sınıf vermezsin; boyu ekrandaki komşu mumlarla kıyaslamazsın; uzun bir fitile,
sayılar desteklemediği hâlde "orada satıcı var" anlamı yüklemezsin (2. ders, Normal ve reddedilen ilk mum).

## Trend

Her ilk mum bir de günlük trendle karşılaştırılır. Trend, bir önceki günün kapanışının {{ S.ema_n }} günlük üssel
ortalamaya göre yeridir: kapanış ortalamanın üstünde ve ortalama son {{ S.ema_egim }} günde yükselmişse trend yukarı,
ikisi de tersi ise aşağı, başka her durumda yatay. İlk mumun yönü trendle aynıysa mum **trend yönünde**, tersse
**trende karşı** sayılır.

Açılış ve fiksing derslerinde trend ayrımı bir tabloyla verilir ve sayıları değiştirmiyor. Haber anlarında olay sayısı
böyle bir ayrım için yetmiyor. Plan trendi bir okuma bilgisi olarak taşır, karar ölçütü yapmaz.

Masada trendi bir satır not olarak yazarsın, bir süzgeç olarak kullanmazsın. Trend yönündeki güçlü bir açılış mumu
trende karşı olanından daha sık devam etmedi (2. ders, Trend bir şey değiştiriyor mu; 3. ders, Trend). "Trendle aynı
yönde, öyleyse bu kez sürer" cümlesi bu derslerin ölçtüğü bir şey değildir.

## İlk mumdan sonra ne olabilir

İlk mum kapandıktan sonra izlenen süre içinde dört şeye bakılır. Hepsi ilk mumun **boyu** cinsinden ölçülür:

- **Yarısına döndü.** Fiyat mumun orta noktasına geri geldi. (Fiksingde: koşunun yarısını geri verdi.)
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

Ayna masada bir alışkanlıktır. "Bak, devam etti" ya da "bak, yarısına döndü" dediğin her an aynı cümleyi aynalanmış
yol için de kurarsın: fiyat tam tersine aynı adımları atsaydı, aynı şeyi görür müydün? Güçlü bir mumda cevap çoğu
zaman evettir, çünkü eşiklerin kapanışa uzaklığı mumun şeklinden gelir.

{{# sema ayna-esik }}

Devam eşiği kapanıştan kısa bir yol, dönüş eşiği neredeyse bir mum boyu uzakta; yazı tura atan bir fiyat da yakın
eşiğe önce varır. Güçlü açılış mumunda devamın dönüşten yüksek çıkması bu yüzden aynada da aynen çıkar
({{ Y.ic.acilis.guclu.devam_ayna }} ve {{ Y.ic.acilis.guclu.donus_ayna }}). Masada sayıyı değil mesafeyi okursun:
kapanıştan iki eşiğe kaç pip olduğunu görünce hangisinin "sık" görüneceğini daha mum kapanırken bilirsin.

{{# sema ayna-yol }}

Tek bir günde gerçek yol ile aynası farklı biter ve bu bir şey kanıtlamaz; ayna binlerce olayda iki payı yan yana
koymak içindir. Gözle yapılan aynanın yararı başka yerdedir: "bu sefer farklı" duygusunun çoğu zaman mumun şeklinden
geldiğini fark ettirir.

{{# kart guclu-acilis }}

{{# ornek londra-guclu }}

Üstteki günde ① güçlü bir açılış mumudur ve fiyat, öbür ucu görmeden kendi ucunu yarım mum boyu aşmıştır; ③ varsa
② yarıya da bir kez dokunmuştur. Alttaki günde ① aynı sınıftan, gövdesi aynı ölçüde dolu bir mumdur; fiyat ③ önce
yarıya dönmüş, sonra kendi ucunu yarım mum aşmadan öbür ucu kırmıştır. ④ iki günde de izleme penceresinin sonudur.
İlk on beş dakikaya bakan biri iki günü ayıramazdı: iki mum da ucuna yakın kapanmış, ikisi de aynı tanımı taşıyor.
Fark sonraki saatlerde ortaya çıkar ve geriye bakınca üstteki gün "açıkça devam", alttaki "açıkça tuzak" görünür. İki
gün birlikte ne devamı ne dönüşü kanıtlar; ölçünün söylediği, binlerce günde iki sonucun aynadaki paylarla aynı
sıklıkta geldiğidir.

Fiksingde ayna başka bir şey söyler: güçlü koşunun yarısını geri vermesi aynadakinden sık
({{ Y.ic.fiksing.guclu.orta }} ve {{ Y.ic.fiksing.guclu.orta_ayna }}), koşunun sürmesi seyrek. Masada bu, fiksingden
sonra koşunun yönünde yeni bir hareket beklemediğin anlamına gelir; koşunun tersine girmenin bir kenar olduğu anlamına
gelmez, çünkü fark maliyetin altında kaldı (3. ders, Bu okumaları işleme çevirmek).

{{# kart fiksing-kosu }}

{{# ornek wmr-guclu }}

Üstteki günde ① fiksinge giden güçlü koşudur; fiksingden sonra fiyat ② koşunun yarısına geri gelir, ③ o dokunuşun
mumudur. Alttaki günde ① aynı sınıftan bir koşudur, ama fiyat fiksingden sonra koşunun yönünde yarım koşu boyu daha
ilerler; ③ varsa yarıya ancak bundan sonra dönmüştür. Fiksinge bakan biri iki koşuyu ayıramazdı; hangisinin "geri
verme günü" olduğu ancak ④ pencerenin sonunda belli olur. Üstteki gün okumayı doğrulamaz, alttaki yanlışlamaz: geri
verme payı aynadakinden yalnız biraz yüksek ve iki sonuç da sık görülür.

ABD verisinde ayna üçüncü bir şey gösterir: normal veri mumunun devam payı iki dönemde de aynadakinin altında. Bu bir
uyarıdır, bir işaret değil.

Bu bölümün masadaki karşılığı üç "yapmazsın" cümlesidir: güçlü açılış mumunun devamını yön saymazsın; fiksingden sonra
koşuyu kovalamazsın ve geri vermeyi bir işleme çevirmezsin; veri mumunun yönünü sürecek bir hareket saymazsın
(4. ders, ABD verileri).

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
arası) ek {{ ON.haber_kayma_pip }} pip. Limit emir kendi fiyatından dolar, kayma ödemez. Riski {{ ON.en_az_risk_pip }}
pipten küçük işlem açılmaz. Her tepkinin bir de **maliyetsiz** sonucu var: aynı kurallar orta fiyatla, makas ve kayma
olmadan. İkisinin farkı maliyetin payıdır.

### Masada: yarım R hedefin hesabı

Masada bir tepkiyi değerlendirmenin ilk adımı kazanma oranı değil, başa baş oranıdır: kayıp bir R, kazanç yarım R ise
üç işlemin ikisi. Maliyet bu sayıyı yukarı iter, çünkü kazanan biraz az kazanır, kaybeden biraz fazla kaybeder; 2024 →
döneminde güçlü açılış mumunda başa baş {{ B.referans.acilis.guclu.dis.basabas }} oldu. Gerçekleşen kazanma oranı
({{ B.referans.acilis.guclu.dis.kazanma }}) bunun altında kaldıkça yüksek görünmesi bir şey değiştirmez.

{{# sema yarim-r }}

Şemadaki hedef kapanışın altında duruyor: yarıya konan limit ile yarım R'lik hedef, mumun zaten gittiği yolun bir
kısmını geri almayı hedefler. Limit tanımı gereği fiyat piyasa girişinin aleyhine yürüdüğünde dolar (8. ders, Limit
neden ucuz görünür: ters seçim); dolduğu an mumun yönündeki okumanın bir kısmı zaten geri alınmıştır.

Bu durumda yapmazsın: kazanma oranına bakıp tepkiyi iyi saymazsın; başa baş oranını maliyetsiz hesaplamazsın (1. ders,
Kazanma oranı ile net sonuç).

## Emri nereye koyarsın

Bu ders bir işlem önermez. Ama başka bir gerekçeyle (kendi modelin, bir akış bilgisi) bir anın ilk mumundan sonra
işleme gireceksen, ilk mum emrin geometrisini, bu derste ölçülen maliyet kuralları da bedelini verir.

- **Giriş emri.** Piyasa emri hemen dolar, makası ve {{ ON.kayma_pip }} pip kaymayı öder. Mumun yarısına limit
  girişte makas ve kayma ödemez, çıkışta öder ve yalnız fiyat aleyhine yürüdüğünde dolar (8. ders, Limit neden ucuz
  görünür: ters seçim). Küçük mumun kırılan ucuna stop emri fiyatın zaten yürüdüğü yerden alır ve kaymayı öder
  (8. ders, Ucun kırılması). Onay mumu beklemek olayların bir kısmında hiç işlem açmamaktır; gelen onay, kaçırılan
  fiyatın bedelini ancak karşıladı (8. ders, Onay mumu).
- **Stop.** Bu serinin tepkilerinde stop ilk mumun öbür ucunun biraz ötesindedir; mumun içine konan stop bu derste
  ölçülmedi. Açılış mumu küçüktür, stop da küçüktür ve aynı makas küçük bir stopta daha büyük bir R olur (8. ders,
  Stop uzaklığı ve maliyet). Riski {{ ON.en_az_risk_pip }} pipten küçük işlem bu derste hiç açılmadı.
- **Hedef.** Yarım R'lik hedef kazanma oranını da başa baş eşiğini de yükseltir; hedefi seçmeden başa baş oranını
  hesaplarsın. Açılışlarda daha uzak hedefler de denendi ve hiçbiri maliyetten sonra artıda kalmadı (2. ders, Bu
  okumaları işleme çevirmek).
- **Emrin iptali.** Limit izlenen sürenin sonuna kadar dolmazsa çekilir; tepkiler o süreyle ölçüldü. Fiyat limit
  dolmadan devam eşiğine giderse emri taşıyıp kovalamazsın; o başka bir emirdir ve bu derste ölçülmedi.
- **Haber penceresi.** Açıklamadan iki dakika önce ile on beş dakika sonrası arasında her piyasa ve stop emri ek
  {{ ON.haber_kayma_pip }} pip kayma öder ve makas açılır (1. ders, Kazanma oranı ile net sonuç; 4. ders, Haber
  anları için masa kartı). Bekleyen bir emir bu pencereye taşınıyorsa maliyeti değişmiştir; önce takvime bakarsın.

{{# sema kucuk-kirilim }}

Şema küçük bir ilk mumun kırılımını gösteriyor: iki uca birer stop emri, biri dolunca öbürünün iptali, zarar stopu öbür
ucun biraz ötesinde, hedef girişten riskin yarısı kadar. Dar mumda bütün mesafeler dardır; makas ve kayma pip
cinsinden sabit kaldığı için R cinsinden büyür. Şemadaki gün tek bir yoldur; ölçü şunu söyler: küçük açılış mumunun
kırılımına girmek maliyetten önce sıfıra yakın, maliyetten sonra eksi çıktı (2. ders, Bu okumaları işleme çevirmek).

{{# kart kucuk-mum }}

## Sık yapılan hatalar

- **Mumu kapanmadan sınıflandırmak.** Sınıf kapanışın ölçüsüdür; onuncu dakikadaki güçlü mum reddedilen olarak
  kapanabilir (1. ders, İlk mumun dört sınıfı).
- **Boyu ekrandaki komşu mumlarla kıyaslamak.** Tipik boy aynı anın geçmiş olaylarından gelir (1. ders, İlk mumun dört
  sınıfı).
- **Devam payını yön sanmak.** Güçlü mum ucuna yakın kapanır, devam eşiği yakındır; aynada da aynı pay çıkar (1. ders,
  Şans ne verirdi: yolun aynası; 2. ders, Güçlü ilk mum).
- **Yarısına dönüşü alım ya da satım sebebi saymak.** Normal mum ortasına yakın kapanır, yarı bir adım ötededir;
  dönüş payı aynadakiyle aynı (2. ders, Normal ve reddedilen ilk mum).
- **Fiksingdeki geri vermeyi bir kenar sanmak.** Geri verme şanstan sık, ama koşunun tersine girmek maliyetten sonra
  çalışmadı (3. ders, Bu okumaları işleme çevirmek).
- **Kazanma oranına bakıp kâr beklemek.** Yarım R hedefte başa baş üçte ikinin üstündedir; açılışın referans tepkileri
  işlemlerin yarısından çoğunu kazanıp kaybettirdi (1. ders, Kazanma oranı ile net sonuç).
- **Merkez bankası kararındaki artı sonucu kural saymak.** Olay sayısı bir hüküm kurmaya yetmiyor (4. ders, Bu
  okumaları işleme çevirmek).

## Masa kontrol listesi

1. Hangi an ve TSİ kaçta? Tokyo açılışı 03:00, Tokyo fiksingi 03:55, Londra açılışı 10:00 (İngiltere kış saatinde
   11:00), ABD verisi 15:30 ve New York açılışı 16:30 (ABD kış saatinde 16:30 ve 17:30), Londra fiksingi 18:00
   (İngiltere kış saatinde 19:00).
2. Yakında bir veri ya da karar var mı? Varsa açıklamadan iki dakika önce ile on beş dakika sonrası arasında maliyet
   değişir.
3. İlk mum kapandı mı? Kapanmadıysa sınıf yok.
4. Boy, aynı anın geçmiş ilk mumlarının ortancasına göre ne kadar; gövde ve en uzun fitil boyun ne kadarı? Sınıf hangisi?
5. İki uç, yarı ve kendi ucunun yarım mum ötesi işaretli mi?
6. Gördüğüm şey aynada da aynı sıklıkta görülür müydü?
7. Fiksingse: koşu güçlü mü, ayın son Londra iş günü mü? Geri verme beklenir, koşunun sürmesi beklenmez.
8. Başka bir gerekçeyle girersem: başa baş oranı ne, maliyet riskin ne kadarı, limit ne zaman çekilir?

## Grafik okuma alıştırmaları

**1.** Londra açılışı (Londra 08:00; TSİ İngiltere yaz saatinde 10:00, kış saatinde 11:00). İlk mum onuncu dakikada
uzun bir gövdeyle yukarıda; on beşinci dakikada geri itilmiş, üst fitili uzun, gövdesi küçük kapanıyor. Onuncu
dakikada mumu "güçlü" diye not etmiştin. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Sınıf kapanışta verilir: mum reddedilen olarak kapandı ve yönü aşağıdır (Şekil M2'nin üçüncü mumu). Onuncu dakikadaki
not geçersizdir. Reddedilen açılış mumunda devam ile dönüş aynadakiyle aynı; yön okuması kurmazsın, iki ucu ve yarıyı
işaretlersin (1. ders, İlk mumun dört sınıfı; 2. ders, Normal ve reddedilen ilk mum).

</details>

**2.** Londra fiksingi (Londra 16:00; TSİ İngiltere yaz saatinde 18:00, kış saatinde 19:00). Fiyat fiksinge güçlü
yukarı koşmuş; fiksingden sonraki on dakikada koşunun üçte birini geri vermiş. Ne beklersin, ne yapmazsın?

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

Veri mumunun yönünün şanstan seyrek sürmesi iki dönemde görülen bir okumadır; bu yönde tepki önceden yazılmadığı için
sınanmadı ve kural değildir. Başka bir gerekçeyle girersen haber penceresinde ek kayma ve açık makas ödersin, dar stop
bu maliyeti R cinsinden büyütür (1. ders, Kısaca; 1. ders, Kazanma oranı ile net sonuç; 8. ders, Stop uzaklığı ve
maliyet).

</details>

**4.** New York açılışı (New York 09:30; TSİ ABD yaz saatinde 16:30, kış saatinde 17:30). İlk mum küçük; yirmi dakika
sonra fiyat üst ucu kırıyor, Şekil M8'deki gibi. Ne yaparsın, ne yapmazsın?

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
- **Bilinen sınırlar.** Referans tepkilerin 2018–2023 sonucu plan yazılırken biliniyordu. Bu verinin 2024 sonrası
  dönemiyle daha önce yirmi iki gün içi kural sınanmış ve yayımlanmıştı; o kuralların çoğunun maliyetten sonra eksi
  kaldığı biliniyordu. Bu planın kendi tepkilerinin 2024 sonrası sonucu ise hiç ölçülmemişti. Yolun aynası ölçüsü
  iki dönem de görüldükten sonra eklendi; bir betimlemedir, hüküm değildir.

Veri: Dukascopy bir dakikalık alış ve satış fiyatları, 2018 başından {{ veri_bitis }} tarihine kadar.

## Serinin dersleri

1. **İlk mumu okumak** (bu ders): anlar, sınıflar, ölçüler.
2. [**Açılışlar**](/arastirma/fx-oyun-acilislar/): Tokyo, Londra ve New York açılışlarının oyun planı.
3. [**Fiksingler**](/arastirma/fx-oyun-fiksingler/): Tokyo fiksingi ve Londra'nın WM/R fiksingi; ay sonu.
4. [**Haber mumları**](/arastirma/fx-oyun-haberler/): ABD istihdam ve enflasyon verisi, Fed, ECB ve BoE kararları.
5. [**Backtest**](/arastirma/fx-oyun-backtest/): planın bütün tepkileri iki dönemde, maliyetle; günün haritası.
