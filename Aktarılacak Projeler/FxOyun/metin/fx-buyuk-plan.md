---
title: 'FX Gün İçi Oyun Planı 9: Büyük Mum — Oyun Planı ve 2024 Sınaması'
description: "Büyük mum okumalarından 2018–2023 verisiyle seçilip 2024 sonrası hiç görülmeden kaydedilen giriş planı: seçim kuralı, taranan {{ plan.aday }} aday, seçilen üç giriş, on iki referans giriş ve 2024 → döneminin sonucu. Sonunda büyük mum için bir oyun planı."
pubDate: 2026-10-20
tags: ['fx', 'gun-ici', 'oyun-plani', 'buyuk-mum', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "2018–2023'ün en iyi üç büyük mum girişi 2024 sonrasında tutmadı; on iki referans girişin hiçbiri de artıda değil. Davranışın kendisi iki dönemde aynı kaldı, ama her girişte maliyetten küçük. Büyük mum bir işlem sinyali değil, bir okuma: nerede kovalanmaz, nerede limitin dolması kötü haberdir, nerede masadan kalkılır."
seviye: 'orta'
onkosul: ['fx-buyuk-mum', 'fx-buyuk-suzgec', 'fx-buyuk-giris']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';

Önceki üç ders büyük mumu okudu, süzdü ve girişin biçimini ölçtü. Bu ders o çalışmanın sınavıdır. 2018–2023'ün sonucu
görülerek bir seçim kuralı yazıldı, kural o dönemin tablosuna uygulandı ve seçilen girişler 2024 ve sonrasının verisi
hiç açılmadan bir ön kayıt dosyasıyla birlikte kaydedildi. Sonra aynı kod 2024 → döneminde ({{ ON.dis_bitis }} tarihine
kadar) koştu. Bu dersin her sayısı o koşudan.

## Kısaca

- **Seçilen üç girişin üçü de tutmadı.** 2018–2023'te iki yarıda da artı olan en iyi girişler 2024 sonrasında eksi ya da
  sıfırdaydı. En iyisi (1 saatte, aynı yönde koşudan sonraki büyük mumda mumun {{ Y.25 }} geri çekilmesine limit) 2018–2023'te
  {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.ic.R }} R verdi, 2024 sonrasında
  {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.R }} R.
- **On iki referans girişin hiçbiri artıda değil.** Büyük mumdan sonra "mumun yönünde gir", "yarısına limitle katıl",
  "tersine gir", "uzamayı sat" girişleri her dilimde maliyetten sonra eksi.
- **Hüküm: {{ plan.bacak_sayi }} girişin {{ hukum_calismiyor }} kadarı çalışmıyor.** Hiçbiri "zayıf" ya da "çalışıyor"
  almadı.
- **Davranış sürdü, kenar sürmedi.** 5 dakikadaki hafif geri verme ve 1 saatteki hafif devam 2024 sonrasında da
  görüldü (6. ders). Ama her girişte maliyetten küçük.

## Seçim kuralı

Kural ön kayıt dosyasında ve sonucu görülmeden yazıldı:

1. Her dilim (5 dakika, 15 dakika, 1 saat) ve her yön (mumun yönünde, tersine) için aday girişler: 8. dersin ızgarasının
   bütün hücreleri (emir biçimi × stop × hedef), süzgeçsiz ya da 7. dersin süzgeçlerinden **tek bir** değerle.
2. Uygun aday: 2018–2023'te en az {{ ON.secim_en_az }} işlem, maliyetten sonra ortalaması sıfırın üstünde, **ve**
   2018–2020 ile 2021–2023 yarılarının ikisinde de sıfırın üstünde.
3. Uygunların içinden maliyetten sonra ortalaması en yüksek olan seçilir. Uygun aday yoksa o dilim ve yön için "işlem
   yok".

