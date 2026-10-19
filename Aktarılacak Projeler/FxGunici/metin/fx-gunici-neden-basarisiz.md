---
title: 'FX Gün İçi Stratejiler 9: Neden Başarısız Oluyorlar — Maliyet, Şans ve Kullanılabilmenin Şartları'
description: "Serinin {{ O.basarisiz.kapsam.kural | n }} kuralı maliyetten sonra neden kaybediyor ve bir gün içi kuralın kullanılabilir sayılması için neyin ölçülmüş olması gerekiyor: isabet ile başabaş isabeti, kaybın yön, zamanlama ve maliyet paylarına ayrışımı, R'nin ölçeği, bir örneklemden ötekine taşınan şey, şansın ve seçimin payı, sık önerilen kurtarma yolları, kuralın kaldırabildiği en yüksek maliyet, ay sonu fiksingi ve ileriye dönük bir sınamanın gücü."
pubDate: 2026-10-19
tags: ['fx', 'gun-ici', 'backtest', 'strateji', 'ders']
durum: 'arsiv'
kaynak: 'Dukascopy 1 dakikalık bid/ask (2018–2026) · önceden kayıt · akademik literatür'
ozet: "Kurallar kaybediyor, çünkü maliyetten önceki yön ve zamanlama bilgisi işlem başına yalnız {{ O.basarisiz.ayrisim.oos.ort.brut | r3 }} R ve ödenen maliyet {{ O.basarisiz.ayrisim.oos.ort.c | s3 }} R; bir örneklemden ötekine taşınan şey kenar değil, maliyetin büyüklüğü. Ders bunun nasıl ölçüldüğünü ve bir kuralın kullanılabilir sayılması için hangi üç şartın birlikte gerektiğini anlatır: kuralın kaldırabildiği maliyetin ödenen maliyetin üstünde olması, kenarın bir kaynağa dayanması ve bunun görülmemiş veride, gücü önceden hesaplanmış bir sınamayla gösterilmesi."
seviye: 'ileri'
onkosul:
  - fx-gunici-giris
  - fx-gunici-karsilastirma
  - fx-gunici-metodoloji
---

<div class="not gezinme"><span class="etiket">Arşiv</span> Bu ders gün içi FX kurallarının ayrıntılı sınamasındandır ve arşivdedir. Gün içi seri şimdi açılış, fiksing ve haber anlarının oyun planı olarak beş derste: [1 · İlk mumu okumak](/arastirma/fx-oyun-okuma/) · [2 · Açılışlar](/arastirma/fx-oyun-acilislar/) · [3 · Fiksingler](/arastirma/fx-oyun-fiksingler/) · [4 · Haber mumları](/arastirma/fx-oyun-haberler/) · [5 · Backtest](/arastirma/fx-oyun-backtest/).</div>

Önceki sekiz ders {{ O.basarisiz.kapsam.kural | n }} kuralı {{ O.basarisiz.kapsam.bilesim | n }} kural–parite
bileşiminde ölçtü. Önceden kayıtlı hüküm kuralına göre sonuç, serinin birincil penceresinde (2024 →)
{{ T.hukum_say.oos.calisiyor | n }} çalışıyor, {{ T.hukum_say.oos.zayif | n }} zayıf ve
{{ T.hukum_say.oos.calismiyor | n }} çalışmıyor; ön kaydın istediği bütün dönemde {{ T.hukum_say.tum.calisiyor | n }}
çalışıyor, {{ T.hukum_say.tum.zayif | n }} zayıf ve {{ T.hukum_say.tum.calismiyor | n }} çalışmıyor{{? T.hukum_say.oos.calisiyor == 0 }}{{? T.hukum_say.tum.calisiyor == 0 }}.
Bu ders iki soru sorar. Birincisi, kurallar neden kaybediyor? İkincisi, bir gün içi kuralın kullanılabilir sayılması
için neyin ölçülmüş olması gerekir? İkinci sorunun cevabı bir tavsiye değildir. Ölçülebilir şartlardan ve bir sınama
planından oluşur.

Kısa cevap üç parçadır. **Maliyet.** Maliyetten önceki yön ve zamanlama bilgisi işlem başına yalnız
{{ O.basarisiz.ayrisim.oos.ort.brut | r3 }} R ve sıfırdan ayırt edilemiyor; ödenen maliyet {{ O.basarisiz.ayrisim.oos.ort.c | s3 }}
R. Maliyetin {{ O.basarisiz.ayrisim.oos.ort.c_makas | s3 }} R'si verinin ölçülmüş bid/ask makası,
{{ O.basarisiz.ayrisim.oos.ort.c_kayma | s3 }} R'si modelin varsaydığı kaymadır: dolum başına
{{ K.temel_kayma_pip | s1 }} pip, haber penceresinde ek {{ K.haber_kayma_pip | s1 }} pip. Sayılar örneklem dışındaki
(2024 →) {{ O.basarisiz.ayrisim.oos.bilesim | n }} bileşimin ortalamasıdır: {{! kurallar O.basarisiz.ayrisim.oos.dislanan_kural }}
kuralının {{ O.basarisiz.ayrisim.oos.dislanan_n | n }} bileşimi dışarıda, çünkü örneklem dışında
{{ K.uygulama_esik.rastgele | n }} işlemden azı var{{? len(O.basarisiz.ayrisim.oos.dislanan_kural) == 1 }}. **Taşınma.** Bir örneklemden ötekine
taşınan şey kenar değil, maliyetin büyüklüğüdür: kuralların örneklem içi ve dışı sırası maliyette
{{ O.basarisiz.kenar.sira_havuz.maliyet.rho | s2 }}, brütte {{ O.basarisiz.kenar.sira_havuz.brut.rho | s2 }}
korelasyonla taşınıyor. **Şart.** Maliyeti düşürmek gerekli ama yeterli değil, belli bir akışa dayanmak da gerekli ama
yeterli değil. Serinin tek adayı ay sonu fiksingidir; dürüst sınaması görülmemiş veride ve gücü önceden hesaplanmış
bir planla yapılır. Bu seride o sınama yapılmadı.

Hükmün kaymaya duyarlılığı aynı yerde söylenmeli, çünkü maliyetin büyük kısmı bir varsayımdır. Örneklem dışında
{{ O.basarisiz.ayrisim.oos.duyarlilik.bilesim | n }} bileşimin yalnız makasla (kayma ve haber kayması sıfır)
{{ O.basarisiz.ayrisim.oos.duyarlilik.yalniz_makas | n }} tanesi, temel kayma sıfırken (haber kayması yerinde)
{{ O.basarisiz.ayrisim.oos.duyarlilik.kayma0 | n }} tanesi, temel senaryoda {{ O.basarisiz.ayrisim.oos.duyarlilik.temel | n }}
tanesi net artı. Bu {{ O.basarisiz.ayrisim.oos.duyarlilik.bilesim | n }} bileşimde ortalama maliyet içinde varsayılan
kaymanın payı {{ O.basarisiz.ayrisim.oos.duyarlilik.kayma_payi | yz0 }}{{? O.basarisiz.ayrisim.oos.duyarlilik.kayma_payi > 0.5 }}.
Kayma hiç olmasaydı da bileşimlerin çoğu eksi kalırdı{{? O.basarisiz.ayrisim.oos.duyarlilik.bilesim == 88 and O.basarisiz.ayrisim.oos.duyarlilik.yalniz_makas < 44 }};
yine de kaymanın gerçek büyüklüğü bu verinin ölçemediği bir şeydir (metodoloji dersi, "Ölçülmeyenler").

### Bu dersteki sayıların dört türü

Dersin sayıları dört türdendir ve her tablonun notu türünü yazar.

- **Hüküm.** Önceden kayıtlı kuralla, sonuç görülmeden yazılmış ölçütlerle verilen sonuç: "çalışıyor", "zayıf",
  "çalışmıyor". Bu derste yeni hüküm yoktur; hükümler karşılaştırma dersindekilerdir.
- **Betimleme.** Bu dersin yeni ölçüleri. İlk sonuçların görüldüğü an {{! ilk_sonuc_zaman }}; bu dersin bütün yeni
  sayıları o andan sonra, iki pencere de görülmüşken kuruldu. Hiçbiri bir hükmü değiştirmez. Görülmüş pencerede kurulan bir
  süzgeç, ayrıştırma ya da sıralama örneklem dışı sınama sayılmaz.
- **Literatür.** Yayımlanmış çalışmaların bulguları, kaynağıyla. Her biri kaynağın metnine karşı doğrulandı. Derginin
  kendi metni ya da özeti açılamadığında kullanılan sürüm (yazarın çalışma metni, kabul edilmiş metin, yayım öncesi
  sürüm, başka bir sürümün özeti, üçüncü taraf bir sitedeki kopya) kaynakçada künyenin yanında yazılıdır. Doğrulanamayan
  derse girmedi.
- **Hipotez.** Ölçülmemiş ama ölçülebilir bir iddia. Adıyla "hipotez" diye yazılır.

Ders üç kısımdır. Önce kuralların neden kaybettiği: beklentinin aritmetiği, kaybın ayrışımı ve ölçek. Sonra neden iyi
göründükleri: maliyetten önceki sonuç, şansın ve seçimin payı, geriye bakan grafiğin görünüşü. En sonda hangi şartla
kullanılabilecekleri: sık önerilen kurtarma yolları, kenarın kaynakları, yürütme, akış ve sınama şartları. Kapanışta
bir kontrol listesi var.

## Beklentinin aritmetiği

Bir kuralın işlem başına beklentisi üç sayıdan kurulur: isabet $p$ (sonucu artı işlemlerin payı; sıfır sonuç kayıp
sayılır), ortalama kazanç $\bar W$ ve ortalama kayıp $\bar L$ (eksi bir sayı). Hepsi R birimindedir:

$$
\begin{aligned}
E &= p\,\bar W + (1-p)\,\bar L \\
  &= (p - p^{*})\,\big(\bar W + |\bar L|\big), \\
p^{*} &= \frac{|\bar L|}{\bar W + |\bar L|}.
\end{aligned}
$$

$p^{*}$ **başabaş isabetidir**: isabet ona eşitse beklenti sıfırdır. İkinci yazım beklentiyi iki çarpana ayırır. Birinci
çarpan isabetin başabaşa uzaklığıdır ("açık"); işareti beklentinin işaretidir. İkinci çarpan kazanç ile kaybın
büyüklüklerinin toplamıdır ve bir puanlık isabetin değerini verir: $\partial E / \partial p = \bar W + |\bar L|$. İsabet
tek başına bir şey söylemez. Yüksek isabetli bir kural, kazançları küçükse başabaşın altında kalabilir; düşük isabetli
bir kural, kazançları büyükse üstünde kalabilir. Sorulacak soru "isabet kaç" değil, "isabet başabaşın ne kadar
üstünde" sorusudur.

Maliyet bu iki çarpana iki ayrı yoldan girer. Bir işlemin net sonucu, orta fiyattan orta fiyata ölçülen brüt
sonucundan maliyetin R karşılığı kadar küçüktür: $r = r_{\text{brüt}} - c/R$. Burada $c$ gidiş-dönüş maliyeti ve $R$
girişten stopa uzaklık, ikisi de pip cinsinden. Birinci yol başabaşı yükseltmektir: kazançlar $c/R$ kadar küçülür,
kayıplar o kadar büyür, $p^{*}$ yukarı çıkar. Bu derste bu farka $\Delta p^{*} = p^{*}_{\text{net}} - p^{*}_{\text{brüt}}$
denir. İkinci yol isabeti düşürmektir: orta fiyatta küçük bir artıyla kapanan işlem makastan sonra eksiye geçer. Bu fark
$\Delta p = p_{\text{brüt}} - p_{\text{net}}$ olarak yazılır. Açık iki yoldan birden küçülür:

$$
p - p^{*} = \big(p_{\text{brüt}} - p^{*}_{\text{brüt}}\big) - \Delta p^{*} - \Delta p .
$$

Maliyetin R karşılığı işlem işlem değişir, çünkü $R$ değişir. Ortalaması $c \cdot E[1/R]$ olur ve Jensen eşitsizliğinden
$E[1/R] \ge 1 / E[R]$ gelir. Bu yüzden riskleri farklı işlemlerden oluşan bir kuralda maliyeti ortalama riske göre
hesaplamak onu küçük gösterir: stopu dar işlemler maliyetin orantısız payını taşır. Bunun ölçülmüş hâli ölçek
bölümündedir.

Son bir teori notu, bu dersin geri kalanının arkasında durur. Orta fiyat bir martingalse, yani yarının beklenen fiyatı
bugünün fiyatıysa, sınırlı her durma kuralı için beklenen fiyat değişimi sıfırdır. Bu, Doob'un opsiyonel durma
teoremidir. Stop, hedef, zaman çıkışı ve iz süren stop bu teoreme göre brüt beklenti yaratmaz; yalnız isabet ile
kazanç–kayıp oranını başabaş eğrisi boyunca birbirine karşı takas eder. Simetrik bir rastgele yürüyüşte girişten
$+a$ uzaklıkta hedef ve $-b$ uzaklıkta stop varsa hedefe önce değme olasılığı $b/(a+b)$ olur. 1R hedef ve 1R stop yarı
yarıya kazanır, 2R hedef ve 1R stop üçte bir kazanır ve iki durumda da brüt beklenti sıfırdır. Bir çıkış kuralı
beklentiyi ancak fiyat martingal değilse değiştirir. O zaman da değişikliği yaratan çıkış kuralı değil, fiyatın
yapısıdır.

<div class="pratik">
  <span class="etiket">Pratik — beklentinin kuruluşu</span>

**Londra ORB.** Örneklem dışında dört paritenin {{ O.basarisiz.basabas.havuz.oos.orb.n | n }} işleminde isabet
{{ O.basarisiz.basabas.havuz.oos.orb.isabet | yz1 }}, ortalama kazanç {{ O.basarisiz.basabas.havuz.oos.orb.kazanc | r }} R,
ortalama kayıp {{ O.basarisiz.basabas.havuz.oos.orb.kayip | r }} R. Başabaş isabeti
$|\bar L| / (\bar W + |\bar L|)$ = {{ O.basarisiz.basabas.havuz.oos.orb.pstar | yz1 }}. Açık
{{ O.basarisiz.basabas.havuz.oos.orb.acik | pu }} puan; bunu kazanç ve kaybın toplamıyla
({{ O.basarisiz.basabas.havuz.oos.orb.toplam | s2 }} R) çarpınca işlem başına
{{ O.basarisiz.basabas.havuz.oos.orb.net | r3 }} R çıkar. Bu sayı kuralın ölçülmüş net beklentisinin ta kendisidir.
Kuralın sorunu isabetinin düşük olması değil, isabetinin başabaşın
{{! hesap carp O.basarisiz.basabas.havuz.oos.orb.acik -100 s1 }} puan altında kalmasıdır{{? O.basarisiz.basabas.havuz.oos.orb.acik < 0 }}.

**Fiksing momentumu.** Orta fiyattan bakıldığında bu kural başabaşın tam üstünde duruyor: brüt isabet
{{ O.basarisiz.basabas.havuz.oos.fiks_momentum.brut_isabet | yz1 }}, brüt başabaş
{{ O.basarisiz.basabas.havuz.oos.fiks_momentum.brut_pstar | yz1 }}. Maliyetten sonra isabet
{{ O.basarisiz.basabas.havuz.oos.fiks_momentum.isabet | yz1 }}, başabaş isabeti
{{ O.basarisiz.basabas.havuz.oos.fiks_momentum.pstar | yz1 }}. Açığın
{{! hesap carp O.basarisiz.basabas.havuz.oos.fiks_momentum.dp 100 s1 }} puanı isabetin düşmesinden,
{{! hesap carp O.basarisiz.basabas.havuz.oos.fiks_momentum.dpstar 100 s1 }} puanı başabaşın yükselmesinden
geliyor{{? O.basarisiz.basabas.havuz.oos.fiks_momentum.dp > 0 and O.basarisiz.basabas.havuz.oos.fiks_momentum.dpstar > 0 and O.basarisiz.basabas.havuz.oos.fiks_momentum.dp > O.basarisiz.basabas.havuz.oos.fiks_momentum.dpstar }}. İsabetin bu
kadar düşmesinin sebebi kuralın yapısı: işlem beş dakika sürer, ortalama hareket küçüktür ve işlemlerin büyük
bölümü orta fiyatta sıfıra yakın bir sonuçla kapanır. Bu işlemleri makas eksiye iter.

</div>

Aynı ölçü bütün kurallarda:

{{! neden_basabas }}

{{! sekil neden-basabas "İsabet başabaş isabetine ne kadar uzak — maliyetten önce ve sonra" }}

Örneklem dışında {{ O.basarisiz.basabas.ozet.oos.kural | n }} kuralın {{ O.basarisiz.basabas.ozet.oos.net_alti | n }}
tanesinde isabet başabaşın altında; açığın medyanı {{ O.basarisiz.basabas.ozet.oos.net_medyan | pu }} puan. Bu cümle
"{{ O.basarisiz.basabas.ozet.oos.net_alti | n }} kuralın net sonucu eksi" cümlesiyle aynı şeyi söyler, çünkü açığın
işareti beklentinin işaretidir. Bilgi sayımda değil açığın büyüklüğündedir. En küçük açık
{{ O.basarisiz.basabas.ozet.oos.en_kucuk | kisa }} kuralında, en büyüğü {{ O.basarisiz.basabas.ozet.oos.en_buyuk | kisa }}
kuralında. Orta fiyattan bakıldığında tablo başka bir şey söyler: aynı kuralların yalnız
{{ O.basarisiz.basabas.ozet.oos.brut_alti | n }} tanesi başabaşın altında ve brüt açığın medyanı
{{ O.basarisiz.basabas.ozet.oos.brut_medyan | pu }} puan. Maliyetsiz oyun yaklaşık adildir. Kayıp maliyetten doğar.
Bileşim düzeyinde de aynı: {{ O.basarisiz.basabas.bilesim.oos.n | n }} bileşimin
{{ O.basarisiz.basabas.bilesim.oos.alti | n }} tanesinde isabet başabaşın altında. Kalan bileşimler, tanım gereği,
örneklem dışında net sonucu artı olanlardır.

