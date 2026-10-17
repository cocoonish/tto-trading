---
title: 'FX Gün İçi Stratejiler 7: Karşılaştırma — Bütün Kurallar Yan Yana'
description: "Serinin bütün kuralları aynı makinenin aynı ölçüleriyle yan yana: örneklem dışında işlem başına net R ve aralığı, parite parite hüküm, maliyet merdiveni, rastgele yön sınaması, stratejiler arası günlük korelasyon ve koşul analizinin ters seçimle sınanması. Hangi kural bir yön bilgisi taşıyor, hangisi yalnız makas ödüyor ve tutan koşulların ne kadarı şans."
pubDate: 2026-10-17
tags: ['fx', 'gun-ici', 'backtest', 'strateji', 'ders']
durum: 'aktif'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt'
ozet: "Beş dersin bütün kuralları tek sayfada: maliyetten sonra ne kaldığı, kenarın yön seçiminde mi zamanlamada mı olduğu, kuralların birbirinin kopyası olup olmadığı ve koşul analizinin 'tuttu' sonuçlarının ne kadarının şansla açıklandığı."
seviye: 'ileri'
onkosul:
  - fx-gunici-giris
  - fx-gunici-seans-kirilimlari
  - fx-gunici-fade
---

Önceki beş ders kuralları tek tek işledi: kural, örnek günler, sonuç, maliyet, koşullar, hüküm. Bu ders hepsini aynı
sayfaya koyar. Karşılaştırma adildir çünkü makine aynıdır: her kural aynı veriyle, aynı yürütme fiyatıyla (gerçek
bid/ask ve dolum başına aynı kayma), aynı örneklem bölmesiyle ve aynı hüküm kuralıyla ölçüldü; hiçbir kuralın
parametresi sonuca bakarak seçilmedi. R'nin paydası kurala göre değişir: stoplu kurallarda stop uzaklığıdır,
stopsuz kurallarda ({{! stopsuz_ad }}) girişteki ATR(14); bu kurallarda R bir risk değil ölçek birimidir (giriş
dersi, R birimi) ve sıralamada iki tür R yan yana durur. Sıralama bir öneri değildir: işlem başına net R'si en yüksek kural "en iyi
strateji" değil, bu örneklemde en az kaybeden ya da en çok kazanan kuraldır ve hüküm kuralının üç şartını sağlamadıkça
şansla ayırt edilemez.

## Bütün kurallar tek tabloda

{{! ders_ozet hepsi }}

Aynı kurallar, havuzun örneklem dışındaki öbür ölçüleriyle:

{{! ozet_olcu hepsi }}

{{! sekil karsilastirma-ozet "Örneklem dışında işlem başına net R — bütün kurallar" }}

{{! genel_hukum }}

## Parite parite

Aynı kural dört paritede ayrı ayrı ölçüldü. Hücre: örneklem dışında işlem başına net R ve varsayılanın 2024 → hükmü; son
sütun dört paritenin işlemleri birlikte (havuz).

{{! hukum_matris }}

Bir kuralın bir paritede iyi görünüp öbürlerinde görünmemesi iki şekilde okunabilir: ya o paritenin bir özelliği
(likidite, seans, haber yoğunluğu) kurala uyuyordur, ya da dört sınamadan biri şansla tutmuştur. Şansın payı hangi
hükümden söz edildiğine bağlıdır. **Çalışıyor** üç şartın birlikte tutmasını ister; yalnız rastgele yön şartı bile tek
başına %5 düzeyinde bir sınamadır ve kenarı olmayan bir kural dört paritenin en az birinde onu şansla en çok
4 × %5 = {{= "%20" }} olasılıkla geçer (sınamalar bağımsız olsaydı 1 − 0,95⁴ ≈ {{= "%19" }}; pariteler aynı dolara
karşı işlem gördüğü için bağımsız değiller ve üst sınır her durumda geçerli). **Zayıf** ise bir sınama değildir:
yalnız örneklem dışı net ortalamanın artı olmasını ister. Kenarı olmayan bir kuralın brüt ortalaması kabaca yarı
yarıya artı çıkar; maliyetten sonra bu olasılık düşer ama sıfır değildir: {{ T.bilesim | n }} bileşimde birkaç
"zayıf" hüküm şansla da çıkabilir. Tek paritede "zayıf" kalan bir kuralı o pariteye özgü bir kenar saymak için o
paritenin yapısından gelen ayrı bir gerekçe gerekir.

