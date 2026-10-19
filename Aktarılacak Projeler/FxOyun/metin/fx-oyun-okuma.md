---
title: 'FX Gün İçi Oyun Planı 1: İlk Mumu Okumak'
description: "Açılışlar, fiksingler, ABD verileri ve merkez bankası kararları: fiyat bu anlarda ilk mumdan sonra genelde ne yapıyor? İlk mumu dört sınıfa ayırıp her sınıfta fiyatın ne yaptığını {{ olay_ic }} olayda okuyan bir oyun planı; plan 2018–2023'ten yazıldı, 2024 sonrasında sınandı."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Bir gün içi işlemci için günün belirli anları vardır: açılış, fiksing, veri, karar. Bu ders o anların ilk mumunu dört sınıfa ayırır (güçlü, normal, reddedilen, küçük), fiyatın her sınıftan sonra genelde ne yaptığını gösterir ve serinin oyun planını nasıl okuyacağınızı anlatır."
seviye: 'giris'
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';

Bir gün içi işlemcinin günü saatlere değil anlara bölünür. Tokyo açılır, Londra açılır, New York açılır; Tokyo ve
Londra'da kur fiksingleri yapılır; ayın belirli günlerinde ABD istihdam ve enflasyon verisi gelir; altı haftada bir
merkez bankaları karar açıklar. Bu anların her birinde fiyat kısa bir süre içinde bir şey söyler. O ilk söz, yani **ilk
mum**, çoğu işlemcinin günün geri kalanını okuduğu yerdir.

Bu seri o anları anlatır. Bir kural listesi değildir: "fiyat şu seviyeyi kırarsa al" demez. Her anın ilk mumunu bir
sınıfa koyar, o sınıftan sonra fiyatın genelde ne yaptığını gösterir ve bunun üstüne bir **oyun planı** yazar: bu
anda ne beklenir, ne beklenmez, nerede sabırlı olunur, nerede masadan kalkılır. Plan 2018–2023 verisinden yazıldı ve
2024 sonrasının verisi hiç açılmadan kaydedildi; sonra 2024 → döneminde, gerçek alış-satış fiyatları ve maliyetle
sınandı.

## Kısaca

Serinin beş dersinin özü:

- **Açılışlarda ilk mum neredeyse her zaman yarısına geri döner.** Normal bir açılış mumunun yarısına dönüş payı
  2018–2023'te {{ D.ic.acilis.normal.orta }}, 2024 → döneminde {{ D.dis.acilis.normal.orta }}. Bu bir giriş sinyali
  değil, açılışın olağan hâlidir: yarısına dönen mumun kendi ucuna geri gitme payı yalnız
  {{ D.ic.acilis.normal.uc_orta }}.
- **Güçlü bir ilk mum yön söyler ama zayıf söyler.** Güçlü açılış mumu {{ D.ic.acilis.guclu.devam }} devam etti,
  {{ D.ic.acilis.guclu.donus }} tersine döndü; 2024 → döneminde {{ D.dis.acilis.guclu.devam }} ve
  {{ D.dis.acilis.guclu.donus }}. Normal ve reddedilen mumda devam ile dönüş yarı yarıya.
- **Fiksinge koşan fiyat koşunun yarısını geri verir ama nadiren tersine döner.** Güçlü bir koşu fiksingden sonraki
  bir saatte {{ D.ic.fiksing.guclu.orta }} yarısını geri verdi; koşunun başladığı yeri kıran yalnız
  {{ D.ic.fiksing.guclu.donus }}.
- **Haber mumları en az güvenilir olanıdır.** ABD verisinde ilk beş dakikanın davranışı 2024 → döneminde değişti;
  merkez bankası kararlarında ise işlem sayısı bir hüküm kuracak kadar değil.