Maliyetin kendisi işlemden işleme az değişir. Örneklem dışındaki {{ O.basarisiz.basabas.maliyet_pip.n | n }}
varsayılan işlemde gidiş-dönüş maliyetinin medyanı {{ O.basarisiz.basabas.maliyet_pip.medyan | s1 }} pip; işlemlerin
onda biri {{ O.basarisiz.basabas.maliyet_pip.p10 | s2 }} pip'ten az, onda biri {{ O.basarisiz.basabas.maliyet_pip.p90 | s1 }}
pip'ten çok öder. Maliyetin R karşılığı ise işlemin riskine göre değişir: maliyetin R'si ile $1/R$ arasındaki
korelasyon {{ O.basarisiz.basabas.maliyet_pip.ilinti | s2 }} ve doğrunun eğimi
{{ O.basarisiz.basabas.maliyet_pip.egim | s2 }} pip. Bu eğim, serinin işlem başına etkin gidiş-dönüş maliyetidir.
İşlemlerin medyan riski {{ O.basarisiz.basabas.maliyet_pip.R_medyan | s1 }} pip; medyan maliyetin medyan riske
oranı {{! hesap bol O.basarisiz.basabas.maliyet_pip.medyan O.basarisiz.basabas.maliyet_pip.R_medyan yz0 }}.

Hesabın son parçası kaybın büyüklüğüdür. Kayıp 1 R'de durmaz. Kaydedilmiş bütün işlemlerde (her kuralın her paritedeki
varsayılanı ve seçileni, bütün dönem) sert stopla çıkan {{ O.basarisiz.basabas.stop_cikis.stop.n | n }} işlemin medyanı {{ O.basarisiz.basabas.stop_cikis.stop.medyan | r }} R
(en kötüsü {{ O.basarisiz.basabas.stop_cikis.stop.en_kotu | r }} R): stop emri tetiklenince makası ve kaymayı da öder.
Kapanış stopuyla çıkan {{ O.basarisiz.basabas.stop_cikis.kapanis_stop.n | n }} işlemde medyan
{{ O.basarisiz.basabas.stop_cikis.kapanis_stop.medyan | r }} R; −2 R'nin ötesinde kapananların payı
{{ O.basarisiz.basabas.stop_cikis.kapanis_stop.pay_2r | yz0 }}, çünkü stop yalnız mum kapanışında sorulur ve mum
stopun ötesinde kapanabilir. Boşlukla dolan stopta medyan
{{ O.basarisiz.basabas.stop_cikis.bosluk_stop.medyan | r }} R. Ortalama kayıp −1'in altına indikçe başabaş isabeti
yükselir; kuralın yazılı stopu ile ödenen kayıp aynı şey değildir.

**Alıştırma 1.** Asya aralığı kırılımının örneklem dışı havuzunda isabet
{{ O.basarisiz.basabas.havuz.oos.asya.isabet | yz1 }}, ortalama kazanç {{ O.basarisiz.basabas.havuz.oos.asya.kazanc | r }} R,
ortalama kayıp {{ O.basarisiz.basabas.havuz.oos.asya.kayip | r }} R. Başabaş isabeti, açık ve işlem başına beklenti
nedir? İsabet bir puan yüksek olsaydı beklenti ne kadar değişirdi?

<details>
<summary>Çözüm</summary>

Kazanç ile kaybın büyüklüklerinin toplamı {{ O.basarisiz.basabas.havuz.oos.asya.toplam | s2 }} R. Başabaş isabeti
kaybın büyüklüğünün bu toplama oranıdır: {{! hesap carp O.basarisiz.basabas.havuz.oos.asya.kayip -1 s2 }} /
{{ O.basarisiz.basabas.havuz.oos.asya.toplam | s2 }} = {{ O.basarisiz.basabas.havuz.oos.asya.pstar | yz1 }}
(yuvarlanmamış değerlerle). Açık {{ O.basarisiz.basabas.havuz.oos.asya.acik | pu }} puan. Beklenti açık ile
kazanç–kayıp toplamının çarpımıdır:
{{! hesap carp O.basarisiz.basabas.havuz.oos.asya.acik O.basarisiz.basabas.havuz.oos.asya.toplam r3 }} R
(yuvarlanmamış değerlerle); tablodaki ölçülmüş değer {{ O.basarisiz.basabas.havuz.oos.asya.net | r3 }} R.

Bir puanlık isabet beklentiye kazanç–kayıp toplamının yüzde birini ekler:
{{! hesap bol O.basarisiz.basabas.havuz.oos.asya.toplam 100 s3 }} R. Kuralın açığı kapanmak için
{{! hesap carp O.basarisiz.basabas.havuz.oos.asya.acik -100 s1 }} puanlık bir isabet artışı
ister{{? O.basarisiz.basabas.havuz.oos.asya.acik < 0 }}.

</details>

## Kaybın ayrışımı