## Maliyet

Aynı kural, artan yürütme maliyetiyle (EUR/USD). Brüt sonuç orta fiyattan orta fiyata, yani makassız ve
kaymasızdır; net sonuçlar gerçek bid/ask makasını ve dolum başına kaymayı içerir. Merdiven aynı işlemlerin değil aynı
kuralın yeniden koşusudur: kayma dolum fiyatını, dolayısıyla stopa ya da hedefe değilen dakikayı değiştirebilir.

{{! sekil karsilastirma-maliyet "Maliyet merdiveni — bütün kurallar" }}

Parite parite, örneklem dışında işlem başına net R beklentisi artı olan kural sayısı:

{{! maliyet_ozet }}

Brüt ile **yalnız makas** sütunu arasındaki fark yalnız gerçek bid/ask makasıdır: o sütunda kayma da haber
penceresinin ek kayması da sıfırdır. Dört paritede örneklem dışında brüt sonucu artı olan {{ T.brut_arti | n }}
kural–parite bileşiminin {{ T.brut_arti_makas_eksi | n }} tanesinde yalnız makasla net sonuç sıfıra ya da altına
iniyor; kayma sıfır kademesinde (haber penceresinin ek kayması sabit kalır) bu sayı {{ T.brut_arti_sifir_eksi | n }},
temel senaryoda (dolum başına {{ K.temel_kayma_pip | s1 }} pip) {{ T.brut_arti_net_eksi | n }}. Bir kuralın kâğıt
üstünde (orta fiyatla) artı görünmesi, piyasa yapıcıya her işlemde ödenen makası karşılamaya yetmez. Stopu yakın
kurallar en çok etkilenir, çünkü makas pip cinsinden sabittir ve R birimi küçüldükçe R cinsinden büyür.

## Yön mü, zamanlama mı?

Bir kuralın kenarı iki yerden gelebilir: doğru **zamanda** işlem açmak (oynaklığın, eğilimin olduğu saatler) ya da
doğru **yönü** seçmek. Rastgele yön sınaması ikisini ayırır: aynı giriş dakikası, aynı risk ve aynı çıkış kuralı, yalnız
yön yazı turayla. Stratejinin sonucu bu dağılımın sağ kuyruğundaysa (yüzdelik ≥ 95) yön seçimi bir şey katıyordur.

{{! sekil yontem-rastgele "Yön seçmenin değeri — sınanan kurallar (EUR/USD)" }}

{{! rastgele_ozet }}

## Kurallar birbirinin kopyası mı?

Aynı seviyeye bakan iki kural (bir aralığın kırılımı ve başarısız kırılımı) aynı günlerde işlem açar; aynı saatte
çalışan iki kural aynı oynaklığı paylaşır. Günlük R'lerin korelasyonu bunu ölçer: yüksek artı korelasyon iki kuralın
aynı bahsi oynadığını, eksi korelasyon birbirinin tersini oynadığını, sıfıra yakın korelasyon ise farklı günlerde ya da
farklı yönlerde kazanıp kaybettiğini söyler.

{{! sekil karsilastirma-korelasyon "Stratejiler arası günlük R korelasyonu" }}

{{! korelasyon_cumle }}

{{! korelasyon_tablo }}

Korelasyonun düşük olması bir portföy argümanı değildir: birbirinden bağımsız iki kaybeden kuralın toplamı, daha
düzgün bir eğriyle kaybeder. Çeşitlendirme ancak bileşenlerin her biri maliyetten sonra artıysa bir değer yaratır.

## Koşullar: tutanların ne kadarı şans?

Her kuralın sonuç bölümünde on dört koşul değişkeni sınandı: örneklem içinde ortalamanın üstünde kalan kovalar seçildi
ve örneklem dışında sınandı. Kural basittir ve gevşektir — seçilen kovaların örneklem dışında artı olması ve tamamlayanı
aşması yeter — çünkü amaç koşulları bulmak değil, örneklem içinde görünen koşulların örneklem dışına taşınıp
taşınmadığını görmekti. Gevşek bir sınamanın bedeli şansla tutan koşullardır. Ne kadarının şans olduğunu ölçmek için
aynı ölçüt **ters seçimle** de koşuldu: örneklem içinde ortalamanın altında kalan kovalar seçilseydi örneklem dışı
ölçütü ne sıklıkla geçerdi? Kova farkları yalnız gürültüyse iki seçimin geçme oranı aynı olur.

{{! kosul_genel }}

