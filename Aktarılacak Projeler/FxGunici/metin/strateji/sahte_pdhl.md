### Ne

Başarısız kırılım, seviye olarak **dünün tepesi ve dibiyle**: fiyat önceki günün tepesinin üstünde (ya da dibinin
altında) kapanır, bir ya da iki mum içinde yeniden içeride kapanırsa ters yönde girilir. Yapı kırılımları
dersindeki önceki gün tepe/dip kuralının aynasıdır.

### Piyasa mantığı

Dünün uçları günlerdir izlenen seviyelerdir ve stop'ların en kalabalık olduğu yerlerden biridir. Bir günün tepesinin
kısa bir süre aşılıp geri dönülmesi grafik okumasında "likidite avı" (*liquidity grab*, *stop hunt*) diye anılır.
Bu kural o okumayı mekanik bir tanıma bağlar: aşılan seviye kapanışla geri alınırsa aşış başarısız sayılır.

### Kurallar

- **Seviye.** Önceki FX işlem gününün (17:00 → 17:00 New York) orta fiyattan tepesi ve dibi.
- **Kırılım, geri dönüş, stop.** Sahte ORB ile aynı.
- **Pencere.** Londra 08:00 → 14:00 New York; gün başına tek işlem.

{{! kural }}

Varsayılan: 15 dakikalık mumlar, iki mumluk pencere, 1R hedef.{{? B.varsayilan.tf == 15 and B.varsayilan.pencere == 2 and B.varsayilan.seviye == "pdhl" and B.varsayilan.hedef == "1R" and B.varsayilan.stop_turu == "sert" }}

### Örnekler

{{! sekil ornek "Örnek günler — Sahte PDH/PDL" }}

{{! ornek }}

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Dünün tepe ve dibi.** 17:00 New York'ta kapanan günün uçları.
2. **Kırılımı gör, girme; geri dönüşü bekle.** En çok iki mum içinde içeride kapanış.
3. **Stop gezintinin ucunda, hedef 1R.** Pencere 14:00 New York'ta kapanır (TSİ 21:00 ya da 22:00).
4. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