Beklentinin aritmetiği kaybın ne kadar olduğunu söyler, nereden geldiğini söylemez. Bir işlemin net sonucunu üç parçaya
ayırmak mümkün: yönü doğru seçmenin payı, işlemin açıldığı ve kapandığı anların payı ve maliyet. Ayırmanın aracı **ayna
işlemdir**: gerçek işlemle aynı dakikada ters yönde açılan, stopu ve hedefi girişe aynı R uzaklığında duran, planlı
çıkışını aynı dakikada yapan işlem. Ayna, rastgele yön sınamasının ters yönlü yarısıdır (karşılaştırma dersi, "Yön mü,
zamanlama mı?").

Yön payına $y$, zamanlama payına $z$, maliyete $c$ denirse:

$$
\begin{aligned}
r &= y + z - c, \\
r_{\text{ayna}} &= -y + z - c, \\
y &= \tfrac{1}{2}\,\big(r - r_{\text{ayna}}\big), \\
z &= \tfrac{1}{2}\,\big(r + r_{\text{ayna}}\big) + c .
\end{aligned}
$$

$y$, yön değişince işaret değiştiren kısımdır: kural yönü yazı turadan iyi seçiyorsa artıdır. $z$, iki yönde de aynı
kalan brüt kısımdır: girişin ve çıkışın zamanlaması, stop ile hedefin fiyatın yoluna verdiği tepki. Stopu ve hedefi
olmayan, yalnız zamanla çıkan bir kuralda aynanın brüt sonucu gerçek işleminkinin tam tersidir ve $z$ sıfırdır. $c$
makas ile kaymadır. İki payın toplamı $y + z$ işlemin orta fiyattan ölçülen brüt sonucudur.

Ayrışım bir varsayımla kurulur: aynanın maliyeti gerçek işleminkine eşit sayılır. Hedefli kurallarda bu tam doğru
değildir. Gerçek işlemin stopu bir piyasa emridir ve kayma öder; aynanın aynı seviyedeki çıkışı bir hedef emridir ve
ödemez. O fark $z$'nin içine karışır. Bu yüzden $z$ bir kenar ölçüsü gibi okunmaz; ayrışımın asıl bilgisi $y$ ile
$c$'nin kıyasıdır. Ayrışımın bir iç tutarlılık sınaması da var: rastgele yön dağılımının ortalaması tanım gereği gerçek
işlem ile aynanın ortalamasıdır ve ölçülen en büyük fark {{ O.basarisiz.ayrisim.oos.ic_tutarlilik | s4 }} R. Ayna,
örneklem dışında en az {{ K.uygulama_esik.rastgele | n }} işlemi olan
{{ O.basarisiz.ayrisim.oos.bilesim | n }} bileşimde kuruldu; kurulamayanlar tablonun notunda.

Örneklem dışında {{ O.basarisiz.ayrisim.oos.bilesim | n }} bileşimin ortalaması: yön payı
{{ O.basarisiz.ayrisim.oos.ort.y | r3 }} R, zamanlama payı {{ O.basarisiz.ayrisim.oos.ort.z | r3 }} R, maliyet
{{ O.basarisiz.ayrisim.oos.ort.c | s3 }} R. Yön ile zamanlama birlikte {{ O.basarisiz.ayrisim.oos.ort.brut | r3 }} R
ediyor: dersin başında "maliyetten önceki yön ve zamanlama bilgisi" denen sayı budur. Maliyetin
{{ O.basarisiz.ayrisim.oos.ort.c_makas | s3 }} R'si makas, {{ O.basarisiz.ayrisim.oos.ort.c_kayma | s3 }} R'si kayma;
pip olarak {{ O.basarisiz.ayrisim.oos.ort.c_makas_pip | s2 }} ve {{ O.basarisiz.ayrisim.oos.ort.c_kayma_pip | s2 }},
toplam {{ O.basarisiz.ayrisim.oos.ort.c_pip | s2 }} pip. Medyanlar aynı tabloyu verir: yön payı
{{ O.basarisiz.ayrisim.oos.medyan.y | r3 }}, zamanlama payı {{ O.basarisiz.ayrisim.oos.medyan.z | ra }}, maliyet
{{ O.basarisiz.ayrisim.oos.medyan.c | s3 }} R.

Yön payının maliyetten büyük olduğu bileşim yalnız {{ O.basarisiz.ayrisim.oos.y_c | n }}. Yön ile zamanlama birlikte
maliyeti {{ O.basarisiz.ayrisim.oos.yz_c | n }} bileşimde aşıyor ve bu sayı, aynası kurulan
{{ O.basarisiz.ayrisim.oos.bilesim | n }} bileşim içinde örneklem dışında net sonucu artı olanların
sayısıdır{{? O.basarisiz.ayrisim.oos.yz_c == O.basarisiz.ayrisim.oos.net_arti }}, çünkü $y + z - c$ net sonucun
kendisidir. Aynası kurulamayan {{ O.basarisiz.ayrisim.oos.dislanan_n | n }} bileşimin
{{ O.basarisiz.ayrisim.oos.dislanan_net_arti | n }} tanesi de net artı; dersin başındaki temel senaryonun
{{ O.basarisiz.ayrisim.oos.duyarlilik.temel | n }} net artı bileşimi bu ikisinin
toplamıdır{{? O.basarisiz.ayrisim.oos.yz_c == O.basarisiz.ayrisim.oos.net_arti and O.basarisiz.ayrisim.oos.net_arti_toplam == O.basarisiz.ayrisim.oos.duyarlilik.temel }}.

Ayna da kaybediyor. {{ O.basarisiz.ayrisim.oos.bilesim | n }} bileşimin {{ O.basarisiz.ayrisim.oos.ayna_eksi | n }}
tanesinde aynanın sonucu eksi ve {{ O.basarisiz.ayrisim.oos.birlikte_eksi | n }} tanesinde gerçek işlem ile ayna
birlikte eksi; {% if O.basarisiz.ayrisim.tum.ayna_eksi == O.basarisiz.ayrisim.tum.bilesim %}bütün dönemde
{{ O.basarisiz.ayrisim.tum.bilesim | n }} bileşimin hepsinde aynanın sonucu eksi{% else %}bütün dönemde
{{ O.basarisiz.ayrisim.tum.bilesim | n }} bileşimin {{ O.basarisiz.ayrisim.tum.ayna_eksi | n }} tanesinde aynanın
sonucu eksi{% endif %}. Sebep aritmetiktir: ayna aynı maliyeti öder ve yön payının işaretini çevirir, yani
$r_{\text{ayna}} = r - 2y$. Yön payı küçük olduğu için kuralın tersi de kuralın kendisi gibi maliyete kaybeder; yön payı
artı olan bir kuralda tersi daha da kötüdür.

{{! neden_ayrisim }}

{{! sekil neden-anatomi "Kaybın anatomisi — yön, zamanlama ve maliyet" }}

Tablo kural kural aynı şeyi söylüyor: yön ile zamanlama paylarının toplamı hiçbir kuralda maliyete
ulaşmıyor{{? O.basarisiz.basabas.ozet.oos.net_alti == O.basarisiz.basabas.ozet.oos.kural }}. {{! neden_yon_cumle }} Bu bir
betimlemedir, aile hükmü değil: her kuralın yön payı kendi tablosunda, kendi aralığıyla okunur ve en büyüğü bile
maliyeti karşılamıyor.

İki haber kuralı bu ayrışımın ders kitabı örneğidir. N1 ilk haber mumunun yönünde girer, N2 tersine (yalnız büyük ilk
hareketlerde ve bir teyit mumundan sonra). Örneklem dışında N1'in yön payı {{ O.basarisiz.ayrisim.oos.kural.n1.y | r3 }} R,
N2'ninki {{ O.basarisiz.ayrisim.oos.kural.n2.y | r3 }} R: ilk mumun yönü bu pencerede devam etmekten çok geri döndü.
Bütün dönemde işaretler aynı (N1 {{ O.basarisiz.ayrisim.tum.kural.n1.y | r3 }}, N2 {{ O.basarisiz.ayrisim.tum.kural.n2.y | r3 }} R),
ve iki pencerede de N2'nin artı yön payı kendi maliyetinin altında kalıyor{{? O.basarisiz.ayrisim.oos.kural.n1.y < 0 and O.basarisiz.ayrisim.oos.kural.n2.y > 0 and O.basarisiz.ayrisim.tum.kural.n1.y < 0 and O.basarisiz.ayrisim.tum.kural.n2.y > 0 and O.basarisiz.ayrisim.oos.kural.n2.y < O.basarisiz.ayrisim.oos.kural.n2.c and O.basarisiz.ayrisim.tum.kural.n2.y < O.basarisiz.ayrisim.tum.kural.n2.c }}.
Bu pencerede haberin ilk dakikalarının tersine girmek doğru yönü seçmekti, ama o yönün değeri yine maliyete yetmedi.

Yön payının değerli olup olmadığını rastgele yön sınaması da ayrıca söylüyor (karşılaştırma dersi).
{{! neden_rastgele }}

**Alıştırma 2.** Londra ORB'nin örneklem dışı havuzunda (dört paritenin işlemleri, işlem sayısıyla ağırlıklı) net sonuç
{{ O.basarisiz.ayrisim.oos.kural.orb.net | r3 }} R, aynanın sonucu {{ O.basarisiz.ayrisim.oos.kural.orb.ayna | r3 }} R ve
maliyet {{ O.basarisiz.ayrisim.oos.kural.orb.c | s3 }} R. Yön ve zamanlama paylarını bulun. Kuralı tersine çevirmek
(her işlemde ters yönde girmek) işlem başına ne verirdi?

<details>
<summary>Çözüm</summary>

Yön payı net ile aynanın farkının yarısıdır: ({{ O.basarisiz.ayrisim.oos.kural.orb.net | r3 }} −
({{ O.basarisiz.ayrisim.oos.kural.orb.ayna | r3 }})) / 2 = {{ O.basarisiz.ayrisim.oos.kural.orb.y | r3 }} R. Zamanlama
payı ikisinin ortalamasına maliyetin eklenmesidir: ({{ O.basarisiz.ayrisim.oos.kural.orb.net | r3 }} +
({{ O.basarisiz.ayrisim.oos.kural.orb.ayna | r3 }})) / 2 + {{ O.basarisiz.ayrisim.oos.kural.orb.c | s3 }} =
{{ O.basarisiz.ayrisim.oos.kural.orb.z | r3 }} R. Kuralı tersine çevirmek aynanın kendisidir:
{{ O.basarisiz.ayrisim.oos.kural.orb.ayna | r3 }} R. Kuralın kendisinden de kötü, çünkü yön payı artı ve ters çevrilince
iki kez kaybedilir: $r - 2y${{? O.basarisiz.ayrisim.oos.kural.orb.y > 0 and O.basarisiz.ayrisim.oos.kural.orb.ayna < O.basarisiz.ayrisim.oos.kural.orb.net }}.

</details>

## Ölçek: maliyet R içinde ne kadar yer tutar

Maliyet pip cinsinden ödenir, sonuç R cinsinden ölçülür. Bir işlemin maliyetinin R karşılığı
$c_R = c_{\text{pip}} / R_{\text{pip}}$'dir: aynı makas, stopu yakın bir işlemde riskin büyük, stopu uzak bir işlemde
küçük bir payıdır. Risk büyüdükçe $c_R$ sıfıra yaklaşır. Bunun pratik anlamı pozisyon büyüklüğündedir: her işlemde
hesap para birimi cinsinden aynı risk alınırsa (1 R sabit), stopu iki kat uzak bir işlem yarım nominalle açılır ve
makas para olarak yarıya iner. Sorulacak soru, riski büyüyen işlemlerin brüt sonucunun da aynı oranda korunup
korunmadığıdır.

Her bileşimin işlemleri kendi içinde riske göre üçe bölündü (dar, orta, geniş):

<div class="sayi-tablo">

| Üçte bir | Medyan risk (pip) | Brüt | Maliyet | Net | Maliyet (pip) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Dar | {{ O.basarisiz.olcek.ucte_bir.oos.R[0] | s1 }} | {{ O.basarisiz.olcek.ucte_bir.oos.brut[0] | r3 }} | {{ O.basarisiz.olcek.ucte_bir.oos.maliyet[0] | s3 }} | {{ O.basarisiz.olcek.ucte_bir.oos.net[0] | r3 }} | {{ O.basarisiz.olcek.ucte_bir.oos.maliyet_pip[0] | s2 }} |
| Orta | {{ O.basarisiz.olcek.ucte_bir.oos.R[1] | s1 }} | {{ O.basarisiz.olcek.ucte_bir.oos.brut[1] | r3 }} | {{ O.basarisiz.olcek.ucte_bir.oos.maliyet[1] | s3 }} | {{ O.basarisiz.olcek.ucte_bir.oos.net[1] | r3 }} | {{ O.basarisiz.olcek.ucte_bir.oos.maliyet_pip[1] | s2 }} |
| Geniş | {{ O.basarisiz.olcek.ucte_bir.oos.R[2] | s1 }} | {{ O.basarisiz.olcek.ucte_bir.oos.brut[2] | r3 }} | {{ O.basarisiz.olcek.ucte_bir.oos.maliyet[2] | s3 }} | {{ O.basarisiz.olcek.ucte_bir.oos.net[2] | r3 }} | {{ O.basarisiz.olcek.ucte_bir.oos.maliyet_pip[2] | s2 }} |

</div>

_Tür: betimleme. Örneklem dışı (2024 →), önceden kayıtlı varsayılanlar; R / işlem, hücre bileşimlerin medyanı. Her
bileşimin işlemleri riske (stop uzaklığının pip karşılığı) göre sıralanıp üçe bölündü; bileşimde en az
{{ O.basarisiz.olcek.ucte_bir.oos.asgari | n }} işlem ({{ O.basarisiz.olcek.ucte_bir.oos.bilesim | n }} bileşim). Dilim
sınırları pencerenin kendi işlemlerinden alındı ve işlem açılırken bilinmez: tablo bir süzgeç değil, maliyetin nerede
yoğunlaştığının betimlemesidir. Hücreler medyan olduğu için toplanmaz: Net sütunu Brüt eksi Maliyet değildir._

Net sonuç geniş üçte birde dar üçte birden iyi: {{ O.basarisiz.olcek.ucte_bir.oos.bilesim | n }} bileşimin
{{ O.basarisiz.olcek.ucte_bir.oos.genis_dar_net | n }} tanesinde. Maliyetin R karşılığı geniş üçte birde hiçbir bileşimde
dardan büyük değil{{? O.basarisiz.olcek.ucte_bir.oos.genis_dar_maliyet == 0 }}, oysa pip cinsinden maliyet üç dilimde
neredeyse aynı. Brütte tablo tersine döner: geniş üçte birin brüt sonucu dar üçte birinkini yalnız
{{ O.basarisiz.olcek.ucte_bir.oos.genis_dar_brut | n }} bileşimde aşıyor{{? O.basarisiz.olcek.ucte_bir.oos.bilesim == 84 and O.basarisiz.olcek.ucte_bir.oos.genis_dar_brut < 42 }}.
Net sonucu iyileştiren şey riski büyük işlemlerin daha iyi bir yön ya da zamanlama taşıması değil; aynı makasın daha
büyük bir riske bölünmesidir. Bütün dönemde ({{ O.basarisiz.olcek.ucte_bir.tum.bilesim | n }} bileşim) aynı sayımlar
{{ O.basarisiz.olcek.ucte_bir.tum.genis_dar_net | n }} (net), {{ O.basarisiz.olcek.ucte_bir.tum.genis_dar_brut | n }}
(brüt) ve {{ O.basarisiz.olcek.ucte_bir.tum.genis_dar_maliyet | n }} (maliyet).

Aynı soru parametre ızgarasında da sorulabilir: öbür bütün parametreleri aynı kalıp yalnız bir parametresi değişen
kombinasyon çiftleri (iki ucunda da örneklem dışında en az {{ O.basarisiz.olcek.izgara_asgari | n }} işlem). Zaman dilimi 5
dakikadan 60 dakikaya çıkan {{ O.basarisiz.olcek.tf_5_60.oos.grup | n }} çiftte örneklem dışı net R çiftlerin
{{ O.basarisiz.olcek.tf_5_60.oos.r_arti | yz0 }} kadarında artıyor (medyan fark {{ O.basarisiz.olcek.tf_5_60.oos.r_medyan | r3 }} R),
işlem başına net pip ise yalnız {{ O.basarisiz.olcek.tf_5_60.oos.pip_arti | yz0 }} kadarında (medyan fark
{{ O.basarisiz.olcek.tf_5_60.oos.pip_medyan | r }} pip). Stopun aralığın ortasından karşı ucuna taşındığı
{{ O.basarisiz.olcek.stop_orta_karsi.oos.grup | n }} çiftte aynı tablo: net R çiftlerin
{{ O.basarisiz.olcek.stop_orta_karsi.oos.r_arti | yz0 }} kadarında, net pip {{ O.basarisiz.olcek.stop_orta_karsi.oos.pip_arti | yz0 }}
kadarında artıyor. Daha geniş bir mum ya da daha uzak bir stop R'yi büyütür, maliyetin R'deki payını küçültür; işlem
başına kazanılan pip ise yazı tura gibi davranır. Izgaranın bütün satırlarında örneklem dışı net R'nin medyanı 5
dakikalık mumlarda {{ O.basarisiz.olcek.tf_medyan.oos.5 | r3 }}, 15 dakikalıkta {{ O.basarisiz.olcek.tf_medyan.oos.15 | r3 }},
60 dakikalıkta {{ O.basarisiz.olcek.tf_medyan.oos.60 | r3 }} R: hepsi eksi ve mum büyüdükçe sıfıra yaklaşıyor{{? O.basarisiz.olcek.tf_medyan.oos.60 < 0 and O.basarisiz.olcek.tf_medyan.oos.5 < O.basarisiz.olcek.tf_medyan.oos.15 and O.basarisiz.olcek.tf_medyan.oos.15 < O.basarisiz.olcek.tf_medyan.oos.60 }}.

{{! sekil neden-olcek "Ölçek — R büyüdükçe maliyetin payı küçülür, brüt büyümez" }}

Çıkış kuralı da aynı hesabın içindedir. Izgarada yalnız hedef türünün değiştiği (1R, 2R, zaman ya da gün sonu)
{{ O.basarisiz.olcek.hedef.oos.grup | n }} grupta isabet, grubun içinde medyanda
{{! hesap carp O.basarisiz.olcek.hedef.oos.isabet_aralik 100 s1 }} puanlık bir aralıkta oynuyor; net R ise yalnız
{{ O.basarisiz.olcek.hedef.oos.r_aralik | s3 }} R'lik bir aralıkta (grupların onda birinde aralık
{{ O.basarisiz.olcek.hedef.oos.r_aralik_p90 | s2 }} R'yi aşıyor). Londra ORB'nin EUR/USD ızgarasında örneklem içinde 1R
hedefli {{ O.basarisiz.olcek.orb_eurusd_hedef.1R.kombinasyon | n }} kombinasyonun isabeti ortalama
{{ O.basarisiz.olcek.orb_eurusd_hedef.1R.isabet | yz1 }}, 2R hedeflilerin {{ O.basarisiz.olcek.orb_eurusd_hedef.2R.isabet | yz1 }},
gün sonunda çıkanların {{ O.basarisiz.olcek.orb_eurusd_hedef.gun_sonu.isabet | yz1 }}; net R sırasıyla
{{ O.basarisiz.olcek.orb_eurusd_hedef.1R.net | r3 }}, {{ O.basarisiz.olcek.orb_eurusd_hedef.2R.net | r3 }} ve
{{ O.basarisiz.olcek.orb_eurusd_hedef.gun_sonu.net | r3 }}. Beklentinin aritmetiğindeki teorem ölçülmüş hâliyle: çıkış
kuralı isabet ile kazanç–kayıp oranını birbirine karşı takas eder ve beklentiyi isabetten çok daha az oynatır. Stop
kuralları üzerine literatürün sonucu bu teoremle çelişmez, ama koşuluyla okunmalıdır. Kaminski ve Lo (2014) stopu,
birikimli zarar bir eşiğe ulaşınca portföyün maruziyetini azaltan bir politika olarak tanımlar: getiriler bağımsız ve
aynı dağılımlıysa stopun beklenen getiriye katkısı her zaman eksidir, çünkü portföyü zaman zaman daha yüksek getirili
varlıktan çıkarır; getirilerde süreklilik (momentum) varsa artı olabilir. Sürüklenmesiz bir fiyatta vazgeçilen getiri
sıfırdır ve teoremin söylediği de budur. Bu bölüm bir süzgeç önermez. Geniş stop ya da büyük mum maliyetin R içindeki
payını küçültür, kuralın kenarını değiştirmez.

## Kenar var mıydı

Maliyet her bileşimde aynı yönde çalışıyor; öyleyse kalan soru, maliyetten önce bir kenar olup olmadığıdır. Bunun üç
ölçüsü var: brüt sonucun anlamlılığı, bileşimler arası farkların ne kadarının gerçek olduğu ve örneklem içinin örneklem
dışını ne kadar öngördüğü.

**Anlamlılık.** Kenarsız bir dünyada bileşim başına brüt ortalamanın t istatistiği yaklaşık standart normal dağılır:
ortalaması sıfır, standart sapması bir, mutlak değeri {{= "1,96" }}'yı aşanlar yüzde beş. Örneklem dışında
{{ O.basarisiz.kenar.t_oos.bilesim | n }} bileşimde t'nin ortalaması {{ O.basarisiz.kenar.t_oos.ort | s2 }}, standart
sapması {{ O.basarisiz.kenar.t_oos.sd | s2 }}; mutlak değeri bu sınırı aşan bileşim
{{ O.basarisiz.kenar.t_oos.mutlak_196 | n }} (şansın beklediği {{ O.basarisiz.kenar.t_oos.sans_mutlak | s1 }}), brüt sonucu
artı olan bileşim {{ O.basarisiz.kenar.t_oos.brut_arti | n }} (yazı tura sınaması p
{{ O.basarisiz.kenar.t_oos.binom_p | p }}). Örneklem içinde aynı ölçüler daha iyi görünür: ortalama
{{ O.basarisiz.kenar.t_is.ort | s2 }}, standart sapma {{ O.basarisiz.kenar.t_is.sd | s2 }}, sınırı aşan
{{ O.basarisiz.kenar.t_is.mutlak_196 | n }} bileşim, brütü artı {{ O.basarisiz.kenar.t_is.brut_arti | n }} (p
{{ O.basarisiz.kenar.t_is.binom_p | p }}). Bileşimler aynı günleri paylaştığı için bu p değerleri bilgi içindir.

**Güvenilirlik.** Bileşimlerin brüt ortalamaları birbirinden farklıdır; ama bu farkın bir kısmı yalnız örnekleme
gürültüsüdür. Gözlenen yayılımın varyansından ortalama örnekleme varyansı çıkarılınca kalan pay, farkların gerçek olan
kısmıdır:

$$
\begin{aligned}
\rho &= \frac{\operatorname{Var}(\hat x) - \overline{\mathrm{SE}^2}}{\operatorname{Var}(\hat x)}, \\
E\big[x_{\text{dışı}} \mid \hat x_{\text{içi}}\big] &\approx \mu + \rho\,\big(\hat x_{\text{içi}} - \mu\big).
\end{aligned}
$$

İkinci ifade büzülmedir: örneklem içinde ortalamadan uzak görünen bir bileşimin gelecekteki beklentisi, aradaki farkın
yalnız $\rho$ kadarını taşır. Örneklem dışında en az {{ K.uygulama_esik.rastgele | n }} işlemi olan
{{ O.basarisiz.kenar.egim.bilesim | n }} bileşimde güvenilirlik örneklem içinde {{ O.basarisiz.kenar.guvenilirlik.is | s2 }},
örneklem dışında {{ O.basarisiz.kenar.guvenilirlik.oos | s2 }}. Bütün bileşimler alınınca örneklem dışı tahmin eksiye
düşüyor ({{ O.basarisiz.kenar.guvenilirlik.oos_hepsi | s2 }}); güvenilirlik eksi olamayacağı için bu sıfır okunur: o
pencerede bileşimler arası brüt farkların tamamı örnekleme gürültüsünden ayırt edilemiyor.

**Taşınma.** Örneklem içinin brüt sonucu örneklem dışınınkini ne kadar öngörüyor? Aynı bileşimlerde kesit eğimi
{{ O.basarisiz.kenar.egim.brut | s2 }} (sağlam bir eğim tahmini olan Theil–Sen ile {{ O.basarisiz.kenar.egim.theil_sen | s2 }},
aralığı {{ O.basarisiz.kenar.egim.theil_sen_alt | s2 }} / {{ O.basarisiz.kenar.egim.theil_sen_ust | s2 }}; korelasyon
{{ O.basarisiz.kenar.egim.pearson | s2 }}, p {{ O.basarisiz.kenar.egim.pearson_p | p }}): örneklem içinde bir R'lik brüt
fark örneklem dışında, iki tahmine göre onda bir ile dörtte bir R arasına iniyor ve Theil–Sen aralığı sıfırı
kapsıyor{{? O.basarisiz.kenar.egim.brut > 0.05 and O.basarisiz.kenar.egim.brut < 0.15 and O.basarisiz.kenar.egim.theil_sen > 0.2 and O.basarisiz.kenar.egim.theil_sen < 0.35 and O.basarisiz.kenar.egim.theil_sen_alt < 0 }}.
Bütün bileşimlerde eğim {{ O.basarisiz.kenar.egim.brut_hepsi | s2 }}; farkı dışarıda kalan dört
bileşim yaratıyor{{? len(O.basarisiz.kenar.dislanan) == 4 }} (örneklem dışında az işlem, büyük sonuç). Aynı ölçü maliyette
{{ O.basarisiz.kenar.egim.maliyet | s2 }}: maliyet örneklemden örnekleme neredeyse birebir taşınıyor.

Sıralar aynı şeyi söylüyor. {{ O.basarisiz.kapsam.kural | n }} kuralın örneklem içi ve dışı sırası (Spearman) netle
{{ O.basarisiz.kenar.sira_havuz.net.rho | s2 }}, maliyetle {{ O.basarisiz.kenar.sira_havuz.maliyet.rho | s2 }}, brütle
{{ O.basarisiz.kenar.sira_havuz.brut.rho | s2 }} (p {{ O.basarisiz.kenar.sira_havuz.brut.p | p }}) korelasyonla
taşınıyor. Bileşim düzeyinde (aynı {{ O.basarisiz.kenar.egim.bilesim | n }} bileşim) netle
{{ O.basarisiz.kenar.sira_bilesim.net | s2 }}, maliyetle {{ O.basarisiz.kenar.sira_bilesim.maliyet | s2 }}, brütle
{{ O.basarisiz.kenar.sira_bilesim.brut | s2 }} (p {{ O.basarisiz.kenar.sira_bilesim_p.brut | p }}), isabetle
{{ O.basarisiz.kenar.sira_bilesim.isabet | s2 }}. {% if O.basarisiz.kenar.sira_bilesim_hepsi.brut.p < 0.05 %}Dışarıda kalan
dört bileşim de katılınca brütle {{ O.basarisiz.kenar.sira_bilesim_hepsi.brut.rho | s2 }} (p
{{ O.basarisiz.kenar.sira_bilesim_hepsi.brut.p | p }}): bu küçük anlamlılığı, eğimde olduğu gibi, az işlemle büyük sonuç
veren o dört bileşim yaratıyor{{? len(O.basarisiz.kenar.dislanan) == 4 }}.{% else %}Dışarıda kalan dört bileşim de katılınca brütle
{{ O.basarisiz.kenar.sira_bilesim_hepsi.brut.rho | s2 }} (p {{ O.basarisiz.kenar.sira_bilesim_hepsi.brut.p | p }}){{? len(O.basarisiz.kenar.dislanan) == 4 }}.{% endif %} Yıldan yıla ({{ O.basarisiz.kenar.sira_yil.net.cift | n }} ardışık yıl
çiftinin medyanı) netle {{ O.basarisiz.kenar.sira_yil.net.medyan | s2 }}, maliyetle
{{ O.basarisiz.kenar.sira_yil.maliyet.medyan | s2 }}, brütle {{ O.basarisiz.kenar.sira_yil.brut.medyan | s2 }}. İsabetin
sırası taşınıyor, çünkü isabeti büyük ölçüde maliyet ve kuralın iskeleti belirler (beklentinin aritmetiği). Kuralların
net sırası da taşınıyor ama sebebi kenar değil: ucuz kural ucuz kalıyor. Net sonucun kurallar arası varyansında
maliyetin payı {{ O.basarisiz.kenar.varyans.oos.maliyet | yz0 }}, brütün payı {{ O.basarisiz.kenar.varyans.oos.brut | yz0 }}
(örneklem dışı; bütün dönemde {{ O.basarisiz.kenar.varyans.tum.maliyet | yz0 }} ve
{{ O.basarisiz.kenar.varyans.tum.brut | yz0 }}; iki payın ortak kısmı eşit bölündü).

{{! sekil neden-kenar "Örneklemden örnekleme ne taşındı — maliyet evet, brüt hayır" }}

**Bütün dönemde görünen, örneklem dışında görünmeyen.** Önceden kayıtlı bootstrap aralığı brütte sıfırın üstünde kalan
bileşim bütün dönemde {{ O.basarisiz.kenar.brut_aralik.tum.brut_alt_arti | n }}; kenarsız bir dünyada beklenen
{{ O.basarisiz.kenar.brut_aralik.tum.sans | s1 }}. Bunların {{ O.basarisiz.kenar.brut_aralik.tum.net_eksi | n }} tanesinde
net sonuç eksi, ve aynı ölçüyü örneklem dışında geçen bileşim {{ O.basarisiz.kenar.brut_aralik.oos.brut_alt_arti | n }}.
Bu iki sayı birlikte okunmalı: örneklem dışı pencere kısa. İşlem başına
{{ O.basarisiz.kenar.guc_ornek.kenar | r }} R'lik gerçek bir brüt kenar bile 2024 → penceresinde aralığı sıfırın
üstüne ancak {{ O.basarisiz.kenar.guc_ornek.olasilik | s2 }} olasılıkla taşır. Örneklem dışında tek bileşimin geçmesi
kenarın yokluğunun kanıtı değildir; kalıcılığının gösterilemediğinin kanıtıdır.

Yıllara bölünce de aynı tablo çıkıyor. Bileşim × yıl hücrelerinde ({{ O.basarisiz.kenar.yil.hucre | n }} hücre,
{{ O.basarisiz.kenar.yil.ilk | yil }}–{{ O.basarisiz.kenar.yil.son | yil }}) net sonucu artı olan hücrelerin payı
{{ O.basarisiz.kenar.yil.net_arti | yz1 }}; {{ O.basarisiz.kenar.yil.hic_arti | n }} bileşimin hiçbir yılı artı değil ve en
iyi bileşim {{ O.basarisiz.kenar.yil.yil | n }} yılın {{ O.basarisiz.kenar.yil.en_cok_arti | n }} tanesinde artı. Brütte
hücrelerin {{ O.basarisiz.kenar.yil.brut_arti | yz1 }} kadarı artı. {{ O.basarisiz.kenar.yil.yil | n }} yılın en az
{{ O.basarisiz.kenar.yil.esik | n }} tanesinde brütü artı olan bileşim {{ O.basarisiz.kenar.yil.brut_yedi | n }}; yıllar
birbirinden bağımsız olsaydı, hücrelerin bu brüt artı payıyla beklenen {{ O.basarisiz.kenar.yil.beklenen_gozlenen | s1 }}.
Brütü yıldan yıla taşıyan bir yapı görünmüyor.

**Örneklem içinde anlamlı olanlar.** Örneklem içinde brüt t'si {{= "1,96" }}'yı aşan
{{ O.basarisiz.kenar.is_anlamli.bilesim | n }} bileşimin brüt ortalaması örneklem içinde
{{ O.basarisiz.kenar.is_anlamli.is | r3 }}, örneklem dışında {{ O.basarisiz.kenar.is_anlamli.oos | r3 }} R: küçülme
{{ O.basarisiz.kenar.is_anlamli.kuculme | yz0 }}. {{ O.basarisiz.kenar.is_anlamli.isaret | n }} tanesi işaretini koruyor,
{% if O.basarisiz.kenar.is_anlamli.net_arti == 0 %}hiçbiri örneklem dışında net artı değil{% else %}{{ O.basarisiz.kenar.is_anlamli.net_arti | n }}
tanesi örneklem dışında net artı{% endif %}. Güvenilirlikten kurulan büzülme bu küçülmeyi önceden söylüyordu: öngörü
{{ O.basarisiz.kenar.is_anlamli.ongoru | r3 }} R, ölçülen {{ O.basarisiz.kenar.is_anlamli.oos | r3 }} R, aradaki fark
ölçünün standart hatasıyla ({{ O.basarisiz.kenar.is_anlamli.oos_se | s3 }}) ayırt edilemiyor{{? abs(O.basarisiz.kenar.is_anlamli.ongoru_z) < 2 }}.
Çok sayıda tahminin en büyükleri gerçek değerlerini büyük olasılıkla abartır (seçim yanlılığı ya da ortalamaya dönüş;
Efron, 2011); seçilmiş bir sonucun gelecekte ortalamaya doğru dönmesi bir talihsizlik değil, seçimin aritmetiğidir.

Sıralamanın başı da aynı dersi verir. Örneklem dışında işlem başına net sonucu en az eksi olan kural
{{ O.basarisiz.tek_gun.birim | kisa }}: {{ O.basarisiz.tek_gun.n | n }} işlemle {{ O.basarisiz.tek_gun.net | r3 }} R
({{ O.basarisiz.tek_gun.kural | n }} kural içinde {{ O.basarisiz.tek_gun.sira | n }}. sırada{{? O.basarisiz.tek_gun.sira == 1 }}).
Bu sonucun büyük kısmı tek bir günden geliyor: {{ O.basarisiz.tek_gun.gun | tarih_uzun }} günü kuralın iki işlemi
{{ O.basarisiz.tek_gun.islem[0].cift | parite }}'de {{ O.basarisiz.tek_gun.islem[0].r | r }} R ve
{{ O.basarisiz.tek_gun.islem[1].cift | parite }}'de {{ O.basarisiz.tek_gun.islem[1].r | r }} R
verdi{{? len(O.basarisiz.tek_gun.islem) == 2 }}. O gün çıkınca net sonuç {{ O.basarisiz.tek_gun.haric | r3 }} R ve kural
{{ O.basarisiz.tek_gun.sira_haric | n }}. sıraya iniyor. Küçük örneklemli bir kuralın sıralamadaki yeri çoğu zaman bir
iki günün eseridir.

**Alıştırma 3.** Örneklem içinde brüt t'si anlamlı bileşimlerin brüt ortalaması {{ O.basarisiz.kenar.is_anlamli.is | r3 }} R,
bütün bileşimlerinki {{ O.basarisiz.kenar.is_anlamli.mu_is | r3 }} R ve örneklem içi güvenilirlik
{{ O.basarisiz.kenar.is_anlamli.rho_is | s2 }}. Bu bileşimlerin örneklem dışı brüt beklentisi ne olmalıydı? Ölçülen
{{ O.basarisiz.kenar.is_anlamli.oos | r3 }} R bu öngörüyle çelişiyor mu?

<details>
<summary>Çözüm</summary>

Büzülmüş beklenti $\mu + \rho(\hat x - \mu)$: {{ O.basarisiz.kenar.is_anlamli.mu_is | s3 }} +
{{ O.basarisiz.kenar.is_anlamli.rho_is | s2 }} × ({{ O.basarisiz.kenar.is_anlamli.is | s3 }} −
{{ O.basarisiz.kenar.is_anlamli.mu_is | s3 }}) = {{ O.basarisiz.kenar.is_anlamli.ongoru | r3 }} R (yuvarlanmamış
değerlerle{{? O.basarisiz.kenar.is_anlamli.mu_is > 0 and O.basarisiz.kenar.is_anlamli.is > 0 }}). Ölçülen değerle farkı, ortalamanın standart hatası cinsinden {{ O.basarisiz.kenar.is_anlamli.ongoru_z | s1 }}: iki
standart hatanın içinde, yani çelişmiyor. Örneklem içinde anlamlı görünen bir brüt kenarın örneklem dışında küçülmesi
bir sürpriz değil, ölçmeden önce hesaplanabilecek bir beklentiydi.

</details>

## Şans, seçim ve süzgeç

Bir sonucun şans olup olmadığını sormanın doğru yolu, kenarın hiç olmadığı bir dünyada aynı sonucun ne sıklıkla
çıkacağını hesaplamaktır. Brüt kenar sıfırsa bir bileşimin örneklem dışı net ortalaması, ortalaması maliyetin eksisi
($-c_i$) ve standart hatası $\mathrm{se}_i$ olan bir normal dağılıma uyar ve bileşimin net artı çıkma olasılığı
$p_i = \Phi(-c_i / \mathrm{se}_i)$ olur. Net artı bileşimlerin sayısı, olasılıkları farklı bağımsız denemelerin
toplamıdır (Poisson-binom dağılımı): beklentisi $\sum_i p_i$, varyansı $\sum_i p_i(1-p_i)$. Bileşimler aynı günleri
paylaşır; beklenen sayı bağımlılıkla değişmez, yalnız dağılım genişler.

Bu taban önceden kayıtlı varsayılanlarda {{ O.basarisiz.sans.varsayilan.bilesim | n }} bileşim için
{{ O.basarisiz.sans.varsayilan.beklenen | s1 }} net artı bileşim bekliyor (standart sapma
{{ O.basarisiz.sans.varsayilan.sd | s1 }}); gözlenen {{ O.basarisiz.sans.varsayilan.gozlenen | n }}. Kenarsız bir dünyada
en az bu kadar net artının çıkma olasılığı {{ O.basarisiz.sans.varsayilan.p_ustu | s2 }}. Aralığının alt ucu sıfırın
üstünde kalan bileşim için taban {{ O.basarisiz.sans.varsayilan.calisiyor_ust | s2 }}; hükmün "çalışıyor" sayısı
{{ T.hukum_say.oos.calisiyor | n }}. Karşı olgu da hesaplanabilir: örneklem içinin brüt sonucu örneklem dışında aynen
sürseydi beklenen net artı sayısı {{ O.basarisiz.sans.varsayilan.is_surseydi | s1 }} olurdu. Gözlenen sayı iki tabanın
arasında{{? O.basarisiz.sans.varsayilan.gozlenen > O.basarisiz.sans.varsayilan.beklenen and O.basarisiz.sans.varsayilan.gozlenen < O.basarisiz.sans.varsayilan.is_surseydi }}
ve şansla açıklanabiliyor.

Izgaradan örneklem içinde seçilen kombinasyonlar için aynı hesap: {{ O.basarisiz.sans.secilen.bilesim | n }} bileşimde
beklenen {{ O.basarisiz.sans.secilen.beklenen | s1 }}, gözlenen {{ O.basarisiz.sans.secilen.gozlenen | n }}, en az bu
kadarının şansla çıkma olasılığı {{ O.basarisiz.sans.secilen.p_ustu | s2 }}; seçilenlerin örneklem içi brütü sürseydi
beklenen {{ O.basarisiz.sans.secilen.is_surseydi | s1 }}. Seçilenlerin tabanı varsayılanlarınkinden yüksek, çünkü
seçim daha ucuz kombinasyonları seçiyor (aşağıda); gözlenen sayı bu tabandan da ayırt edilemiyor{{? O.basarisiz.sans.secilen.p_ustu > 0.1 }}.

{{! sekil neden-sans "Şansın beklediği — kenarsız dünyada kaç bileşim artı çıkardı" }}

**Seçim örneklem dışına ne taşıdı?** Seçilen kombinasyonun varsayılandan ayrı olduğu
{{ O.basarisiz.sans.kazanc.oos.bilesim | n }} bileşimde ortalama, seçilen eksi varsayılan: örneklem içinde net fark
{{ O.basarisiz.sans.kazanc.is.net | r3 }} R; bunun {{ O.basarisiz.sans.kazanc.is.brut | r3 }} R'si brütten,
{{ O.basarisiz.sans.kazanc.is.tasarruf | r3 }} R'si maliyet tasarrufundan. Örneklem dışında net fark
{{ O.basarisiz.sans.kazanc.oos.net | r3 }} R; brütün katkısı {{ O.basarisiz.sans.kazanc.oos.brut | r3 }} R, maliyet
tasarrufunun katkısı {{ O.basarisiz.sans.kazanc.oos.tasarruf | r3 }} R. Seçimin örneklem dışına taşıdığı şey bir brüt
kenar değil, daha ucuz bir kombinasyondur: seçilenlerin varsayılandan ucuz olma payı
{{ O.basarisiz.sans.kazanc.oos.ucuz | yz0 }} ve medyan risklerinin varsayılanınkine oranı
{{ O.basarisiz.sans.kazanc.oos.R_orani | s2 }}. Ölçek bölümündeki mekanizmanın ta kendisi: daha geniş stop, maliyetin R
içindeki payını küçültür.

Seçilen kombinasyon, ızgaranın örneklem dışı sıralamasında da iyi tarafta kalıyor: örneklem dışı Sharpe yüzdeliğinin
medyanı {{ O.basarisiz.sans.secilen_yeri.yuzdelik | s0 }}, {{ O.basarisiz.sans.secilen_yeri.secim | n }} seçimin
{{ O.basarisiz.sans.secilen_yeri.ust_yari | n }} tanesi üst yarıda; ızgaranın içinde örneklem içi ve dışı Sharpe
sırasının korelasyonu (medyan) {{ O.basarisiz.sans.secilen_yeri.izgara_sira | s2 }}. Ama ızgaranın kendisi eksidir:
seçilenlerin yıllık Sharpe'ının medyanı örneklem içinde {{ O.basarisiz.sans.secilen_yeri.is_sharpe | sh }}, dışında
{{ O.basarisiz.sans.secilen_yeri.oos_sharpe | sh }}. Seçilenlerden {{ O.basarisiz.sans.secilen_yeri.oos_arti | n }} tanesi
örneklem dışında net artı; yürüyen pencerede (her yıl yalnız önceki yıllarla yeniden seçim) net artı kalan bileşim
{{ O.basarisiz.sans.yuruyen_arti | n }}. Seçim sayısına göre düzeltilmiş Sharpe olasılığı (deflated Sharpe) 0,95
eşiğini {% if O.basarisiz.sans.secilen_yeri.dsr_gecen == 0 %}{{ O.basarisiz.sans.secilen_yeri.secim | n }} seçimin
hiçbirinde geçmiyor{% else %}{{ O.basarisiz.sans.secilen_yeri.secim | n }} seçimin
{{ O.basarisiz.sans.secilen_yeri.dsr_gecen | n }} tanesinde geçiyor{% endif %} (en yükseği
{{ O.basarisiz.sans.secilen_yeri.dsr_azami | s2 }}). {{ O.basarisiz.sans.geriye_donuk.is_en_iyi_eksi | n }} bileşimde
ızgaranın örneklem içindeki en yüksek Sharpe'ı bile sıfır ya da eksi.

Seçim ancak geriye bakarak kurtarılabilir. Izgaranın {{ O.basarisiz.sans.geriye_donuk.satir | n }} satırının
{{ O.basarisiz.sans.geriye_donuk.satir_arti | n }} tanesi örneklem dışında net artı; her bileşimde ızgaranın örneklem dışı
en iyi satırını seçen biri {{ O.basarisiz.sans.geriye_donuk.bilesim | n }} bileşimin
{{ O.basarisiz.sans.geriye_donuk.arti | n }} tanesinde artı bir sonuç gösterebilirdi. Bu bir sonuç değil, görülmüş bir
pencerede yapılmış bir seçimdir ve tam olarak bu bölümün ölçtüğü yanılgıdır: bir geriye dönük sınamanın en iyi satırı,
o satırın gelecekte ne vereceği hakkında hiçbir şey söylemez.

Koşul süzgeçleri için aynı soru karşılaştırma dersinde soruldu: örneklem içinde seçilen kovalar
{{ T.kosul.sinanan | n }} sınamanın {{ T.kosul.tuttu | n }} tanesinde örneklem dışında tuttu, tam tersine seçilen kovalar
{{ T.kosul.ters_sinanan | n }} sınamanın {{ T.kosul.ters_tuttu | n }} tanesinde; fark şanstan ayırt edilemiyor (McNemar p
{{ T.kosul.p | p }}){{? not T.kosul.ayirt }}. Yerel tatil günlerini dışlamak da sık önerilen bir süzgeçtir: örneklem
dışında kuralların işlemlerinden medyanda {{ O.basarisiz.sans.tatil.oos.dislanan | yz1 }} payını atar, işlem başına net
R'yi medyanda {{ O.basarisiz.sans.tatil.oos.medyan | r3 }}, en çok {{ O.basarisiz.sans.tatil.oos.en_cok | r3 }} R
({{ O.basarisiz.sans.tatil.oos.en_cok_kural | kisa }}) değiştirir (bütün dönemde medyanda
{{ O.basarisiz.sans.tatil.medyan | r3 }}, en çok {{ O.basarisiz.sans.tatil.en_cok | r3 }} R,
{{ O.basarisiz.sans.tatil.en_cok_kural | kisa }}) ve {% if O.basarisiz.sans.tatil.oos.donen == 0 and O.basarisiz.sans.tatil.donen == 0 %}iki
pencerede de hiçbir kuralı eksiden artıya çevirmez{% else %}örneklem dışında {{ O.basarisiz.sans.tatil.oos.donen | n }},
bütün dönemde {{ O.basarisiz.sans.tatil.donen | n }} kuralı eksiden artıya çevirir{% endif %}.

**Aile hata oranı.** {{ O.basarisiz.kapsam.bilesim | n }} bileşim, her biri %5 düzeyde sınanınca, hiçbir kenar yokken
ortalama {{! hesap carp O.basarisiz.kapsam.bilesim 0.05 s1 }} yanlış alarm verir. Sınamaların bir aile olarak
düşünülmesi gerekir, ve ailenin büyüklüğü sorulan soruya göre değişir:

<div class="sayi-tablo">

| Soru | Ailenin büyüklüğü | Gürültüde beklenen geçen |
| :--- | ---: | ---: |
| Hangi kural–parite bileşimi çalışıyor? | {{ O.basarisiz.kapsam.bilesim | n }} | {{! hesap carp O.basarisiz.kapsam.bilesim 0.05 s1 }} |
| Izgaranın hangi satırı iyi? | {{ O.basarisiz.olcek.izgara_satir | n }} | {{! hesap carp O.basarisiz.olcek.izgara_satir 0.05 s0 }} |
| Hangi koşul kovası tutuyor? | {{ T.kosul.sinanan | n }} | {{ T.kosul.gurultu_beklenen | s0 }} |
| Ay sonu hangi biçimde çalışıyor? | {{ O.basarisiz.ay_sonu.aile.n | n }} | {{! hesap carp O.basarisiz.ay_sonu.aile.n 0.05 s1 }} |

</div>

_Tür: betimleme (hesap). Gürültüde beklenen geçen: gerçek etkisi sıfır olan sınamaların ölçütü geçme sayısı. Bileşim,
ızgara ve ay sonu satırlarında ölçüt %5 düzeyli bir sınama sayıldı; ızgaranın satırları hüküm kuralıyla sınanmaz ve
"net sonucu artı" bir %5 sınaması değildir, satır yalnız ailenin büyüklüğünü gösterir. Koşul satırının ölçütü ("tuttu")
%5 düzeyli değildir: gürültüde geçme oranını ters seçim ölçer ({{ T.kosul.ters_sinanan | n }} sınamanın
{{ T.kosul.ters_tuttu | n }} tanesi). Sınamalar bağımsız sayıldı; bağımlılık beklenen sayıyı değiştirmez, dağılımını
genişletir._

Üç düzeltme yaygındır. **Bonferroni** her sınamayı $\alpha / m$ düzeyinde yapar ve ailede en az bir yanlış alarm
olasılığını $\alpha$'nın altında tutar. **Holm** aynı güvenceyi daha az kayıpla verir: p değerleri küçükten büyüğe
dizilir, $k$. sıradaki değer $\alpha / (m - k + 1)$ ile kıyaslanır ve ilk geçemeyen değerde durulur (Holm, 1979).
**Benjamini–Hochberg** başka bir soruyu denetler: reddedilenlerin içindeki yanlışların beklenen payını (yanlış keşif
oranı); $k$. sıradaki değer $q \cdot k / m$ ile kıyaslanır ve geçen en büyük $k$'ya kadar hepsi reddedilir (Benjamini ve
Hochberg, 1995). Teknik işlem kurallarında aynı sorun "veri madenciliği" adıyla incelendi: aynı veri çıkarım ya da
model seçimi için birden çok kez kullanıldığında iyi bir sonuç yöntemin değerinden değil şanstan gelebilir, ve bir
kural evreninin en iyisi evrenin büyüklüğü hesaba katılarak sınanmalıdır (White, 2000). Sullivan, Timmermann ve White
(1999) Brock, Lakonishok ve LeBaron'un 26 kuralını genişletip Dow Jones'un 100 yıllık günlük verisinde bu yöntemle
sınadı: 1897–1986'da bazı kurallar veri madenciliği düzeltmesinden sonra da kıyası yendi. Sonraki on yılda
(1987–1996) evrenin o dönemdeki en iyi kuralı bile düzeltmeden sonra kıyası alışılmış anlamlılık düzeylerinde yenemedi:
en iyi kuralın kıyası yenmemiş olma olasılığı (düzeltilmiş p değeri) {{= "0,12" }}'ye yakındı. Hisse getirilerinin
kesitini açıklamak için yüzlerce faktörün denendiği literatürde yeni bir faktörün t istatistiğinin {{= "3,0" }}'ı aşması
önerildi (Harvey, Liu ve Zhu, 2016); eşik o literatürün deneme sayısından türetildi, başka bir aile için ayrıca
hesaplanır. Seçilmiş en iyi Sharpe'ı deneme sayısına ve getirilerin normal olmamasına göre düzelten ölçü deflated
Sharpe'tır (Bailey ve López de Prado, 2014). Becerisi olmayan (gerçek Sharpe'ı sıfır) stratejiler arasında parlak
görünen bir sonuca az sayıda denemeyle ulaşılır: beş yıllık veride kırk beş bağımsız ayar denendiğinde en iyisinin
örneklem içi Sharpe'ının beklenen değeri 1, örneklem dışındaki 0'dır (Bailey, Borwein, López de Prado ve Zhu, 2014).
Bu serinin hükme giren savunmaları üçtür: sonuç görülmeden yazılmış kurallar, örneklem dışı pencere ve rastgele yön
tabanı. Deflated Sharpe raporlanır, hükme girmez; {{ O.basarisiz.kapsam.bilesim | n }} bileşimlik aileye aile
düzeltmesi uygulanmadı, şansın beklediği sayı bu yüzden yukarıda ayrıca verildi.

