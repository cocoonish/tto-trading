### Ne

**İç mum** (*inside bar*), aralığı bir önceki mumun aralığının tamamen içinde kalan mumdur: tepesi öncekinin
tepesinden aşağıda, dibi öncekinin dibinden yukarıda. Önceki muma **ana mum** (*mother bar*) denir. Kural, iç
mumdan sonra fiyat referans aralığın dışında kapanırsa kırılım yönünde işleme girer. Toby Crabel'in kısa vadeli
fiyat desenleri kitabı (1990) aynı deseni günlük mumlarda "iç gün" (*inside day*) adıyla kullanır; burada tanım gün
içi mumlara uygulanıyor.

### Piyasa mantığı

İç mum bir sıkışmadır: bir mum boyunca alıcı da satıcı da ana mumun uçlarını zorlamadı. Kırılım savunusu,
sıkışmanın bir enerji birikimi olduğunu ve aralık bozulduğunda yönün hızlı açılacağını söyler; stop'un yakın
olması (aralık küçük) da kuralı cazip kılar — küçük bir riskle büyük bir hareket yakalama vaadi. Karşı savunu
aynı yerden gelir: dar bir aralığın iki ucu da kolayca aşılır ve gün içi mumlarda iç mum çok sık oluşur (bu
kural EUR/USD'de örneklem dışında işlem günü sayısından fazla işlem açıyor){{? E.varsayilan.oos.n > E.varsayilan.oos.n_gun }}; desenin bir "bilgi" taşıdığı
varsayımı ölçülmeden kabul edilemez.

### Kurallar

- **İç mum.** Tepe ana mumun tepesinden aşağıda, dip ana mumun dibinden yukarıda (eşitlik iç mum sayılmaz);
  iki mum aynı FX işlem gününde.
- **Referans.** İç mumun kendi uçları ya da ana mumun uçları.
- **Sinyal.** İç mumdan sonraki "geçerlilik" kadar mumun içinde referansın dışında kapanan ilk mum; o pencerede
  kapanış gelmezse desen iptal.
- **Stop.** Referansın karşı ucu (alışta referansın dibi, satışta tepesi).
- **Seans.** Londra + New York (ana mum Londra 08:00'den sonra, sinyal mumu en geç 12:00 New York'ta kapanır) ya
  da bütün gün (sinyal en geç 16:00 New York).
- Gün içinde birden çok desen olabilir; aynı anda tek pozisyon taşınır.

{{! kural }}

Varsayılan ana mumun uçlarını referans alır, üç mumluk geçerlilik verir, Londra + New York seansında arar ve 2R
hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.referans == "ana" and B.varsayilan.gecerlilik == 3 and B.varsayilan.seans == "londra_ny" and B.varsayilan.hedef == "2R" and B.varsayilan.stop_turu == "sert" }} Ana mumun uçları ders kitabının referansıdır: iç mumun kendi aralığı çok dardır ve
stop'u gürültünün içine koyar.

### Örnekler

{{! sekil ornek "Örnek günler — İç mum" }}

{{! ornek }}

Figürde mavi çizgiler referansın (ana mumun) iki ucudur. Figürdeki işlem o günün işlemlerinden biridir; aynı
gün başka desenler de işleme dönüşmüş olabilir (aynı anda tek pozisyon).

### Sonuçlar

{{! sonuclar }}

{{! havuz_cumle }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Seans.** Londra 08:00'den (TSİ yazın 10:00, kışın 11:00) 12:00 New York'a (TSİ 19:00 ya da 20:00) kadar.
2. **Deseni say.** Tepe ve dip ikisi birden öncekinin içinde; eşit uç desen değildir.
3. **Referans ana mum.** Üç mum içinde ana mumun dışında kapanış yoksa desen bitti.
4. **Stop karşı uçta, hedef 2R.**
5. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
