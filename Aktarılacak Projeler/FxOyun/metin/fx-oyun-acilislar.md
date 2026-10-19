---
title: 'FX Gün İçi Oyun Planı 2: Açılışlar'
description: "Tokyo, Londra ve New York açılışlarının ilk {{ AN.londra_acilis.tf }} dakikası: güçlü, normal, reddedilen ve küçük ilk mumdan sonra fiyat ne yapıyor, trend bunu değiştiriyor mu, ve bu davranışa dayanan tepkiler maliyetten sonra ne verdi."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'oyun-plani', 'backtest', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Açılışın ilk mumu neredeyse her zaman yarısına geri döner ve oradan sonrası yazı turadır. Güçlü ilk mum biraz daha sık devam eder ama bu fark, makas ve stopla birlikte bir kazanca dönüşmüyor. Ders açılışların oyun planını sınıf sınıf verir."
seviye: 'giris'
onkosul: ['fx-oyun-okuma']
---

import GrafikEmbed from '../../components/GrafikEmbed.astro';

Açılış bir seansın ilk sözüdür. Tokyo'da gece birikmiş emirler, Londra'da günün en büyük likiditesinin gelişi, New
York'ta hisse piyasasıyla birlikte ABD'nin masaya oturması. Üçünde de ilk {{ AN.londra_acilis.tf }} dakika çoğu zaman
günün ilk aralığını çizer ve işlemcilerin çoğu o aralığa göre plan yapar. Bu ders o aralıktan sonra fiyatın genelde ne
yaptığını anlatır.

