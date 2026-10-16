### Ne

Aynı başarısız kırılım kuralı, seviye olarak **Asya aralığıyla** (Londra 00:00 → 08:00): Londra açıldıktan sonra
fiyat gecenin aralığının dışında kapanır, bir ya da iki mum içinde yeniden içeride kapanırsa ters yönde girilir.
Kırılım dersindeki Asya aralığı kuralının aynasıdır.

### Piyasa mantığı

Asya aralığı geceden kalan stop emirlerinin haritasıdır: gece pozisyon taşıyan herkes stop'unu gecenin tepesinin
üstüne ya da dibinin altına koyar. Londra'nın ilk saatinde bu uçların sınanması, Avrupa masalarının o likiditeyi
kullanmasıdır; yeni bir bilgi yoksa fiyat aralığa geri döner. Asya aralığının ORB'den farkı genişliğidir: sekiz
saatlik aralığın uçları açılıştaki fiyattan uzak olabilir ve o uçlara gün içinde hiç uzanılmayabilir.

### Kurallar

- **Seviye.** Londra 00:00 → 08:00 arasındaki 1 dakikalık orta fiyatların en yükseği ve en düşüğü (TSİ'de yazın
  02:00 → 10:00, kışın 03:00 → 11:00).
- **Kırılım, geri dönüş, stop.** Sahte ORB ile aynı: dışarıda kapanış, en çok "pencere" kadar mum içinde içeride
  kapanış, stop gezintinin ucunda.
- **Pencere.** Londra 08:00 → 14:00; gün başına tek işlem.

{{! kural }}

Varsayılan: 15 dakikalık mumlar, iki mumluk pencere, 1R hedef.{{? B.varsayilan.tf == 15 and B.varsayilan.pencere == 2 and B.varsayilan.seviye == "asya" and B.varsayilan.hedef == "1R" and B.varsayilan.stop_turu == "sert" }}

### Örnekler

{{! sekil ornek "Örnek günler — Sahte Asya" }}

{{! ornek }}

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Gece aralığı.** Londra 00:00 → 08:00 tepe ve dip.
2. **Kırılımı gör, girme; geri dönüşü bekle.** En çok iki mum içinde aralığın içinde kapanış.
3. **Stop gezintinin ucunda, hedef 1R.** Pencere Londra 14:00'te kapanır.
4. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
