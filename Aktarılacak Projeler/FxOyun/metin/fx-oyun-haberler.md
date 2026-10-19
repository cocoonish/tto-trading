---
title: 'FX Gün İçi Oyun Planı 4: Haber Mumları'
description: "ABD istihdam ve enflasyon verisi, Fed, ECB ve BoE kararları: açıklamadan sonraki ilk {{ AN.nfp.tf }} dakikanın mumu ne söylüyor? Güçlü, normal, reddedilen ve küçük haber mumundan sonra fiyatın davranışı, iki dönemde nasıl değiştiği, ve planın tek artı işaret veren tepkileri."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'haber', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · resmî yayım takvimleri · önceden kayıt'
ozet: "Haber mumu serinin en oynak anıdır ve en az güvenilir olanıdır. ABD verisinden sonraki davranış 2024 sonrasında değişti; merkez bankası kararlarında planın tepkileri iki dönemde de artı işaret verdi ama işlem sayısı bir hüküm kurmaya yetmiyor. Ders haber anlarının oyun planını ve sınırlarını verir."
seviye: 'orta'
onkosul: ['fx-oyun-okuma']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';

Bir veri ya da karar açıklandığında fiyat birkaç dakika içinde yeni bilgiyi fiyatlamaya çalışır. İlk mum bu yüzden
haber anlarında açılışlardan ve fiksinglerden çok daha büyüktür ve çok daha az sıktır: bir açılış her iş günü gelir,
bir istihdam verisi ayda bir, bir merkez bankası kararı yılda sekiz kez. Bu ders iki aileyi ayrı okur: **ABD verileri**
(tarım dışı istihdam ve tüketici fiyatları) ve **merkez bankası kararları** (Fed, ECB, BoE).