**Alıştırma 4.** Kenarsız tabanda beklenen net artı sayısı {{ O.basarisiz.sans.varsayilan.beklenen | s2 }}, standart
sapması {{ O.basarisiz.sans.varsayilan.sd | s2 }}; gözlenen {{ O.basarisiz.sans.varsayilan.gozlenen | n }}. Normal
yaklaşımla (süreklilik düzeltmesiyle) en az bu kadar artının şansla çıkma olasılığı nedir?

<details>
<summary>Çözüm</summary>

Süreklilik düzeltmesi tam sayılı bir sayımı normal dağılıma yarım birimle bağlar: z = (gözlenen − {{= "0,5" }} −
beklenen) / standart sapma = ({{ O.basarisiz.sans.varsayilan.gozlenen | n }} − {{= "0,5" }} −
{{ O.basarisiz.sans.varsayilan.beklenen | s2 }}) / {{ O.basarisiz.sans.varsayilan.sd | s2 }} =
{{ O.basarisiz.sans.varsayilan.z | s2 }}. Standart normalin bu değerin üstünde kalma olasılığı
{{ O.basarisiz.sans.varsayilan.p_normal | s2 }}; kesin Poisson-binom dağılımıyla {{ O.basarisiz.sans.varsayilan.p_ustu | s2 }}.
Gözlenen sayı şansla açıklanabiliyor.

