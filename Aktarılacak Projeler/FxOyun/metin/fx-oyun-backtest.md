---
title: 'FX Gün İçi Oyun Planı 5: Backtest — Plan 2024 Sonrasında Ne Verdi'
description: "Oyun planının bütün tepkileri, 2018–2023 (planın yazıldığı dönem) ve 2024 → (planın hiç sınanmadığı dönem) arasında, gerçek alış-satış fiyatları ve maliyetle: kazanma oranı, işlem başına net sonuç, maliyetin payı, güven aralığı ve hüküm; sonunda günün haritası."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Planın tepkilerinin hiçbiri 2024 sonrasında 'çalışıyor' hükmü almadı. Sık gelen anlarda yüksek kazanma oranlı tepkiler maliyetten sonra kaybettirdi; açılışta kenar maliyetten önce de yok, fiksingte küçük bir kenar var ve maliyet onu yiyor. Tek artı adaylar merkez bankası kararlarında, birkaç karar gününe dayanıyor."
seviye: 'orta'
onkosul: ['fx-oyun-okuma', 'fx-oyun-acilislar', 'fx-oyun-fiksingler', 'fx-oyun-haberler']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';

Önceki dört ders bir oyun planı yazdı: hangi anda, hangi ilk mumdan sonra fiyatın genelde ne yaptığı ve bunun ne
kadarının şansın ötesinde olduğu. Bu ders o planın **işleme çevrilmiş** hâlinin sonucunu verir. Planın tepkileri
2018–2023 verisinden yazıldı ve 2024 sonrası veride hiç koşturulmadan kaydedildi; burada iki dönemin sonucu yan yana
durur. Hüküm yalnız 2024 → döneminden verilir ({{ ON.dis_bitis }} tarihine kadar).

## Kısaca

- **Davranış iki dönemde aynı kaldı.** Açılışta ilk mumun yön bilgisi taşımaması, fiksingte koşunun şanstan sık geri
  verilmesi iki dönemde de görüldü.
- **Davranıştan para çıkmadı.** {{ ref_sayi }} referans tepkinin ve {{ islem_sayi }} işlem tepkisinin hiçbiri
  "çalışıyor" hükmü almadı. İşlem tepkilerinde {{ islem_zayif }} zayıf, {{ islem_calismiyor }} çalışmıyor,
  {{ islem_olculemedi }} ölçülemedi.
- **Kazanma oranı yüksek kurulabildi.** Açılışta yarım R hedefli tepkiler işlemlerin
  {{ B.referans.acilis.normal.dis.kazanma }}–{{ B.referans.acilis.guclu.dis.kazanma }} kadarını kazandı; başa baş için
  {{ B.referans.acilis.guclu.dis.basabas }} gerekiyordu.
- **Tek artı adaylar merkez bankası kararlarında.** Güçlü karar mumunun yönünde kalmak 2024 → döneminde
  {{ B.islem.mb.guclu.dis.n }} işlemde ({{ B.islem.mb.guclu.dis.gun_n }} karar günü) {{ B.islem.mb.guclu.dis.R }} R verdi.
  {{ ON.hukum_en_az }} işlemin altında hüküm kurulmaz.

## Tepki nedir, nasıl seçildi

Plan her an ailesinde (açılış, fiksing, ABD verisi, merkez bankası) ve her ilk mum sınıfında bir **tepki** yazar. İki
tür vardır.

- **Referans tepki** planın kendi okumasının en düz işlem hâlidir. Yön sınıflarında ilk mumun yarısına limitle mumun
  yönünde girmek ve yarım R hedeflemek; küçük mumda kırılan uçtan girmek; fiksingde koşunun tersine girip koşunun
  yarısını hedeflemek. 2024 sonrası sonucuna bakılmadan yazıldı; 2018–2023 sonucu yazılırken biliniyordu. Amacı
  "okuma doğruysa kazanma oranı yüksek olur" sözünü sınamaktır.
