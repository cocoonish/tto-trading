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

- **VWAP ve bant.** Çapadan (FX günü başı 17:00 New York ya da Londra 08:00) bu yana her dakikanın tipik fiyatı
  (tepe + dip + kapanış) / 3, hacimle ağırlıklı ortalama; σ aynı ağırlıklarla standart sapma. Bant VWAP ± k·σ.
- **Isınma.** Çapadan sonraki ilk 60 dakika sinyal yok (ortalama ve sapma birkaç dakikalık veriyle anlamsızdır).
- **Sinyal.** Kapanış bandın dışına çıkar; sonra bandın **içine** kapanan ilk mum VWAP yönünde giriş verir.
- **Stop.** Bant dışı gezintinin ucu (yukarı gezintide en yüksek tepe).
- **Hedef.** "VWAP": sinyal anındaki VWAP seviyesi; ya da 1R, 2R, zaman. Sinyal en geç 16:00 New York.

{{! kural }}

Varsayılan VWAP'ı Londra açılışında başlatır, bandı 2σ'da kurar ve hedefi sinyal anındaki VWAP'a koyar.{{? B.varsayilan.tf == 15 and B.varsayilan.capa == "londra" and B.varsayilan.k == 2.0 and B.varsayilan.hedef == "vwap" and B.varsayilan.stop_turu == "sert" }}
VWAP hedefinin R cinsinden uzaklığı işlemden işleme değişir: bant dışı gezinti uzunsa stop girişten uzaklaşır ve
VWAP hedefi risk biriminde yakınlaşır.

### Örnekler

{{! sekil ornek "Örnek günler — VWAP dönüşü" }}

{{! ornek }}

Figürde mavi çizgiler sinyal anındaki bandın iki ucudur; hedef sinyal anındaki VWAP'tır.

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Çapa Londra 08:00** (TSİ 10:00 ya da 11:00); ilk saat sinyal yok.
2. **Bandın dışına çıkışı izle, girme.** Giriş bandın içine kapanışta.
3. **Stop gezintinin ucunda, hedef VWAP.**
4. **Hacmin ne olduğunu unutma.** FX'te merkezî hacim yok; bu VWAP bir likidite ağırlıklı ortalamadır.
5. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
