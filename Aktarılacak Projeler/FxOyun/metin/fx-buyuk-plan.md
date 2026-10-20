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

## Referans girişler

Seçimin dışında, her dilimde aynı dört giriş de koşturuldu. Bunlar büyük mum için en sık söylenen dört tepkinin en düz
hâlidir ve seçimden bağımsızdır; 2018–2023'teki sonuçları da bu yüzden şişmemiştir.

{{# bacaklar referans }}

Referansların hepsi 2024 sonrasında maliyetten sonra eksi. Maliyetten önce 5 dakikada tersine piyasa girişi
({{ B.referans.5.ters:piyasa:s2:h1.dis.brut }} R) ve 1 saatte mumun yönündeki girişler sıfırın biraz üstünde: 6. dersin
okumaları burada da görünüyor, ama yine maliyetin altında.

{{# sekil 01_bacaklar "On beş girişin iki dönemi" }}

{{# sekil 02_egri "Seçilen üç giriş, birikimli" }}

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
