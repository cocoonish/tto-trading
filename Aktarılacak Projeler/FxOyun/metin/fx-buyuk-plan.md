---
title: 'FX Gün İçi Oyun Planı 9: Büyük Mum — Oyun Planı ve 2024 Sınaması'
description: "Büyük mum okumalarından 2018–2023 verisiyle seçilip 2024 sonrası hiç görülmeden kaydedilen giriş planı: seçim kuralı, taranan {{ plan.aday }} aday, seçilen üç giriş, on iki referans giriş ve 2024 → döneminin sonucu. Sonunda büyük mum için bir oyun planı."
pubDate: 2026-10-20
tags: ['fx', 'gun-ici', 'oyun-plani', 'buyuk-mum', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "2018–2023'ün en iyi üç büyük mum girişi 2024 sonrasında tutmadı; on iki referans girişin hiçbiri de artıda değil. 5 dakikadaki geri verme 2024 sonrasında da görüldü, 1 saatteki devam yalnız nokta tahmini olarak; ikisi de her girişte maliyetten küçük. Büyük mum bir işlem sinyali değil, bir okuma: nerede kovalanmaz, nerede limitin dolması kötü haberdir, nerede masadan kalkılır."
seviye: 'orta'
onkosul: ['fx-buyuk-mum', 'fx-buyuk-suzgec', 'fx-buyuk-giris']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';
import Diyagram from '../../components/Diyagram.astro';

Önceki üç ders büyük mumu okudu, süzdü ve girişin biçimini ölçtü. Bu ders o çalışmanın sınavıdır. 2018–2023'ün sonucu
görülerek bir seçim kuralı yazıldı, kural o dönemin tablosuna uygulandı ve seçilen girişler, 2024 ve sonrasının
fiyatları hiçbir hesaba girmeden, ön kayıtla birlikte kaydedildi. Sonra aynı kurallar 2024 → döneminde
({{ ON.dis_bitis }} tarihine kadar) koşturuldu. Bu dersin 2024 → sayılarının hepsi o sınamadan.

## Kısaca

Kısa cevap: 5 dakikada büyük mumu kovalama, 1 saatte tersine girme. İki eğilim de 2018–2023'te ölçülebiliyor, 5
dakikadaki 2024 sonrasında da; ikisi de maliyetten sonra işlem çıkarmıyor. Limit maliyeti düşürür, kenar yaratmaz.

- **Seçilen üç girişin üçü de tutmadı.** 2018–2023'te iki yarıda da artı olan en iyi girişler 2024 sonrasında eksi ya da
  sıfırdaydı. En iyisi (1 saatte, aynı yönde koşudan sonraki büyük mumda mumun {{ Y.25 }} geri çekilmesine limit) 2018–2023'te
  {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.ic.R }} R verdi, 2024 sonrasında
  {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.R }} R.
- **On iki referans girişin hiçbiri artıda değil.** Büyük mumdan sonra "mumun yönünde gir", "yarısına limitle katıl",
  "tersine gir", "uzamayı sat" girişleri her dilimde maliyetten sonra eksi.
- **Hüküm: {{ hukum_cumle }}.** Hiçbiri "zayıf" ya da "çalışıyor" almadı.
- **Davranış kısmen sürdü, kenar sürmedi.** 5 dakikadaki hafif geri verme 2024 sonrasında da aralığıyla görüldü;
  1 saatteki devam 2024 sonrasında yalnız nokta tahmini olarak sürdü ({{ D.60.dis.net_24 }} ATR, aralık
  {{ D.60.dis.net_24_alt }} … {{ D.60.dis.net_24_ust }}). İkisi de her girişte maliyetten küçük (6. ders).

## Bu dersi masada nasıl kullanırsın

Bu dersin tabloları bir işlem listesi değildir; on beş girişin hepsi çalışmıyor. Masada kullanılacak olan şey tabloların
arkasındaki sıradır: büyük bir mum kapandığında hangi soruyu hangi sırayla sorduğun ve hangi cevabın seni durdurduğu.
Büyük mum burada da önceki derslerdeki tanımıyla okunur: aralığı kendinden önceki mumun ATR'sinin en az iki katı olan
ve kümenin ilk büyük mumu olan mum (6. ders, Büyük mum nasıl tanımlandı). Aşağıdaki şema o sırayı baştan sona verir:
önce dilim, sonra takvimdeki haber, sonra kapanışın yeri, sonra seans. Her soru ya seni durdurur ya da bir sonrakine
geçirir.

