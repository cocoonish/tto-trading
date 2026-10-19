---
title: 'FX Gün İçi Oyun Planı 2: Açılışlar'
description: "Tokyo, Londra ve New York açılışlarının ilk {{ AN.londra_acilis.tf }} dakikası: güçlü, normal, reddedilen ve küçük ilk mumdan sonra fiyat ne yapıyor, bunun ne kadarı mumun kendi şeklinden geliyor, trend bunu değiştiriyor mu, ve bu davranışa dayanan tepkiler maliyetten sonra ne verdi."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Açılışın ilk mumu çoğu zaman yarısına geri döner ve güçlü mum çoğu zaman devam ediyor gibi görünür; ikisi de mumun kendi şeklinden geliyor, fiyat yön bilgisi taşımıyor. Ders açılışların oyun planını sınıf sınıf verir: ne beklenir, ne kadar sürer, neye işlem açılmaz."
seviye: 'giris'
onkosul: ['fx-oyun-okuma']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';

Açılış bir seansın ilk sözüdür. Tokyo'da gece birikmiş emirler, Londra'da günün en büyük likiditesinin gelişi, New
York'ta hisse piyasasıyla birlikte ABD'nin masaya oturması. Üçünde de ilk {{ AN.londra_acilis.tf }} dakika günün ilk
aralığını çizer ve işlemcilerin çoğu o aralığa göre plan yapar. Bu ders o aralıktan sonra fiyatın genelde ne yaptığını
ve bunun ne kadarının bir şey söylediğini anlatır.