Kural toplam {{ plan.aday }} adayı taradı. Bu sayı önemli: bu kadar adayın içinden en iyisini seçmek, en iyisinin
2018–2023'teki sonucunu şansla şişirir. 2024 → dönemi o şişkinliği ölçer.

Seçimin bir sınırı da kayda geçsin: aynı veriyle (dört majör, 2024 →) bu seride daha önce başka kuralların sonuçları
yayımlandı; 2024 sonrasının toplu davranışı bu plan yazılırken biliniyordu. Büyük mumdan sonraki davranışın ve bu
girişlerin 2024 sonrası sonucu ise ölçülmemişti.

## Seçilen girişler

{{# bacaklar islem }}

Altı dilim × yön hücresinin {{ plan.islem_sayi }} kadarında kurala uyan bir aday çıktı, {{ plan.yok_sayi }} kadarında
çıkmadı. Seçilenlerin üçü de bir süzgeç taşıyor: ikisi takvimdeki haber mumu, biri aynı yönde koşudan sonraki büyük mum.
Bu bir rastlantı değil: süzgeç, aday sayısını yirmi kat büyütür ve en iyi adayın küçük bir alt kümeden çıkma olasılığı
yükselir. Küçük alt küme, şansın en kolay şişirdiği yerdir.

- **5 dakika, haber mumunu ucundan tersine.** 2018–2023'te {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.ic.n }} işlem,
  iki yarıda {{ P.5.ters.y1 }} ve {{ P.5.ters.y2 }} R. 2024 sonrasında {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.dis.n }}
  işlem, {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.dis.R }} R. Maliyetten önce
  {{ B.islem.5.ters:limit_uc:s2:h2.haber=haber.dis.brut }} R.
- **1 saat, aynı yönde koşudan sonraki büyük mumda {{ Y.25 }} geri çekilmeye limit.** 2018–2023'te iki yarıda
  {{ P.60.devam.y1 }} ve {{ P.60.devam.y2 }} R. 2024 sonrasında {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.n }}
  işlem, {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.R }} R ({{ Y.95 }} aralık
  {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.alt }} … {{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.ust }}):
  aralığın tamamı sıfırın altında. Maliyetten önce de eksi ({{ B.islem.60.devam:limit_0.25:s1:h2.kosu=ayni.dis.brut }} R):
  2018–2023'teki sonuç bir kenar değil, o dönemin şansıydı.
- **1 saat, haber mumunu ucundan tersine.** 2018–2023'te {{ B.islem.60.ters:limit_uc:s1:h2.haber=haber.ic.R }} R (en küçük
  artı), 2024 sonrasında {{ B.islem.60.ters:limit_uc:s1:h2.haber=haber.dis.R }} R.

Kuralın "işlem yok" dediği hücreler ve o hücrelerin en iyi adayı:

{{# yok }}

## Referans girişler

Seçimin dışında, her dilimde aynı dört giriş de koşturuldu. Bunlar büyük mum için en sık söylenen dört tepkinin en düz
hâlidir ve seçimden bağımsızdır; 2018–2023'teki sonuçları da bu yüzden şişmemiştir.

{{# bacaklar referans }}

Referansların on ikisi de 2024 sonrasında maliyetten sonra eksi. Maliyetten önce 5 dakikada tersine piyasa girişi
({{ B.referans.5.ters:piyasa:s2:h1.dis.brut }} R) ve 1 saatte mumun yönündeki girişler sıfırın biraz üstünde: 6. dersin
okumaları burada da görünüyor, ama yine maliyetin altında.

{{# sekil 01_bacaklar "On beş girişin iki dönemi" }}

{{# sekil 02_egri "Seçilen üç giriş, birikimli" }}

## Hüküm kuralı

Hüküm 2024 → dönemi için ön kaydın kuralıyla verildi: dört parite birlikte, ortalama net R'nin {{ Y.95 }} aralığı,
{{ ON.bootstrap }} tekrarlı ve **işlem günü düzeyinde** yeniden örneklemeyle. Büyük mumlar dolar haberinde dört paritede
aynı anda olur; işlemleri tek tek örneklemek aralığı olduğundan dar gösterirdi. Aralığın alt ucu sıfırın üstündeyse
"çalışıyor", ortalama artı ama alt uç sıfırın altındaysa "zayıf", ortalama sıfır ya da eksiyse "çalışmıyor";
{{ ON.hukum_en_az }} işlemin altında "ölçülemedi". Sonuç: {{ hukum_calismiyor }} çalışmıyor, {{ hukum_zayif }} zayıf,
{{ hukum_calisiyor }} çalışıyor, {{ hukum_olculemedi }} ölçülemedi.

## Büyük mum için oyun planı

Ölçümün söylediği şey bir giriş kuralı değil, bir dizi "yapma"dır. Her madde iki dönemde ölçülen bir davranışa dayanıyor.

1. **Büyük mumu tek başına bir sinyal sayma.** Hangi dilimde olursa olsun, büyük mumdan sonra fiyatın önce hangi yöne 1
   ATR gideceği bir yazı turadan birkaç puan uzakta (6. ders).
2. **5 dakikada kovalama.** Ucunda kapanan büyük mum, özellikle Asya'da ve arka arkaya büyük mumların geldiği piyasada,
   yarısını şanstan biraz sık geri verir (7. ders). Mumun yönünde giriş yapacaksan kapanıştan değil, geri çekilmeden yap;
   ama bunun bir kenar değil, daha az kötü bir fiyat olduğunu bil.
3. **Limitin dolması iyi haber değildir.** Yarıya konan limit, fiyatın gerçekten geri verdiği olaylarda dolar ve o
   olaylarda mumun yönündeki işlem çoğunlukla kaybeder (8. ders). Limit dolduysa mumun yönündeki okuma zayıflamıştır.
4. **5 dakikada tersine girmenin küçük kenarını limit yok eder.** Geri verme kenarı kapanışta tersine piyasadan girene
   maliyetten önce kalır; mumun ucuna limitle bekleyene kalmaz (8. ders).
5. **1 saatte mumun yönüne saygı göster, özellikle günlük trendle aynı yöndeyse.** 1 saatlik büyük mum ortalama bir gün
   boyunca mumun yönünde bir parça daha gider (6. ve 7. ders). Bu bir giriş değil, bir "tersine girme" uyarısıdır.
6. **Stopu yaklaştırma.** 5 dakikada 1 ATR'lik stopla makas ve kayma işlem başına R'nin önemli bir kısmını yer
   (8. ders).
7. **Haber mumunda okuma yok.** Takvimdeki büyük haberin mumu az ve dağılımı çok geniş; ne fade ne devam ölçülebiliyor
   (7. ders). Seçimin iki girişi buradan çıktı ve 2024 sonrasında tutmadı.

## Bu sonuç nasıl okunmalı

Bu serinin önceki derslerinde de görülen tablo burada da tekrarlandı: davranış gerçek, kenar maliyetten küçük. Büyük
mumdan sonra fiyatın yaptığı şey rastgele değil; 5 dakikada biraz geri verir, 1 saatte biraz devam eder ve bu iki
dönemde aynıdır. Ama "biraz" 5 dakikada bir pipin altında, makas ise bir pipe yakın. Seçim kuralının bulduğu artı
girişler, binlerce adayın içinden şansın en kolay şişirdiği küçük alt kümelerden çıktı ve görülmemiş dönemde söndü.

## Ölçülmeyenler

- **İki süzgeçli bileşimler** seçime girmedi (ön kayıt kuralı).
- **Dinamik çıkış, kısmi kâr, iz süren stop** ölçülmedi.
- **Komisyon ve kısmi dolum** yok; limit dolumu tablodakinden kötü olabilir.
- **Dört majör dışı pariteler ve 1 saatten büyük dilimler** ölçülmedi.