{{# karar plan-akis }}

Şemanın hiçbir kutusu "gir" demez. Bu bir yazım tercihi değil, sınamanın sonucudur: 2024 sonrasında hiçbir giriş
maliyetten sonra artıda kalmadı (9. ders, Hüküm kuralı). Şemanın verdiği üç cevap (yapma, bekle, kalk) neyi
yapmayacağını, nerede bekleyeceğini ve ne zaman masadan kalkacağını söyler. Mumdan bağımsız bir gerekçeyle (bir seviye,
daha büyük dilimde bir plan, bir haber görüşü) zaten işleme girecek biri için emrin biçimi, yeri ve iptali bu dersin
"Emri nereye koyarsın" bölümündedir; şema o gerekçeyi ne güçlendirir ne çürütür.

## Seçim kuralı

Kural, 2018–2023 ızgarası görüldükten sonra ve 2024 sonrasının fiyatları hiçbir hesaba girmeden ön kayda yazıldı:

1. Her dilim (5 dakika, 15 dakika, 1 saat) ve her yön (mumun yönünde, tersine) için aday girişler: 8. dersin ızgarasının
   bütün hücreleri (emir biçimi × stop × hedef), süzgeçsiz ya da 7. dersin süzgeçlerinden **tek bir** değerle.
2. Uygun aday: 2018–2023'te en az {{ ON.secim_en_az }} işlem, maliyetten sonra ortalaması sıfırın üstünde, **ve**
   2018–2020 ile 2021–2023 yarılarının ikisinde de sıfırın üstünde.
3. Uygunların içinden maliyetten sonra ortalaması en yüksek olan seçilir. Uygun aday yoksa o dilim ve yön için "işlem
   yok".

Kural toplam {{ plan.aday }} adayı taradı. Bu sayı önemli: bu kadar adayın içinden en iyisini seçmek, en iyisinin
2018–2023'teki sonucunu şansla şişirir. 2024 → dönemi o şişkinliği ölçer.

Stop emirli girişlerde dolum dakikasının nasıl sayılacağı 2024 sınamasından sonra değişti (8. dersin "Ölçülmeyenler"i).
Seçim yeni kuralla yeniden uygulandığında seçilen üç giriş ve referanslar aynı kaldı; değişen tek şey, kuralın "işlem
yok" dediği 15 dakika tersine hücresinin en iyi adayı oldu. 2024 → sonuçlarının hiçbiri değişmedi.

Seçimin bir sınırı var: aynı veriyle (dört majör, 2024 →) bu seride daha önce başka kuralların sonuçları
yayımlandı; 2024 sonrasının toplu davranışı bu plan yazılırken biliniyordu. Büyük mumdan sonraki davranışın ve bu
girişlerin 2024 sonrası sonucu ise ölçülmemişti.

## Seçilen girişler

{{# bacaklar islem }}

Altı dilim × yön hücresinden {{ plan.islem_sayi }} hücrede kurala uyan bir aday çıktı, {{ plan.yok_sayi }} hücrede
çıkmadı. Seçilenlerin üçü de bir süzgeç taşıyor: ikisi takvimdeki haber mumu, biri aynı yönde koşudan sonraki büyük mum.
Bu bir rastlantı değil: süzgeçli adaylar süzgeçsizlerin kat kat fazlasıdır ve en iyi adayın küçük bir alt kümeden çıkma
olasılığı yükselir. Küçük alt küme, şansın en kolay şişirdiği yerdir.

- **5 dakika, haber mumunu ucundan tersine.** 2018–2023'te {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.ic.n }} işlem,
  iki yarıda {{ P.5.ters.y1 }} ve {{ P.5.ters.y2 }} R. 2024 sonrasında {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.dis.n }}
  işlem, {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.dis.R }} R. Maliyetten önce
  {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.dis.brut }} R.
- **1 saat, aynı yönde koşudan sonraki büyük mumda {{ Y.25 }} geri çekilmeye limit.** 2018–2023'te iki yarıda
  {{ P.60.devam.y1 }} ve {{ P.60.devam.y2 }} R. 2024 sonrasında {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.n }}
  işlem, {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.R }} R ({{ Y.95 }} aralık
  {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.alt }} … {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.ust }};
  hafta düzeyinde {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.hafta_alt }} …
  {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.hafta_ust }}). Maliyetten önce de eksi
  ({{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.brut }} R): 2018–2023'teki sonuç görülmemiş dönemde tekrarlanmadı.
- **1 saat, haber mumunu ucundan tersine.** 2018–2023'te {{ B.islem.60.ters:limit_uc:s1:h2.haber=haber.ic.R }} R (en küçük
  artı), 2024 sonrasında {{ B.islem.60.ters:limit_uc:s1:h2.haber=haber.dis.R }} R.

Kuralın "işlem yok" dediği hücreler ve o hücrelerin en iyi adayı:

{{# yok }}

### Masada: seçilen ama tutmayan girişler

Üç giriş tutmadı, ama masada bir şey öğretir: hangi görüntüye güvenmeyeceğini. İkisi takvimdeki haber mumundan çıktı,
yani 7. dersin "okuma yok" dediği yerden (7. ders, Fade mi, devam mı: okuma tablosu). Seçim kuralı okumayı bilmez; en
yüksek ortalamayı arar, ve en yüksek ortalama çoğu zaman olayı az, dağılımı geniş yerde şansla çıkar. 5 dakikalık haber
girişi 2024 sonrasında maliyetten önce sıfıra yakın kaldı
({{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.dis.brut }} R): geri vermenin izi orada da çok küçük, ve haber
penceresindeki maliyet onu siliyor. Şema bu girişin masadaki görüntüsüdür.

{{# sema uc-limit }}

Şemanın öğrettiği şey dolumun zamanlamasıdır. Mumun ucuna konan tersine limit, fiyat uca geri geldiğinde dolar; fiyatın
uca geri gelmesi ise o olayda geri vermenin olmadığı anlamına gelir. İlk mumdaki küçük geri verme gerçek olsa da limit
onu yakalamaz, çünkü emir o mumda dolmaz (8. ders, Limit neden ucuz görünür: ters seçim).

1 saatlik giriş ikinci dersi verir: küçük alt küme. Koşu süzgeci 7. dersin tablosunda 24 mumluk yolu kendi başına
ayırmıyordu (7. ders, 1 saat); ızgaranın tek bir hücresiyle birleşince 2018–2023'te iki yarıda artı göründü ve 2024
sonrasında maliyetten önce de eksi kaldı. Ayrı ayrı bir şey söylemeyen iki parçanın birlikte iyi görünmesi, binlerce
adayın içinde en kolay ortaya çıkan şeydir.

{{# kart kosu-sonrasi }}

Bu durumlarda yapmazsın: "Seçilen girişler" tablosundaki bir satırı işlem planına kopyalamazsın, çünkü 2018–2023 sütunu
seçimin kendisidir ve 2024 sütunu onun sınavıdır; haber mumunun ucuna tersine limit koyup bunu sınanmış bir giriş
saymazsın; bir süzgecin tek başına ayırmadığı bir durumu, bir stop ve hedefle birleşti diye kural saymazsın.

## Referans girişler

Seçimin dışında, her dilimde aynı dört giriş de koşturuldu. Bunlar büyük mum için en sık söylenen dört tepkinin en düz
hâlidir ve seçimden bağımsızdır; 2018–2023'teki sonuçları da bu yüzden şişmemiştir.

{{# bacaklar referans }}

Referansların hepsi 2024 sonrasında maliyetten sonra eksi. Maliyetten önce 5 dakikada tersine piyasa girişi
({{ B.referans.5.ters:piyasa:s2:h1.dis.brut }} R) ve 1 saatte mumun yönündeki girişler sıfırın biraz üstünde: 6. dersin
okumaları burada da görünüyor, ama yine maliyetin altında.

{{# sekil 01_bacaklar "On beş girişin iki dönemi" }}

{{# sekil 02_egri "Seçilen üç giriş, birikimli" }}

### Masada: dört düz tepki

Referansların masadaki değeri, büyük mumdan sonra en sık duyulan dört cümlenin ölçülmüş karşılığı olmalarıdır: "mumun
yönünde gir", "yarısına limitle katıl", "tersine gir", "uzamayı sat". Dördü de aynı mumun üstüne üç çizgiyle konur.

{{# sema dort-tepki }}

Okunuşu iki adımlıdır. Önce maliyetten önceki sonuca bakarsın: işareti, mumun o dilimde taşıdığı küçük bilgiyi söyler (5
dakikada tersine taraf, 1 saatte mumun yönü; 6. ders, Dilim dilim okuma). Sonra maliyetten sonrakine: on iki satırın on
ikisinde eksi (9. ders, Referans girişler). Aradaki fark girişin biçimine bağlıdır; piyasa emri ikisini de girişte öder,
limit girişte ödemez ama yalnız fiyat aleyhine yürüdüğünde dolar (8. ders, Limit neden ucuz görünür: ters seçim).

Bu durumda yapmazsın: en az kaybeden referansı kazanan sanmazsın; 1 saatte maliyetten önce sıfırın biraz üstünde kalan
mumun yönündeki girişleri "çalışıyor" diye okumazsın; ve bir referansı kendi süzgecinle "iyileştirip" yeniden
kullanmazsın, çünkü o andan sonra o referans değil bir adaydır ve seçimin bütün şişkinliğini taşır.

## Hüküm kuralı

Hüküm 2024 → dönemi için ön kaydın kuralıyla verildi: dört parite birlikte, ortalama net R'nin {{ Y.95 }} aralığı,
{{ ON.bootstrap }} tekrarlı ve **işlem günü düzeyinde** yeniden örneklemeyle. Büyük mumlar dolar haberinde dört paritede
aynı anda olur; işlemleri tek tek örneklemek aralığı olduğundan dar gösterirdi. 1 saatlik işlemler ertesi güne
taşabildiği için gün düzeyindeki aralık da bir miktar dar kalabilir; tablolardaki ikinci aralık hafta düzeyinde yeniden
örneklenmiştir (FX haftası hafta sonu boşluğuyla biter). Hükmü değiştirmez: hiçbir girişin ortalaması sıfırın üstünde
değil. Aralığın alt ucu sıfırın üstündeyse
"çalışıyor", ortalama artı ama alt uç sıfırın altındaysa "zayıf", ortalama sıfır ya da eksiyse "çalışmıyor";
{{ ON.hukum_en_az }} işlemin altında "ölçülemedi". Sonuç: {{ hukum_calismiyor }} çalışmıyor, {{ hukum_zayif }} zayıf,
{{ hukum_calisiyor }} çalışıyor, {{ hukum_olculemedi }} ölçülemedi.

## Kendi seçim kuralını yazarken: tuzaklar

Bu dersin asıl öğrettiği, bir seçim kuralının nasıl yanıldığıdır. Kendi kuralını yazarken aynı tuzaklar seni bekler:

1. **Aday sayısını saymamak.** Kural {{ plan.aday }} adayı taradı ve en iyisinin 2018–2023 sonucu bu yüzden şişti.
   Denediğin her süzgeç, stop ve hedef bir adaydır; not etmediklerin de (9. ders, Seçim kuralı).
2. **İki yarıyı ikinci bir sınav sanmak.** Seçilen üç girişin üçü de iki yarıda artıydı ve tutmadı. Seçim o veriyle
   yapıldıktan sonra yarılar bağımsız bir kanıt olmaz (9. ders, Seçilen girişler).
3. **Küçük alt kümeye güvenmek.** Olay ne kadar azsa ortalaması şansla o kadar kolay şişer; seçilenlerin ikisi haber
   mumundandı (9. ders, Seçilen girişler).
4. **Maliyetten önceki sonuçla seçmek.** Maliyetten önce sıfırın biraz üstünde kalan girişlerin hepsi maliyetten sonra
   eksi (9. ders, Referans girişler).
5. **Görülmüş dönemi görülmemiş saymak ya da kuralı sonuçtan sonra değiştirmek.** 2024 sonrasının toplu davranışı bu
   plan yazılırken biliniyordu; stop emirli dolumun sayılışı sınamadan sonra değişti ve seçim yeni kuralla yeniden
   uygulandı. İkisini de yazarsın (9. ders, Seçim kuralı).
6. **Olayları bağımsız saymak.** Dolar haberinde dört paritede aynı anda büyük mum çıkar; hükmü gün ya da hafta
   düzeyinde ve sonucu görmeden yazarsın (9. ders, Hüküm kuralı).
7. **Kıyas noktası koşturmamak.** Seçimin şişirmediği tek kıyas, aynı dilimin en düz tepkisidir (9. ders, Referans
   girişler).

## Büyük mum için oyun planı

Ölçümün söylediği şey bir giriş kuralı değil, bir dizi "yapma"dır. Her madde iki dönemde ölçülen bir davranışa dayanıyor.

1. **Büyük mumu tek başına bir sinyal sayma.** Hangi dilimde olursa olsun, büyük mumdan sonra fiyatın önce hangi yöne 1
   ATR gideceği bir yazı turadan birkaç puan uzakta (6. ders).
2. **5 dakikada kovalama; limitin dolmasını da iyi haber sayma.** Ucunda kapanan büyük mum, özellikle Asya'da, yarısını
   aynasından biraz sık geri verir (6. ve 7. ders). Mumun yönünde giriş yapacaksan kapanıştan değil geri çekilmeden yap,
   ama bunun bir kenar değil daha az kötü bir fiyat olduğunu bil: yarıya konan limit fiyatın geri verdiği olaylarda
   dolar ve o olaylarda mumun yönündeki işlem çoğunlukla kaybeder (8. ders).
3. **5 dakikada tersine girmenin küçük kenarını limit yok eder.** Geri verme kenarı kapanışta tersine piyasadan girene
   maliyetten önce kalır; mumun ucuna limitle bekleyene kalmaz (8. ders).
4. **1 saatte tersine girme.** 1 saatlik büyük mum ortalama bir gün boyunca mumun yönünde bir parça daha gider; 2018–2023'te
   aralığıyla, 2024 sonrasında yalnız nokta tahmini olarak (6. ders). Bu bir giriş değil, bir "tersine girme" uyarısıdır.
5. **Stopu yaklaştırma.** 5 dakikada 1 ATR'lik stopla makas ve kayma işlem başına R'nin önemli bir kısmını yer
   (8. ders).
6. **Haber mumunda okuma yok.** Takvimdeki büyük haberin mumu az ve 24 mum sonraki yolu, ortalaması bir yön
   söyleyemeyecek kadar dağınık (7. ders). Seçimin iki girişi buradan çıktı ve 2024 sonrasında tutmadı.

### Masada: planın altı maddesi

Her madde masada bir görüntüye karşılık gelir. Aşağıda maddeler sırayla, her biri bir şema ya da bir kartla.

**Madde 1, tek başına sinyal yok.** Büyük mum kapandığında bildiğin tek şey mumun kendisidir. Kapanışın bir ATR
yukarısı ile bir ATR aşağısı arasındaki yarışta mumun yönü 5 dakikada yazı turadan birkaç puan geride, 1 saatte yazı
turadan ayırt edilemiyor (6. ders, Dilim dilim okuma).

{{# sema iki-yol }}

Bu durumda yapmazsın: mum kapandı diye yön seçmezsin; mumun büyüklüğünü yönün gücü sanmazsın, çünkü 5 ATR'lik bir mumun
2 ATR'lik bir mumdan güvenilir bir dönüş ya da devam işareti olduğunu bu veri göstermiyor (6. ders, Büyüklük
değişince).

**Madde 2, 5 dakikada kovalama; limitin dolması iyi haber değil.** Ucunda kapanan 5 dakikalık mum yarısını aynasından
biraz sık geri verir; geri verme Asya seansında (Londra 07:00'den önce başlayan mum; TSİ İngiltere yaz saatinde
09:00'dan, kış saatinde 10:00'dan önce) ve önceki 4–24 mumda başka büyük mum varken belirgindir (7. ders, 5 dakika).
Bu, kapanışta kovalamanın kötü bir fiyat olduğunu söyler; yarıya konan limitin kazanan bir işlem olduğunu söylemez.

{{# sema yari-limit }}

{{# kart bes-dk-kovalama }}

**Madde 3, tersine girmenin küçük kenarını limit yok eder.** 5 dakikadaki geri verme yalnız kapanışta tersine
piyasadan girene maliyetten önce kalır. Mumun ucuna konan tersine limit, yukarıdaki haber mumu şemasında görüldüğü gibi,
fiyat uca geri döndüğünde, yani geri vermenin olmadığı olaylarda dolar (8. ders, 5 dakika).

{{# kart bes-dk-tersine }}

**Madde 4, 1 saatte tersine girme.** 1 saatlik büyük mumun ortalama yolu bir gün boyunca mumun yönündedir; trende
karşı büyük mum da iki dönemde mumun yönünde gitti (7. ders, Bu sonuç nasıl okunmalı). Bu bir giriş değildir: mumun
yönündeki girişler de maliyetten sonra eksi (9. ders, Referans girişler). Maddenin masadaki tek işi, "çok uzadı"
diye kurulan ters işlemi plana yazdırmamaktır.

{{# kart saat-tersine }}

**Madde 5, stopu yaklaştırma.** Makas ve kayma pip cinsinden aynıdır; R cinsinden stopun uzaklığına bölünür. 5
dakikalık bir ATR birkaç pip olduğu için bir ATR'lik stopta maliyet planlanan riskin büyük bir parçasıdır, ve
olayların bir kısmında risk ölçülen emirlerin alt sınırı olan üç pipin altına düşer (8. ders, Stop uzaklığı ve
maliyet).

{{# sema stop-makas }}

Bu durumda yapmazsın: stopu yaklaştırıp aynı riskle pozisyonu büyütmezsin; bu, maliyeti büyütür ve kenar yaratmaz.
Dilimi büyütmek (1 saat) maliyeti R cinsinden küçültür, ama orada da hiçbir giriş maliyetten sonra artıda değil
(8. ders, 15 dakika ve 1 saat).

**Madde 6, haber mumunda okuma yok.** Takvimdeki büyük haberin mumu grafiğin en okunaklı yeri gibi görünür ve tam
tersidir: olay az, sonrası dağınık, ve ölçümün kayma varsayımı o pencerede daha büyük (7. ders, Fade mi, devam mı: okuma tablosu; 8. ders, Ölçülmeyenler).

{{# kart haber-mumu }}

## Masada: üç örnek

6. dersin Şekil 01'indeki üç EUR/USD mumunu bu planla okumak, planın ne yaptığını ve ne yapmadığını gösterir.

**5 dakikalık mum** ({{ O.5.gun }}, başlangıcı TSİ {{ O.5.saat }}, {{ O.5.yon }}, {{ O.5.kat }} ATR) kapanışı
aralığının {{ O.5.kapanis }} kaldı. Plan burada kovalamamayı söyler (madde 2): mumun yönünde girilecekse geri çekilme
beklenir. Fiyat mumun yarısına {{ O.5.geri50 }}; o noktada yarıya konan alış limiti dolardı ve plan bunun bir
uyarı olduğunu söyler (yine madde 2). Bu örnekte uyarı yanıldı: fiyat sonra mumun ucunu {{ O.5.uc }} ve 24 mum sonra mumun
yönünde {{ O.5.net24 }} ATR'deydi. Tek bir olay ortalamayı ne doğrular ne yanlışlar.

**15 dakikalık mum** ({{ O.15.gun }}, başlangıcı TSİ {{ O.15.saat }}, {{ O.15.yon }}) için plan zayıf bir geri verme
beklentisinden fazlasını söylemez: 15 dakikada iki dönemde tutan tek süzgeç Asya seansı (7. ders) ve bu mum Asya
seansında değil. Fiyat yarısına {{ O.15.geri50 }}, ucunu {{ O.15.uc }} ve 24 mum sonra
{{ O.15.net24 }} ATR'deydi.

**1 saatlik mum** ({{ O.60.gun }}, başlangıcı TSİ {{ O.60.saat }}, {{ O.60.yon }}) kapanışı aralığının
{{ O.60.kapanis }} kaldı. Plan burada tersine girmemeyi söyler (madde 4). Fiyat mumun yarısına {{ O.60.geri50 }}, ucunu
{{ O.60.uc }} ve bir gün sonra mumun yönünde {{ O.60.net24 }} ATR'deydi: tersine giren bir işlemci zarar ederdi, mumun
yönünde giren ise bir günün sonunda maliyetini çıkaramazdı.

Üç örneğin hiçbiri planı sınamaz; plan binlerce olayın ortalamasına dayanır ve 2024 sonrasındaki sınaması yukarıdaki
tablolardır. Örneklerin işi, planın masada bir işlem kuralı değil bir okuma sırası olduğunu göstermek.

Yukarıdaki üç mum bir şeklin içinden alınmıştı. Aşağıdaki iki çift ise kuralla seçildi: koşula uyan olaylardan Aralık
2023'ten önceki en son olay, biri dersin ölçtüğü eğilimle biten tipik gün, öbürü ters giden gün. Kimse "güzel bir
grafik" seçmedi; tarihleri ve fiyatları figür gösterir.

{{# ornek plan-asya-5dk }}

İki gün kapandığı anda birbirinden ayırt edilemez: ikisinde de ① Asya seansında, takvimde haber yokken ucunda kapanan
bir 5 dakikalık büyük mum var. Üstteki günde fiyat ② mumun yarısına geri geldi, ③ yarıya ilk dokunduğu mum işaretli,
ve ④ iki saatlik pencerenin sonunda mumun tersinde kapandı: dersin ölçtüğü geri vermenin kendisi. Alttaki günde fiyat
② yarıya hiç inmedi, ③ işareti yok, ve ④ pencere mumun yönünde, en az bir ATR ileride bitti. Kararın sonradan "belli"
görünmesinin sebebi, iki günü ayıran tek şeyin mum kapandıktan sonra gelmesidir: yarıya dokunulup dokunulmadığı. O
dokunuş, yarıya konan alış limitinin dolduğu andır; ve dolduğu gün mumun yönündeki işlem kaybeden taraftadır, dolmadığı
gün kaçan işlem kazanandır (8. ders, Limit neden ucuz görünür: ters seçim). Tek bir çift Asya'daki geri vermeyi ne
doğrular ne yanlışlar: iki gün de o ortalamanın içinde vardır.

{{# ornek plan-saat-kosu }}

Bu çift seçimin 1 saatlik girişinin durumundan: önceki on iki mumda mumun yönünde en az iki ATR yürümüş bir piyasada,
haber olmadan gelen 1 saatlik büyük mum. Üstteki günde ① mumdan sonra fiyat sığ geri çekilme seviyesine bile gelmedi;
② yarı uzakta kaldı, ③ işareti yok, ve ④ bir gün sonra fiyat mumun yönündeydi. Seçimin girişi bu günde hiç işlem
açmazdı: limit dolmadı ve kaçan işlem kazanandı. Alttaki günde fiyat geri çekildi, ③ yarıya dokundu, mumun öbür ucuna
kadar döndü ve ④ pencere mumun tersinde bitti. Limit bekleme süresi içinde dolduysa işlem stopa giderdi, çünkü mumun
öbür ucu sığ geri çekilme seviyesinden bir ATR'den uzaktır. Kapanış anında iki gün aynıdır; aynı koşu, aynı mum, aynı
"koşu sürüyor" izlenimi. Bu çift seçilen girişin neden tutmadığını göstermez, onu iki dönemin tabloları gösterir; tek
gösterdiği şey limitin hangi günde dolduğudur.

## Emri nereye koyarsın

Bu bölüm mumdan bağımsız bir gerekçeyle (bir seviye, daha büyük dilimde bir plan, bir haber görüşü) işleme girecek biri
içindir. Büyük mum o gerekçeyi ne doğrular ne çürütür; yalnız emrin biçimini, yerini ve zamanını değiştirir. Aşağıdakilerin
hiçbiri bir kenar değildir: ölçülen giriş biçimlerinin hepsi maliyetten sonra eksi (8. ders, Kısaca).

- **Giriş emri.** Piyasa emri makası ve kaymayı girişte de çıkışta da öder (8. ders, 5 dakika). Limit girişte ödemez,
  çıkışta öder, ve yalnız fiyat aleyhine yürüdüğünde dolar (8. ders, Limit neden ucuz görünür: ters seçim). Ucun
  kırılmasına stop emri kaymayı öder ve fiyatın zaten yürüdüğü yerden alır (8. ders, Ucun kırılması). Onay mumu işlem
  sayısını azaltır, girişi kötüleştirir (8. ders, Onay mumu). En ucuzu çoğu zaman limittir; dolması ise okumanın
  aleyhine bir işarettir.
- **Limitin yeri.** Mumun yönünde sığ ({{ Y.25 }}) ya da yarı geri çekilme; limit derinleştikçe daha seyrek dolar ve
  dolduğu olaylarda daha sık kaybeder (8. ders, Limit neden ucuz görünür: ters seçim). Tersine mumun ucu ya da ucun yarım
  ATR ötesi; ikisi de geri vermenin olmadığı olaylarda dolar.
- **Stop.** Girişten iki ATR öte. 5 dakikada bir ATR'lik stop maliyeti R cinsinden büyütür ve olayların bir kısmında
  planlanan riski üç pipin altına indirir (8. ders, Stop uzaklığı ve maliyet). Stopu mumun öbür ucuna koymak ölçülmedi.
- **Hedef.** Bir ya da iki R; hedefi değiştirmek hiçbir dilimde maliyetten sonra kenar yaratmadı (8. ders, 15 dakika ve
  1 saat). Ne stop ne hedef görülürse ölçülen işlem 24 mumun sonunda kapandı.
- **İptal.** Ölçülen limit ve stop emirleri altı mum bekledi, dolmayan iptal edildi (8. ders, On bir giriş biçimi).
  Dolmayan limitin peşinden kovalamazsın; kaçan işlem çoğu zaman iyi olanıdır.
- **Haber penceresi.** Haber mumunda okuma yok (7. ders, Fade mi, devam mı: okuma tablosu). Ölçüm, haberin iki dakika
  öncesinden on beş dakika sonrasına kadar stop ve piyasa emirlerine ek kayma varsaydı; gerçek kayma, kısmi dolum ve
  kuyruk sırası ölçülmedi (8. ders, Ölçülmeyenler). Süresine bir haber saati giren bekleyen emri haberden önce gözden
  geçirirsin; bunun etkisi bu derste ölçülmedi.
- **Cuma, devir, açılış.** 1 saatlik grafikte perşembe akşamından sonra açılan mum, FX gününün devrine değen mum (New
  York 16:50–17:10; TSİ ABD yaz saatinde 23:50–00:10, kış saatinde 00:50–01:10) ve hafta başı yeniden açılışın ilk saati
  ölçüye girmedi (6. ders, Büyük mum nasıl tanımlandı). Bu durumlarda plan bir şey söylemez.

## Sık yapılan hatalar

- **Seçilen girişler tablosunu işlem listesi gibi okumak.** 2018–2023 sütunu seçimin kendisi, 2024 sütunu sınavı; üçü
  de tutmadı (9. ders, Seçilen girişler).
- **Limitin dolmasını onay saymak.** Dolduğu olaylarda piyasa girişi çoğunlukla kaybeder (8. ders, Limit neden ucuz
  görünür: ters seçim).
- **Mumun ucuna tersine limiti daha iyi fiyat sanmak.** 5 dakikadaki küçük tersine kenarı yok eder (8. ders, 5 dakika).
- **5 dakikada stopu bir ATR'ye çekip pozisyonu büyütmek.** Aynı makas daha kısa mesafeye bölünür (8. ders, Stop
  uzaklığı ve maliyet).
- **1 saatte "çok uzadı" diye tersine girmek.** Ortalama yol mumun yönünde; tersine referanslar iki dönemde de eksi
  (6. ders, Dilim dilim okuma; 9. ders, Referans girişler).
- **Haber mumunu okumak.** Olay az, sonrası dağınık; buradan seçilen iki giriş görülmemiş dönemde söndü (7. ders, Fade
  mi, devam mı: okuma tablosu).
- **Büyüklüğü güvenilirlik sanmak.** "5 ATR'lik mum döner" okuması iki dönemde aynı yöne bakmıyor (6. ders, Büyüklük
  değişince).

## Masa kontrol listesi

Büyük bir mum kapandığında sırayla:

1. Dilim 5 dakika, 15 dakika ya da 1 saat mi? Değilse bu seri bir şey ölçmedi.
2. Mum kümenin ilk büyük mumu mu? Önceki üç mumdan biri de büyükse aynı olayın devamıdır.
3. Mum FX gününün devrine (New York 16:50–17:10; TSİ ABD yaz saatinde 23:50–00:10, kış saatinde 00:50–01:10) ya da
   hafta başı açılışın ilk saatine mi değiyor? Öyleyse ölçüye girmedi.
4. Takvimde büyük bir haber mumun içine düşüyor mu? ABD istihdam ve enflasyon New York 08:30 (TSİ ABD yaz saatinde
   15:30, kış saatinde 16:30), FOMC New York 14:00 (TSİ ABD yaz saatinde 21:00, kış saatinde 22:00), ECB Frankfurt
   14:15 (TSİ Avrupa yaz saatinde 15:15, kış saatinde 16:15), BoE Londra 12:00 (TSİ İngiltere yaz saatinde 14:00, kış
   saatinde 15:00). Varsa kalkarsın.
5. Dilim 1 saatse aklındaki işlem mumun tersine mi? Plana yazmazsın. Mum perşembe akşamından sonra mı açıldı?
   Ölçülmedi.
6. Dilim 5 dakikaysa kapanış uç çeyrekte mi, seans Asya mı (Londra 07:00'den önce; TSİ İngiltere yaz saatinde
   09:00'dan, kış saatinde 10:00'dan önce), önceki 4–24 mumda başka büyük mum var mı? Kovalamazsın.
7. Mumdan bağımsız bir gerekçen var mı? Yoksa kalkarsın.
8. Varsa: limit mi, stop girişten iki ATR öte mi, planlanan risk üç pipin üstünde mi, limit dolarsa ne düşüneceğini not
   ettin mi?
9. Emir altı mum içinde dolmadıysa çekersin; süresine haber saati giriyorsa haberden önce gözden geçirirsin.

## Grafik okuma alıştırmaları

**1.** 5 dakikalık EUR/USD grafiğinde Londra 08:30'da (TSİ İngiltere yaz saatinde 10:30, kış saatinde 11:30) başlayan
yukarı yönlü, üç ATR'lik bir büyük mum ucunda kapandı; takvimde haber yok. Daha büyük dilimdeki bir destek yüzünden
zaten alıcı olmayı düşünüyorsun. Ne yaparsın, ne yapmazsın?

<details>
<summary>Çözüm</summary>

Kapanışta kovalamazsın (9. ders, Büyük mum için oyun planı, madde 2). Gerekçen duruyorsa alış limitini sığ geri
çekilmeye ya da yarıya, stopu girişten iki ATR öteye koyarsın; altı mum içinde dolmazsa çekersin (8. ders, On bir giriş
biçimi). Dolarsa okumanın zayıfladığını bilirsin (8. ders, Limit neden ucuz görünür: ters seçim). Büyük mum gerekçeni
güçlendirmez: 5 dakikada yön bilgisi değil, hafif bir geri verme taşır (6. ders, Dilim dilim okuma).

</details>

**2.** 1 saatlik GBP/USD grafiğinde New York 09:00'da (TSİ ABD yaz saatinde 16:00, kış saatinde 17:00) başlayan aşağı
yönlü, dört ATR'lik bir mum günün yeni dibini yaptı ve ucunda kapandı. Masadaki biri "ucun yarım ATR altına alış limiti
koyalım" diyor. Ne yaparsın?

<details>
<summary>Çözüm</summary>

Uzamayı almazsın: 1 saatlik büyük mumun ortalama yolu mumun yönündedir (6. ders, Dilim dilim okuma) ve "ucun yarım ATR
ötesine limit" referansı 1 saatte iki dönemde de maliyetten sonra eksi (9. ders, Referans girişler). Dört ATR olması da
bir dönüş işareti değildir (6. ders, Büyüklük değişince).

</details>

**3.** 5 dakikalık USD/JPY grafiğinde ABD enflasyon verisinin mumu (New York 08:30; TSİ ABD yaz saatinde 15:30, kış
saatinde 16:30) yukarı yönlü ve ucunda kapandı. 2018–2023 tablosu bu durum için "mumun ucuna tersine limit"i seçmişti.
Ne yaparsın?

<details>
<summary>Çözüm</summary>

Masadan kalkarsın: karar şemasının ikinci sorusu seni orada durdurur. Haber mumunda okuma yok (7. ders, Fade mi, devam
mı: okuma tablosu) ve o giriş 2024 sonrasında maliyetten sonra eksi kaldı (9. ders, Seçilen girişler). Tablonun satırını
plana kopyalamazsın.

</details>

**4.** Yarıya alış limiti şemasındasın: limit ② noktasında doldu, fiyat bir mum daha düştü ve stopa yaklaşıyor. Stopu
yaklaştırmak ya da daha aşağıya ikinci bir alış limiti koymak aklından geçiyor. Ne yaparsın?

<details>
<summary>Çözüm</summary>

İkisini de yapmazsın. Ölçülen emirlerde stop sabitti; iz süren stop ve pozisyona ekleme bu seride ölçülmedi (9. ders,
Ölçülmeyenler). Ölçülen şey, limitin dolduğu olaylarda piyasa girişinin çoğunlukla kaybettiğidir; ikinci limit aynı ters
seçimin ikinci kez yaşanmasıdır (8. ders, Limit neden ucuz görünür: ters seçim).

</details>

## Bu sonuç nasıl okunmalı

Bu serinin önceki derslerinde de görülen tablo burada da tekrarlandı: davranış gerçek, kenar maliyetten küçük. Büyük
mumdan sonra fiyatın yaptığı şey tamamen rastgele değil: 5 dakikada biraz geri verir (iki dönemde de), 1 saatte biraz
devam eder (2018–2023'te aralığıyla, 2024 sonrasında yalnız nokta tahmini olarak). Ama "biraz" 5 dakikada bir pipin
altında, makas ise bir pipe yakın; 1 saatte iki pip kadar ve makastan büyük, ama stoplu ve hedefli bir işlemde
maliyetten önce ancak sıfırın biraz üstünde kalıyor. Seçim kuralının bulduğu artı
girişler, binlerce adayın içinden şansın en kolay şişirdiği küçük alt kümelerden çıktı ve görülmemiş dönemde söndü.

## Ölçülmeyenler

- **İki süzgeçli bileşimler** seçime girmedi (ön kayıt kuralı).
- **Dinamik çıkış, kısmi kâr, iz süren stop** ölçülmedi.
- **Komisyon ve kısmi dolum** yok; limit dolumu tablodakinden kötü olabilir.
- **Dört majör dışı pariteler ve 1 saatten büyük dilimler** ölçülmedi.
- **Cuma öğleden sonrasının 1 saatlik mumları.** 24 mumluk pencere hafta sonuna taştığı için ölçüye girmedi (6. ders);
  ABD istihdam raporunun 1 saatlik mumu bu yüzden hiçbir 1 saatlik ölçüde yok.