{{# an_tablo acilis }}

## Plan tek cümlede

**Açılışın ilk mumu bir aralık çizer, bir yön değil.** Yarısına dönmesi de, güçlü mumun devam etmesi de mumun kendi
şeklinin verdiği paydır; fiyatın yönü rastgele olsaydı da aynı sayılar çıkardı. Açılış bir işlem fırsatı değil, günün
ilk referanslarını işaretleme anıdır.

## İlk mumdan sonra fiyat nereye gidiyor

İlk mum kapandıktan sonra ortalama fiyat, mumun yönünde ve mumun boyu cinsinden. Sıfır çizgisi ilk mumun kapanışıdır;
yukarı, mumun yönüne devam demektir.

{{# sekil 01_patika "Açılıştan sonra ortalama fiyat yolu, ilk mumun yönünde" }}

Çizgilerin hepsi sıfıra yakın dolaşıyor. Güçlü bir açılış mumundan sonra bile ortalama fiyat mumun yönünde yol
almıyor: devam ettiği günlerle döndüğü günler ortalamada birbirini götürüyor.

## Sınıf sınıf, şansın payıyla

Her sınıfta yarısına dönüş, devam ve dönüş payı; yanında yolun aynasında, yani yön rastgele olsaydı, aynı payın
değeri. Üç açılışın toplamı:

{{# ayna acilis }}

Gerçek pay ile aynadaki pay her satırda birkaç puan içinde. Açılışın ilk mumu, kendi şeklinin ötesinde, fiyatın
sonraki iki üç saati hakkında bir şey söylemiyor. Her açılış tek tek, iki dönemde:

{{# davranis acilis }}

{{# sekil 02_devam_donus "Devam ve dönüş: üç açılış, üç sınıf, gerçek ve ayna" }}

### Güçlü ilk mum

Fiyat açılışta bir yöne gitmiş ve o yönde kapanmış. Devam payı ({{ Y.ic.acilis.guclu.devam }}) dönüşten
({{ Y.ic.acilis.guclu.donus }}) yüksek, ve bu fark akla "yön var" dedirtir. Aynada da aynı fark çıkıyor
({{ Y.ic.acilis.guclu.devam_ayna }} ve {{ Y.ic.acilis.guclu.donus_ayna }}): güçlü mum ucuna yakın kapandığı için
kendi ucunun yarım mum boyu ötesi, öbür ucundan çok daha yakındır. 2024 → döneminde de aynı: gerçek
{{ Y.dis.acilis.guclu.devam }}, ayna {{ Y.dis.acilis.guclu.devam_ayna }}.

Güçlü mum yarısına dönmeyi genelde biraz zaman alarak yapar. Yarısına dönenlerde ortanca süre Londra'da
{{ A.ic.londra_acilis.guclu.orta_dk }}, Tokyo'da {{ A.ic.tokyo_acilis.guclu.orta_dk }}, New York'ta
{{ A.ic.ny_acilis.guclu.orta_dk }} dakika.

Oyun planı şöyle okur:

- Güçlü mumun yönü bir işlem gerekçesi değildir. Kovalamak da, yarısına gelince katılmak da maliyetten sonra
  kaybettirdi (aşağıda).
- Güçlü mumun iki ucu günün ilk referanslarıdır. Gün içinde fiyat bu uçlara geldiğinde ne yaptığı bu derste
  ölçülmedi.

### Normal ve reddedilen ilk mum

Açılışların çoğu buraya düşer. Normal mum {{ Y.ic.acilis.normal.orta }} yarısına döndü ve bu çoğu zaman hemen olur:
ortanca süre Londra'da {{ A.ic.londra_acilis.normal.orta_dk }}, New York'ta {{ A.ic.ny_acilis.normal.orta_dk }}
dakika. Ama normal mum ortasına yakın kapanır, yani yarısına dönüş aynada da {{ Y.ic.acilis.normal.orta_ayna }}.
Devam ile dönüş eşit ({{ Y.ic.acilis.normal.devam }} ve {{ Y.ic.acilis.normal.donus }}).

Reddedilen mum işlemcilerin çoğunun güçlü bir işaret saydığı mumdur: "o seviyede satıcı var". Sayılar bu okumayı
desteklemiyor. Reddin yönünde devam {{ Y.ic.acilis.reddedilen.devam }}, dönüş {{ Y.ic.acilis.reddedilen.donus }};
aynada {{ Y.ic.acilis.reddedilen.devam_ayna }} ve {{ Y.ic.acilis.reddedilen.donus_ayna }}. Fitil bir şey söylüyorsa
bile, açılıştan sonraki saatlere taşımıyor.

### Küçük ilk mum

Açılış sessiz geçmiş: ilk mum tipik boyun altında. Akla gelen tepki, aralık kırıldığında kırılan tarafa gitmektir
("sıkışma patlar"). Kırılan tarafta fiyatın bir mum boyu daha ilerleme payı:

{{# kucuk acilis }}

Bu payın tek başına bir anlamı yok; anlamı tepkinin sonucundadır, o da aşağıda: kırılımın yönüne girmek maliyetten
önce sıfıra yakın, maliyetten sonra eksi.

## Trend bir şey değiştiriyor mu

Günlük trend yönünde açılan güçlü bir mumun daha sık devam etmesi beklenir. 2018–2023'te üç açılışın toplamında
trend yönündeki güçlü mum {{ T.acilis.guclu.trendle.devam }}, trende karşı olanı {{ T.acilis.guclu.karsi.devam }},
trend yatayken {{ T.acilis.guclu.yatay.devam }} devam etti. Trend sayıyı değiştirmiyor. Bütün sınıflar:

<details>
<summary>Trend ayrımı tablosu (2018–2023)</summary>

{{# trend acilis }}

</details>

## Bu okumaları işleme çevirmek

Her sınıf için akla ilk gelen tepki sınandı. Yön sınıflarında: mumun yarısına limit emirle mumun yönünde gir, stopu
öbür ucun {{ ref_tampon }} mum boyu ötesine koy, yarım R hedefle. Küçük mumda: kırılan uçtan gir, stopu öbür ucun
{{ ref_tampon }} mum boyu ötesine koy, yarım R hedefle. 2024 → dönemindeki sonuç:

{{# kisa referans acilis }}

Kazanma oranları yüksek, dördü de "çalışmıyor". İki şey birlikte kaybettiriyor:

- **Maliyetten önce kenar yok.** Aynı kurallar orta fiyatla, makas ve kayma olmadan sınandığında da sonuç sıfıra yakın
  ya da eksi: güçlü mumda {{ B.referans.acilis.guclu.dis.brut }} R, normal mumda {{ B.referans.acilis.normal.dis.brut }} R,
  küçük mumun kırılımında {{ B.referans.acilis.kucuk.dis.brut }} R. Limit emir yalnız fiyat geri geldiğinde dolar, ve
  geri gelen günlerden sonrası yazı turadır.
- **Maliyet sıfırı eksiye çeviriyor.** Açılış mumu küçüktür, stop da küçüktür (ortanca risk normal mumda
  {{ B.referans.acilis.normal.dis.risk_pip }}, küçük mumda {{ B.referans.acilis.kucuk.dis.risk_pip }} pip). Makas bu
  stopun görünür bir parçasıdır: normal mumda maliyetin payı {{ B.referans.acilis.normal.dis.maliyet }} R, küçük mumun
  kırılımında (kayma da ödenir) {{ B.referans.acilis.kucuk.dis.maliyet }} R.

2018–2023'te açılışın her sınıfında beş altı tepki daha denendi: kapanışta mumun yönünde girmek, daha uzak hedef,
daha geniş stop. Hiçbiri maliyetten sonra artıda kalmadı. En iyisi güçlü mumda kapanışta mumun yönünde girmekti
({{ I.acilis.guclu.ad }}): işlem başına {{ I.acilis.guclu.R }} R. Yarısına limitle girmekle arasında belirgin fark
yok, ve kovalamak 2024 sonrasında sınanmadı. Plan bu hücrelerde "izle, işlem açma" der; ayrıntı
[backtest dersinde](/arastirma/fx-oyun-backtest/).

## Açılış için masa kartı

- **İlk {{ AN.londra_acilis.tf }} dakika bir aralık çizer.** Üst ve alt ucu günün ilk referanslarıdır.
- **Normal mumda yarısına dönüş birkaç dakika içinde beklenir.** Bu, mumun şeklinin sonucudur; ne alış ne satış
  sebebidir.
- **Güçlü mumun "devam ediyor" görüntüsü yanıltıcıdır.** Yön rastgele olsaydı da aynı oranda devam ederdi.
- **Fitile ve trende anlam yükleme.** İkisi de sayılarda görünmüyor.
- **Sessiz açılışın kırılımı bir sinyal değildir.** Kırılımın yönüne girmek maliyetten önce de kazandırmadı.
- **Açılışta masada kalmanın sebebi işlem değil, referanstır.** Plan bu anda işlem önermiyor.
