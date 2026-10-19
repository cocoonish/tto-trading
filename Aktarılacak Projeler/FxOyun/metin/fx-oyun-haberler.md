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

## Haberden sonra fiyat nereye gidiyor

İlk mum kapandıktan sonra ortalama fiyat, mumun yönünde ve mumun boyu cinsinden; iki aile, iki dönem.

{{# sekil 01_patika "Haber mumundan sonra ortalama fiyat yolu, ilk mumun yönünde" }}

Haber anlarında olay sayısı az olduğu için ortalama yol açılışlardaki kadar düzgün değildir; tek bir olay çizgiyi
belirgin oynatabilir. Şekil bir yön söylemek için değil, iki dönemin birbirinden ne kadar ayrıştığını görmek için.

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

## Küçük haber mumu

Açıklama ilk beş dakikada fiyatı oynatmamışsa, sonra kırıldığı tarafa ne kadar gidiyor:

{{# kucuk veri mb }}

Fed kararında küçük ilk mumdan sonra kırılan tarafta bir mum boyu ilerleme {{ K.ic.fomc.ilerle }}
(2024 → {{ K.dis.fomc.ilerle }}): karar metni fiyatı oynatmamışsa, hareket çoğu zaman sonra geliyor; basın toplantısı
izlenen sürenin içinde. ABD verisinde ise küçük ilk mum 2024 → döneminde daha da az ilerliyor (enflasyon verisinde
{{ K.dis.cpi.ilerle }}). ECB ve BoE'nin olay sayıları küçük ({{ K.dis.ecb.n }} ve {{ K.dis.boe.n }}).

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