{{! kosul_genel_cumle }}

_Ters seçim önceden kayıtta yoktu ve sonradan eklendi. Hiçbir hükmü değiştirmez; yalnız "tuttu" sayısının ne
kadarının şansla açıklanabileceğini ölçer (metodoloji dersi)._

## Hangi koşulda hangisi

Bir karşılaştırmanın son sorusu bir karar tablosudur: hangi koşulda hangi kural. Bu serinin cevabı ölçümün izin
verdiği kadardır. Önceden kayıtlı kuralların hiçbiri örneklem dışında hükmün üç şartını sağlamadı, yani "bu koşulda
şunu kullan" diyebilecek ölçülmüş bir kural yok{{? T.calisiyor == 0 }}.{{! ay_sonu_istisna }} Ölçümün verebildiği şey **adaylardır**: örneklem içinde seçilip örneklem
dışında en az iki paritede aynı kova seçimiyle tutan koşullar. Her kuralın kontrol listesindeki "Ne zaman" maddesi bu
tablonun kendi satırlarıdır.

{{! hangi_kosul }}

Tablonun okunuşu dar tutulmalı. Bir aday, örneklem içinde yapılan aynı kova seçiminin (bir ya da birkaç kova) en az
iki paritede örneklem dışında da birlikte artı ve seçilmeyen kovaların birlikte ortalamasının üstünde kaldığını
söyler; seçimin içindeki tek tek kovalar bunun altında kalabilir. Aday güven aralığını ve rastgele yön sınamasını
taşımaz; bütün kurallar birlikte sayıldığında gerçek seçim ters seçimden ayırt edilemiyor (yukarıdaki bölüm).

{{! ay_sonu_ozet }}

## Ne öğrendik

Seri, gün içi FX işlem kitaplarının en çok anılan kurallarını aynı makinede, maliyetiyle ve önceden yazılmış bir hüküm
kuralıyla ölçtü. Üç soru bütün derslerde tekrar etti.

**Makas.** {% if T.brut_arti and T.net_eksi_brut_oran > 0.5 %}Orta fiyatla artı görünen kural–parite
bileşimlerinin çoğu, makas ve dolum başına {{ K.temel_kayma_pip | s1 }} pip kaymayla eksiye dönüyor{% if T.makas_brut_oran > 0.5 %}; çoğu için makasın
kendisi yetiyor{% endif %} (maliyet bölümü).{% elif T.brut_arti %}Orta fiyatla artı görünen kural–parite bileşimlerinin
bir kısmı maliyetle eksiye dönüyor (maliyet bölümü).{% else %}Örneklem dışında brüt sonucu artı olan bileşim yok:
kuralların sorunu makastan önce gelir, orta fiyatla bile yön yok.{% endif %} Bir backtest'in ilk sorusu "kaç R
kazandırdı" değil, "hangi fiyatla ölçüldü" olmalıdır.

**Yön seçimi.** Örneklem dışında (2024 →) rastgele yön sınamasında {{ T.rastgele_n | n }} bileşimin
{{ T.rastgele_ust | n }} tanesi eşiği (rastgele dağılımda yüzdelik ≥ 95) geçti; hiçbir kenarın olmadığı bir dünyada beklenen yaklaşık
{{ T.rastgele_beklenen | n }}. Sayı tohuma bağlıdır: aynı yordam {{ K.rastgele_duyarlilik.tohum | n }} sabit tohumla
koşunca her tohumda geçen {{ T.rastgele_ust_her_tohum | n }}, en az birinde geçen
{{ T.rastgele_ust_bir_tohum | n }} bileşim var (tohum sınaması yüzdeliği {{ K.rastgele_duyarlilik.taban | n }}'ın
üstündeki bileşimlerde yapıldı{{? K.rastgele_duyarlilik.taban == 90 }}; altındakiler iki sayımda da geçmeyen sayıldı). {% if T.rastgele_binom_p < 0.05 %}Bu sayı şansın beklediğinin üstünde (binom p
{{ T.rastgele_binom_p | s2 }}); eşiği geçen kurallar yukarıdaki bölümde adıyla. Sınamalar bağımsız değildir, aynı
paritenin kuralları aynı günleri paylaşır.{% else %}Bu sayı şansın beklediğinden ayırt edilemiyor (binom p
{{ T.rastgele_binom_p | s2 }}): bu pencerede kuralların yön seçimi, toplu olarak, yazı turadan ayırt edilemiyor.{% endif %}{% if T.arti_n %}
Örneklem dışında net sonucu artı olan {{ T.arti_n | n }} bileşimden rastgele yön sınaması yapılabilenler
{{ T.arti_rastgele_n | n }} tane; bunların {{ T.arti_rastgele_alt | n }} tanesinde yön seçimi tek başına da yazı turadan
ayırt edilemiyor. {{! arti_rastgele_ayirt }}{% if T.arti_n > T.arti_rastgele_n %} Öbürlerinde sınama yapılmadı: örneklem dışında
{{ K.uygulama_esik.rastgele | n }}'den{{? K.uygulama_esik.rastgele == 20 }} az işlem var.{% endif %}{% endif %}
{{! rastgele_tum }}

