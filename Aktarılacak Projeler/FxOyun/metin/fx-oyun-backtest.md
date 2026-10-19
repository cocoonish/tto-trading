---
title: 'FX Gün İçi Oyun Planı 5: Backtest — Plan 2024 Sonrasında Ne Verdi'
description: "Oyun planının bütün tepkileri, 2018–2023 (planın yazıldığı dönem) ve 2024 → (planın hiç görmediği dönem) arasında, gerçek alış-satış fiyatları ve maliyetle: kazanma oranı, işlem başına net sonuç, maliyetin payı, güven aralığı ve hüküm."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Planın okumaları iki dönemde büyük ölçüde aynı kaldı; o okumalara dayanan tepkilerin hiçbiri 2024 sonrasında 'çalışıyor' hükmü almadı. Sık gelen anlarda yüksek kazanma oranlı tepkiler maliyetten sonra kaybettirdi; tek artı adaylar merkez bankası kararlarında ve hüküm kuracak kadar işlemleri yok."
seviye: 'orta'
onkosul: ['fx-oyun-okuma', 'fx-oyun-acilislar', 'fx-oyun-fiksingler', 'fx-oyun-haberler']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';

Önceki dört ders bir oyun planı yazdı: hangi anda, hangi ilk mumdan sonra fiyatın genelde ne yaptığı. Bu ders o planın
**işleme çevrilmiş** hâlinin sonucunu verir. Plan 2018–2023 verisinden yazıldı ve 2024 sonrasının verisi hiç açılmadan
kaydedildi; burada iki dönemin sonucu yan yana durur. Hüküm yalnız 2024 → döneminden verilir
({{ ON.dis_bitis }} tarihine kadar).

## Kısaca

- **Okumalar tuttu.** Açılışta ilk mumun yarısına dönmesi, güçlü mumun biraz daha sık devam etmesi, fiksingte koşunun
  geri verilip dönmemesi iki dönemde neredeyse aynı sayılarla görüldü.
- **Okumalardan para çıkmadı.** {{ ref_sayi }} referans tepkinin ve {{ islem_sayi }} işlem tepkisinin hiçbiri
  "çalışıyor" hükmü almadı. İşlem tepkilerinde {{ islem_zayif }} zayıf, {{ islem_calismiyor }} çalışmıyor,
  {{ islem_olculemedi }} ölçülemedi.
- **Kazanma oranı yüksekti.** Sık gelen anlarda tepkiler işlemlerin {{ sik_kaz_alt }} ile {{ sik_kaz_ust }} kadarını
  kazandı. İşlem başına net sonuç {{ sik_R_alt }} ile {{ sik_R_ust }} R arasında kaldı.
- **Tek artı adaylar merkez bankası kararlarında.** Güçlü karar mumunun yönünde kalmak 2024 → döneminde
  {{ B.islem.mb.guclu.dis.n }} işlemde {{ B.islem.mb.guclu.dis.R }} R verdi. {{ ON.hukum_en_az }} işlemin altında hüküm
  kurulmaz.

## Tepki nedir, nasıl seçildi

Plan her an ailesinde (açılış, fiksing, ABD verisi, merkez bankası) ve her ilk mum sınıfında bir **tepki** yazar. İki
tür vardır.

- **Referans tepki** planın kendi okumasının en düz işlem hâlidir ve sonuca bakılmadan önceden yazıldı. Yön sınıflarında
  ilk mumun yarısına limitle mumun yönünde girmek ve yarım R hedeflemek; küçük mumda kırılan uçtan girmek; fiksingte
  koşunun tersine girip koşunun yarısını hedeflemek. Amacı "plan doğruysa kazanma oranı yüksek olur" sözünü sınamaktır.
- **İşlem tepkisi**, her hücrede 2018–2023'te denenen {{ aday_alt }} ila {{ aday_ust }} adayın içinden, önceden yazılmış kuralla seçildi:
  en az {{ ON.secim_en_az }} işlemi olan ve maliyetten sonra artıda kalanların en iyisi. Böyle bir aday çıkmayan
  hücrede plan "izle, işlem açma" der. {{ izle_sayi }} hücre bu durumdaydı; {{ islem_sayi }} hücrede işlem tepkisi
  seçildi.