</details>

## Geriye bakan grafik neden iyi görünür

Eksi beklentili bir kuralın geriye dönük grafiği yine de ikna edici görünebilir. Üç mekanizması var: kuyruk, tuzak
payları ve seçilmiş örnek.

**Kuyruk.** Gün içi kuralların sonucu, az sayıda büyük işlemden gelebilir. {{! neden_kuyruk_cumle }}

{{! neden_kuyruk }}

Bileşimlerin aynı paritede toplanması bir yapının izi de olabilir (o paritenin bu penceredeki oynaklığı), şansın da. Bu
bir hipotezdir: net artı bileşimlerin sayısı zaten şansın beklediğinden ayırt edilemiyor (şans bölümü){{? O.basarisiz.sans.varsayilan.p_ustu > 0.1 }}.

**Tuzak payları.** Kaybeden işlemlerin bir kısmı önce lehe gider. Örneklem dışında kaybeden işlemlerin en az
{{ O.basarisiz.basabas.tuzak.esik.lehine | s1 }} R lehine gitmiş olma payı kuralların medyanında
{{ O.basarisiz.basabas.tuzak.lehine_medyan | yz0 }}; {{ O.basarisiz.basabas.tuzak.esik.ulasma | r1 }} R'ye ulaşan
işlemlerin zararla kapanma payı {{ O.basarisiz.basabas.tuzak.ulasip_zarar_medyan | yz0 }} (Londra ORB'de sırasıyla
{{ O.basarisiz.basabas.tuzak.kural.orb.lehine | yz0 }} ve {{ O.basarisiz.basabas.tuzak.kural.orb.ulasip_zarar | yz0 }}).
İki payın paydası farklıdır: birincisi kaybeden işlemler, ikincisi {{ O.basarisiz.basabas.tuzak.esik.ulasma | r1 }} R'ye
ulaşan bütün işlemler. Bu sayılar "çıkışı biraz farklı yapsaydım kazanırdım" hissini doğurur. Kenarsız bir piyasada
aynı paylar şöyledir: sürüklenmesiz bir rastgele yürüyüşte, −1 R'de stop ve ufukta çıkışla, ufka kadarki oynaklık
{{ O.basarisiz.basabas.tuzak.taban.sigma[0].sigma | n }} ile {{ O.basarisiz.basabas.tuzak.taban.sigma[3].sigma | n }} R
arasında değişirken kaybedenlerin lehine gitme payı {{ O.basarisiz.basabas.tuzak.taban.sigma[0].lehine | yz0 }} ile
{{ O.basarisiz.basabas.tuzak.taban.sigma[3].lehine | yz0 }} arasında, {{ O.basarisiz.basabas.tuzak.esik.ulasma | r1 }} R'ye
ulaşanların zararla kapanma payı {{ O.basarisiz.basabas.tuzak.taban.sigma[0].ulasip_zarar | yz0 }} ile
{{ O.basarisiz.basabas.tuzak.taban.sigma[3].ulasip_zarar | yz0 }} arasında. Taban kuralların hedef yapısını taşımaz,
yalnız büyüklüğün mertebesini verir: tuzak payları bir kenarın izi değil, kenarsız bir piyasada da bu büyüklükte
beklenir. Çıkış kuralının beklentiyi değiştirmediğini söyleyen teorem (beklentinin
aritmetiği) bu hissin cevabıdır.

**Seçilmiş örnek.** Okura ulaşan geriye dönük sınamalar seçilmiştir: yayımlanan, paylaşılan, pazarlanan sınama iyi
sonuç verendir. Yalnız ayakta kalanlar incelendiğinde başarının sürdüğü yanılsaması doğabilir (Brown, Goetzmann,
Ibbotson ve Ross, 1992). Gün içi işlem yapan bireylerin taban oranları da aynı yöndedir. Tayvan'da 1992–2006 arasında,
ortalama bir yılda gün içi işlem hacmi yılda 600 bin Tayvan dolarını aşan yaklaşık 277 bin kişinin beşte biri
ücretlerden (komisyon ve işlem vergisi) sonra artı anormal getiri elde etti; ertesi yıl da işlem maliyetlerinden sonra
güvenilir biçimde artı anormal getiri elde edenler yalnız önceki yılın en kârlı 4 bin gün içi işlemcisiydi, yani bütün
gün içi işlemcilerin {{= "%1" }}'inden azı (Barber, Lee, Liu ve Odean, 2014); Brezilya'nın hisse senedi vadeli piyasasında 2013–2015 arasında gün içi işleme başlayıp {{= "300" }} günden uzun
sürenlerin {{= "%97" }}'si para kaybetti (Chague, De-Losso ve Giovannetti, 2019). Kaldıraçlı perakende ürünlerde de
oran aynı yöndedir: Avrupa Menkul Kıymetler ve Piyasalar Otoritesi, ulusal otoritelerin analizlerine dayanarak
perakende CFD hesaplarının tipik olarak {{= "%74" }}–{{= "89" }}'unun para kaybettiğini yazdı (ESMA, 2018); bu oran
hesaplara aittir, gün içi işlemcilere değil. Bu kaynaklar dersin kurallarına dair bir şey söylemez; bir geriye dönük
sınamanın arka planındaki taban oranını söyler.

## Sık önerilen kurtarma yolları

Kaybeden bir kural için en sık önerilen yollar şunlardır. Çoğunun bu seride ölçülmüş bir karşılığı var; Tür sütunu
her satırın ne olduğunu söyler.

<div class="sayi-tablo">

| Öneri | Tür | Bu seride ölçülen | Bölüm |
| :--- | :--- | :--- | :--- |
| Parametreleri iyileştirmek | Ön kayıt ve betimleme | Seçim örneklem dışına {{ O.basarisiz.sans.kazanc.oos.net | r3 }} R taşıdı; brütün katkısı {{ O.basarisiz.sans.kazanc.oos.brut | r3 }} R | Şans, seçim ve süzgeç |
| Koşul ya da rejim süzgeci | Ön kayıt ve betimleme | {{ T.kosul.sinanan | n }} sınamada {{ T.kosul.tuttu | n }} tuttu; tam tersine seçilen kovalarla {{ T.kosul.ters_sinanan | n }} sınamada {{ T.kosul.ters_tuttu | n }} | Şans, seçim ve süzgeç |
| Kuralı tersine çevirmek | Betimleme | Ayna {{ O.basarisiz.ayrisim.oos.bilesim | n }} bileşimin {{ O.basarisiz.ayrisim.oos.ayna_eksi | n }} tanesinde eksi | Kaybın ayrışımı |
| Stopu uzatmak, mumu büyütmek | Betimleme | Net R artıyor ama ızgara medyanı eksi kalıyor; işlem başına pip yazı tura{{? O.basarisiz.olcek.tf_medyan.oos.60 < 0 }} | Ölçek |
| Çıkışı değiştirmek | Betimleme | Grubun içinde isabet medyanda {{! hesap carp O.basarisiz.olcek.hedef.oos.isabet_aralik 100 s0 }} puan, beklenti {{ O.basarisiz.olcek.hedef.oos.r_aralik | s2 }} R oynuyor | Ölçek |
| Yerel tatilleri dışlamak | Betimleme | Hiçbir kural eksiden artıya dönmüyor{{? O.basarisiz.sans.tatil.oos.donen == 0 and O.basarisiz.sans.tatil.donen == 0 }} | Şans, seçim ve süzgeç |
| Kuralları tek kitapta birleştirmek | Betimleme | Hacim {{ O.basarisiz.esik.netlesme.oos.esit.tasarruf | yz0 }} azalır; başabaş için maliyetin {{ O.basarisiz.esik.netlesme.oos.kitap_gereken | yz0 }} kadarı gitmeli | Yürütme şartı |
| Pozisyon büyüklüğünü ayarlamak | Türetim | Eksi beklentide en iyi pay sıfırdır | Aşağıda |
| En ucuz pariteyi seçmek | Betimleme | Yalnız makasla bakılınca maliyet seçimi; kayma eklenince sıralama makası izlemiyor | Aşağıda |
| Limit emirle girmek | Ölçülmedi | Dolum fiyata bağlıdır ve ters seçime uğrar; net etkinin yönü bilinmiyor | Yürütme şartı |
| Daha ucuz yürütme | Betimleme | {{ O.basarisiz.esik.ozet.oos.sifir_alti_n | n }} kuralda başabaş maliyeti sıfır ya da altında; aralıklar sıfırı kapsıyor{{? O.basarisiz.esik.ozet.oos.sifir_alti_kapsar_n == O.basarisiz.esik.ozet.oos.sifir_alti_n }} | Yürütme şartı |
| Haberle ilk saniyede girmek | Ölçülmedi | 1 dakikalık veride haber saniyesinin makası ve kayması yok; ölçülen, hareketin büyük kısmının ilk beş dakikada fiyata girdiği | Kenarın kaynakları |

</div>

_Tür: ön kayıt, ölçütü sonuç görülmeden yazılmış bir ölçünün sonucu (parametre seçiminin ve koşul doğrulamasının
ölçütleri; brüt ile maliyet tasarrufu ayrımı ve ters seçim bu dersin ve karşılaştırma dersinin betimlemesidir);
betimleme, iki pencere de görüldükten sonra kurulan ölçü; türetim, aritmetikten çıkan sonuç; ölçülmedi, bu seride
ölçülmeyen. Hiçbir satır bir hüküm değildir ve hiçbiri bir kuralı kullanılabilir yapmaz. Bölüm sütunu ölçünün bu
dersteki yerini gösterir._

Tablonun ortak cevabı kısadır: maliyetten önceki kenar sıfıra yakınsa, kuralın görünüşünü değiştiren bir ayar sonucun
işaretini değiştirmez ve brütü artırmaz. Önerilerin çoğu ya isabeti başabaş eğrisi boyunca kaydırır (çıkış, stop), ya
maliyetin R içindeki payını küçültür (zaman dilimi, seçim), ya da görülmüş pencerede iyi görüneni seçer (süzgeç,
parametre). Üçü de brütün kendisini artırmaz.

**Pozisyon büyüklüğü.** İşlem başına getirisi $r$ olan bir kuralda sermayenin $f$ payıyla işlem yapılırsa, sermayenin
logaritmik büyümesi küçük getiriler için

$$
\begin{aligned}
g(f) &= E\big[\ln(1 + f\,r)\big] \\
     &\approx f\,\mu - \tfrac{1}{2}\,f^{2}\,\sigma^{2}, \\
f^{*} &= \frac{\mu}{\sigma^{2}}
\end{aligned}
$$

olur. $\mu$ eksiyse en iyi pay eksidir; ters pozisyon da aynayı açmak demektir ve ayna da kaybeder (kaybın ayrışımı).
Geriye kalan en iyi pay sıfırdır. Pozisyon büyüklüğü bir eksi beklentiyi artıya çeviremez, yalnız kaybın hızını ve
dağılımını belirler.