{{# an_tablo veri mb }}

Saatler resmî yayım takviminden alınır, tahmin edilmez. Burada **ilk mum** açıklamadan sonraki ilk {{ AN.nfp.tf }}
dakikadır. Tipik boy o anın son {{ S.haber_pencere }} olayından ölçülür. Haber anında makas açılır ve emirler kayar;
maliyet bu yüzden açıklamadan iki dakika önce ile on beş dakika sonrası arasında ek {{ ON.haber_kayma_pip }} pip
kayma içerir.

## Plan tek cümlede

**Haber mumunu tek başına bir sinyal olarak okumak iki dönemde aynı sonucu vermiyor.** ABD verisinde ilk mumun devam
etme payı 2024 sonrasında belirgin düştü. Merkez bankası kararlarında güçlü ilk mumun yönünde kalmak iki dönemde de
artı işaret verdi, ama 2024 sonrasında yalnız {{ B.islem.mb.guclu.dis.n }} işlemle; bu bir hüküm değil, izlenecek bir
aday.

## Haberden sonra fiyat nereye gidiyor

İlk mum kapandıktan sonra ortalama fiyat, mumun yönünde ve mumun boyu cinsinden; iki aile, iki dönem.

{{# sekil 01_patika "Haber mumundan sonra ortalama fiyat yolu, ilk mumun yönünde" }}

Haber anlarında olay sayısı az olduğu için ortalama yol açılışlardaki kadar düzgün değildir; tek bir olay çizgiyi
belirgin oynatabilir. Şekil bir yön söylemek için değil, iki dönemin birbirinden ne kadar ayrıştığını görmek için.

## ABD verileri

{{# davranis veri }}

2018–2023'te ABD verisinden sonra güçlü bir ilk mum çoğu zaman yönünde kaldı: {{ D.ic.veri.guclu.devam }} devam,
{{ D.ic.veri.guclu.donus }} dönüş. 2024 → döneminde iki pay da düştü ({{ D.dis.veri.guclu.devam }} ve
{{ D.dis.veri.guclu.donus }}): olayların çoğunda fiyat izlenen süre boyunca ne ilk mumun ucunu yarım mum boyu aştı ne
öbür ucunu kırdı. Normal
mumda devam {{ D.ic.veri.normal.devam }} iken {{ D.dis.veri.normal.devam }} oldu. Yarısına dönüş ise hâlâ yüksek
(normal mumda {{ D.dis.veri.normal.orta }}).

Bunun sebebi bu derste ölçülmedi. İki dönemin farkı bir piyasa değişimi olabilir (veriden sonraki ilk dakikalarda
fiyatlamanın daha hızlı bitmesi), küçük örneklemin dalgalanması da olabilir: 2024 → döneminde güçlü veri mumu
{{ D.dis.veri.guclu.n }} olay. Plan için sonuç aynı: ABD verisinin ilk mumuna dayanan bir okuma iki dönemde aynı
yöne bakmıyor.

## Merkez bankası kararları

{{# davranis mb }}

Kararlarda güçlü ilk mum 2018–2023'te {{ D.ic.mb.guclu.devam }} devam etti, {{ D.ic.mb.guclu.donus }} döndü;
2024 → döneminde {{ D.dis.mb.guclu.devam }} devam etti ve tersine dönen olmadı. Ama 2024 → döneminde güçlü karar mumu
yalnız {{ D.dis.mb.guclu.n }} olay. Reddedilen karar mumu iki dönemde de devamı dönüşten sık gösteriyor
({{ D.ic.mb.reddedilen.devam }} ve {{ D.ic.mb.reddedilen.donus }}; 2024 → {{ D.dis.mb.reddedilen.devam }} ve
{{ D.dis.mb.reddedilen.donus }}), yine çok az olayla ({{ D.ic.mb.reddedilen.n }} ve {{ D.dis.mb.reddedilen.n }}).

Kararın ilk beş dakikası yalnız karar metnidir. Fed'de basın toplantısı karardan yarım saat sonra başlar (ECB'de
bugün yarım saat, 2022 ortasına kadar üç çeyrek saat) ve izlenen {{ AN.fomc.pencere }} dakika onu da içerir. Yani bir
karar mumunun "devam etmesi", metnin ve basın toplantısının aynı yöne bakması anlamına gelebilir. Basın toplantısının
ayrı etkisi bu derste ölçülmedi.

## Küçük haber mumu

Açıklama ilk beş dakikada fiyatı oynatmamışsa, sonra kırıldığı tarafa ne kadar gidiyor:

{{# kucuk veri mb }}

Küçük haber mumu iki aile arasında en çok ayrışan sınıf. Fed kararında küçük ilk mumdan sonra kırılan tarafta bir mum
boyu ilerleme {{ K.ic.fomc.ilerle }} (2024 → {{ K.dis.fomc.ilerle }}): karar metni fiyatı oynatmamışsa, hareket
çoğu zaman sonra geliyor; basın toplantısı izlenen sürenin içinde. ABD verisinde ise küçük ilk mum 2024 → döneminde daha da az ilerliyor
(enflasyon verisinde {{ K.dis.cpi.ilerle }}). ECB ve BoE'nin olay sayıları küçük ({{ K.dis.ecb.n }} ve
{{ K.dis.boe.n }}).

## Bu okumaları işleme çevirmek

Haber anlarında planın iki tür tepkisi var. **Referans tepkiler** açılış ve fiksinglerle aynı kuralla kuruldu (yarısına
limit, yarım R hedef; küçük mumda kırılım). **İşlem tepkileri** ise önceden yazılmış seçim kuralıyla, 2018–2023'te
denenen adayların içinden maliyetten sonra artıda kalan en iyisi olarak seçildi. Önce referanslar:

{{# bacaklar referans veri mb }}

Merkez bankasının küçük mumunda kırılım tepkisi 2024 → döneminde işlemlerin {{ B.referans.mb.kucuk.dis.kazanma }}
kadarını kazandı ve net {{ B.referans.mb.kucuk.dis.R }} R verdi; aralığın alt ucu
{{ B.referans.mb.kucuk.dis.alt }}, yani hüküm "{{ B.referans.mb.kucuk.hukum }}". 2018–2023'te aynı tepki
{{ B.referans.mb.kucuk.ic.R }} R kaybettirmişti. İki dönemde ayrı işaret veren bir tepki plana girmez.

İşlem tepkileri:

{{# bacaklar islem veri mb }}

{{# sekil 02_bacaklar "Haber anlarında işlem tepkileri: iki dönemde net sonuç" }}

- **Güçlü karar mumu, kapanışta mumun yönünde, yarım R hedef.** 2024 → döneminde {{ B.islem.mb.guclu.dis.n }}
  işlemin {{ B.islem.mb.guclu.dis.kazanma }} kadarı kazandı, net {{ B.islem.mb.guclu.dis.R }} R. Hiçbiri stopta
  bitmedi. Ama {{ ON.hukum_en_az }} işlemin altında hüküm kurulmaz ("{{ B.islem.mb.guclu.hukum }}"), ve 2018–2023'teki
  sonucu sıfıra çok yakındı ({{ B.islem.mb.guclu.ic.R }} R, {{ B.islem.mb.guclu.ic.n }} işlem). Stop geniş: ortanca
  risk {{ B.islem.mb.guclu.dis.risk_pip }} pip.
- **Normal karar mumu, yarısına limit, bir R hedef.** {{ B.islem.mb.normal.dis.n }} işlemde net
  {{ B.islem.mb.normal.dis.R }} R; aralık {{ B.islem.mb.normal.dis.alt }} … {{ B.islem.mb.normal.dis.ust }}, hüküm
  "{{ B.islem.mb.normal.hukum }}".
- **Reddedilen karar mumu, kapanışta reddin yönünde, bir R hedef.** {{ B.islem.mb.reddedilen.dis.n }} işlem;
  ölçülemedi.
- **Güçlü veri mumu, yarısına limit, hedef mumun ucu.** 2018–2023'te artıda kalmıştı
  ({{ B.islem.veri.guclu.ic.R }} R); 2024 → döneminde {{ B.islem.veri.guclu.dis.n }} işlemde
  {{ B.islem.veri.guclu.dis.R }} R. Yukarıda görülen davranış değişikliği burada sonuca yansıyor: işlemlerin
  {{ B.islem.veri.guclu.dis.zaman_pay }} kadarı ne hedefe ne stopa ulaşıp sürenin sonunda kapandı.
- **Küçük veri mumu, kırılımda, bir R hedef.** {{ B.islem.veri.kucuk.dis.n }} işlemde net
  {{ B.islem.veri.kucuk.dis.R }} R, hüküm "{{ B.islem.veri.kucuk.hukum }}"; maliyetsiz sonucu artı
  ({{ B.islem.veri.kucuk.dis.brut }} R).

## Haber anları için masa kartı

- **Haber mumu yeni bilginin ilk fiyatıdır, son fiyatı değil.** Yarısına dönüş haberde de sıktır.
- **ABD verisinin ilk beş dakikası 2024 sonrasında daha az şey söylüyor.** Veri mumunun yönüne dayanan bir okuma
  bugün eskisi kadar sürmüyor.
- **Karar metni fiyatı oynatmadıysa hareket sonra gelebilir.** Fed'de küçük ilk mumdan sonra kırılım iki dönemde de
  çoğu zaman yol aldı; ama üç bankanın küçük karar mumu kırılımı bir işleme çevrildiğinde iki dönem ayrı işaret
  verdi.
- **Güçlü karar mumunun yönünde kalmak, serinin tek tutarlı artı adayıdır.** Tutarlı ama küçük: 2024 sonrasında
  {{ B.islem.mb.guclu.dis.n }} işlem. Bir sonraki dönemde, önceden yazılmış kuralla yeniden sınanmadan bir kural
  sayılmaz.
- **Haber anının maliyeti farklıdır.** Makas açılır, kayma artar; dar stoplu bir haber işlemi maliyete en çok
  dayanan işlemdir.