- **Yüksek kazanma oranı kurmak kolay, kâr etmek değil.** Sık gelen anlarda (açılış ve fiksing) yakın hedefli
  tepkiler 2024 → döneminde işlemlerin {{ sik_kaz_alt }}–{{ sik_kaz_ust }} kadarını kazandı, ama işlem başına net
  sonuç {{ sik_R_alt }} ile {{ sik_R_ust }} R arasında kaldı. {{ sik_sayi }} tepkinin {{ sik_calismiyor }} tanesi
  "çalışmıyor" hükmü aldı.

Bu sonuç ilk bakışta kafa karıştırır: işlemlerin çoğu kazanıyorsa nasıl kaybedilir? Cevap aşağıda, "Kazanma oranı
ile net sonuç" başlığında. Kısa hâli: yakın bir hedefle kazanılan küçük kazançlar, ara sıra gelen tam stopları
karşılamıyor.

## On an

Seri {{ an_sayi }} anı inceler; hepsi {{ pariteler }} paritelerinde. Saatler yerel saat ve Türkiye saati (TSİ) olarak
verilir. Avrupa ve ABD yaz saatine geçtiğinde TSİ karşılığı bir saat erkene kayar; Tokyo yaz saati uygulamaz.

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
  kadarı. Fiyat bir yöne karar vermiş ve o yönde kapanmış. Yönü mumun yönüdür.
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

Sonuç önceden söylensin: trend ilk mumdan sonraki davranışı belirgin değiştirmiyor. Her derste trend ayrımı bir tabloyla
verilir ve sayılar neredeyse aynıdır. Plan bu yüzden trendi bir okuma bilgisi olarak taşır, karar ölçütü yapmaz.

## İlk mumdan sonra ne olabilir

İlk mum kapandıktan sonra izlenen süre içinde dört şeye bakılır. Hepsi ilk mumun **boyu** cinsinden ölçülür:

- **Yarısına döndü.** Fiyat mumun orta noktasına geri geldi. (Fiksingde: koşunun yarısını geri verdi.)
- **Devam etti.** Fiyat, mumun öbür ucunu görmeden, kendi ucunu yarım mum boyu aştı.
- **Tersine döndü.** Fiyat, kendi ucunu yarım mum boyu aşmadan, mumun öbür ucunu kırdı.
- **Geri çekilip devam etti.** Fiyat önce yarısına döndü, sonra öbür uca gitmeden kendi ucuna ulaştı.

Aynı dakikada iki seviye birden görülürse hangisinin önce geldiği bilinemez; o olay iki sonuçta da "olmadı" sayılır.

Dört an ailesinde, üç yönlü sınıfta, iki dönemde yarısına dönüş, devam ve dönüş:

{{# sekil 02_yarisi "Yarısına dönüş, devam ve dönüş: dört aile, iki dönem" }}

Şekil serinin özetidir. Açılışlarda yarısına dönüş neredeyse kesindir ve iki dönemde de aynıdır. Fiksinglerde güçlü
koşu sık geri verilir ama nadiren tersine döner. Haberlerde iki dönem birbirinden en çok ayrışan ailedir.

## Kazanma oranı ile net sonuç

Planın her okuması bir **tepkiye** çevrilip sınandı: ilk mumun yarısına limitle mumun yönünde girmek, küçük mumun
kırılan ucundan girmek, fiksingde koşunun tersine girmek gibi. Her tepkinin bir stopu ve bir hedefi var.

Sonuç **R** cinsinden yazılır. R, riske edilen mesafedir: giriş ile stop arası. Hedef girişten riskin yarısı kadar
uzaktaysa ("hedef yarım R") kazanan işlem yarım R kazanır, stopa gelen işlem bir R kaybeder. Böyle bir tepkinin başa baş
kalması için işlemlerin üçte ikisini kazanması gerekir: üç işlemin ikisi kazanıp biri kaybederse toplam sıfırdır.

Bu yüzden kazanma oranı tek başına hiçbir şey söylemez. Hedef yaklaştıkça kazanma oranı yükselir, ama kazanan işlemin
getirdiği de küçülür. Sık gelen anlarda yakın hedefli tepkiler (yarım R ya da fiksingde koşunun yarısı) 2024 →
döneminde işlemlerin {{ sik_kaz_alt }} ile {{ sik_kaz_ust }} kadarını kazandı; her birinde başa baş için gereken oran
bunun üstündeydi, bu yüzden işlem başına net sonuç {{ sik_R_alt }} ile {{ sik_R_ust }} R arasında kaldı. Bir örnek:
Londra, Tokyo ve New York açılışlarında güçlü ilk mumun yarısına limitle girip yarım R hedefleyen tepki işlemlerin
{{ B.referans.acilis.guclu.dis.kazanma }} kadarını kazandı; ortalama kazanç {{ B.referans.acilis.guclu.dis.kazanc }} R,
ortalama kayıp {{ B.referans.acilis.guclu.dis.kayip }} R, başa baş için gereken kazanma oranı
{{ B.referans.acilis.guclu.dis.basabas }}. Sonuç işlem başına {{ B.referans.acilis.guclu.dis.R }} R.

Net sonuç maliyetten sonradır. Her işlem gerçek alış-satış farkını (makas) öder. Piyasa, stop ve kırılım emirleri
ayrıca {{ ON.kayma_pip }} pip kayma öder; veri ve karar anında (açıklamadan iki dakika önce ile on beş dakika sonrası
arası) ek {{ ON.haber_kayma_pip }} pip. Limit emir kendi fiyatından dolar, kayma ödemez. Riski {{ ON.en_az_risk_pip }}
pipten küçük işlem açılmaz: o kadar dar bir stopu makas tek başına yer.

## Bu planın dürüstlük kuralları

- **Plan 2018–2023'ten yazıldı.** Gözlem ({{ olay_ic }} olay) ve tepkilerin seçimi yalnız o dönemin verisiyle
  yapıldı. 2024 sonrasının dosyaları gözlem sırasında hiç açılmadı.
- **Seçim kuralı önceden yazıldı.** Bir an ailesi ve ilk mum sınıfı için "işlem" tepkisi, 2018–2023'te en az
  {{ ON.secim_en_az }} işlemi olan ve maliyetten sonra artıda kalan adaylardan en iyisidir. Hiçbir aday artıda
  değilse o hücrede plan "izle, işlem açma" der.
- **Hüküm 2024 → döneminden verilir.** İşlem başına net sonucun güven aralığı (işlemlerden yeniden örnekleme,
  {{ ON.bootstrap }} tekrar) tamamen sıfırın üstündeyse **çalışıyor**, ortalama artı ama aralık sıfırı kapsıyorsa
  **zayıf**, ortalama eksiyse **çalışmıyor**. {{ ON.hukum_en_az }} işlemin altında hüküm **ölçülemedi**dir; sonuç
  yine yazılır.
- **Bilinen bir sınır.** Bu verinin 2024 sonrası dönemiyle daha önce yirmi iki gün içi kural sınanmış ve yayımlanmıştı;
  o kuralların çoğunun maliyetten sonra eksi kaldığı, bu plan yazılırken biliniyordu. Bu planın kendi tepkilerinin
  2024 sonrası sonucu ise hiç ölçülmemişti.

Veri: Dukascopy bir dakikalık alış ve satış fiyatları, 2018 başından {{ veri_bitis }} tarihine kadar.

## Serinin dersleri

1. **İlk mumu okumak** (bu ders): anlar, sınıflar, ölçüler.
2. [**Açılışlar**](/arastirma/fx-oyun-acilislar/): Tokyo, Londra ve New York açılışlarının oyun planı.
3. [**Fiksingler**](/arastirma/fx-oyun-fiksingler/): Tokyo fiksingi ve Londra'nın WM/R fiksingi; ay sonu.
4. [**Haber mumları**](/arastirma/fx-oyun-haberler/): ABD istihdam ve enflasyon verisi, Fed, ECB ve BoE kararları.
5. [**Backtest**](/arastirma/fx-oyun-backtest/): planın bütün tepkileri iki dönemde, maliyetle; neyin çalışmadığı.