**Parite seçimi.** Yalnız makasla (kayma sıfır) ölçüldüğünde örneklem dışında net artı kalan
{{ O.basarisiz.ayrisim.oos.duyarlilik.yalniz_makas | n }} bileşimin pariteleri: EUR/USD
{{ O.basarisiz.ayrisim.oos.duyarlilik.yalniz_makas_parite.EURUSD | n }}, USD/JPY
{{ O.basarisiz.ayrisim.oos.duyarlilik.yalniz_makas_parite.USDJPY | n }}, GBP/USD
{{ O.basarisiz.ayrisim.oos.duyarlilik.yalniz_makas_parite.GBPUSD | n }}, AUD/USD
{{ O.basarisiz.ayrisim.oos.duyarlilik.yalniz_makas_parite.AUDUSD | n }}. Verinin medyan makası aynı sırayla EUR/USD'de
{{ O.basarisiz.esik.makas.EURUSD | s1 }}, USD/JPY'de {{ O.basarisiz.esik.makas.USDJPY | s1 }}, GBP/USD'de
{{ O.basarisiz.esik.makas.GBPUSD | s1 }}, AUD/USD'de {{ O.basarisiz.esik.makas.AUDUSD | s1 }} pip. Yalnız makasla
bakılınca parite seçimi bir maliyet seçimidir: dar makaslı paritede aynı kural daha az
kaybeder{{? O.basarisiz.ayrisim.oos.duyarlilik.yalniz_makas_parite.EURUSD > O.basarisiz.ayrisim.oos.duyarlilik.yalniz_makas_parite.AUDUSD and O.basarisiz.esik.makas.EURUSD < O.basarisiz.esik.makas.AUDUSD }}.
Kayma da eklenince (temel senaryo) net artı kalan {{ O.basarisiz.ayrisim.oos.duyarlilik.temel | n }} bileşimin
pariteleri EUR/USD {{ O.basarisiz.ayrisim.oos.duyarlilik.temel_parite.EURUSD | n }}, USD/JPY
{{ O.basarisiz.ayrisim.oos.duyarlilik.temel_parite.USDJPY | n }}, GBP/USD
{{ O.basarisiz.ayrisim.oos.duyarlilik.temel_parite.GBPUSD | n }}, AUD/USD
{{ O.basarisiz.ayrisim.oos.duyarlilik.temel_parite.AUDUSD | n }}: sıralama artık makası
izlemiyor{{? O.basarisiz.ayrisim.oos.duyarlilik.temel_parite.EURUSD < O.basarisiz.ayrisim.oos.duyarlilik.temel_parite.USDJPY and O.basarisiz.ayrisim.oos.duyarlilik.temel_parite.AUDUSD >= O.basarisiz.ayrisim.oos.duyarlilik.temel_parite.EURUSD and O.basarisiz.esik.makas.EURUSD < O.basarisiz.esik.makas.USDJPY }}
ve net artıların toplandığı parite kuyruk bölümündeki hipoteze döner. Maliyetin makas kısmı ölçülmüştür, kayma kısmı
bu verinin ölçemediği bir varsayımdır.

## Kenarın kaynakları

Kurtarma yolları sonuç vermiyorsa soru tersinden sorulmalıdır: bir gün içi kuralın kenarı, olacaksa, nereden gelir?
Bu ders dört kaynak ayırır. Her biri bir karşı tarafın neden para kaybetmeye razı olduğunu açıklar; kaynağı
olmayan bir kural, kenarını şansa borçludur.

<div class="sayi-tablo">

| Kaynak | Karşı taraf neden öder | Bu serideki karşılığı | Değerlendirme |
| :--- | :--- | :--- | :--- |
| Yürütme | Likidite isteyen, aracının üstlendiği stok riskinin karşılığını öder | Bütün kurallar likidite alır, makası öder | Ölçülmedi: likidite sağlayan kural yok |
| Akış | Fiyattan bağımsız sebeple işlem yapmak zorundadır | Fiksing, gün içi momentum, VWAP | Ölçüldü; çalışan kural yok, tek aday ay sonu |
| Bilgi | Haberi geç ya da kötü işler | Beş haber kuralı | Ölçüldü; çalışan kural yok |
| Risk primi | Taşımak istemediği riski devreder | Yok: pozisyonlar gece taşınmaz | Kapsam dışı |

</div>

_Tür: kaynak sütunu bu dersin kendi ayrımıdır, dayandığı literatür aşağıda kaynağıyla; değerlendirme sütunu betimlemedir
ve bu serinin ölçtüğü kurallar içindir: bir kaynağın var olup olmadığı hakkında değil, bu kuralların ona ulaşıp
ulaşmadığı hakkındadır._

**Yürütme.** Piyasada bilgili işlemciler varsa makas, piyasa yapıcı risk nötr olsa ve beklenen kârı sıfır olsa bile
artıdır: makas, bilgisiz tarafın bilgiliye kaybettiğinin karşılığıdır (Glosten ve Milgrom, 1985). Makasın bu kısmı
likidite sağlayana kenar bırakmaz; aldığını bilgili tarafa geri verir. Likidite sağlamanın kenar olabilecek kısmı
üstlenilen riskin karşılığıdır: fiksinglerdeki dolar yönlü fiyat örüntüsü, aracıların fiksinglerde koşulsuz dolar
talebine aracılık ederken taşıdığı stok riskiyle tutarlıdır (Krohn, Mueller ve Whelan, 2024). Kâr al emirleri yuvarlak sayılarda, zarar durdur emirleri onların hemen ötesinde
kümelenir; bu kümelenme fiyatın destek ve direnç seviyelerinde dönmesini ve seviye geçildikten sonra hızlanmasını
açıklayabilir (Osler, 2003). Bu serinin bütün kuralları likidite ister: giriş ve piyasa çıkışları makası öder.
Likidite sağlayan bir kural ölçülmedi.

**Akış.** Bazı katılımcılar fiyattan bağımsız sebeplerle belirli bir anda işlem yapmak zorundadır: fiksing emirleri,
endeks ve portföy yeniden dengelemesi, yabancı portföylerin kur koruması. Melvin ve Prins (2015) uluslararası hisse
portföylerinin kur koruma işlemlerinin Londra fiksinginde yoğunlaştığını kurumsal bir öncül olarak alır, işlemlerin
yönünü geçmiş hisse getirilerinden okur ve hisse piyasasının ay içindeki değer artışının ay sonu fiksinginden önceki kur
değer kaybını öngördüğünü gösterir. 2004–2013 verisinde, fiksingin hesaplama penceresinin bir dakika olduğu dönemde,
fiksingin hemen öncesindeki ve sonrasındaki kur değişimleri olağanüstü oynaktı ve güçlü bir eksi ardışık ilinti
gösteriyordu, özellikle ayın son işlem gününde (Evans, 2018); dolar fiksinglere giderken değer kazanır, sonra kaybeder
(Krohn, Mueller ve Whelan, 2024). Bu serinin akışa dayanan kuralları fiksingin iki kuralı (momentum ve dönüş), gün içi
momentum ve VWAP geri çekilmesidir.

**Bilgi.** Emir akışı kurun belirleyicisidir, çünkü bilgi taşır: emir akışına dayanan bir model Alman markı–dolar
kurunun günlük değişimlerinde R²'yi {{= "%60" }}'ın üstüne çıkarır (Evans ve Lyons, 2002). Bilgisel olarak tam etkin
bir piyasa olanaksızdır (Grossman ve Stiglitz, 1980); bilgi kaynağı bu yüzden vardır: fiyat bilgiyi tam yansıtsaydı onu
toplamanın bir getirisi kalmazdı. Haber kuralları bu kaynağa haberin kendisinden ulaşmaya çalışır. Ölçülen patika haberin fiyata ne hızla girdiğini gösteriyor:

{{! neden_haber }}

Veri anlarında fiyat ilk beş dakikada günlük ATR'nin dörtte birinden fazlasını yol alıyor (tarım dışı istihdamda
{{ O.basarisiz.haber.NFP.h5 | yz0 }}, tüketici fiyatlarında {{ O.basarisiz.haber.CPI.h5 | yz0 }}){{? O.basarisiz.haber.NFP.h5 > 0.25 and O.basarisiz.haber.CPI.h5 > 0.25 }}.
Sonraki 55 dakikada ortalama hareket ya sıfıra yakın (tüketici fiyatları {{ O.basarisiz.haber.CPI.d60 | yzs1 }}) ya da
geri dönüş (tarım dışı istihdam {{ O.basarisiz.haber.NFP.d60 | yzs1 }}){{? abs(O.basarisiz.haber.CPI.d60) < 0.01 and O.basarisiz.haber.NFP.d60 < 0 }}.
FOMC basın toplantısında ilk beş dakikanın hareketi küçük ve sonraki bir saatte ondan fazlası geri veriliyor
({{ O.basarisiz.haber.FOMC_basin.d60 | yzs1 }}){{? abs(O.basarisiz.haber.FOMC_basin.d60) > O.basarisiz.haber.FOMC_basin.h5 and O.basarisiz.haber.FOMC_basin.d60 < 0 }}.
Gün içi bir kuralın ölçebildiği ufukta haber fiyata büyük ölçüde ilk dakikalarda giriyor: bir kural ilk mum kapandıktan
sonra girdiğinde bilginin çoğu fiyattadır ve kalan hareket, haber penceresinin geniş makasını ve ek kaymasını
karşılamıyor. Haber dersinin kırılım ↔ fade devam tablosu aynı soruyu stop ve hedef olmadan sorar: hücrelerinin
{{ O.haber.devam.hukum_sayimi."ayrışmıyor" | n }} tanesinde kazanan yok, {{ O.haber.devam.hukum_sayimi."yetersiz örneklem" | n }}
tanesinde örneklem yetersiz{{? len(O.haber.devam.hukum_sayimi) == 2 }}; kırılımın ya da fade'in kazandığı hücre yok.

**Risk primi.** Yüksek faizli paralar ortak bir risk faktörüne düşük faizli paralardan daha çok yüklenir ve bu faktör
iki grup arasındaki ortalama fazla getiri farkının çoğunu açıklar: düşük faizli parayla borçlanıp yüksek faizli paraya
yatıran, küresel riski üstlenir (Lustig, Roussanov ve Verdelhan, 2011). Bu kaynak, riski taşımak için zaman ister: bu serinin bütün pozisyonları gün sonunda kapanır ve faiz
farkı doğmaz.

Bir kaynağa dayanmak gerekli ama yeterli değil. Serinin akış ve haber kuralları da bir kaynağın adını taşıyordu ve
kaybetti. Kaynağın varlığı, kuralın o kaynağa maliyetinden ucuza ulaştığını göstermez; ulaşan çok kişiyse kenar
paylaşılır ve küçülür. Döviz piyasasında genetik programla ve doğrusal bir tahmin modeliyle seçilen gün içi teknik
kurallar için, gerçekçi işlem maliyeti ve işlem saatleri hesaba katıldığında, örneklem dışında fazla getiri
sağladıklarına dair kanıt çıkmadı; kurallar verideki şaşırtıcı ölçüde istikrarlı bazı örüntüleri yine de buldu (Neely
ve Weller, 2003). Örüntünün varlığı kenarın
varlığı değildir. Döviz piyasasında daha önce yayımlanmış teknik kuralların 1970'ler ve 1980'lerdeki fazla getirisi
gerçekti, ama filtre ve hareketli ortalama kurallarında 1990'ların başında kaybolmuştu (Neely, Weller ve Ulrich,
2009). Algoritmik işlemin yayılması üçgen arbitraj fırsatlarının sıklığını ve yüksek frekanslı getirilerin
özilintisini azalttı; daha yavaş işlemcilere daha yüksek ters seçim maliyeti yükleyebilir (Chaboud, Chiquoine,
Hjalmarsson ve Vega, 2014). Hisse senetlerinde kesitsel getiriyi öngördüğü gösterilmiş 97 değişkenin portföy getirisi
örneklem dışında {{= "%26" }}, yayımdan sonra {{= "%58" }} daha düşüktü; yazarlar örneklem dışındaki düşüşü veri
madenciliği etkisinin üst sınırı sayar, yayımdan sonraki ek {{= "32" }} puanı yayımı okuyan işlemlere bağlar (McLean ve
Pontiff, 2016). Birinci kısım, bu dersin "Kenar var mıydı" bölümünde ölçülen küçülmenin, yani seçimin aritmetiğinin, hisse
senetlerindeki karşılığıdır.

Bu seride sınanmamış akış anları da var. Tokyo fiksinginde bankalar kuru, bankalar arası piyasanın Tokyo 09:55'teki
({{! tsi "" "Tokyo 09:55" }}) işlemlerine göre ilan eder; fiksingden önceki emir akışı dolar yönüne eğilimlidir ve bu
öngörülebilir bir fiyat örüntüsü doğurur (Ito ve Yamada, 2017). New York'taki opsiyon vade kesimi
({{! tsi "" "New York 10:00" }}) ve çeyrek sonları da zorunlu akışın birikebildiği anlardır. Bunlar bu seri için
**hipotezdir**: aynı yöntemle, sonuç görülmeden yazılmış bir planla sınanmadıkça bu serinin kuralları hakkında hiçbir
şey söylemezler.

## Yürütme şartı: kural ne kadar maliyet kaldırır

Kullanılabilirliğin birinci şartı aritmetiktir: kuralın kaldırabildiği maliyet, ödenecek maliyetin üstünde olmalıdır.
İşlem başına sabit bir gidiş-dönüş maliyeti $c$ (pip) için işlemin net sonucu $r_{\text{brüt}} - c / R_{\text{pip}}$'dir
ve beklenti

$$
\begin{aligned}
E[r_{\text{net}}] &= E[r_{\text{brüt}}] - c\,E\big[1/R_{\text{pip}}\big], \\
c^{*} &= \frac{E[r_{\text{brüt}}]}{E\big[1/R_{\text{pip}}\big]}
\end{aligned}
$$

olur. $c^{*}$ **başabaş maliyetidir**: kural işlem başına bu kadar maliyetle sıfıra iner. Hesap ilk mertebedir:
maliyet değişince işlemler aynı kalır sayılır (gerçekte daha ucuz bir yürütme bazı işlemleri de değiştirir). Aralık,
brüt sonucun önceden kayıtlı bootstrap aralığının uçlarından gelir.

{{! neden_esik }}

{{! sekil neden-maliyet-esigi "Bir kural ne kadar maliyet kaldırır — başabaş maliyeti ve ödenen" }}

Örneklem dışında {{ O.basarisiz.esik.ozet.oos.sifir_alti_n | n }} kuralda başabaş maliyetinin nokta tahmini sıfır ya
da altında ({{! kurallar O.basarisiz.esik.ozet.oos.sifir_alti }}) ve aralıklarının hepsi sıfırı
kapsıyor{{? O.basarisiz.esik.ozet.oos.sifir_alti_kapsar_n == O.basarisiz.esik.ozet.oos.sifir_alti_n }}: bu kurallarda
maliyetsiz bir yürütmeyle de bir kenar gösterilemiyor (brütleri sıfırdan ayırt edilemiyor). Öbür
kuralların hiçbirinde başabaş maliyeti ödenen maliyete ulaşmıyor{{? O.basarisiz.esik.ozet.oos.ustu_n == 0 }}; ödenen
maliyet kurallar arasında {{ O.basarisiz.esik.ozet.oos.odenen_alt | s2 }} ile {{ O.basarisiz.esik.ozet.oos.odenen_ust | s2 }}
pip arasında. Aralığın alt ucu sıfırın üstünde kalan kural örneklem dışında {{ O.basarisiz.esik.ozet.oos.alt_arti_n | n }}
({{! kurallar O.basarisiz.esik.ozet.oos.alt_arti }}), bütün dönemde {{ O.basarisiz.esik.ozet.tum.alt_arti_n | n }}
({{! kurallar O.basarisiz.esik.ozet.tum.alt_arti }}). Bütün dönemde başabaş maliyeti ödenen maliyetin üstünde kalan tek
kural {{! kurallar O.basarisiz.esik.ozet.tum.ustu }}{{? O.basarisiz.esik.ozet.tum.ustu_n == 1 and O.basarisiz.esik.ozet.tum.ustu[0] == "n4" }},
ve o kuralın sonucu tek bir günün eseridir (kenar bölümü).

Aynı soru bileşim düzeyinde de sorulabilir: maliyet bugünküne göre küçülseydi örneklem dışında kaç bileşim net artı
kalırdı? Bugünkü maliyetle {{ O.basarisiz.esik.lambda.oos.kat."1.0" | n }}, maliyetin dörtte üçüyle
{{ O.basarisiz.esik.lambda.oos.kat."0.75" | n }}, yarısıyla {{ O.basarisiz.esik.lambda.oos.kat."0.5" | n }}, dörtte
biriyle {{ O.basarisiz.esik.lambda.oos.kat."0.25" | n }}, onda biriyle {{ O.basarisiz.esik.lambda.oos.kat."0.1" | n }},
maliyetsiz {{ O.basarisiz.esik.lambda.oos.kat."0.0" | n }} (brütü artı olanların hepsi). Brütü artı bileşimlerde
brütün maliyete oranının medyanı {{ O.basarisiz.esik.lambda.oos.oran | s2 }}: tipik bir brüt artı bileşim maliyetinin
ancak üçte birini karşılıyor{{? O.basarisiz.esik.lambda.oos.oran > 0.25 and O.basarisiz.esik.lambda.oos.oran < 0.4 }}.

Başabaş maliyeti, maliyet merdiveninden bulunan başabaş kaymasıyla da tutarlıdır (karşılaştırma dersi, "Maliyet"):
Londra ORB EUR/USD'de örneklem dışı başabaş maliyeti {{ O.basarisiz.esik.merdiven.cstar | s2 }} pip; makasın pip
maliyeti ({{ O.basarisiz.esik.merdiven.makas | s2 }}) ile iki dolumun başabaş kaymasının
({{! hesap carp O.basarisiz.esik.merdiven.kayma 2 s2 }}) toplamı {{ O.basarisiz.esik.merdiven.toplam | s2 }} pip. İki
ayrı yoldan gelen iki sayının birbirine yakın olması, ilk mertebe yaklaşımının bu kuralda tuttuğunu gösterir.

**Kuralları birleştirmek.** Bir masa bütün kuralları tek kitapta yürütseydi, aynı dakikada açılıp kapanan ters
işlemler birbirini götürür ve makas yalnız net akışa ödenirdi. Ölçüldü: aynı paritenin bütün kurallarının emirleri
aynı dakikada netleşseydi işlem hacmi örneklem dışında {{ O.basarisiz.esik.netlesme.oos.esit.tasarruf | yz1 }} (eşit
nominal) ya da {{ O.basarisiz.esik.netlesme.oos.R.tasarruf | yz1 }} (her işlem 1 R) azalırdı. Kitabın başabaşı için
gereken azalma çok daha büyük: kitabın brüt toplamının maliyet toplamına oranı {{ O.basarisiz.esik.netlesme.oos.kitap_oran | yz1 }},
yani maliyetin {{ O.basarisiz.esik.netlesme.oos.kitap_gereken | yz0 }} kadarı ortadan kalkmalı.

