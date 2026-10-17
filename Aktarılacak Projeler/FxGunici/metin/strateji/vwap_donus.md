### Ne

**VWAP** (*volume-weighted average price*, hacim ağırlıklı ortalama fiyat), bir çapadan bu yana işlem görmüş
fiyatların hacimle ağırlıklı ortalamasıdır. Hisse piyasalarında kurumsal emirlerin yürütme ölçütüdür: büyük bir
emir "VWAP'tan iyi" dolduysa iyi yürütülmüş sayılır. Dönüş kuralı fiyatın VWAP'tan istatistiksel olarak uzaklaşıp
geri gelmeye başladığı anda VWAP yönünde girer.

### Piyasa mantığı

Fiyat VWAP'tan uzaklaştıkça, gün boyu VWAP'a göre emir yürüten katılımcılar için ortalamanın altında alma (ya da
üstünde satma) fırsatı büyür; dönüş savunusu bu akışın fiyatı ortalamaya geri çektiğini söyler. Bu savunu hisse
piyasası için kurulmuştur ve FX'e taşınırken iki zayıflık taşır. Birincisi hacim: FX'te merkezî bir işlem hacmi
yoktur; burada ağırlık Dukascopy'nin kotasyonlarındaki likidite miktarıdır, gerçekleşmiş işlem hacmi değil —
yalnız işlem yoğunluğunun bir vekilidir. İkincisi çapa: FX'in bir açılış çanı yoktur, VWAP'ın hangi andan
başlatılacağı bir seçimdir ve ızgarada iki çapa sınanıyor.

### Kurallar

- **VWAP ve bant.** Çapadan (FX günü başı 17:00 New York ya da Londra 08:00;
  {{! tsi "ya da" "New York 17:00" "Londra 08:00" }}) bu yana her dakikanın tipik fiyatı
  (tepe + dip + kapanış) / 3, hacimle ağırlıklı ortalama; σ aynı ağırlıklarla standart sapma. Bant VWAP ± k·σ.
- **Isınma.** Çapadan sonraki ilk 60 dakika sinyal yok ve kuralın durumu da o saat dolunca başlar: ilk saatte
  bandın dışına çıkış bir gezinti başlatmaz (ortalama ve sapma birkaç dakikalık veriyle anlamsızdır).
- **Sinyal.** Kapanış bandın dışına çıkar; sonra çıkılan bandın berisine kapanan ilk mum VWAP yönünde giriş verir
  (yukarı gezintide kapanışı üst bandın üstünde olmayan ilk mum; alt bandın da altında kapansa bile).
- **Stop.** Bant dışı gezintinin ucu (yukarı gezintide en yüksek tepe).
- **Hedef.** "VWAP": sinyal anındaki VWAP seviyesi; ya da 1R, 2R, zaman ({{ ON.genel.desen_zaman_mum | n }} mum). Seviye yürütülen girişin (makas ve kayma dahil) gerisinde ya da tam üstündeyse işlem yok; atılan sinyal sayısı bu yüzden kaymaya bağlıdır. Sinyal en geç 16:00 New York
  ({{! tsi "" "New York 16:00" }}).

{{! kural }}

Varsayılan VWAP'ı Londra açılışında başlatır, bandı 2σ'da kurar ve hedefi sinyal anındaki VWAP'a koyar.{{? B.varsayilan.tf == 15 and B.varsayilan.capa == "londra" and B.varsayilan.k == 2.0 and B.varsayilan.hedef == "vwap" and B.varsayilan.stop_turu == "sert" }}
VWAP hedefinin R cinsinden uzaklığı işlemden işleme değişir: bant dışı gezinti uzunsa stop girişten uzaklaşır ve
VWAP hedefi risk biriminde yakınlaşır. Dört paritenin işlemlerinde hedefin uzaklığı {{! hedef_uzaklik }}: bu
bir "kısa hedef" değildir, çoğu işlemde 1R'nin ötesindedir.

### Örnekler

{{! sekil ornek "Örnek günler — VWAP dönüşü" }}

{{! ornek }}

Figürde noktalı mavi çizgiler sinyal anındaki bandın iki ucu ve VWAP'ın kendisi (sinyal mumundan başlar: VWAP ve bant gün içinde yürür, figür sinyal anındaki değeri gösterir), yeşil çizgi hedeftir
(sinyal anındaki VWAP); mavi bant bandın içine kapanan sinyal mumudur. Kaybeden örnek lehine yarım R'ye
ulaşmadan zararla kapanan işlem, tuzak örneği önce lehine en az yarım R gidip zararla kapanan işlemdir: fiyat
{{! tuzak "ortalamaya dönmeye başlıyor, sonra gezinti yeniden başlayıp stopu alıyor." "ortalamaya dönmeye başlıyor ama dönüş sürmüyor; işlem stopa değmeden zararla kapanıyor ({cikis})." }}

### Sonuçlar

{{! sonuclar }}

**Ön kaydın harfiyle.** Ön kaydın harfi iki yerde bu dersteki okumadan farklı okunabilir; iki okuma da ilk
sonuçlardan önce sabitlendi ve hüküm onlarla verilir. Birincisi ilk saat: ön kayıt "çapadan sonraki ilk 60 dakika
sinyal yok" der ve yalnız sinyali yasaklar. Bu ölçüm ilk saatte kuralın durumunu da sıfırlar (yukarıda, ısınma);
harfiyle okunursa bant dışı gezinti çapadan başlar ve ilk saatte başlayan bir gezinti, bandın berisine ilk saatten
sonra kapanırsa sinyal verir. İkincisi bandın içine dönüş: harf "bandın içine kapanan ilk mum" der, yani dönüş mumu
iki bandın arasında kapanır; karşı bandın ötesinde kapanan mum sinyal vermez ve o yanda yeni bir gezinti başlatır.
Bu ölçüm yalnız çıkılan bandı sorar. Harfin iki okuması aynı koşuda ayrıca, her biri tek başına ölçüldü.
{{! yorum_cumle }}

{{! yorum }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Çapa Londra 08:00** (TSİ 10:00 ya da 11:00, İngiltere'nin saatine göre); ilk saat sinyal yok.
4. **Bandın dışına çıkışı izle, girme.** Giriş çıkılan bandın berisine kapanışta.
5. **Stop gezintinin ucunda, hedef VWAP.**
6. **Hacmin ne olduğunu unutma.** FX'te merkezî hacim yok; bu VWAP bir likidite ağırlıklı ortalamadır.
7. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
