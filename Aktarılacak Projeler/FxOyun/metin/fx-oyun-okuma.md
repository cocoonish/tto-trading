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

## Trend

Her ilk mum bir de günlük trendle karşılaştırılır. Trend, bir önceki günün kapanışının {{ S.ema_n }} günlük üssel
ortalamaya göre yeridir: kapanış ortalamanın üstünde ve ortalama son {{ S.ema_egim }} günde yükselmişse trend yukarı,
ikisi de tersi ise aşağı, başka her durumda yatay. İlk mumun yönü trendle aynıysa mum **trend yönünde**, tersse
**trende karşı** sayılır.

Açılış ve fiksing derslerinde trend ayrımı bir tabloyla verilir ve sayıları değiştirmiyor. Haber anlarında olay sayısı
böyle bir ayrım için yetmiyor. Plan trendi bir okuma bilgisi olarak taşır, karar ölçütü yapmaz.

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
