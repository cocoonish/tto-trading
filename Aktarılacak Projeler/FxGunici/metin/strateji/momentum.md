### Ne

**Gün içi momentum**: günün ilk hareketinin yönü günün sonraki bir dilimini öngörür mü? Hisse piyasasında Gao, Han,
Li ve Zhou (2018) S&P 500 borsa yatırım fonunda ilk yarım saatin getirisinin son yarım saatin getirisini
öngördüğünü gösterdi; FX'te aynı soruyu soran çalışmalar da var (Elaut, Frömmel ve Lampaert, 2018). Bu dersin
kuralı FX'in kendi saatlerine taşınmış hâlidir: Londra açılışının ilk mumu, New York öğleden sonrasının yönü.

### Piyasa mantığı

İki savunu var. Birincisi bilgi: Londra açılışı günün ilk büyük bilgi ve akış anıdır, ilk hareket bilgili akışın
yönünü taşıyorsa o yön gün boyunca yeniden fiyatlanmaya devam eder. İkincisi geç kalan akış: yönü sabah belli olan
bir hareketi öğleden sonra tamamlayan katılımcılar (portföyünü gün sonu kapanışına göre ayarlayanlar) ilk yönü
uzatır. Karşı savunu basit: sinyal mumunun kapanışından girişe sekiz saat geçer (Londra 09:00 → New York 12:00; {{! tsi "→" "Londra 09:00" "New York 12:00" }};
Londra ile New York arasındaki farkın dört saate indiği ara haftalarda yedi saat) ve ilk mumun bilgisi o arada
çoktan fiyatlanmıştır.

### Kurallar

- **Sinyal.** Londra 08:00'den ({{! tsi "" "Londra 08:00" }}) itibaren ilk mumun getirisi (kapanış − açılış);
  60 dakikalık mumda ilk saat.
  Getiri sıfırsa işlem yok.
- **Giriş.** Getirinin yönünde, 12:00 New York ({{! tsi "" "New York 12:00" }}).
- **Çıkış.** 16:00 ya da 16:55 New York ({{! tsi "ya da" "New York 16:00" "New York 16:55" }}); stopsuz (ızgarada sert ve kapanış stopu da var: 1 × ATR).
- **R birimi.** Girişteki ATR(14, 60 dakikalık mumlar).

{{! kural }}

Varsayılan Londra'nın ilk saatini kullanır ve 12:00 → 16:00 New York ({{! tsi "→" "New York 12:00" "New York 16:00" }}) arasında taşır.{{? B.varsayilan.tf == 60 and B.varsayilan.cikis_et == "16:00" and B.varsayilan.stop_turu == "yok" }}

### Örnekler

{{! sekil ornek "Örnek günler — Gün içi momentum" }}

{{! ornek }}

Noktalı mavi çizgiler Londra'nın ilk mumunun tepesi ve dibi, mavi bant o mumun kendisidir; giriş sekiz saat
sonra gelir. Kuralın stopu olmadığı için figürde stop çizgisi yoktur; R birimi girişteki ATR'dir. Kaybeden örnek lehine yarım R'ye ulaşmadan zararla kapanan işlem, tuzak örneği önce lehine en az yarım R gidip zararla kapanan işlemdir.

### Sonuçlar

{{! sonuclar }}

### Öngörü gücü

Ön kayıt, kuralın kendisinden ayrı olarak sinyalin öngörü gücünü bir regresyonla sordu: öğleden sonra getirisi
(12:00 → çıkış, orta fiyat) ilk mumun getirisinin bir fonksiyonu mu? İki getiri de girişteki 60 dakikalık
ATR(14)'e bölünür, yani yıllar ve pariteler arasında aynı birimdedir. Bu ölçü stop, hedef, makas ve kayma içermez: işlem kuralının
sonucundan bağımsız olarak "bilgi var mı" sorusunu sorar.

$$\frac{r_{\text{öğleden sonra}}}{\text{ATR}} = \alpha + \beta \cdot \frac{r_{\text{ilk mum}}}{\text{ATR}} + \varepsilon$$

Standart hata Newey–West (HAC) ile, Bartlett çekirdeği ve ⌊4·(n/100)^(2/9)⌋ gecikmeyle: komşu günlerin hataları
ilintiliyse sıradan standart hata eğimi olduğundan kesin gösterir.

{{! regresyon }}

_β: ilk mumdaki bir ATR'lik hareketin öğleden sonraya taşıdığı ATR. İşaret tutturma: ilk mumla öğleden sonranın aynı
yönde olduğu günlerin payı (sinyalin maliyetsiz isabeti)._

{% if E.varsayilan.regresyon.oos.p_beta >= 0.05 %}EUR/USD'de örneklem dışı eğim sıfırdan ayırt edilemiyor (p {{ E.varsayilan.regresyon.oos.p_beta | s2 }}).{{? E.varsayilan.regresyon.oos.p_beta >= 0.05 }}{% else %}EUR/USD'de örneklem dışı eğim sıfırdan ayırt ediliyor (p {{ E.varsayilan.regresyon.oos.p_beta | s2 }}); işareti ve büyüklüğü tablodadır.{{? E.varsayilan.regresyon.oos.p_beta < 0.05 }}{% endif %}
R² değerleri ilk mumun öğleden sonra hareketinin ne kadarını açıkladığını gösterir; gün içi getiride yüzde birin
altındaki bir R² bile bir kenar olabilir, ama ancak maliyetten sonra ve örneklem dışında artı kalırsa.

### Koşullar

{{! kosullar }}

### Kontrol listesi

1. **Hüküm.** {{! kontrol_hukum }}
2. **Ne zaman.** {{! ne_zaman }}
3. **Londra'nın ilk saatini oku.** 08:00–09:00 Londra: TSİ 10:00–11:00 (İngiltere yaz saati) ya da 11:00–12:00.
4. **12:00 New York'ta gir** (TSİ 19:00 ya da 20:00, ABD'nin saatine göre), **16:00'da çık** (TSİ 23:00 ya da 00:00).
5. **Stop yok, R birimi ATR.** Pozisyon büyüklüğü girişteki 60 dakikalık ATR'den kurulur.
6. **Maliyet.** {{! basabas }}

### Hüküm

{{! hukum_cumle }}

{{! hukum }}
