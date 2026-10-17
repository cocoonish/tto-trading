### Ne

**İç mum** (*inside bar*), aralığı bir önceki mumun aralığının tamamen içinde kalan mumdur: tepesi öncekinin
tepesinden aşağıda, dibi öncekinin dibinden yukarıda. Önceki muma **ana mum** (*mother bar*) denir. Kural, iç
mumdan sonra fiyat referans aralığın dışında kapanırsa kırılım yönünde işleme girer. Toby Crabel'in kısa vadeli
fiyat desenleri kitabı (1990) aynı deseni günlük mumlarda "iç gün" (*inside day*) adıyla kullanır; burada tanım gün
içi mumlara uygulanıyor.

### Piyasa mantığı

İç mum bir sıkışmadır: bir mum boyunca alıcı da satıcı da ana mumun uçlarını zorlamadı. Kırılım savunusu,
sıkışmanın bir enerji birikimi olduğunu ve aralık bozulduğunda yönün hızlı açılacağını söyler; stopun yakın
olması (aralık küçük) da kuralı cazip kılar — küçük bir riskle büyük bir hareket yakalama vaadi. Karşı savunu
aynı yerden gelir: dar bir aralığın iki ucu da kolayca aşılır ve gün içi mumlarda iç mum sık oluşur —
{{! gun_ici }}{{? E.varsayilan.oos.n > E.varsayilan.oos.n_gun }}. Sık oluşan bir desenin "bilgi" taşıdığı varsayımı ölçülmeden kabul edilemez.

### Kurallar

- **İç mum.** Tepe ana mumun tepesinden aşağıda, dip ana mumun dibinden yukarıda (eşitlik iç mum sayılmaz);
  iki mum aynı FX işlem gününde.
- **Referans.** İç mumun kendi uçları ya da ana mumun uçları.
- **Sinyal.** İç mumdan sonraki "geçerlilik" kadar mumun içinde referansın dışında kapanan ilk mum; o pencerede
  kapanış gelmezse desen iptal.
- **Stop.** Referansın karşı ucu (alışta referansın dibi, satışta tepesi).
- **Hedef.** 1R, 2R ya da zaman ({{ ON.genel.desen_zaman_mum | n }} mum).
- **Seans.** Londra + New York (ana mum Londra 08:00'den sonra, sinyal mumu en geç 12:00 New York'ta kapanır;
  {{! tsi "→" "Londra 08:00" "New York 12:00" }}) ya da bütün gün (sinyal en geç 16:00 New York;
  {{! tsi "" "New York 16:00" }}).
- Gün içinde birden çok desen olabilir; aynı anda tek pozisyon taşınır.

{{! kural }}

Varsayılan ana mumun uçlarını referans alır, üç mumluk geçerlilik verir, Londra + New York seansında arar ve 2R
hedefler.{{? B.varsayilan.tf == 15 and B.varsayilan.referans == "ana" and B.varsayilan.gecerlilik == 3 and B.varsayilan.seans == "londra_ny" and B.varsayilan.hedef == "2R" and B.varsayilan.stop_turu == "sert" }} Ana mumun uçları ders kitabının referansıdır: iç mumun kendi aralığı çok dardır ve
stopu gürültünün içine koyar.

### Örnekler

{{! sekil ornek "Örnek günler — İç mum" }}

{{! ornek }}

Figürde noktalı mavi çizgiler referansın (ana mumun) iki ucu (ana mumdan başlar), mavi bant sinyal mumudur. Figürdeki işlem o
günün işlemlerinden biridir; aynı gün başka desenler de işleme dönüşmüş olabilir (aynı anda tek pozisyon).
Kaybeden örnek lehine yarım R'ye ulaşmadan zararla kapanan işlem, tuzak örneği önce lehine en az yarım R gidip
zararla kapanan işlemdir.

### Sonuçlar

{{! sonuclar }}

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Seans.** Londra 08:00'den (TSİ 10:00 ya da 11:00, İngiltere'nin saatine göre) 12:00 New York'a (TSİ
   19:00 ya da 20:00, ABD'nin saatine göre) kadar.
4. **Deseni say.** Tepe ve dip ikisi birden öncekinin içinde; eşit uç desen değildir.
5. **Referans ana mum.** Üç mum içinde ana mumun dışında kapanış yoksa desen bitti.
6. **Stop karşı uçta, hedef 2R.**
7. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