**Limit emir.** Limit emir makası ödemek yerine almayı dener. Ama limit emir fiyata bağlıdır: fiyat ona doğru
geldiğinde dolar ve onu dolduran karşı taraf bilgili olabilir; dolmayan emir ise fiyatın lehte gittiği, kaçırılan bir
işlem olabilir. Bireysel yatırımcıların işlemlerinden sonraki kötü getirilerin büyük kısmı limit emir kullanmalarıyla
açıklanabilir, çünkü limit emir fiyata bağlıdır ve ters seçime uğrar (Linnainmaa, 2010). Limit emirle yürütülen bir
kuralın sonucu orta fiyattan ölçülen brütten iyi de kötü de olabilir: dolan emir makasın bir kısmını alır, ters seçim
ve kaçırılan işlemler onu geri verebilir. Bu seride limit emir benzetilmedi; net etkinin yönü ölçülmedi. Elektronik döviz piyasasında likidite
sağlayıcı, işlem talebini kabul edip etmeyeceğine ve ederse hangi kurdan edeceğine talep ulaştıktan sonra karar
verebilir ("son bakış"); talep iletilirken fiyat hareket etmiş olabilir (Oomen, 2017). Bu uygulama yürütme maliyetini
verinin dışından etkiler.

**Ulaşılabilir maliyet.** Döviz likiditesi kurdan kura belirgin biçimde farklıdır, likiditesizliğin maliyeti
büyüktür ve likidite kurlar arasında, hisse ve tahvil piyasalarıyla birlikte hareket eder; 2007–2009'da likidite riski
taşıma getirisini belirgin biçimde etkiledi (Mancini, Ranaldo ve Wrampelmeyer, 2013). Bir kuralın maliyet şartı bu yüzden ortalama bir makasla değil, kuralın işlem
yaptığı dakikanın ölçülmüş makası ve kendi yürütmesinin ölçülmüş kaymasıyla sorulur. Bu serinin kayması bir
varsayımdır (dolum başına {{ K.temel_kayma_pip | s1 }} pip); kullanacak olanın kendi kaymasını ölçmesi gerekir.

**Alıştırma 5.** Londra ORB'nin örneklem dışı başabaş maliyeti {{ O.basarisiz.esik.havuz.oos.orb.cstar | s2 }} pip,
ödenen maliyeti {{ O.basarisiz.esik.havuz.oos.orb.odenen | s2 }} pip. Kuralın başabaşa gelmesi için maliyetin hangi
katına (λ*) inmesi gerekir? Aralığın alt ucu ({{ O.basarisiz.esik.havuz.oos.orb.alt | s2 }} pip) neyi söyler?

<details>
<summary>Çözüm</summary>

λ* = başabaş maliyeti / ödenen maliyet = {{ O.basarisiz.esik.havuz.oos.orb.cstar | s2 }} /
{{ O.basarisiz.esik.havuz.oos.orb.odenen | s2 }} = {{! hesap bol O.basarisiz.esik.havuz.oos.orb.cstar O.basarisiz.esik.havuz.oos.orb.odenen s2 }}.
Aralığın alt ucu sıfırın altında{{? O.basarisiz.esik.havuz.oos.orb.alt < 0 }}: bu pencerede kuralın maliyetsiz
yürütmeyle bile artı olduğu gösterilemiyor. Başabaş maliyetinin nokta tahmini artı olsa da şart, aralığın alt ucunun
ödenen maliyetin üstünde olmasıdır; bu kural ondan çok uzakta.

</details>

## Akış şartı: ay sonu fiksingi

Serinin tek adayı fiksing momentumunun ay sonu alt kümesidir. Kural Londra 16:00 fiksingine giden son beş dakikalık
mumu taşır: Londra 15:50–15:55 mumunun ({{! tsi "" "Londra 15:50–15:55" }}) yönünde 15:55'te girer, 16:00'da çıkar
({{! tsi "→" "Londra 15:55" "Londra 16:00" }}); stop yoktur, R girişteki ATR(14)'tür. Fiksingin hesaplama penceresi
16:00'ı ortalayan beş dakikadır (Londra 15:57:30–16:02:30; {{! tsi "" "Londra 15:57:30–16:02:30" }}): işlem pencerenin
ilk yarısını da taşır ve çıkış pencerenin ortasındadır. Ay sonu ayın son Londra iş günüdür (ön kaydın tanımı). Ön kayıt
bu alt kümeyi ayrıca raporlamayı yazdı, ona hüküm kuralı uygulamadı; aşağıdakilerin hepsi betimlemedir.{{? O.birim.fiks_momentum.varsayilan.tf == 5 }}

{{! neden_ay_sonu }}

{{! sekil neden-ay-sonu "Ay sonu fiksingi — tek aday, dört paritede" }}

Aralıkların bazı uçları sıfıra çok yakın. Böyle bir ucun işareti bootstrap tohumuna bağlıdır: önceden kayıtlı yordam
{{ O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.sinir.alt.tohum_sayisi | n }} farklı tohumla yeniden koşulunca bir
tohumda artı, öbüründe eksi uç verir. Ders böyle bir ucu "sınırda" diye adlandırır; tohumların artı çıkma payını ve
{{ O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.sinir.alt.tekrar | n }} tekrarlı kestirimi de basar. Tabloda ve
metinde yazan uç önceden kayıtlı yordamın sonucudur; sınır kaydı yalnız işaretinin ne kadar sağlam olduğunu söyler.

GBP/USD iki ayrık pencerede de net artı ve önceden kayıtlı yordamla aralığının alt ucu iki pencerede de sıfırın
üstünde. 2024 →'de {{ O.basarisiz.ay_sonu.parite.GBPUSD.oos.ay_sonu.net | r3 }} R
({{ O.basarisiz.ay_sonu.parite.GBPUSD.oos.ay_sonu.alt | r3 }} / {{ O.basarisiz.ay_sonu.parite.GBPUSD.oos.ay_sonu.ust | r3 }}).
2018–2023'te {{ O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.net | r3 }} R, alt uç
{{ O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.alt | r3 }} ve sınırda: tohumların artı çıkma payı
{{ O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.sinir.alt.pozitif_pay | yz0 }}, büyük tekrarlı kestirim
{{ O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.sinir.alt.kesin | r3 }}{{? O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.alt > 0 and O.basarisiz.ay_sonu.parite.GBPUSD.oos.ay_sonu.alt > 0 and O.basarisiz.ay_sonu.parite.GBPUSD.is.ay_sonu.sinir.alt.sinirda }}.
USD/JPY'de 2024 → aralığının alt ucu önceden kayıtlı yordamla sıfırın hemen üstünde
({{ O.basarisiz.ay_sonu.parite.USDJPY.oos.ay_sonu.alt | r3 }}), ama sınırda: tohumların artı çıkma payı
{{ O.basarisiz.ay_sonu.parite.USDJPY.oos.ay_sonu.sinir.alt.pozitif_pay | yz0 }}, büyük tekrarlı kestirim
{{ O.basarisiz.ay_sonu.parite.USDJPY.oos.ay_sonu.sinir.alt.kesin | r3 }}; 2018–2023 aralığı sıfırı
kapsıyor{{? O.basarisiz.ay_sonu.parite.USDJPY.oos.ay_sonu.alt > 0 and O.basarisiz.ay_sonu.parite.USDJPY.oos.ay_sonu.sinir.alt.sinirda and O.basarisiz.ay_sonu.parite.USDJPY.is.ay_sonu.alt < 0 and O.basarisiz.ay_sonu.parite.USDJPY.is.ay_sonu.ust > 0 }}.
EUR/USD iki pencerede de sıfırı kapsıyor. AUD/USD iki pencerede de eksi: 2024 → aralığı sıfırın altında, 2018–2023'ün
üst ucu ({{ O.basarisiz.ay_sonu.parite.AUDUSD.is.ay_sonu.ust | r3 }}) sınırda (tohumların artı çıkma payı
{{ O.basarisiz.ay_sonu.parite.AUDUSD.is.ay_sonu.sinir.ust.pozitif_pay | yz0 }}). Brüt sonucu ise iki pencerede de artı
({{ O.basarisiz.ay_sonu.parite.AUDUSD.is.ay_sonu.brut | r3 }} ve
{{ O.basarisiz.ay_sonu.parite.AUDUSD.oos.ay_sonu.brut | r3 }} R): R'nin pip karşılığı küçük
({{ O.basarisiz.ay_sonu.parite.AUDUSD.tum.ay_sonu.R | s1 }} pip) ve makas geniş, maliyet bütün dönemde
{{ O.basarisiz.ay_sonu.parite.AUDUSD.tum.ay_sonu.maliyet | s3 }} R{{? O.basarisiz.ay_sonu.parite.AUDUSD.is.ay_sonu.ust < 0 and O.basarisiz.ay_sonu.parite.AUDUSD.oos.ay_sonu.ust < 0 and O.basarisiz.ay_sonu.parite.AUDUSD.is.ay_sonu.sinir.ust.sinirda and O.basarisiz.ay_sonu.parite.AUDUSD.is.ay_sonu.brut > 0 and O.basarisiz.ay_sonu.parite.AUDUSD.oos.ay_sonu.brut > 0 and O.basarisiz.ay_sonu.parite.EURUSD.is.ay_sonu.alt < 0 and O.basarisiz.ay_sonu.parite.EURUSD.oos.ay_sonu.alt < 0 and O.basarisiz.ay_sonu.parite.EURUSD.is.ay_sonu.ust > 0 and O.basarisiz.ay_sonu.parite.EURUSD.oos.ay_sonu.ust > 0 }}.

Maliyetten önce tablo daha düzgün: dört parite ve iki pencere, {{ O.basarisiz.ay_sonu.brut_hucre | n }} hücrenin
{% if O.basarisiz.ay_sonu.brut_arti == O.basarisiz.ay_sonu.brut_hucre %}hepsinde{% else %}{{ O.basarisiz.ay_sonu.brut_arti | n }}
tanesinde{% endif %} brüt sonuç artı; aynı kuralın öbür günlerinin brütü {{ O.basarisiz.ay_sonu.obur_brut[0] | r3 }} ile
{{ O.basarisiz.ay_sonu.obur_brut[1] | r3 }} R arasında. Dört paritenin brüt sonucu ay başına tek gözlemle (paritelerin
ortalaması) havuzlanınca 2018–2023'te {{ O.basarisiz.ay_sonu.brut_havuz.is.brut | r3 }} R (t
{{ O.basarisiz.ay_sonu.brut_havuz.is.t | s1 }}, {{ O.basarisiz.ay_sonu.brut_havuz.is.ay | n }} ay), 2024 →'de
{{ O.basarisiz.ay_sonu.brut_havuz.oos.brut | r3 }} R (t {{ O.basarisiz.ay_sonu.brut_havuz.oos.t | s1 }},
{{ O.basarisiz.ay_sonu.brut_havuz.oos.ay | n }} ay). Bu ölçü ön kayıtta yoktu; bir keşiftir ve öyle okunmalıdır.

Ay sonu ayrımı ailenin {{ O.basarisiz.ay_sonu.aile.n | n }} biçiminde ölçüldü (kural, parite, zaman dilimi; varsayılan
ve seçilen). Ay sonu ile öbür günlerin farkı %5 düzeyde örneklem içinde {{ O.basarisiz.ay_sonu.aile.is.p05 | n }},
örneklem dışında {{ O.basarisiz.ay_sonu.aile.oos.p05 | n }} biçimde anlamlı; şansın her pencerede beklediği
{{ O.basarisiz.ay_sonu.aile.sans_p05 | s1 }}. Holm düzeltmesiyle iki pencerede {{ O.basarisiz.ay_sonu.aile.is.holm | n }}
ve {{ O.basarisiz.ay_sonu.aile.oos.holm | n }}, yanlış keşif oranı {{ O.basarisiz.ay_sonu.aile.bh_q | yz0 }} olan
Benjamini–Hochberg düzeltmesiyle {{ O.basarisiz.ay_sonu.aile.is.bh | n }} ve {{ O.basarisiz.ay_sonu.aile.oos.bh | n }}
biçim kalıyor. Yanlış keşif oranı denetimi bağımsız sınamalar için kanıtlanmıştır (Benjamini ve Hochberg, 1995);
ailenin biçimleri aynı günleri paylaştığı için buradaki düzeltme yaklaşıktır. İki pencerede birden %5 düzeyde anlamlı olan biçim {{ O.basarisiz.ay_sonu.aile.iki_p05 | n }} (bağımsız
pencerelerde şansın beklediği {{ O.basarisiz.ay_sonu.aile.sans_iki | s2 }}); Bonferroni eşiğiyle iki pencerede birden
{{ O.basarisiz.ay_sonu.aile.iki_esik | n }}. Ailenin tutma ölçütünü (iki ayrık pencerede aralığın alt ucu sıfırın üstünde,
ay sonu ile öbür günlerin farkı düzeltilmiş eşiğin altında) sağlayan tek biçim GBP/USD'nin önceden kayıtlı
varsayılanıdır{{? len(O.karsi_olgu.ay_sonu_alt_kume.tutan_bugun) == 1 and O.karsi_olgu.ay_sonu_alt_kume.tutan_bugun[0].cift == "GBPUSD" and O.karsi_olgu.ay_sonu_alt_kume.tutan_bugun[0].kim == "varsayilan" }}.

Büyüklüğü küçüktür. GBP/USD'de bir ay sonu işlemi ortalama {{ O.basarisiz.ay_sonu.parite.GBPUSD.tum.ay_sonu.brut_pip | s1 }}
pip brüt kazanıyor, {{ O.basarisiz.ay_sonu.parite.GBPUSD.tum.ay_sonu.maliyet_pip | s1 }} pip maliyet ödüyor ve
{{ O.basarisiz.ay_sonu.parite.GBPUSD.tum.ay_sonu.net_pip | s1 }} pip net bırakıyor. Yılda
{{ O.basarisiz.ay_sonu.olcek.islem_yil | s0 }} işlem, yılda {{ O.basarisiz.ay_sonu.olcek.pip_yil | s0 }} pip ve yıllık
Sharpe {{ O.basarisiz.ay_sonu.olcek.sharpe_yil | s2 }}. Sonuç yıllara yayılıyor ama her yıl artı değil: 2022 ve 2023
eksi, öbür yedi yıl artı{{? O.basarisiz.ay_sonu.parite.GBPUSD.yil."2022" < 0 and O.basarisiz.ay_sonu.parite.GBPUSD.yil."2023" < 0 and O.basarisiz.ay_sonu.parite.GBPUSD.yil."2018" > 0 and O.basarisiz.ay_sonu.parite.GBPUSD.yil."2019" > 0 and O.basarisiz.ay_sonu.parite.GBPUSD.yil."2020" > 0 and O.basarisiz.ay_sonu.parite.GBPUSD.yil."2021" > 0 and O.basarisiz.ay_sonu.parite.GBPUSD.yil."2024" > 0 and O.basarisiz.ay_sonu.parite.GBPUSD.yil."2025" > 0 and O.basarisiz.ay_sonu.parite.GBPUSD.yil."2026" > 0 }}.
En iyi üç işlem çıkınca işlem başına {{ O.basarisiz.ay_sonu.parite.GBPUSD.uc_haric | r3 }} R kalıyor; dört paritenin
sonuçları birbirine doğru büzülünce (ampirik Bayes) GBP/USD'nin beklentisi {{ O.basarisiz.ay_sonu.buzulme.GBPUSD.buzulmus | r3 }} R
(gözlenen {{ O.basarisiz.ay_sonu.buzulme.GBPUSD.gozlenen | r3 }}).

Bir gerilim de var. Ay sonu etkisi ortak bir dolar akımıysa paritelerin aynı ay sonundaki sonuçları birlikte
hareket etmeli. Ay sonu net sonuçlarının korelasyonu GBP/USD ile USD/JPY arasında
{{ O.basarisiz.ay_sonu.ilinti_ozet.aday | s2 }}, öbür {{ O.basarisiz.ay_sonu.ilinti_ozet.obur_n | n }} çiftte
{{ O.basarisiz.ay_sonu.ilinti_ozet.obur_min | s2 }} ile {{ O.basarisiz.ay_sonu.ilinti_ozet.obur_max | s2 }}
arasında{{? abs(O.basarisiz.ay_sonu.ilinti_ozet.aday) < 0.05 and O.basarisiz.ay_sonu.ilinti_ozet.obur_min > 0 }}: sonucu en
güçlü olan GBP/USD ile USD/JPY'nin ay sonu sonuçları arasında bir ilinti görünmüyor. Bu bir çürütme değildir (akım paritelere farklı oranlarda ve
farklı aylarda dağılabilir), ama ortak bir akımın bu iki paritede aynı anda iz bıraktığı da bu ölçüyle desteklenmiyor.
Ölçü yalnız ortak bir dolar akımını sınar, aracıların fiksinglerde karşıladığı koşulsuz dolar talebi gibi (Krohn,
Mueller ve Whelan, 2024). Melvin ve Prins'in mekanizmasında akımın yönü her paritenin kendi hisse piyasasının ay içindeki
getirisine bağlıdır; o mekanizmada paritelerin birlikte hareket etmesi gerekmez.

{{! ay_sonu_eski_tanim kisa }}