- **İşlem tepkisi**, her hücrede 2018–2023'te denenen {{ aday_alt }} ila {{ aday_ust }} adayın içinden, önceden yazılmış
  kuralla seçildi: en az {{ ON.secim_en_az }} işlemi olan ve maliyetten sonra artıda kalanların en iyisi. Bu kural
  gereği seçilen her tepkinin 2018–2023 sonucu artıdır; kanıt 2024 → sonucudur. Böyle bir aday çıkmayan hücrede plan
  "izle, işlem açma" der. {{ izle_sayi }} hücre bu durumdaydı; {{ islem_sayi }} hücrede işlem tepkisi seçildi.

Trend seçime girmedi: gözlemde trend ilk mumdan sonraki davranışı belirgin değiştirmiyordu.

## Kazanma oranı ve net sonuç

Her tepkinin 2024 → dönemindeki kazanma oranı ve işlem başına net sonucu (dairenin büyüklüğü işlem sayısı):

{{# sekil 01_kazanma_net "Açılış ve fiksing tepkileri: kazanma oranı yüksek ya da düşük, hepsi eksi" }}

Şekilde iki küme var. Büyük daireler açılış ve fiksing tepkileri: yüzlerce, kimi binlerce işlem, ve hepsi sıfırın
altında. Açılışta kazanma oranları yarının üstünde ama yarım R'lik kazanç kaybı karşılamıyor. Fiksingde güçlü koşunun
tersine giren tepki işlemlerin yalnız {{ B.referans.fiksing.guclu.dis.kazanma }} kadarını kazandı; kazananı ortalama
{{ B.referans.fiksing.guclu.dis.kazanc }} R getirdi, başa baş için {{ B.referans.fiksing.guclu.dis.basabas }} yetiyordu,
o oran da tutmadı. Sağ üstteki küçük noktalar merkez bankası kararları: hem kazanma oranı hem net sonuç yüksek, ama her
biri en çok {{ mb_n_ust }} işlem. O kümede iki ölçünün birlikte yükselmesi birkaç iyi kararın ikisini birden yukarı
itmesi olabilir; ayrılmadı.

Aritmetik açılışta en açık hâlindedir. Güçlü ilk mumun yarısına limitle girip yarım R hedefleyen tepkide kazanan işlem
ortalama {{ B.referans.acilis.guclu.dis.kazanc }} R kazandı, kaybeden ortalama {{ B.referans.acilis.guclu.dis.kayip }} R
kaybetti. Bu ikisiyle başa baş için işlemlerin {{ B.referans.acilis.guclu.dis.basabas }} kadarını kazanmak gerekir; tepki
{{ B.referans.acilis.guclu.dis.kazanma }} kazandı. Kazanma oranı istenen yere çekilebilir (hedef yaklaştıkça yükselir),
ama başa baş oranı da onunla birlikte yükselir.

## Referans tepkiler

{{# bacaklar referans }}

Açılış ve fiksingin {{ sik_sayi }} referans tepkisinin hepsi "çalışmıyor" ve hepsinin güven aralığı sıfırın altında.
Haber anlarında işlem sayıları küçük; merkez bankası kararlarında normal ve küçük mumun referans tepkisi 2024 →
döneminde artıda, ikisinin de aralığı sıfırı kapsıyor ("zayıf").

## Maliyet nereye gidiyor

Her tepkinin maliyetsiz (aynı kurallar orta fiyatla, makas ve kayma olmadan) ve maliyetli sonucu:

{{# sekil 02_maliyet "Maliyetten önce ve sonra: açılışta kenar yok, fiksingte küçük kenar maliyete gidiyor" }}

Üç ayrı hikâye var.

- **Açılışta kenar maliyetten önce de yok.** Yarısına limitle girilen tepkilerin maliyetsiz sonucu sıfıra yakın ya da
  eksi (güçlü mumda {{ B.referans.acilis.guclu.dis.brut }} R, normal mumda {{ B.referans.acilis.normal.dis.brut }} R);
  küçük mumun kırılımı da öyle ({{ B.referans.acilis.kucuk.dis.brut }} R). Maliyet, sıfırı belirgin bir eksiye
  çeviriyor: küçük mum küçük stop demektir ve makas o stopun görünür bir parçasıdır.
- **Fiksingde küçük bir kenar var, maliyet onu yiyor.** Koşunun tersine girmenin maliyetsiz sonucu 2018–2023'te normal
  koşuda {{ B.referans.fiksing.normal.ic.brut }} R, 2024 → döneminde {{ B.referans.fiksing.normal.dis.brut }} R. Bu,
  fiksing dersinde şansla kıyaslanan geri vermenin işlem hâlidir. Maliyet
  ({{ B.referans.fiksing.normal.dis.maliyet }} R) ondan büyük.
- **Merkez bankasında maliyetsiz sonuç artı.** Küçük karar mumunun kırılımında maliyetsiz
  {{ B.referans.mb.kucuk.dis.brut }} R, maliyetli {{ B.referans.mb.kucuk.dis.R }} R; az işlemle.

## İşlem tepkileri

{{# bacaklar islem }}

İşlem tepkilerinin 2024 → dönemindeki birikimli sonucu, işlem işlem:

{{# sekil 03_egri "İşlem tepkilerinin 2024 sonrasında birikimli sonucu" }}

- Merkez bankasında **güçlü karar mumunun yönünde** kalmak {{ B.islem.mb.guclu.dis.n }} işlemin
  {{ B.islem.mb.guclu.dis.kazanma }} kadarını kazandı (net {{ B.islem.mb.guclu.dis.R }} R). İşlemler yalnız
  {{ B.islem.mb.guclu.dis.gun_n }} karar gününe düşüyor; aynı kararda dört paritenin işlemi birlikte hareket eder. İşlem
  düzeyindeki aralık ({{ B.islem.mb.guclu.dis.alt }} … {{ B.islem.mb.guclu.dis.ust }}) bu yüzden olduğundan dardır;
  karar günlerinden yeniden örneklenen aralık {{ B.islem.mb.guclu.dis.gun_alt }} … {{ B.islem.mb.guclu.dis.gun_ust }}.
  Yılda birkaç olay gelen bir kural için bu bir başlangıçtır, sonuç değil.
- Merkez bankasında **reddedilen karar mumu** {{ B.islem.mb.reddedilen.dis.n }} işlemde
  ({{ B.islem.mb.reddedilen.dis.gun_n }} karar günü) {{ B.islem.mb.reddedilen.dis.R }} R, **normal karar mumu**
  {{ B.islem.mb.normal.dis.n }} işlemde {{ B.islem.mb.normal.dis.R }} R ("{{ B.islem.mb.normal.hukum }}").
- ABD verisinde **güçlü veri mumu** 2024 → döneminde {{ B.islem.veri.guclu.dis.R }} R, **küçük veri mumu**
  {{ B.islem.veri.kucuk.dis.R }} R ("{{ B.islem.veri.kucuk.hukum }}").

## İzle, işlem açma

Bu hücrelerde 2018–2023'te denenen hiçbir aday maliyetten sonra artıda kalmadı. Tabloda denenen aday sayısı ve en
iyisinin sonucu:

{{# izle }}

Açılış ve fiksinglerin bütün hücreleri burada. Plan bu anlarda okumayı sürdürür ama işlem önermez.

## Günün haritası

Planın bütün okumaları tek tabloda, günün sırasıyla. Saatler TSİ; parantez içi İngiltere, Avrupa ya da ABD kış
saatinde.

| TSİ | An | Ne beklenir | Ne yapılmaz |
|---|---|---|---|
| {{ AN.tokyo_acilis.tsi_yaz }} | Tokyo açılışı | İlk {{ AN.tokyo_acilis.tf }} dakika bir aralık çizer; yön bilgisi yok | Güçlü mumu kovalamak, yarısında katılmak |
| {{ AN.tokyo_fiks.tsi_yaz }} | Tokyo fiksingi | Fiksinge koşu varsa bir geri çekilme | Fiksingden sonra koşunun yönünde girmek |
| {{ AN.londra_acilis.tsi_yaz }} ({{ AN.londra_acilis.tsi_kis }}) | Londra açılışı | Normal mumda birkaç dakika içinde yarısına dönüş | Yarıya dönüşü bir giriş sinyali saymak |
| {{ AN.boe.tsi_yaz }} ({{ AN.boe.tsi_kis }}) | BoE kararı | Tutanak kararla birlikte gelir; olay az | İlk mumdan hüküm kurmak |
| {{ AN.ecb.tsi_yaz }} ({{ AN.ecb.tsi_kis }}) | ECB kararı | Basın toplantısı yarım saat sonra | İlk mumu son söz saymak |
| {{ AN.nfp.tsi_yaz }} ({{ AN.nfp.tsi_kis }}) | ABD verisi | İlk mumun itişi şanstan seyrek sürer | Veri mumunun yönünde kalmak |
| {{ AN.ny_acilis.tsi_yaz }} ({{ AN.ny_acilis.tsi_kis }}) | New York açılışı | Açılışlardaki gibi: aralık, yön değil | Sessiz açılışın kırılımına girmek |
| {{ AN.wmr.tsi_yaz }} ({{ AN.wmr.tsi_kis }}) | Londra fiksingi | Koşunun bir kısmı geri verilir; ay sonunda koşu daha da az sürer | Fiksingden sonra koşuyu kovalamak; geri vermeyi maliyetle işlemek |
| {{ AN.fomc.tsi_yaz }} ({{ AN.fomc.tsi_kis }}) | FOMC kararı | Güçlü ya da reddedilen mumun yönü 2024 sonrasında sürdü; birkaç karar günü | Sınanmamış bir adayı kural saymak |

## Bu sonuç nasıl okunmalı

- **Okumalar iki dönemde aynı kaldı.** Açılışta ve fiksingte fiyatın davranışı iki dönemde de aynı. Bu okumaların
  başka bir kurulumu iyileştirip iyileştirmediği bu seride ölçülmedi.
- **Plan bir işlem sistemi olarak kazandırmıyor.** Açılışta okumanın kenarı maliyetten önce de yok; fiksingde var ama
  maliyeti karşılayacak kadar büyük değil.
- **Kazanma oranı kurulabilir, kâr kurulamadı.** Yakın hedefle işlemlerin çoğunu kazanmak mümkün; ama açılış ve
  fiksinglerde 2018–2023'te denenen stop ve hedef bileşimlerinin hiçbiri bu maliyetle net sonucu artıya çevirmedi.
- **Merkez bankası kararları izlenecek tek yer.** Artı sonuç 2024 → döneminde orada; ama birkaç karar gününe dayanıyor.
  Bir kural olması için bundan sonraki kararlarda, bugünkü hâliyle değiştirilmeden sınanması gerekir.

## Ölçülmeyenler

- Gerçek sürpriz: veri ve kararlarda beklentiye göre sapma ölçülmedi; ilk mum sapmanın vekilidir.
- Basın toplantısının karar metninden ayrı etkisi.
- Gün içi dokunuşların sırası dakikadan kısa sürelerde (aynı dakikada stop ve hedef görülürse stop sayıldı).
- Piyasa derinliği, kısmi dolum, komisyon ve emir gecikmesi.
- {{ pariteler }} dışındaki pariteler ve beş dakikadan kısa ilk mumlar.

Veri Dukascopy'nin bir dakikalık alış ve satış fiyatlarıdır (2018 başından {{ veri_bitis }} tarihine kadar).
