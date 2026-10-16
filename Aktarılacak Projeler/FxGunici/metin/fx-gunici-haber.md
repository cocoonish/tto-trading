---
title: 'FX Gün İçi Stratejiler 5: Haber — Kırılım mı Fade mi, FOMC Kararı ve Basın Toplantısı, Beş Haber Stratejisi'
description: "ABD tarım dışı istihdamı, ABD TÜFE'si, FOMC, ECB ve BoE kararları anında dört majör paritede ne olduğu, 2018–2026 bid/ask verisiyle: resmî takvim ve saat denetimi, haber dakikasının makası, hangi koşulda ilk hareketin sürdüğünü (kırılım) hangisinde geri döndüğünü (fade) gösteren devam tablosu, ortalama fiyat patikaları, FOMC kararı ile basın toplantısının ilişkisi ve beş haber stratejisi (N1–N5)."
pubDate: 2026-10-16
tags: ['fx', 'gun-ici', 'haber', 'nfp', 'fomc', 'ecb', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · BLS yayım takvimi ve bültenleri (Internet Archive kopyaları) · Fed, ECB, BoE karar arşivleri · önceden kayıt'
ozet: "Bir veri ya da merkez bankası kararı anında fiyatın ilk hareketi sürer mi, geri mi döner? Olay olay, ilk hareketin büyüklüğüne ve haber öncesi trende göre ölçülmüş bir devam tablosu, FOMC'de kararın basın toplantısında ne sıklıkla tersine döndüğü ve beş mekanik haber stratejisinin maliyetten sonraki sonucu."
seviye: 'ileri'
onkosul:
  - fx-gunici-giris
  - fx-gunici-seans-kirilimlari
  - fx-gunici-fade
---

Haber anı, gün içi FX'in en yoğun ve en pahalı dakikalarıdır. Fiyat bir dakikada günlük aralığının büyük bir kısmını
yürüyebilir; makas açılır, kayma büyür, ilk tepki bazen dakikalar içinde geri alınır. Masalarda iki karşıt sezgi
vardır: "ilk hareket sürer, yönü takip et" ve "ilk hareket aşırıdır, sol". Bu ders iki sezgiyi aynı olaylarda, aynı
maliyetle, ön kaydın kuralıyla sınar.

Ders üç parçadır. Önce **takvim ve maliyet**: olayların saati nereden geldi, nasıl denetlendi ve haber dakikasında
işlem yapmanın bedeli ne. Sonra **betimleyici ölçüler**: stop ve hedef taşımayan, yalnız "ilk hareket sürdü mü"
sorusunu soran devam tablosu, ortalama fiyat patikaları ve FOMC'de karar ile basın toplantısının ilişkisi. En son
**beş strateji**: N1 kırılım, N2 fade, N3 haber öncesi aralık kırılımı, N4 başarısız haber kırılımı ve N5 geri
çekilme sonrası devam.

## Olaylar ve saatleri

Ölçülen olaylar ve eşlendikleri pariteler: ABD verileri (tarım dışı istihdam ve TÜFE) ile FOMC dört paritede; ECB
kararı ve basın toplantısı EUR/USD'de; BoE kararı GBP/USD'de. Her olayın saati resmî bir kaynaktan geldi: ABD
verilerinde yayımın kendi ambargo satırından, FOMC kararında karar metninin yayım satırından, ECB basın toplantısında
duyurunun kendi cümlesinden, tarih tarih; BoE kararında, ECB kararında ve FOMC basın toplantılarının çoğunda kurumun
yayımladığı saat kuralından. Hiçbir saat "genelde 08:30'dur" diye varsayılmadı; hangi olayın saatinin nereden geldiği
metodoloji dersinde.

{{! takvim }}

_Saatler yerel saattir; TSİ karşılıkları giriş dersinin tablosunda. Saatin kaynağı: tarih tarih (resmî metnin
kendi saat satırından) ya da kuraldan (kurumun yayımladığı saat kuralından). Fiyat sınaması: resmî saatte 1 dakikalık fiyatta
olağandışı bir sıçrama var mı (doğrulandı), yoksa bir saat ya da yarım saat önce/sonra mı daha iyi oturuyor (çelişki),
yoksa piyasa hiç kımıldamadı mı (sessiz). Sınama yalnız raporlar: hiçbir olay fiyat yüzünden dışarıda bırakılmadı.
Ayrıntısı ve takvimin bilinen boşlukları metodoloji dersinde._

Fiyat sınamasının bir olayı dışarıda bırakmaması bilinçlidir. Resmî belge birincil kaynaktır; beklenen bir karar
fiyatı oynatmayabilir, ve tepkisiz ya da çelişkili görünen olayları atmak, bir haber stratejisinin örneklemini
sonuca bakarak seçmek olurdu. Saati yanlış bir olay sonuçları sulandırır, şişirmez.

## Haber dakikasının maliyeti

Açıklama anında likidite incelir. Makasın olay saatine göre seyri (EUR/USD, olayların medyanı, pip):

{{! haber_makas }}

_Dakika: olay saatine göre 1 dakikalık mumun başlangıcı; değer o mumun kapanışındaki makastır. −1 açıklamadan önceki
son kotasyon, 0 açıklamadan bir dakika sonrasıdır. Olaysız gün: aynı UTC dakikası, takvimde hiçbir olay olmayan hafta
içi günlerin medyanı. Zirve: makasın en geniş olduğu dakika ve olaysız güne göre katı._

Dört paritede her olayın zirvesi (pip, parantezde olaysız güne göre katı):

{{! haber_makas_ozet }}

{{! haber_makas_cumle }} Piyasa yapıcılar kotasyonlarını açıklamadan önce genişletir; açıklamadan sonraki seyri
tablonun sağ sütunlarında. Bu dersin stratejileri ilk haber mumunun kapanışından sonra girer, yani en pahalı dakikayı zaten atlar; yine de haber
penceresinde (olaydan önceki iki dakikadan sonraki on beş dakikaya) her dolum için ayrıca {{ K.haber_kayma_pip | s1 }}
pip kayma eklenir. Makasın kendisi gerçek bid/ask'tan geldiği için ayrıca sayılır.

**Sürpriz vekili.** Bir verinin piyasayı ne kadar şaşırttığını ölçmenin doğru yolu açıklanan değeri piyasa
beklentisiyle (anket medyanı) kıyaslamaktır. Bu ders o beklentilere sahip değil; yerine **ilk haber mumunun
hareketinin, haberden önceki ATR'ye oranı** kullanılır. Bu bir ölçüm değil vekildir: büyük bir ilk hareket büyük bir
sürprizin de, sığ likiditenin de sonucu olabilir ve ikisi ilk mumda ayırt edilemez. Tablolarda "ilk mum / ATR"
kovaları bu vekildir: 0,5'in altı, 0,5–1, 1–2 ve 2'nin üstü.

## Kırılım mı fade mi: devam tablosu

Ön kayıt, strateji kurallarından bağımsız bir tablo istedi: ilk haber mumu kapandıktan sonraki ilk dakikada, ilk
hareketin **yönünde** (kırılım) ya da **tersinde** (fade) girilir; stop ve hedef yoktur, çıkış 15, 60 ya da 120 dakika
sonradır. İki yön de yürütülebilir fiyatla ve haber kaymasıyla ölçülür. Birinin brüt kazancı öbürünün brüt kaybıdır,
yani iki yönün net sonuçlarının toplamı her olayda iki yönün maliyeti kadar eksidir: bir yönün artıya geçmesi için
hareketin maliyeti aşması gerekir. Ölçü birimi net getirinin günlük ATR'ye oranıdır (yüzde): pariteler arası pipler
kıyaslanamaz.

Gözlem birimi **olaydır**. Aynı ABD verisi dört paritede aynı dakikada ölçülür ve dört ölçüm bağımsız değildir:
hepsi doların tepkisidir. Bir hücrede aynı olaya düşen paritelerin ortalaması tek gözlem sayılır; aksi, dört ölçüm
tam ilintili olduğunda örneklemi dörde katlar ve t istatistiğini yapay olarak iki katına çıkarır.

{{! devam_cumle }}

**Olaya göre.**

{{! devam olay }}

**İlk mumun büyüklüğüne göre** (sürpriz vekili):

{{! devam kova }}

**Haber öncesi trende göre** (olaydan önceki on iki mumun yönü ile ilk mumun yönü):

{{! devam trend_uyum }}

**Zaman dilimine göre** (ilk mum 5, 15 ya da 60 dakika):

{{! devam tf }}

**Pariteye göre** (her parite kendi içinde; gözlem birimi o paritedeki olay):

{{! devam cift }}

<details>
<summary>Olay ve ilk mum büyüklüğü birlikte (bütün hücreler)</summary>

{{! devam olay_kova }}

Bu ayrıntıda gözlemler incelir: {{! devam_yetersiz olay_kova }}; bir olay türünün gözlemleri dört kovaya bölünür
ve kovalar eşit dolmaz.
Bu tablo hüküm için değil, bir hücrenin tek başına göze çarpan sayısının kaç olaydan geldiğini görmek için var.

</details>

_Kırılım ve fade: hücredeki olayların net ortalaması, günlük ATR'nin yüzdesi. Hüküm ön kaydın kuralıyla: en az
{{ O.haber.devam.kural.asgari_olay | n }} olay ve Benjamini–Hochberg q < {{ O.haber.devam.kural.fdr_q | s2 }} ise
"kırılım kazanır" ya da "fade kazanır"; değilse "ayrışmıyor"._

Tabloyu okurken iki şey akılda tutulmalı. Birincisi maliyet: iki yön birlikte negatif olabilir (ikisi de makas ve
kayma öder), yani "fade kazanır" hükmü yokken fade'in kırılımdan iyi görünmesi bir kenar değildir. İkincisi çoklu
sınama: tabloların hepsi tek bir ailedir; tek bir hücrenin tek başına "anlamlı" görünmesi beklenen bir şeydir ve
hüküm bu yüzden ailenin düzeltilmiş q değeriyle verilir.

## Ortalama fiyat patikaları

Her olay için olay anındaki orta fiyattan değişimin ortalaması, haberden otuz dakika öncesinden iki saat sonrasına,
ilk beş dakikanın yönüne göre iki kümede. Bir patika ilk beş dakikadan sonra aynı yönde sürüyorsa kırılım, geri
dönüyorsa fade lehine bir betimlemedir; gölge, ortalamanın %95 aralığıdır.

{% if O.haber.cift.EURUSD.patika.NFP %}{{! sekil haber-patika-nfp "Ortalama patika — NFP" }}{% endif %}

{% if O.haber.cift.EURUSD.patika.CPI %}{{! sekil haber-patika-cpi "Ortalama patika — TÜFE" }}{% endif %}

{% if O.haber.cift.EURUSD.patika.FOMC_karar %}{{! sekil haber-patika-fomc-karar "Ortalama patika — FOMC kararı" }}{% endif %}

{% if O.haber.cift.EURUSD.patika.FOMC_basin %}{{! sekil haber-patika-fomc-basin "Ortalama patika — FOMC basın toplantısı" }}{% endif %}

{% if O.haber.cift.EURUSD.patika.ECB_karar %}{{! sekil haber-patika-ecb-karar "Ortalama patika — ECB kararı" }}{% endif %}

{% if O.haber.cift.EURUSD.patika.ECB_basin %}{{! sekil haber-patika-ecb-basin "Ortalama patika — ECB basın toplantısı" }}{% endif %}

{% if O.haber.cift.GBPUSD.patika.BoE_karar %}{{! sekil haber-patika-boe-karar "Ortalama patika — BoE kararı" }}{% endif %}

Patikalar betimleyicidir: ortalama bir patika tek bir olayın yolunu anlatmaz, ve ilk beş dakikanın yönüne göre
kümelemek patikanın ilk beş dakikasını tanımı gereği o yöne iter. Asıl bilgi beşinci dakikadan sonrasıdır.

## FOMC: karar ve basın toplantısı

Basın toplantılı her FOMC toplantısında iki ayrı olay var: kararın açıklanması (14:00 New York; TSİ 21:00, ABD kış
saatinde 22:00) ve yarım saat sonra başkanın basın toplantısı. Piyasa kararı yarım saat fiyatlar, sonra toplantıda yeniden fiyatlar. Ön kaydın soruları:
basın toplantısının ilk saatindeki hareket kararın ilk yarım saatindekini ne sıklıkla tersine çeviriyor, ikisi
arasındaki ilinti ne, ve dönüş olasılığı kararın büyüklüğüne bağlı mı?

{% if O.haber.cift.EURUSD.fomc %}{{! sekil haber-fomc "FOMC: karar ve basın toplantısı" }}

{{! fomc }}

_Dönüş oranı: basın toplantısının ilk saatindeki hareketin, kararın ilk yarım saatindekiyle ters işaretli olduğu
toplantıların payı (%50 yazı turadır). Korelasyon: iki hareketin ilintisi; aralıklar toplantıların yeniden
örneklenmesiyle. Son üç sütun: dönüş oranı, kararın ilk yarım saatteki hareketinin büyüklüğüne göre (günlük ATR'nin
katı; parantezde toplantı sayısı)._

{{! fomc_cumle }}{% else %}FOMC basın toplantılarının saati takvime henüz girmedi; bu bölüm onunla birlikte ölçülecek.{% endif %}

## N1 — haber kırılımı

{{! strateji n1 }}

## N2 — haber fade'i

{{! strateji n2 }}

## N3 — haber öncesi aralık kırılımı

{{! strateji n3 }}

## N4 — başarısız haber kırılımı

{{! strateji n4 }}

## N5 — geri çekilme sonrası devam

{{! strateji n5 }}

## Beş stratejinin özeti

{{! ders_ozet }}

<div class="pratik">
  <span class="etiket">Pratik — haber</span>

{{! pratik_islem n1 "Alıştırma 1" kaybeden }}

{{! pratik_islem n2 "Alıştırma 2" }}

</div>

_Yatırım tavsiyesi değildir. Ölçülen her şey geçmişe aittir; geçmiş sonuçlar gelecekteki sonuçların göstergesi
değildir._