Trend seçime girmedi: gözlemde trend ilk mumdan sonraki davranışı belirgin değiştirmiyordu.

## Kazanma oranı ve net sonuç

Her tepkinin 2024 → dönemindeki kazanma oranı ve işlem başına net sonucu (dairenin büyüklüğü işlem sayısı):

{{# sekil 01_kazanma_net "Açılış ve fiksing tepkileri işlemlerin çoğunu kazandı, hepsi eksi kaldı" }}

Şekilde iki küme var. Büyük daireler açılış ve fiksing tepkileri: binlerce işlem, kazanma oranları çoğunda yarının üstünde, ve
hepsi sıfırın altında. İşlemlerin çoğunu kazanıyorlar ama kazanan işlemin getirdiği, kaybeden işlemin götürdüğünü
karşılamıyor. Sağ üstteki küçük noktalar merkez bankası kararları: hem kazanma oranı hem net sonuç yüksek, ama her biri
en çok {{ mb_n_ust }} işlem. Bu kümede kazanma oranıyla net sonucun birlikte yükselmesi, birkaç iyi kararın iki ölçüyü
birden yukarı itmesidir; bir kural değil.

Bunun aritmetiği basit. Açılışta güçlü ilk mumun yarısına limitle girip yarım R hedefleyen tepkide kazanan işlem
ortalama {{ B.referans.acilis.guclu.dis.kazanc }} R kazandı, kaybeden ortalama {{ B.referans.acilis.guclu.dis.kayip }} R
kaybetti. Bu ikisiyle başa baş için işlemlerin {{ B.referans.acilis.guclu.dis.basabas }} kadarını kazanmak gerekir;
tepki {{ B.referans.acilis.guclu.dis.kazanma }} kazandı. Kazanma oranı istenen yere çekilebilir (hedef yaklaştıkça
yükselir), ama başa baş oranı da onunla birlikte yükselir.

## Referans tepkiler

{{# bacaklar referans }}

Sık gelen anların {{ sik_sayi }} referans tepkisinin {{ sik_calismiyor }} tanesi "çalışmıyor" ve hepsinin güven aralığı
sıfırın altında. Haber anlarında işlem sayıları küçük; merkez bankası kararlarında normal ve küçük mumun referans tepkisi
2024 → döneminde artıda, ikisinin de aralığı sıfırı kapsıyor ("zayıf").

## Maliyet nereye gidiyor

Her tepkinin maliyetten önceki (orta fiyattan, makas ve kayma yok) ve sonraki sonucu:

{{# sekil 02_maliyet "Maliyetten önce ve sonra: kenar nerede kayboluyor" }}

İki ayrı hikâye var.

- **Yön sınıflarında kenar maliyetten önce de yok.** Açılışta yarısına limitle girilen tepkilerin maliyetsiz sonucu
  bile eksi: güçlü mumda {{ B.referans.acilis.guclu.dis.brut }} R, normal mumda {{ B.referans.acilis.normal.dis.brut }} R.
  Limit emir makas ve kayma ödemediği için maliyet küçük ({{ B.referans.acilis.guclu.dis.maliyet }} R); sorun
  maliyet değil, yarıya dönüşten sonraki yazı tura.
- **Küçük mumlarda kenar var, maliyet onu yutuyor.** Açılışta küçük mumun kırılım tepkisi maliyetten önce
  {{ B.referans.acilis.kucuk.dis.brut }} R, sonra {{ B.referans.acilis.kucuk.dis.R }} R. Küçük mum küçük stop demektir;
  ortanca risk {{ B.referans.acilis.kucuk.dis.risk_pip }} pip ve makasla kayma bunun önemli bir parçası. Fiksingte
  aynı tablo: {{ B.referans.fiksing.kucuk.dis.brut }} R → {{ B.referans.fiksing.kucuk.dis.R }} R.

Küçük mumun kırılımında maliyetsiz bir kenar görünmesi ilginçtir ama işlenebilir değildir: kenar, makasın ve kaymanın
olmadığı bir dünyada var. Daha geniş bir stopla maliyetin payı küçülür, ama 2018–2023'te denenen geniş stoplu
adaylar kenarı da küçülttü ve hiçbiri artıda kalmadı.

## İşlem tepkileri

{{# bacaklar islem }}

İşlem tepkilerinin 2024 → dönemindeki birikimli sonucu, işlem işlem:

{{# sekil 03_egri "İşlem tepkilerinin 2024 sonrasında birikimli sonucu" }}

- Merkez bankasında **güçlü karar mumunun yönünde** kalmak {{ B.islem.mb.guclu.dis.n }} işlemin
  {{ B.islem.mb.guclu.dis.kazanma }} kadarını kazandı (net {{ B.islem.mb.guclu.dis.R }} R, aralık
  {{ B.islem.mb.guclu.dis.alt }} … {{ B.islem.mb.guclu.dis.ust }}). 2018–2023'te sonucu sıfıra çok yakındı
  ({{ B.islem.mb.guclu.ic.R }} R). Yılda birkaç olay gelen bir kural için bu aralık bir başlangıçtır, sonuç değil.
- Merkez bankasında **normal karar mumu** iki dönemde de artı işaret verdi, ama aralık sıfırı kapsıyor
  ({{ B.islem.mb.normal.dis.alt }} … {{ B.islem.mb.normal.dis.ust }}): "{{ B.islem.mb.normal.hukum }}".
- ABD verisinde **güçlü veri mumu** 2018–2023'te artıdaydı, 2024 → döneminde {{ B.islem.veri.guclu.dis.R }} R; **küçük
  veri mumu** {{ B.islem.veri.kucuk.dis.R }} R ("{{ B.islem.veri.kucuk.hukum }}").

## İzle, işlem açma

Bu hücrelerde 2018–2023'te denenen hiçbir aday maliyetten sonra artıda kalmadı. Tabloda denenen aday sayısı ve en
iyisinin sonucu:

{{# izle }}

Açılış ve fiksinglerin bütün hücreleri burada. Plan bu anlarda okumayı sürdürür ama işlem önermez: bir sonraki kurulumun
yönünü ya da günün ilk referanslarını verir, kendi başına bir giriş sebebi vermez.

## Bu sonuç nasıl okunmalı

- **Plan bir okuma aracı olarak işe yarıyor.** Açılışta ve fiksingte fiyatın davranışı yıldan yıla aynı; bunu bilmek,
  bir açılış mumunu kovalamamayı ya da bir fiksing koşusunun arkasına geç kalmamayı söyler.
- **Plan bir işlem sistemi olarak kazandırmıyor.** Sık gelen anlarda okumanın kenarı ya maliyetten önce yok ya da
  maliyeti karşılayacak kadar büyük değil.
- **Kazanma oranı kurulabilir, kâr kurulamadı.** Yakın hedefle işlemlerin çoğunu kazanmak mümkün; ama açılış ve
  fiksinglerde 2018–2023'te denenen stop ve hedef bileşimlerinin hiçbiri bu maliyetle net sonucu artıya çevirmedi.
- **Merkez bankası kararları izlenecek tek yer.** Artı işaret iki dönemde de orada; ama işlem sayısı bir kural kurmaya
  yetmiyor. O kural ancak bundan sonraki kararlarda, bugünkü hâliyle değiştirilmeden sınanırsa bir kural olur.

## Ölçülmeyenler

- Gerçek sürpriz: veri ve kararlarda beklentiye göre sapma ölçülmedi; ilk mum sapmanın vekilidir.
- Basın toplantısının karar metninden ayrı etkisi.
- Gün içi dokunuşların sırası dakikadan kısa sürelerde (aynı dakikada stop ve hedef görülürse stop sayıldı).
- Piyasa derinliği, kısmi dolum, komisyon ve emir gecikmesi.
- {{ pariteler }} dışındaki pariteler ve beş dakikadan kısa ilk mumlar.

Veri Dukascopy'nin bir dakikalık alış ve satış fiyatlarıdır (2018 başından {{ veri_bitis }} tarihine kadar).
