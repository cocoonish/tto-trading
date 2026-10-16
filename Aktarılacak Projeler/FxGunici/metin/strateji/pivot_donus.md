### Ne

Klasik (salon) pivotlarının (yapı kırılımları dersinde tanımlandı: P, R1, S1) dönüş kuralı: fiyat seviyeye **değer**
ama geldiği yanda kapanırsa seviyeden geri dönüş yönünde girilir. R1'e yükselip altında kapanan mum satış,
S1'e düşüp üstünde kapanan mum alış verir.

### Piyasa mantığı

Kırılım kuralı seviyedeki emir birikiminin kesilince hızlandırdığını, dönüş kuralı kesilmeyince geri ittiğini
varsayar. Dönüş kuralının hedefi doğal olarak bir sonraki seviyedir: R1'den dönen fiyatın hedefi P, P'den
dönenin hedefi R1 ya da S1. Kuralın zayıf noktası, seviyeye değip geri dönen mumun bir dönüşün başı mı yoksa
kırılımdan önceki son duraklama mı olduğunu kapanışta bilememesidir.

### Kurallar

- **Seviyeler.** Önceki FX işlem gününün orta fiyattan H, L, C'sinden P, R1, S1.
- **Sinyal.** R1: tepe R1'e ulaşır (ya da geçer), kapanış R1'in altında ve önceki kapanış da altında → satış.
  S1: dip S1'e ulaşır, kapanış ve önceki kapanış S1'in üstünde → alış. P: yukarıdan değip üstünde kapanış alış,
  aşağıdan değip altında kapanış satış.
- **Stop.** Sinyal mumunun seviye ötesindeki ucu (R1 dönüşünde mumun tepesi).
- **Hedef.** "Seviye": R1 ve S1 dönüşünde P; P dönüşünde R1 ya da S1. Ya da 1R, 2R, zaman.
- **Pencere.** Londra 08:00 → 14:00 New York; her seviye için günde tek işlem.

{{! kural }}

Varsayılan R1 ve S1'den dönüşü arar ve P'yi hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.seviye == "R1S1" and B.varsayilan.tur == "donus" and B.varsayilan.hedef == "seviye" and B.varsayilan.stop_turu == "sert" }} Stop sinyal mumunun ucunda olduğu için risk küçüktür ve
P'ye kadar olan yol risk biriminde uzundur: dört paritenin işlemlerinde hedefin uzaklığı {{! hedef_uzaklik }}.
Bu kural, adı "dönüş" olsa da, kısa bir hedefi değil uzak bir hedefi küçük bir stop'la oynar.

### Örnekler

{{! sekil ornek "Örnek günler — Pivot dönüşü" }}

{{! ornek }}

Figürde noktalı mavi çizgiler dönüşün yaşandığı seviye ile hedef seviye (P), mavi bant sinyal mumudur.
Kaybeden örnek lehine yarım R'ye ulaşmadan zararla kapanan işlem, tuzak örneği önce lehine en az yarım R gidip
zararla kapanan işlemdir: seviyeden geri dönüş başlıyor, sonra fiyat seviyeyi kesip stop'u alıyor.

### Sonuçlar

{{! sonuclar }}

Yapı kırılımları dersindeki pivot kırılımı kuralıyla birlikte okunmalı: aynı seviyelere zıt iki bahis.

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Seviyeleri hesapla.** Dünün tepe, dip ve kapanışından P, R1, S1.
4. **Değişi bekle, kapanışa bak.** Seviyeye değen mum seviyenin geldiği yanında kapanmalı; önceki kapanış da o yanda.
5. **Stop mumun seviye ötesindeki ucunda, hedef P.**
6. **Pencere.** Londra 08:00 → 14:00 New York (TSİ 10:00 ya da 11:00 → 21:00 ya da 22:00).
7. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
