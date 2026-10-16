### Ne

**Taban pivotları** (*floor pivots*), vadeli işlem salonlarında (çukurda, *pit*) işlem yapan aracıların günün
referans seviyelerini kâğıt kalemle hesaplamak için kullandığı formüllerdir ve bugün hemen her grafik
platformunda hazır gelir. Önceki günün tepesi (H), dibi (L) ve kapanışından (C):

$$P = \frac{H + L + C}{3}, \qquad R_1 = 2P - L, \qquad S_1 = 2P - H.$$

Kırılım kuralı fiyat bir seviyeyi kapanışla kestiğinde kesiş yönünde girer. Aynı seviyelerin dönüş kuralı fade
dersinde ayrıca sınanıyor.

### Piyasa mantığı

Pivotun bir iktisadi içeriği yoktur: P dünün ortalama fiyatına yakın bir noktadır, R1 ve S1 dünün aralığını P'nin
etrafında yansıtır. Kurala güç veren şey çok kişinin aynı seviyeye bakmasıdır — emirler orada birikir. Bu, kuralın
hem kırılım hem dönüş için savunulabilmesinin sebebidir: aynı birikim kesilince hızlandırır, kesilmeyince
geri iter. Hangisinin baskın olduğu bir inanç değil ölçü sorusudur.

### Kurallar

- **Seviyeler.** Önceki FX işlem gününün orta fiyattan H, L, C'si; P, R1, S1 yukarıdaki gibi (R2 ve S2 bu derste
  kullanılmıyor).
- **Seviye seçimi.** Yalnız P ya da R1 ile S1 birlikte.
- **Sinyal.** Kapanışın seviyeyi kesmesi: bir önceki kapanış seviyenin öbür yanında (ya da tam seviyede). R1 yalnız
  yukarı kesişte alış, S1 yalnız aşağı kesişte satış verir; P iki yönde de.
- **Stop.** Sinyal mumunun karşı ucu.
- **Pencere.** Londra 08:00 → 14:00 New York; her seviye için günde tek işlem.

{{! kural }}

Varsayılan R1 ve S1'i kullanır ve 2R hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.seviye == "R1S1" and B.varsayilan.tur == "kirilim" and B.varsayilan.hedef == "2R" and B.varsayilan.stop_turu == "sert" }} R1'in üstünde ya da S1'in altında kapanış, fiyatın dünün aralığının
P çevresinde yansıtılmış hâlinden — genişliği dünün aralığı kadar olan banttan — çıktığı anlamına gelir.

### Örnekler

{{! sekil ornek "Örnek günler — Pivot kırılımı" }}

{{! ornek }}

Figürdeki mavi çizgi kesilen seviyedir (R1 ya da S1).

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Seviyeleri hesapla.** Dünün tepe, dip ve kapanışından P, R1, S1 (gün 17:00 New York'ta kapanır: TSİ yazın
   00:00, kışın 01:00).
2. **Pencere.** Londra 08:00 → 14:00 New York.
3. **Kesişi bekle.** R1'in üstünde ya da S1'in altında kapanış; önceki kapanış seviyenin öbür yanında.
4. **Stop sinyal mumunun karşı ucunda, hedef 2R.**
5. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