Adayı tehdit eden şeyler adıyla:

- **Alt küme seçimi.** Ay sonu ayrımı ön kayıttaydı, ama bu derste ona odaklanma kararı iki pencere de görüldükten sonra
  verildi.
- **Eksi yıllar.** GBP/USD'de iki yıl üst üste eksi; etkinin kalıcı olduğu varsayılamaz.
- **Fiksing uygulaması.** Düzenleyiciler 2013'ten itibaren dünyanın en büyük bankalarından bazılarının döviz
  fiksingleri çevresindeki işlemlerini soruşturdu (Evans, 2018); fiksing öncesi hareketin yapısı o dönemden sonra değişmiş olabilir (hipotez).
- **Hesaplama penceresi.** Finansal İstikrar Kurulu, WM/R fiksinginin bir dakikalık hesaplama penceresinin
  genişletilmesini önerdi; piyasa görüşlerinin medyanı ana paralar için beş dakikaydı (FSB, 2014). Pencere 15 Şubat
  2015'te beş dakikaya çıktı (Krohn, Mueller ve Whelan, 2024); bu serinin örneklemi tamamen yeni pencerededir ve eski
  pencereden bir şey öğrenmez. Kenarın kaynakları bölümünde anılan fiksing öncesi eksi ilinti bulgusu (Evans, 2018)
  ise 2004–2013 verisinden, yani bir dakikalık pencerenin döneminden gelir.
- **Sinyal.** Kaynağın ay sonu öngörücüsü ayın hisse getirisidir (Melvin ve Prins, 2015); bu kural fiksinge giden
  mumun yönünü kullanır. Kaynağın sinyali bu seride sınanmadı; kuralın sonucu o mekanizmanın sınaması değildir.
- **Kapasite.** Fiksing anındaki derinlik ve büyük bir emrin fiyatı itmesi ölçülmedi.
- **Tek besleme.** Fiyatlar tek bir kaynağın kotasyonudur; fiksing dakikasında başka bir kaynağın makası farklı olabilir.
- **Çeyrek sonu.** Çeyrek sonları ay sonlarının alt kümesidir ({{ O.basarisiz.ay_sonu.ceyrek_sonu.GBPUSD | n }} gözlem,
  GBP/USD); ayrı sınanmadı.

Bu alt küme bir kural değil, bir adaydır: ileriye dönük bir sınamanın konusu.

## Sınama şartı: güç ve plan

Bir aday ancak görülmemiş veride, sonuç görülmeden yazılmış ve gücü önceden hesaplanmış bir planla sınanınca kural
olabilir. Gücün aritmetiği basittir. İşlem başına net etki $\mu$ ve standart sapma $\sigma$ olan bir kuralın ortalamasını
tek yönlü $\alpha$ düzeyinde ve $1 - \beta$ güçle sıfırdan ayırmak için gereken işlem sayısı

$$
\begin{aligned}
n &= \left(\frac{(z_{1-\alpha} + z_{1-\beta})\,\sigma}{\mu}\right)^{2}, \\
\mu_{\min}(n) &= \frac{(z_{1-\alpha} + z_{1-\beta})\,\sigma}{\sqrt{n}}
\end{aligned}
$$

olur; ikinci ifade $n$ işlemle görülebilecek **en küçük etkidir**. {{ O.basarisiz.guc.alfa | yz0 }} düzey ve
{{ O.basarisiz.guc.hedef | yz0 }} güç için $z_{1-\alpha}$ = {{ O.basarisiz.guc.z_alfa | s3 }}, $z_{1-\beta}$ =
{{ O.basarisiz.guc.z_guc | s3 }}. Bir etki bir anlamlılık eşiğinden geçtiği için ilan edildiyse ve onu bulan sınama
düşük güçlüyse, ölçülen büyüklüğün gerçeğinden büyük olması beklenir (Ioannidis, 2008); bu etkiye kazananın laneti
denir. Bu yüzden güç, gözlenen etkiyle birlikte büzülmüş ve daha küçük etkilerle de
hesaplanır.

GBP/USD ay sonu kuralında bütün dönemin ölçüsüyle $\sigma$ = {{ O.basarisiz.guc.gbp.sd | s2 }} R ve ayda bir işlem:

<div class="sayi-tablo">

| Senaryo | Net etki (R) | Gereken işlem | Süre (yıl) | Aile düzeltmeli eşikle (yıl) |
| :--- | ---: | ---: | ---: | ---: |
| Gözlenen | {{ O.basarisiz.guc.gbp.senaryo.gozlenen.mu | r3 }} | {{ O.basarisiz.guc.gbp.senaryo.gozlenen.n | s0 }} | {{ O.basarisiz.guc.gbp.senaryo.gozlenen.yil | s1 }} | {{ O.basarisiz.guc.gbp.senaryo.gozlenen.yil_esik | s1 }} |
| Büzülmüş | {{ O.basarisiz.guc.gbp.senaryo.buzulmus.mu | r3 }} | {{ O.basarisiz.guc.gbp.senaryo.buzulmus.n | s0 }} | {{ O.basarisiz.guc.gbp.senaryo.buzulmus.yil | s1 }} | {{ O.basarisiz.guc.gbp.senaryo.buzulmus.yil_esik | s1 }} |
| Gözlenenin yarısı | {{ O.basarisiz.guc.gbp.senaryo.yari.mu | r3 }} | {{ O.basarisiz.guc.gbp.senaryo.yari.n | s0 }} | {{ O.basarisiz.guc.gbp.senaryo.yari.yil | s1 }} | {{ O.basarisiz.guc.gbp.senaryo.yari.yil_esik | s1 }} |

</div>

_Tür: betimleme (hesap). Tek yönlü {{ O.basarisiz.guc.alfa | yz0 }} düzey, {{ O.basarisiz.guc.hedef | yz0 }} güç; σ ve etki bütün dönemin ay sonu işlemlerinden. Aile düzeltmeli eşik: ailenin
{{ O.basarisiz.ay_sonu.aile.n | n }} biçimi için Bonferroni, iki yönlü. Etkiler görülmüş veriden ölçüldü; güç bu yüzden
iyimserdir._

Tablonun en iyimser satırı bile yedi yıldan uzun bir sınama istiyor{{? O.basarisiz.guc.gbp.senaryo.gozlenen.yil > 7 }}. GBP/USD
ile USD/JPY birlikte sınansaydı (ayda iki işlem) gözlenen etkiyle {{ O.basarisiz.guc.havuz.yil | s1 }} yıl gerekirdi; bu
sayı daha da iyimserdir, çünkü bu iki parite görülmüş pencereden seçildi. Örneklem içinde anlamlı brüt kenarların örneklem
dışında ölçülen küçülmesi ({{ O.basarisiz.guc.gbp.kuculme.oran | yz0 }}, kenar bölümü) ay sonu brütüne uygulanırsa net
etki {{ O.basarisiz.guc.gbp.kuculme.net | r3 }} R olur{{? O.basarisiz.guc.gbp.kuculme.net < 0 }}: o senaryoda hiçbir süre
yetmez, çünkü kenar maliyetin altında kalır.

Bir yıllık sonuç neredeyse hiçbir şey söylemez. İlk yılın {{ O.basarisiz.guc.gbp.siklik | n }} işlemiyle %95 aralığının
yarı genişliği ±{{ O.basarisiz.guc.gbp.ilk_yil.yari_genislik | s2 }} R. Gözlenen etki gerçek olsa bile bu aralığın
alt ucunun sıfırın üstüne çıkma olasılığı {{ O.basarisiz.guc.gbp.ilk_yil.aralik_disla | s2 }}, tek yönlü {{ O.basarisiz.guc.alfa | yz0 }}
sınamanın etkiyi sıfırdan ayırma olasılığı {{ O.basarisiz.guc.gbp.ilk_yil.guc | s2 }}. Ölü bir kenar (brüt sıfır, net
{{ O.basarisiz.guc.gbp.ilk_yil.olu_net | r3 }} R) ilk yıl {{ O.basarisiz.guc.gbp.ilk_yil.olu_arti | s2 }} olasılıkla artı
görünür.

Her yıl sonuca bakmak da bir sınamadır. Her bakışta "anlamlı mı" diye sorup sınırı düzeltmemek, yanlış alarm
olasılığını düzeyin çok üstüne çıkarır (Armitage, McPherson ve Rowe, 1969). Çözüm, bakış sayısını önceden sabitleyip
sınırı erken bakışlarda sıkı, sonda gevşek kurmaktır: böyle bir yordamda toplam yanlış alarm olasılığı ve güç, aynı
gözlemle yapılan tek sınamanınkiyle neredeyse aynı kalır ve sınama erken bitebilir (O'Brien ve Fleming, 1979). Yılda bir bakan ve beş yılda biten bir planın z sınırları {{ O.basarisiz.guc.bakis.sinir[0] | s2 }},
{{ O.basarisiz.guc.bakis.sinir[1] | s2 }}, {{ O.basarisiz.guc.bakis.sinir[2] | s2 }}, {{ O.basarisiz.guc.bakis.sinir[3] | s2 }}
ve {{ O.basarisiz.guc.bakis.sinir[4] | s2 }}. Benzetimle: etki sıfırken planın yanlış alarm olasılığı
{{ O.basarisiz.guc.bakis.bos | s3 }}; gözlenen etkide gücü {{ O.basarisiz.guc.bakis.guc.gozlenen | s2 }}, büzülmüş etkide
{{ O.basarisiz.guc.bakis.guc.buzulmus | s2 }} (beş yılın sonunda tek bakışla {{ O.basarisiz.guc.bakis.sabit_ufuk.gozlenen | s2 }}
ve {{ O.basarisiz.guc.bakis.sabit_ufuk.buzulmus | s2 }}); ölü bir kenarda sınırı aşma olasılığı
{{ O.basarisiz.guc.bakis.guc.olu | s3 }}. Ara bakışların bedeli küçüktür, ama beş yılda bile güç hedefin ({{ O.basarisiz.guc.hedef | yz0 }}) altında kalıyor{{? O.basarisiz.guc.bakis.guc.gozlenen < O.basarisiz.guc.hedef }}.

{{! sekil neden-guc "Bir etkiyi görmek ne kadar sürer — ayda bir işlemle" }}

İşlem sıklığı gücün asıl belirleyicisidir:

{{! neden_mde }}

Ayda bir işlem yapan bir kuralda beş yılda görülebilecek en küçük etki {{ O.basarisiz.guc.mde.tablo.ayda.5 | s2 }} R; her
iş günü işlem yapan bir kuralda {{ O.basarisiz.guc.mde.tablo.gunde.5 | s2 }} R. Ama sık işlem yapan kuralın maliyeti de
sık ödenir ve kalın kuyruklu bir kuralda σ büyüktür: Londra ORB'nin örneklem dışı standart sapması
{{ O.basarisiz.guc.orb.sigma | s2 }} R ve {{ O.basarisiz.guc.orb.kenar | r }} R'lik bir etki için
{{ O.basarisiz.guc.orb.n | s0 }} işlem gerekir.

Görülmemiş veri de var: WM/R penceresinin beş dakikaya çıktığı Şubat 2015'ten (Krohn, Mueller ve Whelan, 2024) serinin
başlangıcına kadar {{ O.basarisiz.guc.gecmis.ay | n }} ay sonu. Gözlenen etkiyle bu verinin gücü {{ O.basarisiz.guc.gecmis.guc | s2 }}, yarı etkiyle
{{ O.basarisiz.guc.gecmis.guc_yari | s2 }}. Bu seride o sınama yapılmadı.

Bir sınama planı, sonuç görülmeden şunları yazar ve tarihler:

1. **Kuralın harfi.** Giriş, çıkış, R birimi ve alt kümenin tanımı (ayın hangi günü ay sonu sayılır).
2. **Pariteler.** Birincil parite ve ikincil olanlar, adıyla; ikincil sonuçlar hüküm vermez.
3. **Maliyet.** Ölçülmüş makas ve kayma modeli; kullanılacak yürütmenin kendisi.
4. **Süre.** Güç hesabından çıkan asgari işlem sayısı ve takvim.
5. **Bakışlar.** Bakış günleri ve her bakışın sınırı.
6. **Durdurma.** Sınır aşılırsa, süre dolarsa ya da etki önceden yazılmış bir eşiğin altına inerse ne olacağı.
7. **Aile.** Kaç biçimin sınandığı ve hangi düzeltmenin uygulanacağı.
8. **Takvim.** Tatil ve iş günü takviminin kaynağı, sonuçtan önce doğrulanmış olarak.
9. **Kayıt.** Planın kendisi ve sonuçların ayrı, değiştirilemez bir kaydı.

Ön kayıt, öngörüyü (sınamayı) sonradan açıklamadan (keşiften) ayırır (Nosek, Ebersole, DeHaven ve Mellor, 2018); bu
serinin bütün hükümleri o ayrımın üstüne kuruldu.

**Alıştırma 6.** GBP/USD ay sonu kuralında σ = {{ O.basarisiz.guc.gbp.sd | s2 }} R. Gerçek net etki
{{ O.basarisiz.guc.egri[2].mu | s2 }} R olsaydı, tek yönlü {{ O.basarisiz.guc.alfa | yz0 }} düzey ve {{ O.basarisiz.guc.hedef | yz0 }} güçle ayda bir işlemle kaç
yıl gerekirdi?

<details>
<summary>Çözüm</summary>

n = (({{ O.basarisiz.guc.z_alfa | s3 }} + {{ O.basarisiz.guc.z_guc | s3 }}) × {{ O.basarisiz.guc.gbp.sd | s2 }} /
{{ O.basarisiz.guc.egri[2].mu | s2 }})² ≈ {{! hesap carp O.basarisiz.guc.egri[2].yil 12 s0 }} işlem (yuvarlanmamış
değerlerle); ayda bir işlemle
{{ O.basarisiz.guc.egri[2].yil | s0 }} yıl. Etki yarıya inince gereken işlem dört katına çıkar: güç hesabında etkinin
karesi paydadadır.

</details>

## Kullanmadan önce: kontrol listesi

Bir gün içi kuralı kullanmadan önce cevabı ölçülmüş olması gereken on altı soru. İlk beşi sonuç görülmeden, sonraki
yedisi sonuç okunurken, son dördü kullanmadan önce sorulur.

**Sonuç görülmeden**

1. Kuralın harfi, parametreleri ve hüküm ölçütü tarihli olarak yazıldı mı?
2. Maliyet modeli ölçülmüş makası, dolum başına kaymayı ve haber penceresinin ek maliyetini taşıyor mu?
3. Kenarın kaynağı adıyla belli mi: yürütme, akış, bilgi ya da risk primi?
4. Gereken işlem sayısı ve süre güç hesabıyla bulundu mu?
5. Kaç kural, kaç parametre ve kaç alt kümenin deneneceği, yani ailenin büyüklüğü belli mi?

**Sonuç okunurken**

6. Net sonuç brütten ayrı okundu mu; isabet ile başabaş isabeti yan yana mı?
7. Kayıp yön, zamanlama ve maliyet paylarına ayrıldı mı?
8. Sonucun birimi pozisyon büyüklüğüyle uyumlu mu: sabit riskle (her işlem 1 R) işlem yapılacaksa R'deki iyileşme
   paradır; sabit nominalle yapılacaksa sonuç pip olarak da okundu mu?
9. En iyi bir ve en iyi üç işlem çıkınca sonuç ne oluyor?
10. Rastgele yön tabanı ve şansın beklediği sayı biliniyor mu?
11. Seçim örneklem dışına brüt mü taşıdı, maliyet tasarrufu mu?
12. Kuralın başabaş maliyeti, aralığının alt ucuyla, ödenen maliyetin üstünde mi?

**Kullanmadan önce**

13. Görülmemiş veride, önceden yazılmış bir planla sınandı mı?
14. Planın gücü, bakış takvimi ve durdurma kuralı yazılı mı?
15. Kendi yürütmenizin makası ve kayması ölçüldü mü? Bu serinin medyan maliyeti
    ({{ O.basarisiz.basabas.maliyet_pip.medyan | s1 }} pip) 10 pip'lik bir riskte işlem başına
    {{! hesap bol O.basarisiz.basabas.maliyet_pip.medyan 10 s2 }} R eder.
16. Kapasite ve akışın yapısal değişimi (düzenleme, hesaplama penceresi, katılımcılar) ölçüldü mü?

## Ölçülmeyenler

Bu dersin sınırları, serinin metodoloji dersindeki listeye ek olarak:

- **Görülmemiş veri.** 2015–2017 ay sonları ve serinin bitişinden sonraki aylar sınanmadı; güçleri yukarıda.
- **Gerçek yürütme.** Limit emir, kısmi dolum, son bakış, gecikme ve kendi makas ve kaymanız benzetilmedi.
- **Kapasite.** Hiçbir kuralda büyük bir emrin fiyatı itmesi ölçülmedi.
- **Kuralların birleşimi.** Netleşmenin hacme etkisi ölçüldü; birleşik bir kitabın sonucu, riski ve korelasyonu ölçülmedi.
- **Sınanmamış akışlar.** Tokyo fiksingi, opsiyon vade kesimi, çeyrek sonu ve endeks yeniden dengelemesi.
- **Literatürün kendi sonuçları.** Anılan çalışmaların bulguları kendi örneklemlerine aittir; bu serinin verisiyle
  yeniden üretilmedi.

## Kaynaklar

{{! kaynaklar fx-gunici-neden-basarisiz }}

_Yatırım tavsiyesi değildir. Ölçülen her şey geçmişe aittir; geçmiş sonuçlar gelecekteki sonuçların göstergesi
değildir._