{{# an_tablo acilis }}

## Plan tek cümlede

**Açılışın ilk mumunu kovalamak da, yarısına döndüğünde ona katılmak da maliyetten sonra kaybettiriyor.** İlk mum
neredeyse her zaman yarısına geri döner, ama oradan sonra kendi ucuna gitme ihtimali yarı yarıyadır. Açılışın bir işlem
fırsatı değil bir **okuma** fırsatı olduğu, iki dönemde de aynı sayılarla görülüyor.

## İlk mumdan sonra fiyat nereye gidiyor

İlk mum kapandıktan sonra ortalama fiyat, mumun yönünde ve mumun boyu cinsinden. Sıfır çizgisi ilk mumun kapanışıdır;
yukarı, mumun yönüne devam demektir.

{{# sekil 01_patika "Açılıştan sonra ortalama fiyat yolu, ilk mumun yönünde" }}

Çizgilerin hepsi sıfıra yakın dolaşıyor. Güçlü bir açılış mumundan sonra bile **ortalama** fiyat mumun yönünde anlamlı
bir yol almıyor. Bu, güçlü mumun hiç devam etmediği anlamına gelmez; devam ettiği günlerle döndüğü günlerin ortalamada
birbirini götürdüğü anlamına gelir.

## Sınıf sınıf

Aşağıdaki tablo her açılışın her sınıfında yarısına dönüş, devam ve dönüş paylarını iki dönemde verir:

{{# davranis acilis }}

İki dönemin sayıları birbirine çok yakın. Bu serinin en sağlam bulgusu budur: açılışların davranışı yıldan yıla
değişmiyor.

{{# sekil 02_devam_donus "Devam ve dönüş: üç açılış, üç sınıf, iki dönem" }}

### Güçlü ilk mum

Fiyat açılışta bir yöne gitmiş ve o yönde kapanmış. Üç açılışın toplamında 2018–2023'te güçlü mum
{{ D.ic.acilis.guclu.devam }} devam etti, {{ D.ic.acilis.guclu.donus }} tersine döndü; 2024 → döneminde
{{ D.dis.acilis.guclu.devam }} ve {{ D.dis.acilis.guclu.donus }}. Devam dönüşten daha sık. Ama güçlü mum da çoğu
zaman yarısına döner: {{ D.ic.acilis.guclu.orta }} (2024 → {{ D.dis.acilis.guclu.orta }}).

Oyun planı şöyle okur:

- Güçlü mumun yönü günün ilk ipucudur. Ama mumun ucunda, kapanışta mumun yönünde girmek en kötü yerdir: fiyatın
  çoğu zaman yarıya geri geleceği bilinir.
- Yarıya geri gelen güçlü mum ikiye ayrılır: kendi ucuna dönenler ve öbür uca gidenler. Yarısına dönen güçlü
  mumların yalnız {{ D.ic.acilis.guclu.uc_orta }} kadarı kendi ucuna geri gitti (2024 → {{ D.dis.acilis.guclu.uc_orta }}).
  Yani geri çekilme "ucuz giriş" değil, yazı turanın başladığı yerdir.
- Güçlü mumun karşı ucu kırılırsa açılışın sözü geri alınmıştır. O günler azınlıktadır ama hepsi stopa gider.

### Normal ilk mum

Açılışların çoğu buraya düşer. Normal mum {{ D.ic.acilis.normal.orta }} yarısına döndü; devam
({{ D.ic.acilis.normal.devam }}) ile dönüş ({{ D.ic.acilis.normal.donus }}) eşit. 2024 → döneminde
{{ D.dis.acilis.normal.devam }} ve {{ D.dis.acilis.normal.donus }}.

Oyun planı: normal mum yön söylemez. Açılış aralığı günün ilk referansıdır; üst ve alt ucu, gün içinde fiyatın
nerede tepki verdiğine bakmak için işaretlenir. Mumun kendisi işlem gerekçesi değildir.

### Reddedilen ilk mum

Açılışta fiyat bir yöne gitmiş, geri itilmiş ve uzun bir fitil bırakmış. İşlemcilerin çoğu bunu güçlü bir işaret
olarak okur: "o seviyede satıcı var". Sayılar bu okumayı desteklemiyor. Reddin yönünde devam
{{ D.ic.acilis.reddedilen.devam }}, dönüş {{ D.ic.acilis.reddedilen.donus }}; 2024 → döneminde
{{ D.dis.acilis.reddedilen.devam }} ve {{ D.dis.acilis.reddedilen.donus }}. Fitil bir şey söylüyorsa bile, açılıştan
sonraki saatlere taşımıyor.

### Küçük ilk mum

Açılış sessiz geçmiş: ilk mum tipik boyun altında. Burada akla gelen tepki, aralık kırıldığında kırılan tarafa
gitmektir ("sıkışma patlar"). Kırılan tarafta fiyatın bir mum boyu ilerleme payı:

{{# kucuk acilis }}

Pay yarı yarıya. Sıkışmanın bir yöne patladığı doğru olabilir, ama hangi yöne patladığını kırılımın ilk dakikası
söylemiyor.

## Trend bir şey değiştiriyor mu

Günlük trend yönünde açılan bir güçlü mumun daha sık devam etmesi beklenir. 2018–2023'te üç açılışın toplamında:

{{# trend acilis }}

Değiştirmiyor. Trend yönündeki güçlü mum {{ T.acilis.guclu.trendle.devam }}, trende karşı olanı
{{ T.acilis.guclu.karsi.devam }} devam etti. Plan trendi bir okuma bilgisi olarak taşır; karar ölçütü yapmaz.

## Bu okumaları işleme çevirmek

Her sınıf için akla ilk gelen tepki, önceden yazılmış kurallarla sınandı. Yön sınıflarında tepki: mumun yarısına
limit emirle mumun yönünde gir, stopu öbür ucun hemen ötesine koy, yarım R hedefle. Küçük mumda: kırılan uçtan gir,
stopu öbür uca koy, yarım R hedefle. Sonuç:

{{# bacaklar referans acilis }}

Kazanma oranları yüksek: güçlü mumda {{ B.referans.acilis.guclu.dis.kazanma }}, küçük mumda
{{ B.referans.acilis.kucuk.dis.kazanma }}. Dört tepkinin dördü de "çalışmıyor" hükmü aldı. Sebepleri ayrı:

- **Yön sınıflarında kenar maliyetten önce de yok.** Güçlü mum tepkisinin maliyetsiz sonucu
  {{ B.referans.acilis.guclu.dis.brut }} R, normal mumunki {{ B.referans.acilis.normal.dis.brut }} R. Limit emir
  makas ve kayma ödemediği için maliyet küçük ({{ B.referans.acilis.guclu.dis.maliyet }} R); kaybettiren şey
  geri çekilmeden sonraki yazı turadır. Yarım R hedefle başa baş için işlemlerin
  {{ B.referans.acilis.guclu.dis.basabas }} kadarını kazanmak gerekirdi.
- **Küçük mumda kenar var ama maliyet onu yutuyor.** Kırılım tepkisinin maliyetsiz sonucu
  {{ B.referans.acilis.kucuk.dis.brut }} R, maliyet {{ B.referans.acilis.kucuk.dis.maliyet }} R: küçük mum küçük
  stop demektir (ortanca risk {{ B.referans.acilis.kucuk.dis.risk_pip }} pip) ve makasla kayma o stopun büyük bir
  parçasıdır. Net sonuç {{ B.referans.acilis.kucuk.dis.R }} R.

2018–2023'te açılışların hiçbir sınıfında, denenen hiçbir tepki maliyetten sonra artıda kalmadı. Plan bu hücrelerde
"izle, işlem açma" der; ayrıntı [backtest dersinde](/arastirma/fx-oyun-backtest/).

## Açılış için masa kartı

- **Açılışın ilk mumu bir aralık çizer, bir yön değil.** Aralığın üst ve alt ucu günün ilk referanslarıdır.
- **Yarısına dönüş beklenir.** Yarıya geri gelen fiyat ne alış ne satış yeridir; açılışın olağan hâlidir.
- **Güçlü mumun yönü hafif bir eğilimdir.** Gün içinde sonraki bir kurulumun yönünü seçerken işe yarayabilir;
  tek başına bir giriş sebebi değildir.
- **Fitile ve trende fazla anlam yükleme.** İkisi de sayılarda görünmüyor.
- **Küçük stop, büyük maliyet.** Sessiz bir açılışın kırılımına girmek, maliyetin stopun büyük bir parçası olduğu
  bir işlemdir.