**Örneklem içi seçim.** Seçim {{ T.bilesim | n }} bileşimin {{ T.secilen_n | n }} tanesinde kuruldu{% if T.secimsiz %};
öbür {{ T.secimsiz | n }} bileşimde ızgaranın hiçbir kombinasyonu örneklem içinde asgari işlem sayısına ulaşmadı:
{{! secimsiz }}{% endif %}. Izgaradan örneklem içinde seçilen kombinasyonların deflated Sharpe olasılığı
{{ T.dsr_n | n }} bileşimin {% if T.dsr_ust == 0 and T.dsr_gurultu_ust == 0 %}hiçbirinde ne denemelerin yayılımından
kurulan eşikle ne örnekleme gürültüsü eşiğiyle 0,95'i aşmıyor.{% elif T.dsr_ust == 0 %}{{ T.dsr_gurultu_ust | n }}
tanesinde örnekleme gürültüsü eşiğiyle 0,95'i aşıyor; denemelerin yayılımından kurulan eşikle hiçbirinde
aşmıyor.{% elif T.dsr_gurultu_ust == 0 %}{{ T.dsr_ust | n }} tanesinde denemelerin yayılımından kurulan eşikle 0,95'i
aşıyor; örnekleme gürültüsü eşiğiyle hiçbirinde aşmıyor.{% else %}{{ T.dsr_ust | n }} tanesinde denemelerin
yayılımından kurulan eşikle, {{ T.dsr_gurultu_ust | n }} tanesinde örnekleme gürültüsü eşiğiyle 0,95'i aşıyor.{% endif %} {% if T.dsr_n and T.dsr_ust_oran < 0.5 %}{% if T.secilen_sr_eksi %}{{ T.secilen_sr_eksi | n }}
bileşimde ızgaranın en iyi kombinasyonunun örneklem içi Sharpe'ı bile sıfır ya da eksi: açıklanacak bir artı yok.
Artı olan {{ T.secilen_sr_arti | n }} bileşimde{{? T.dsr_ust == 0 and T.dsr_gurultu_ust == 0 }}{% else %}Geri kalanında{% endif %} en iyi kombinasyonun örneklem içi
Sharpe'ı, denenen kombinasyon sayısının şansla üretebileceği en yüksek değerden ayırt edilemiyor: örneklem içinde iyi
görünen bir ayar, çoğu zaman yalnız en şanslı ayardır.{% else %}Bu
bileşimlerde seçimin örneklem içi üstünlüğü denenen kombinasyon sayısıyla açıklanamıyor; örneklem dışı sonuçları
seçim tablolarında.{% endif %}{% if T.kosul.ters_sinanan %} Koşul analizinde {% if T.kosul.ayirt %}gerçek seçim ters
seçimden daha sık tuttu, ama fark tek tek koşulları karar kuralı yapacak kadar büyük değil{% elif T.kosul.ters_ustun %}ters
seçim gerçek seçimden daha sık tuttu: örneklem içinde iyi görünen koşullar örneklem dışında daha sık kötü kovaya
döndü{% else %}gerçek seçim ters seçimden ayırt edilemedi{% endif %} (yukarıdaki bölüm).{% endif %}

{{! ay_sonu_ders }}

Bu sonuçlar bu kuralların bu biçimleri içindir: başka bir yürütme maliyeti (daha dar makas, likidite sağlayan emirler),
başka bir zaman dilimi, ya da kuralın bir parçası olarak gerçek bir haber beklentisi başka sonuç verebilir. Ölçülmeyen
şeylerin listesi metodoloji dersinde.

_Yatırım tavsiyesi değildir. Ölçülen her şey geçmişe aittir; geçmiş sonuçlar gelecekteki sonuçların göstergesi
değildir._
