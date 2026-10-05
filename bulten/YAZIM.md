# Bülten yazım rehberi

Bu dosya, günlük ve haftalık bülteni **yazan** katmanın görev tarifidir. Bültenin
ölçülen kısmı (piyasa fotoğrafı, takvim, göstergeler, dünden bu yana gelen veriler) otomatik
koşudan gelir ve yazan taraf ona **dokunmaz**. Yazan taraf şu alanları doldurur:
`manset`, `ozet.ne_oldu`, `yorum`, `gundem` (günlük: Türkiye · Küresel · Emtia ·
Bugün ve önümüzdeki günler · Risk; haftalık sayının kendi bölüm seti için bkz.
"Haftaya bakış (haftalık kip)"), okumayı bir işlem yapısına çeviren `fikirler`
ve açık bir fikrin erken kapanışı `fikir_kapat` (bkz. "İşlem fikirleri (biçim
3)") ve — yalnız yayımlanmış bir sayı düzeltiliyorsa — `duzeltmeler`.

Hedef kitle profesyonel trader ve portföy yöneticisi. Yazdığın şey bir **sabah
notudur**: hükümle açılan, her olguyu bir kez söyleyen, ne fiyatlandığını ve
riskin hangi yöne asimetrik olduğunu söyleyen bir not. Okurun yedi–on dakikası
var (pazar sayısı ayrıdır: 30–45 dakikalık haftalık rapor). Uzunluk kendi başına değer değildir; **ayrıntı** değerdir — ama ayrıntı
tekrarla değil YENİ olguyla gelir (bkz. "Ayrıntı: notu ne uzatır, ne uzatmaz").

---

## Akış

0. **Önce zincire bak: `python3 bulten/zincir.py`.** Tek komut, ağsız, saniye
   sürer. Bülten üç halkalı bir zincirdir — veri tazeleme → ölçüm → yazı — ve
   ilk iki halka GitHub'ın zamanlanmış tetikleyicisine bağlıdır. O tetikleyici
   bu depoda ölçülebilir biçimde güvenilmez: kayda geçen zamanlanmış koşuların
   TAMAMI 30–60 dakika gecikmeli başladı, sabah penceresindekiler ise hiç
   başlamadı (26.08'de ölçüm, 27.08'de hem veri hem ölçüm). Araç ne eksikse
   söyler ve çıkış koduyla ne yapacağını bildirir:

   | kod | anlamı | yapılacak |
   |---|---|---|
   | 0 | ölçüm hazır, yazı bekleniyor | 1. adımdan devam et |
   | 1 | ölçüm yok / boş ölçüyle üretilmiş / veri bayat | **iş akışlarını tetikle** (aşağı bak) |
   | 2 | bugünün bülteni zaten yazılmış | yapacak bir şey yok |
   | 3 | cumartesi | bülten üretilmez |

   **Kod 1 ise: bülteni YEREL ÜRETMEYE ÇALIŞMA.** Rutin metni "dosya yoksa
   `python3 bulten.py --tur gunluk` ile üret" diyor; bu, yazı katmanının koştuğu
   bulut oturumunda İŞLEMİYOR. Oturumun ağ politikası piyasa ve haber uçlarını
   kapatıyor — yfinance, bütün RSS kaynakları ve resmî yayım siteleri CONNECT
   aşamasında 403 dönüyor. 27.08.2026'da denendi: 0 enstrümanlık piyasa
   fotoğrafı, 0 haber, 15 engel. Üstelik deneme kirlilik de bırakıyor (piyasa
   önbelleği ve takvim arşivi boş veriyle üzerine yazılıyor); commit'ten önce o
   dosyaları geri al.

   Doğrusu ölçümü ağı ve anahtarları olan yerde koşturmak. Sırayla:
   **`veri.yml` (Veri tazeleme)** → koşunun commit'ini bekle → **`bulten.yml`
   (Günlük bülten)** → commit'ini bekle → `git pull` → `zincir.py`yi yeniden
   koştur. Kod 0 olunca yaz. 27.08'de böyle yapıldı ve bülten zamanında çıktı.

   **AYNI KAPALI AĞ, DENETİMİN BİR UYARISINI SAHTE YAPIYOR — onu arıza sanma.**
   Yazı katmanının oturumunda `bulten/denetim.py` (ve `bulten/tazeleme.py`)
   "yayım takvimi okunamadı — 18 hattın TAMAMI kör koşu listesinde" der. Bu bir
   depo kusuru DEĞİL, bu oturumun kapalı ağının izidir: tazeleme takvimi ağdan
   çözülüyor, çözülemeyince araç güvenli tarafa düşüp her hattı "kör koşu"
   sayıyor. 11.09.2026'da ölçüldü — aynı gün aynı ölçüt BULUTTA koştu ve takvimi
   sorunsuz okudu; oradaki gerçek uyarı çok daha dar çıktı ("bugün tazelenmesi
   gereken ama tazelenemeyen hatlar: USD/TRY devalüasyon hızı, DİBS verim
   eğrisi"). Yani yerelde ölçüt 18 hattı birden şişiriyor, bulutta iki hattı
   adıyla veriyor. **Hangi hattın bugün bayat olduğunu yerelden değil,
   `bulten.yml` koşusunun kaydından oku**; yerel liste hiçbir şey söylemiyor.
   Bunu bildirime "arıza" diye yazmak, ölçülmemiş bir şeyi ölçülmüş gibi
   göstermenin bir biçimi olur — bu depoda bir kez yapıldı ve commit mesajına
   geçti.

   **Zinciri saat değil RUTİN sürükler.** Zincirin en güvenilir halkası
   GitHub'ın zamanlayıcısı değil, seni ateşleyen bulut rutinidir — o her sabah
   koşuyor. Zamanlanmış koşular koşarsa işini azaltır; koşmazsa eksik halkayı
   sen tamamlarsın. Bu bir istisna değil, tasarımın kendisi.

   **Eksik halka bulursan BİLDİR.** Depodaki nöbetçi (`nobetci.yml`) bülten
   çıkmadığında iş akışını düşürüp e-posta gönderiyor — ama o da bir GitHub
   cron'u, yani aynı zamanlayıcının insafında. Zamanlayıcı topluca düşerse
   alarmı da düşer. GitHub'a hiç bağlı olmayan tek kanal senin bildirimin.
   Bu yüzden zinciri elle tamamladığın her sabah bunu bildirimde YAZ: hangi
   halka düştü, ne tetiklendi, bülten kaçta çıktı. Sessizce onarmak, arızayı
   görünmez kılar — ve bu zincirin asıl kusuru zaten görünmez olmasıydı.
   Bildirimde gecikme DAKİKASI ve darboğaz halka yazılır — "gecikti" değil,
   kaç dakika ve hangi halka; `zincir.py` ikisini de basıyor.

1. **Bülteni oku ve damgasını not al.** `site/src/data/bulten/<bugün>.json`.
   İçinde ölçülmüş her şey var: 51 enstrümanlık piyasa fotoğrafı, TL faiz seti
   ve DİBS eğrisi, takvim, taranmış haberler (`haberler.kurum`,
   `haberler.haber`), kilit gelişmeler (`haberler.kilit`), izlenen temalar
   (`temalar`), rejim panosu (`rejim`), olağandışılık sıralaması
   (`piyasa.en_cok_hareket.sigma`), söz defteri (`izleme`), "ne bekleniyordu,
   ne geldi" (`sonuclar`) ve dünden bu yana gelen veriler (`gruplar`). **`olusturma` alanını hemen
   kaydet** — yamayı uygularken bu damgayı vereceksin; ölçüm sen yazarken
   yenilenirse yama reddedilir ve metni güncel ölçüye göre gözden geçirirsin
   (26.08.2026'da bu kaza gerçekten oldu: yazı 04:31'de yazıldı, ölçüm 05:01'de
   yeniden kuruldu, sayfa ölçülmeyen sayıları anlattı).
2. **Kilit gelişmeleri araştır.** `haberler.kilit` listesindeki her maddeyi,
   `%1,5`'i aşan her fiyat hareketini VE `piyasa.en_cok_hareket.sigma`
   listesinde **2σ'yı aşan** her hareketi kaynağına inerek anla. İki eşik
   farklı soruları yakalar: yüzde eşiği büyük hareketi, σ eşiği olağandışı
   hareketi. Yüzdesi küçük diye 2σ'lık bir hareketi atlama — 26.08'de günün
   asıl haberi (kredi endekslerinin 1,6σ'lık ortak hareketi) ham listede hiç
   görünmüyordu. Manşete bakıp sebep uydurma; hareketin gerçek sürücüsünü bul.
3. **Yaz.** Aşağıdaki bölümleri doldur; yamayı `yama.json` dosyasına yaz.
   **Her sayıda en az bir işlem fikri beklenir** (karar 05.10.2026; bkz.
   "İşlem fikirleri (biçim 3)" → "Sayı"). Rutin metni "yaz.py yalnız
   yorum/ozet/gundem alanlarına yazmana izin verir" diyorsa o cümle eskidir:
   `fikirler` ve `fikir_kapat` da yazılabilir alanlardır. Fikirleri yazı
   katmanı yazıldıktan SONRA, AYRI bir yamayla yaz (bir fikrin reddi o zaman
   sabahın notunu durdurmaz): önce `python3 bulten/fikir.py --evren --tarih <sayı günü>` (ölçülebilir
   bacaklar), sonra `python3 bulten/fikir.py --sina fikir.json --tarih <sayı
   günü>` (bkz. "İşlem fikirleri (biçim 3)" → "İş akışı").
4. **Denetle — yazmadan.** `python3 bulten/yaz.py yama.json --damga "<okuduğun
   olusturma>" --denetle`: yama bellekte uygulanır, denetim o sonuç üzerinde
   koşar, dosyaya yazılmaz. Çıkış kodu 0 olana kadar düzelt. Denetim güven
   değil ölçüm içindir: "atladığımız bir şey var mı" sorusunun cevabını o verir.
   (Eski akış `denetim.py`yi doğrudan çağırıyordu; o araç DİSKTEKİ dosyayı okur,
   yani yazı henüz dosyada yokken koşuyordu.)
5. **Kaydet.** Aynı komut `--denetle` olmadan: `python3 bulten/yaz.py yama.json
   --damga "<okuduğun olusturma>"`. Kapı iki kez sorar — damga tutmuyorsa (çıkış
   3) bülteni yeniden oku ve metni güncel ölçüye göre gözden geçir; denetim
   ENGEL üretiyorsa (çıkış 5) dosya YAZILMAZ, engelleri gider. Ölçüm katmanından
   gelen ve senin gideremeyeceğin bir engel varsa (ör. kapanmamış seansın barı)
   bunu BİLDİR; `--engelle-yaz` yalnız bilinçli istisnadır ve engeller dosyaya
   işlenir.
6. **Push et — YAYINLAMA.** `git add -A && git commit -m "bülten: <tarih>
   yazı katmanı" && git pull --rebase --autostash && git push`. Push'tan sonrası
   senin işin değil: ayrı bir iş akışı siteyi public depoya çıkarır. `yayinla.py`
   ELLE ÇAĞRILMAZ — public depoya yazma yetkisi bulut iş akışında duruyor,
   yazı katmanının oturumunda yok; çağırmak boşuna hataya çıkar.
   (Bu satır eskiden "sonra `python3 yayinla.py`" diyordu ve rutinin metniyle
   çelişiyordu. Rutin "rehbere birebir uy" dediği için çelişki rehberin
   aleyhineydi.)

---

## Biçim: sayının kendisi söyler

Her ölçülen sayı yazı biçimini beyan eder: `surum` alanı. **`surum: 3` (1 Ekim
2026'dan sonra ölçülen her sayı) bir SABAH NOTUDUR** ve bu bölüm onun tarifidir.
`surum: 2` arşivdir (12 bölümlü eski düzen); arşiv sayısına yalnız düzeltme
yazılır ve onu kendi kuralları ölçer. Gündem bölüm kimliklerini **sayının
`gundem_yazi_bolumleri` alanından** oku; yazma kapısı (`yaz.py`) beyan dışı
kimliği reddeder.

Neden: eski düzen her gün 12 bölümü asgari uzunlukla zorunlu kılıyordu (yorum
≥350 · 8 haber bölümü ≥200 · 4 yazı bölümü ≥300 kelime). Günlük düzyazı
4.000–5.400 kelimeye çıktı ve aynı olgu 3–7 bölümde yeniden anlatıldı: "Ne
oldu"nun rakamlarının %53–88'i "Günün okuması"nda yeniden sayılıyordu, aynı
sabit rakamlar (politika faizi seti, ÖTV takvimi, cari açık) iki haftanın
10–13 sabahında yeniden basılıyordu. Okurun hükmü: "gerçek bir piyasa
profesyoneli tarafından yazılmış gibi değil; çok tekrar var".

---

## Doldurulacak alanlar (biçim 3)

| alan | sayfadaki adı | uzunluk (günlük · haftalık) | zorunlu |
|---|---|---|---|
| `manset` | başlık (h1) | tek cümle, ≤110 karakter | evet |
| `ozet.ne_oldu` | Bu sabah · Haftanın özeti | 4–6 · 7–10 madde · 90–240 · 320–550 kelime | evet |
| `yorum` | Günün / Haftanın okuması | 300–550 · 1000–1500 | evet |
| `gundem.turkiye` | Türkiye · Türkiye: piyasalar | 200–450 · 950–1400 | evet |
| `gundem.kuresel` | Küresel | 180–420 · 1050–1500 | evet |
| `gundem.emtia` | Emtia ve enerji | 60–250 · 450–800 | haftalıkta evet; günlükte yalnız söyleyecek bir şey varsa |
| `gundem.takvim` | Bugün ve önümüzdeki günler · Önümüzdeki hafta — gün gün | 120–320 · 700–1100 | evet |
| `gundem.risk` | Risk haritası · Senaryolar ve risk haritası | ≤220 · 600–1000 | haftalıkta evet; günlükte isteğe bağlı |
| `gundem.karne` | Haftanın karnesi | — · 250–500 | evet |
| `gundem.turkiye_makro` | Türkiye: makro, politika ve maliye | — · 700–1100 | evet |
| `fikirler` | İşlem fikirleri | 1–3 · 3–6 fikir; fikir başına gerekçe ≤60 kelime | her sayıda en az bir fikir beklenir; yoksa UYARI (zorla fikir yazılmaz, sebebi bildirimde yazılır) |
| `fikir_kapat` | İşlem fikirleri (karnede "erken kapandı") | kayıt başına bir sebep cümlesi | yalnız açık bir fikrin görüşü bozulduysa |
| `duzeltmeler` | Düzeltmeler | — | yalnız yayımlanmış bir sayı düzeltilirken |

"—" o bölümün o kipte OLMADIĞINI söyler: `karne` ve `turkiye_makro` yalnız
haftalık sayının bölümleridir (sayının beyanında yalnız orada geçer, yazma kapısı
günlük sayıda onları reddeder). Haftalık sayının bölüm sırası ve alt bölümleri
"Haftaya bakış (haftalık kip)" başlığı altında. `fikirler` ve `fikir_kapat` bir
gündem bölümü DEĞİLDİR: yapılandırılmış listedir, toplam yazı sayımına girmez,
gönderiye ve ana sayfaya girmez; sözleşmesi "İşlem fikirleri (biçim 3)"
başlığı altında. Bir biçim 3 yamasının iskeleti:

```json
{
  "manset": "…",
  "ozet": {"ne_oldu": "<ul><li>…</li></ul>"},
  "yorum": "<p>…</p>",
  "gundem": {"turkiye": "<p>…</p>", "kuresel": "<p>…</p>", "takvim": "<p>…</p>"},
  "fikirler": [
    {"baslik": "TL eğrisinde 2y–5y dikleştirici", "tur": "egri",
     "bacaklar": [{"seri": "dibs:spot_2y", "katsayi": -1}, {"seri": "dibs:spot_5y", "katsayi": 1}],
     "yon": "yukari", "hedef": -300, "stop": -415, "ufuk": "2026-10-23",
     "enstruman": "TRY OIS 2 yıl / 5 yıl",
     "gerekce": "…", "ne_bozar": "…", "dayanak": "turkiye", "senaryo": "Ana senaryo"}
  ],
  "fikir_kapat": [{"kimlik": "2026-10-02-1", "sebep": "…"}]
}
```

Fikrin tam hâli ve örnekleri "İşlem fikirleri (biçim 3)" → "Örnekler"de;
`fikir_kapat` yalnız önceki bir sayıda açılmış ve hâlâ açık bir fikir varsa
gönderilir.

**Toplam yazı (manşet + madde + okuma + gündem): günlük hedef 1.000–1.700
kelime, haftalık 6.000–9.000.** Günlükte 2.100, haftalıkta 10.800 kelimeyi aşan
yazı ve haftalıkta 4.500 kelimenin altında kalan yazı denetimde ENGEL alır; bir
bölüm kendi üst sınırının 1,5 katını aşarsa o da ENGEL'dir. Bunların dışında
aralığın altı ve üst sınırla 1,5 katı arası yalnız UYARI'dır: söyleyecek az şey
varsa az yaz (haftalıkta 4.500 tabanına kadar). Boş zorunlu bölüm ENGEL'dir.

Aralık 01.10.2026 akşamı genişledi (okur: "önceye göre çok beğendim ama biraz
kısa; tekrara kaçmadan daha fazla ayrıntı"). Genişleyen yer tekrar değil
ayrıntıdır: denetimin bilgi satırı her sayının **tekil olgu** sayısını ve
**tekrar oranını** yazar ("ayrıntı: 36 tekil olgu, 37 geçiş (tekrar %3)").
İlk biçim 3 sayısı 36 tekil olgu taşıyordu, aynı günün eski düzendeki metni
173 tekil olguyu %37 tekrarla. Hedef: tekil olgu artar, oran %10'un altında
kalır.
`ozet.ne_bekleniyor` biçim 3'te YOKTUR (ileriye bakış `gundem.takvim`dedir);
yazma kapısı onu reddeder.

### `manset` — günün tezi
Tek cümle, düz metin, özneli ve yüklemli bir HÜKÜM; olayın adı değil.
En çok iki ölçüm sayısı; Türkiye'ye etkisi varsa aynı satırda. Örnek: *"Uzun uç
petrolden koptu: Brent −%2,6 iken ABD 30 yıllık %5,59'a çıktı;
TL kımıldamadı."*

### `ozet.ne_oldu` — Bu sabah (4–6 madde)
`<ul><li>…</li></ul>`. **Günün rakamlarının TEK evi.** Ters piramit: ilk
madde en büyük olgu + sayı + kıyası; her madde bir olgu, onun ölçeği ve anlamı
(en çok ~45 kelime). Türkiye ilk iki maddede. Tabloda zaten basılı her rakamı
buraya taşıma — yalnız argümanı taşıyanı.

### `yorum` — Günün okuması
Tek tez, dört adım: **tez** (bir cümle) → **mekanizma** (neden oldu) →
**fiyatlanan ve risk asimetrisi** ("piyasa X fiyatlıyor; risk Y yönünde
asimetrik, çünkü …" — tavsiye dili yok) → **görüşü ne değiştirir** (bugün ya da
bu hafta hangi veri/seviye). Maddelerdeki rakamları yeniden saymaz; en çok iki
çapa rakamla ilişki kurar ve kendi sayıları TÜRETİLMİŞ ölçülerdir (makas,
oran, σ, bileşim). Her paragraf bir hükümle biter, çıplak bir haber cümlesiyle
değil. Türkiye ilk iki paragrafta.

### `gundem` bölümleri — her konunun tek evi
| konu | ev |
|---|---|
| TCMB, Türkiye makro verisi, politika/düzenleme, USD/TRY, TLREF, DİBS, BIST | `turkiye` |
| Fed, ECB, BoJ, ABD/AB verisi, jeopolitik, G10 faiz ve döviz, küresel hisse | `kuresel` |
| Brent/WTI, ürün marjları, altın ve metaller | `emtia` |
| bugünün ve yakın günlerin yayımları, ihaleler, toplantılar | `takvim` |
| tetik → etki yönü → izlenecek ölçü (2–3 madde) | `risk` |
| okumanın işlem yapısı: bacaklar, yön, hedef, stop, ufuk, görüşü ne bozar | `fikirler` (gündem bölümü değil) |

Bir konu kendi evinde tam anlatılır; başka bölümde en çok TEK cümleyle anılır.
İşlem yapısının tek evi `fikirler`dir: düzyazı eğrinin dikleşeceğini yazabilir,
dikleştiricinin kurulduğunu yazmaz; fikrin seviyeleri (giriş, hedef, stop,
kullanım fiyatı) düzyazıda yinelenmez ve düzyazı fikre atıf yapmaz.
Bölüm günün özetiyle açılmaz; kendi konusundaki yeni bilgiyle açılır. Piyasa
etkisi olmayan haber yazılmaz (bir ülkenin BM'deki talebi, dijital ruble).

Bölümler kısa, kalın başlıklı paragraflardan kurulur (`<p><strong>Başlık.</strong>
…</p>`); her paragraf bir alt konudur ve şu sırayla ilerler: **yeni bilgi →
ölçek ve aktör → mekanizma (karşı mekanizma dahil) → türetilmiş ölçü ya da
fiyatlama → izlenecek ölçü**. Hepsini her paragrafta yazmak zorunlu değil;
sıralama zorunlu. Bölümlerin alt konuları:

| bölüm | alt konular (o gün söyleyecek bir şey olanlar) |
|---|---|
| `turkiye` | **TL faizi ve DİBS** (TLREF−politika, gösterge ve eğri, başabaş ayrıştırması) · **kur** · **hisse ve kredi** (sektör kırılımı) · **politika ve düzenleme** (kurum, kuruluş adları, tutar, tavan) · **dünden bu yana yayımlanan Türkiye verisi** (sonuç, önceki değer, anlamı — yalnız kaynaklıysa) |
| `kuresel` | **ABD faizi** (eğri şekli, çok günlü birikim) · **dolar ve G10** (Türkiye'ye geçişi: euro/TL) · **hisse ve kredi** · **Avrupa ve Asya** · **politika ve jeopolitik** · **bu sabah** (Asya kapanışı, vadeliler — adlı kaynakla) |
| `emtia` | **ham petrol ve ürün** (marjlar, arz/talep sürücüsü) · **değerli metaller** (adlı katalizör) · **Türkiye'ye geçiş** (pompa, TÜFE kalemi) |
| `takvim` | Türkiye takvimi önce; her yayım için önceki değer ve **iki yönlü sonuç → anlam** ("güçlü gelirse X, zayıf gelirse Y"); planı değişen takvim ("ne değişti": yeni ihale takvimi, ertelenen yayım) |
| `risk` | 2–4 madde: tetik · etki yönü · olasılığını artıran ölçü ve onun eşiği |

`takvim`: her yayım için **hangi sonuç neyi değiştirir** — beklenti sayısını
yineleme, tablo basıyor; ÖNCEKİ değer kıyas için yazılabilir (tablo onu
basmaz). Haftalık sayıda önümüzdeki haftanın her takvim maddesi
burada tek tek işlenir ve sayısal beklentisi olan her maddenin takvim kaydında
`beklenti_sayi` alanının dolu olduğunu doğrula (sürpriz ölçümü o alanla çalışır;
serbest metinden sayı türetilmez). Beklenti yoksa yokluğunu YAZMA — tablo "—"
basar.

`risk`: 2–4 madde, her biri: tetik · etki yönü · olasılığını artıran ölçü.

### Ayrıntı: notu ne uzatır, ne uzatmaz

01.10.2026'da aynı günün iki metni cümle cümle karşılaştırıldı: eski düzenin
267 cümlesinin yalnız **16'sı** yeni notta eksik kalan gerçek ayrıntıydı;
107'si yeni notta zaten vardı, 39'u tabloda basılı sayıyı yeniden okuyordu,
32'si kronik, 28'i dolgu, 21'i süreç dili, 12'si güvenilmez, 12'si kendi içinde
tekrar. Yani ayrıntı eski metni geri getirerek ARTMAZ. Asıl eksik, iki metnin
de yazmadığı türlerdi.

**Notu uzatan ayrıntı** (her biri ölçülmüş ya da adlı kaynaklı):

1. **Aktör ve ölçek.** Kuruluşun, kişinin, fonun adı; tutar, tavan, kaç
   kuruluş. "BDDK beş kuruluşun yönetimini devretti" yerine Tera, Destek ve
   Hedef yatırım bankaları ile Destek ve Tera faktoring; ara ödemenin tavanı
   1 milyon TL. Ad ve ölçek "nereye uzanır" sorusunu sayıyla daraltır.
2. **Karşı mekanizma.** Riskin öbür yönü: tasfiyede ara ödemenin başlaması
   satış baskısını öne çeker AMA belirsizliği de azaltır; TMSF devri bir el
   koyma değil yönetim devridir ve devredilenler mevduat bankası değildir.
   Tek yönlü kurulmuş bir asimetri hükmü eksik bir hükümdür.
3. **Alt kırılım.** Manşet rakamın altındaki bileşen: aylık ve yıllık okuma
   birlikte; iki kalemin aynı birimde kıyası (benzinde pompaya 4,15 TL,
   motorinde 3,60 TL); bir primdeki düşüşün hangi bacaktan geldiği. Bacağın
   kendisi de sınanır: başabaş nominal ile reel getirinin farkıdır ve TÜFEX
   sığ işlem görür — 2 yıllık reel getiri 21.08–30.09 arasında yalnız 7 bp
   kaydı (%8,18 → %8,11), nominal 2 yıllık aynı sürede 174 bp'lik bir bantta
   oynarken; o günlerde başabaşın hareketi nominal hareketin aynasıydı.
   "Düşüşün tamamı başabaştan geldi" demeden önce reel bacağın kıpırdayıp
   kıpırdamadığına bakılır; kıpırdamıyorsa ayrı bir enflasyon okuması kurulmaz.
4. **Çok günlü birikim.** Bir olaydan ya da bir notun açıldığı günden beri
   kaç seansta nereden nereye ("25.09'dan beri 5s30s 50 → 55 bp"); bir eşiğe
   kalan uzaklık. Tablo günlük farkı basar, birikimi basmaz.
5. **Çapraz varlık bağı.** Bir hareketin başka bir varlıkta neye karşılık
   geldiği: EUR/USD yılın dibindeyken euro/TL'nin düşüşü; Türkiye ETF'i
   −%2,73 iken gelişen ülke hisseleri −%0,91. **Havlamayan köpek** de bir
   ölçüdür: bankalar −%4,58 iken TL tahvilinin SATILMAMASI, tezin karşı
   kanıtıdır — 1σ altı bir hareket kendi başına haber değildir ama bir tezin
   sınavı olarak tek cümleyle yazılır (bkz. kural 6).
6. **Eksik varlık sınıfı.** Gün sakin geçse bile dolar ve G10, değerli metaller,
   TL faizi notta en az bir cümle bulur; sakinliği ölçüsüyle söylenir.
7. **Bu sabah katmanı.** Kapanış tablosunun veremediği: Asya'nın açılışı,
   vadeliler, gece gelen haber — adlı kaynakla. Dünkü kapanışa göre kurulmuş
   bir hüküm bu sabah eskimişse ("Japon getirisi geri çekildi" — FT 07:17:
   yeniden sıçradı) güncel hâli yazılır.
8. **Takvimde iki yönlü sonuç ve "ne değişti".** Bir yayımın iki olası
   sonucunun ne anlama geldiği; planı değişen takvim (yeni stratejiyle ihale
   günü ve modelin tahmini).

**Notu uzatmayan:** tablodaki seviyeyi cümleye çevirmek; değişmeyen değeri
yeniden yazmak (kronik); aynı rakamı ikinci bölümde saymak; süreç dili;
geçiş ve özet cümleleri ("Günün resmi şu"); kaynağı haber akışında olmayan
iddia.

**Her ayrıntı doğrulanır, zamanlaması dahil.** Bir nedensellik iddiası
haberin DAMGASINA karşı sınanır: 01.10 notu "kaybın tamamı devir kararının
duyurulduğu saatlerde oluştu" yazdı — karar 18:51'de, borsa kapandıktan
SONRA duyurulmuştu. Kapanış tablosundaki bir hareketi ancak seans içinde
bilinen bir olay açıklayabilir.

### `duzeltmeler` — yayımlanmış bir sayının düzeltme kaydı

Denetimin "YAYIMLANAN SAYI DEĞİŞTİ" uyarısına verilen cevabın YAPISAL eşi.
Metindeki "yayımlanan X yerine gerçek değer Y" kalıbı kalır (okur metinde
görür); aynı düzeltme bir de liste olarak yazılır ki sayfa onu "Düzeltmeler"
bölümünde bassın ve site bütün bültenlerin düzeltmelerini `/duzeltmeler/`
sayfasında tek listede toplayabilsin. Her kayıt dört alan taşır:

```json
"duzeltmeler": [
  {"alan": "Brent günlük değişim, 28.08 kapanışı",
   "eski": "−%11,36", "yeni": "−%1,74",
   "sebep": "vadeli devir düzeltmesi kurulamamıştı; ham kontrat kapanışı yayımlandı"}
]
```

`tarih` boş bırakılırsa bugünün tarihi yazılır. `alan`, `eski`, `yeni` eksikse
yazma reddedilir — neyin neye düzeltildiğini söylemeyen kayıt okura hesap
vermez. Liste yamada bütünüyle yazılır. Düzeltme yoksa alan hiç gönderilmez.
Sebep okur diliyle yazılır: "ölçü kusuru" değil, kusurun ne olduğu.

---

## Yazım kuralları — sabah notu

Denetimin üslup ölçütü (`bulten/uslup.py`) bunların ölçülebilir olanlarını
sınar: süreç dili ENGEL, bütçeli kalıplar UYARI.

1. **Süreç dili yok (ENGEL).** Okura ölçüm tesisatını anlatma: "ölçülen elli
   bir satır", "X satırı", "kaydın çürütme ölçütü", "kurduğumuz kayıt", "bir
   ölçü uyarısı / kısıtı / boşluğu", "dürüstçe kayda geçsin", "hüküm
   kurulmadı", "beklenti elimizde yok / sürpriz ölçülmeyecek", "hattımız",
   "söz defterinde", "sürümünde donmuş", "kapanışını taşıyor", "barını boş verdi",
   "beş ayrı kaynakta yer buldu". Veri kısıtı (bir satırın hangi seansa ait
   olduğu, boş bar, vade devri, bayat seri) **sayfanın kendi dipnotunda**
   durur; düzyazıya girmez. Güvenilmez bir seri kullanılmaz ve neden
   kullanılmadığı da anlatılmaz.
2. **Bir olgu bir kez.** Rakam maddede durur; okuma ve bölümler onu yeniden
   saymaz. Aynı ondalık üç bölümde geçerse denetim uyarır; madde ile okuma en
   çok iki rakam paylaşır.
3. **Değişmeyeni yazma.** Önceki sayıdan beri değişmemiş bir değer (politika
   faizi seti, ÖTV takvimi, cari açık, ihale modeli) düzyazıya yalnız olay
   günü ya da değiştiği gün girer. Bugün ve önceki iki sayının üçünde de
   yazılmış değerler üçten fazlaysa denetim onları "kronik olgu" diye listeler.
   σ katsayıları ("1,5σ") bu ölçüye girmez: seviye değil oynaklığa bölünmüş
   harekettir ve günden güne başka serilerde tesadüfen aynı çıkar.
4. **Okuma her gün yeni bir cümleyle açılır.** Dünün açılışını yeniden kurma.
5. **Cümle kısa.** Ortalama en çok 22 kelime ve 35 kelimeyi aşan cümle en çok
   %8 (denetimin eşiği; hedef ortalama 14–18), cümle başına en çok dört
   ölçüm sayısı, en çok bir uzun tire. Etken çatı. "yani" bağlacı 300 kelimede
   en çok bir; "bir X değil bir Y" kalıbı sayı başına en çok iki;
   "İkincisi/Üçüncüsü" yerine madde.
6. **σ disiplini.** Olağandışılık "(1,5σ)" biçiminde yazılır. 1σ altındaki
   hareket HABER olarak düzyazıya girmez (tablo zaten basıyor); tek istisnası
   bir tezin sınavıdır — "bankalar −%4,58 iken TL tahvili satılmadı" gibi,
   beklenen hareketin OLMAMASI tek cümleyle yazılır; 2σ ve üstü sebebiyle girer,
   sebep netleşmediyse bir kez "sebebi netleşmedi" denir. 1σ altı tek günlük
   hareketten rejim hükmü kurulmaz; "kesin / kanıt / ta kendisi" yalnız 2σ ve
   üstünde ya da çok günlü birikimde.
7. **52 hafta konumu** yalnız uçlarda (%95 ve üstü, %5 ve altı) ve sayı başına
   en çok üç kez; tablo içi sıralama ("haftanın en büyük beşinci hareketi")
   yazılmaz.
8. **Standart adlar.** MOVE, VIX, WTI, HY, IG, EMBI, TLREF, 2s10s, 5s30s, bp —
   "tahvil oynaklığı ölçüsü" değil MOVE. Tanım her gün yeniden yapılmaz
   ("kur arındırılmış on üç haftalık yıllıklandırılmış kredi büyümesi" →
   "kredi büyümesi (13h)").
9. **Kaynak ve kişi adıyla.** Her dış iddia adlı kaynakla (Reuters, FT,
   Bloomberg, kurumun adı) ve kişinin adıyla: "bir yatırım bankası", "bir
   bölge başkanı… bir diğeri", "haber akışına göre" yazılmaz.
10. **Geçmiş çağrılar** söz defterinde durur. Günlük sayıda düzyazıda sayı
    başına en çok bir atıf, "(20.09 notu)" biçiminde; haftalık sayıda atıf
    YALNIZ karne bölümündedir ve hesabı verilen (kapanan ya da vadesi geçen)
    kayıt sayısı kadardır, en az bir (öbür bölümlerde
    sıfır; bkz. "Haftaya bakış").
11. **Fiyatlama dili serbest, tavsiye dili yasak.** Düzyazıda "piyasa X'i
    fiyatlıyor; risk Y yönünde asimetrik" yazılır; al/sat, "hedef fiyat",
    pozisyon dili yazılmaz — bu kural fikirler eklendikten sonra da aynen
    sürer. Okumanın işlem yapısına çevrilmiş hâli YALNIZ `fikirler` alanında
    durur ve orada da betimleyici dille yazılır: bacak, yön, seviye ("2 yılda
    sabit alan, 5 yılda sabit ödeyen"; "eğri dikleşirse kazanır"), emir kipi
    ve öneri fiili yok. Düzyazı fikre atıf yapmaz, sayılarını yinelemez;
    sorumluluk cümlesi de yazılmaz — sayfanın fikir bölümü kendi uyarı
    metnini taşır (bkz. "İşlem fikirleri (biçim 3)").
12. **Sayılar rakamla** ("52 haftalık", "17 Eylül"); vurgu büyük harfle değil
    `<strong>` ile, paragraf başına en çok bir.

---

## Haftaya bakış (haftalık kip)

Pazar sayısı aynı biçimin **haftalık kipidir** ve günlük notun uzun hâli değil,
kendi bölüm seti olan bir haftalık rapordur (kullanıcı, 01.10.2026: "çok daha
detaylı ve uzun"). Hedef **6.000–9.000 kelime** (30–45 dakikalık okuma);
10.800'ü aşan yazı ENGEL alır. Uzunluk eski düzenin TEKRARIYLA gelmez: biçim 2
pazar sayıları 5.000 kelimede 161 tekil olgu taşıyordu ve geçişlerin %41'i
tekrardı. Uzunluk, iki biçimin de yazmadığı bloklarla gelir: senaryolar, gün
gün takvim, haftanın karnesi, Türkiye'nin iki ayrı evi ve her varlık sınıfının
alt bölümleri. Tekrar ölçüleri günlükle aynıdır; hedef en az 200 tekil olgu ve
%10'un altında tekrar (denetimin bilgi satırı yazar, eşik değildir).

Okurun kısa yolu açık tutulur: **özet → okuma → senaryolar → önümüzdeki hafta**
(~2.600–4.200 kelime, dakikada 200 kelimeyle 13–21 dakika; aralık aşağıdaki dört
bölümün aralıklarının toplamıdır). Sayfa künyesi tahmini okuma süresini ve kısa
yolu AYNI hızla (dakikada 200 kelime) basar;
bu dört bölüm kendi başına okunduğunda haftanın tezi, mekanizması ve önümüzdeki
haftanın sınavı eksiksiz anlaşılmalıdır. Ayrıntı bölümleri onu derinleştirir,
tekrar etmez.

### Bölümler ve sıra

Sayfa bölümleri bu sırayla basar (sayının beyanı, `gundem_yazi_bolumleri`):

| sıra | alan | başlık | kelime | alt bölüm (`<h3>`) |
|---|---|---|---|---|
| 1 | `ozet.ne_oldu` | Haftanın özeti | 7–10 madde · 320–550 | — |
| 2 | `yorum` | Haftanın okuması | 1.000–1.500 | — |
| 3 | `gundem.risk` | Senaryolar ve risk haritası | 600–1.000 | en az 2: ana · alternatif · kuyruk |
| 4 | `gundem.takvim` | Önümüzdeki hafta — gün gün | 700–1.100 | gün paragrafları |
| 5 | `gundem.karne` | Haftanın karnesi | 250–500 | — |
| 6 | `gundem.turkiye` | Türkiye: piyasalar | 950–1.400 | en az 3 |
| 7 | `gundem.turkiye_makro` | Türkiye: makro, politika ve maliye | 700–1.100 | en az 3 |
| 8 | `gundem.kuresel` | Küresel | 1.050–1.500 | en az 4 |
| 9 | `gundem.emtia` | Emtia ve enerji | 450–800 | en az 2 |

Hepsi haftalık sayıda **zorunludur**; alt bölümü az olan bölüm UYARI alır.
Aralıklar YÖNERGEDİR (bölüm aralık dışına düşerse UYARI); iki şey ENGEL'dir:
toplamın 10.800 kelimeyi aşması ve **4.500 kelimenin altında kalması** — eski
rutin talimatıyla yazılmış ~2.800 kelimelik bir pazar sayısı bölüm bölüm yalnız
uyarı alıp yayına gidiyordu; taban, haftalık kipin sözleşmesinin kendisidir.
Alt bölüm `<h3>Başlık</h3>` ile açılır ve altında günlükteki kalın başlıklı
paragraf düzeni sürer. Ayrı bir "kilit gelişmeler" bölümü YOKTUR (biçim 2'nin
tekrarının ana taşıyıcısı oydu: başka bölümlerin hikâyelerini önceden anlatıyordu).
Sayfa 3. bölümün (senaryolar) hemen ardından işlem fikirlerini basar
(`fikirler`): yazı bölümü değildir, tablodaki sıraya ve kelime sayımına girmez.

**1. Haftanın özeti.** Haftanın rakamlarının TEK evi. Her madde: haftalık
hareket (`h1`) ya da yayımlanan veri + kıyası + anlamı; olağandışılık haftalık
σ ile (`h1_sigma`, "(2,1σ)"). Türkiye ilk üç maddede. Ters piramit.

**2. Haftanın okuması.** Tek tez, beş adım: **tez** (bir cümle) → **mekanizma**
(karşı mekanizma dahil) → **rejim panosunun hafta içindeki gerilimi** (hangi iki
satır çelişiyor, hangisi önce kırılır; pano haftalık sayıda farkı bir önceki
haftalık sayıya göre basar) → **ne fiyatlanıyor ve risk hangi yönde asimetrik**
→ **görüşü değiştirecek tek tetik**, adıyla ve bir cümleyle; koşulun kendisi
(ne olursa ne olur) senaryo bölümünün evidir. İleriye bakışın İKİ evi vardır:
senaryolar (koşullu patika) ve gün gün takvim (yayım yayım sonuç → anlam);
varlık alt bölümleri haftalık kipte "izlenecek ölçü" cümlesiyle KAPANMAZ —
günlük bölüm anatomisinin o parçası haftalıkta senaryoya taşınır. Maddelerdeki
rakamları yeniden saymaz (özetle en çok iki ortak olgu); geçen pazarın açılış
cümlesini tekrar etmez. Tek günlük bir hareket ancak TARİHİYLE ve haftalık
birikimin kaçta kaçı olduğuyla anılır.

**3. Senaryolar ve risk haritası.** İki ya da üç BİRLEŞİK patika, her biri bir
`<h3>` (ör. "Ana senaryo: …", "Alternatif: …", "Kuyruk: …"); ana senaryo İLK
alt bölümdür, çünkü gönderi bölümün ilk paragrafını "Ana senaryo:" diye alır.
Her patika üç parçadan kurulur:
- **tetik** — adıyla bir yayım ya da bir seviye ve eşiği ("PPK 22 Ekim'de
  koridoru daraltırsa", "USD/TRY haftalık %0,5'i aşarsa");
- **varlık etkisi** — TL faizi ve DİBS eğrisi, USD/TRY ve taşıma, BIST, ABD uzun
  ucu, altın ya da petrol: hangi yönde ve hangi mekanizmayla;
- **teyit ölçüsü** (metinde bu adla; "çürütme ölçütü" üslup kapısında ENGEL
  kalıbıdır) — hangi seri, hangi değeri görürse patika
  doğrulanmış ya da düşmüş sayılır.
Olasılık rakamı UYDURULMAZ; adlı bir piyasa fiyatlaması varsa o yazılır (ör.
vadeli faiz sözleşmelerinin ima ettiği artırım ihtimali, kaynağıyla).

**Söz defterine YALNIZ ana senaryo girer.** Alternatif ve kuyruk patikaları
birbirini dışlar; hepsi ayrı söz olarak kaydedilseydi her hafta en az biri
yapısal olarak "tutmadı" çıkar ve isabet oranı ölçtüğü şeyi değil senaryo
SAYISINI ölçerdi. Kaydın tezi ana senaryonun tezidir; teyit ölçüsü kaydın
`ne_bakilacak` alanına, alternatifin tetiği ise aynı alana "şu olursa düşer"
diye yazılır. **Vade tetiğin tarihidir** (PPK 22 Ekim'deyse vade 22 Ekim);
tetik tarihsiz bir seviyeyse vade bir sonraki pazardır. **Aynı tetiğe bağlı AÇIK
bir ana senaryo kaydı varsa yeni kayıt açılmaz**: tez değiştiyse o kayıt
güncellenir, değişmediyse dokunulmaz — aynı sonucu haftalar boyunca ayrı
kayıtlarla saymak isabeti hafta sayısıyla ağırlıklandırırdı. Karne böylece ölçülen
katmandan, tek kayıtla kurulur.

**Senaryodan işlem fikrine.** Sayfa işlem fikirlerini bu bölümün hemen ardında
basar. Haftalık sayının 3–6 fikri en az iki varlık sınıfına yayılır ve her biri
`senaryo` alanıyla bir patikaya bağlanır; alanın değeri patikanın `<h3>`
başlığıyla açılan kısa bir etikettir ("Ana senaryo", "Alternatif: enflasyon
yukarı şaşırtır", "Kuyruk: rezerv aşınması kur ritmini bozar"). Fikrin "görüşü
ne bozar" koşulu, bölümde zaten yazılmış bir eşiği kullanır — bağlandığı
patikanın düşme ölçüsünü ya da o patikayı dışlayan patikanın ölçüsünü (teyit
ölçüsü, varlık etkisinin bandı): aynı eşik iki yerde iki ayrı sayıyla yazılırsa
okur hangisinin geçerli olduğunu bilemez. Söz defterindeki kuralın eşi burada da
geçerli: **birbirini dışlayan iki patikaya ters yönlü iki doğrusal fikir
yazılmaz** — biri öbürünün sigortası olur
ve karne görüşü değil senaryo sayısını ölçer. Ana senaryo dışındaki bir patika
ya asimetrik bir yapıyla (opsiyon: kayıp primle sınırlı) ya da ana patikayla
çelişmeyen bir yapıyla ifade edilir — ama yalnız tetiği bugünkü veride görünmeye
başladıysa: tetiği henüz görünmeyen bir patika fikir değil izlemedir (bkz.
"İşlem fikirleri (biçim 3)" → "Sayı"). Fikir söz defterine ayrıca kaydedilmez;
karnesi kendi mekanik karnesidir.

**4. Önümüzdeki hafta — gün gün.** Her gün bir paragraf:
`<p><strong>Pazartesi 5 Ekim.</strong> …</p>`. Günün içinde Türkiye önce.
Anket beklentisi ve modelin tahmini (Hazine ihaleleri dahil) sayfanın ölçülen
**"Haftanın takvimi"** tablosundadır; düzyazı o sayıları YİNELEMEZ. **Önceki
değer tabloda YOKTUR**: kıyas için gün paragrafında bir kez yazılır (sayfanın
başka bir tablosunda — gösterge şeridi, haftalık değişim tablosu — zaten
duruyorsa yinelenmez). Düzyazının asıl işi **iki yönlü sonuç → anlam** ("beklentinin üstünde gelirse
X, altında gelirse Y") ve beklentiden ya da modelden sapmanın neyi
değiştireceğini yazar. Merkez bankası toplantıları ve konuşmacılar adıyla;
planı değişen takvim ("ne değişti"). Senaryo bölümü bir yayımı ancak tetik
olarak adıyla anar; aynı sonucu ikinci kez anlatmaz.

**5. Haftanın karnesi.** Sayfa ölçülen karneyi bölümün başında **dizin**
olarak basar: bu hafta kapanan (tuttu/kısmen/tutmadı sayımıyla), açılan, vadesi
önümüzdeki haftaya düşen ve vadesi geçip açık kalan sözler, her biri
konu ve tarihiyle; her konu, sözün tam metnine (söz, sonuç, ne bakılacak)
sayfanın aşağısındaki söz defterinde bağlanır. Tam metin yalnız orada basılır.
Yazı SAYIM YAPMAZ ve sözü yeniden yazmaz: neyin NEDEN tuttuğunu ya da
tutmadığını ve vadesi bu hafta dolan ana senaryonun gerçekleşip
gerçekleşmediğini yazar; vadesi gelmemiş açık ana senaryo, teyit ölçüsünün
bugünkü durumuyla tek cümleyle anılır. Haftanın gelen verilerinin sonucu ÖZETİN evidir; karne bir veriyi ancak
bir sözün sonucunu belirlediyse ve rakamı yinelemeden anar. Geçmiş çağrı atfı
("(27.09 notu)") yalnız bu bölümde ve hesabı verilen kayıt sayısı kadar; öbür
bölümlerde sıfır. Vadesi geçen bir söz bu bölümde hesabıyla kapanır ya da
neden ölçülemediği kayda yazılır.

**SIRA KURALI — karnede kapatılacak her kayıt ÖLÇÜMDEN ÖNCE deftere
işlenir.** Dizin ölçüm anında kurulur: bu bölümde kapatılan ya da notlanan
kayıt (isabet, kapanış, sonuç) önce `izleme.json`a işlenir ve push edilir,
sonra ölçüm `bulten.yml`'in `yeniden_olc` girdisiyle (`--yeniden-olc`) yeniden kurulur, sonra yazılır
(temalardaki kuralın aynısı; bkz. "Defteri düzeltmek SAYFAYI düzeltmez").
Sıra atlanırsa kayıt aynı sayfada "açık kalan" görünür ve bir sonraki pazarın
"Bu hafta kapanan" listesine kayar. Kapanmamış ama tezi sarsılmış bir kayıt
varsa kaydın kendisi güncellenir (izleme.json), burada tek cümleyle anılır.
Okurun cümlesiyle yazılır, defterin diliyle değil: "27.09 notu TLREF'in hafta
içinde koridor tavanına döneceğini söylemişti; döndü, çünkü …" — "kaydın tezi",
"kurduğumuz kayıt", "çürütme ölçütü" gibi defter dili üslup kapısında ENGEL'dir;
birinci çoğul "demiştik" de okur dili kapısında yapım dilidir (her alanda ENGEL),
izinli biçimler "(27.09 notu)" ve üçüncü tekil "27.09 notu … söylemişti".

**Fikirlerin karnesi.** Önceki sayılarda açılmış işlem fikirlerinin karnesini
sayfa fikir bölümünde kendisi basar (açık fikirlerin bugünkü değeri, yakın
zamanda kapananların sonucu) ve sayımı da sayfa basar (kümülatiftir: başlangıçtan
beri kapanan fikirler, ortalama R). Karne bölümü fikir karnesini en çok TEK
paragrafta anabilir ve **sayım yapmaz** (söz karnesindeki kuralın aynısı): "bu
hafta üç fikir kapandı" gibi bir cümle kümülatif sayımla karışır. Paragrafın işi
söz karnesindekiyle aynıdır: hangi fikir hangi mekanizmayla tuttu ya da tutmadı. Fikir açıldığı gün
ve yapısıyla anılır ("2 Ekim'de açılan 2y–5y dikleştirici"), makine kimliğiyle
değil. Opsiyon fikrinin vade sonu ödemesi primsizdir ve "kazandı" diye yazılmaz;
ölçülemeyen fikrin sonucu yoktur.
Fikir karnesi SIRA KURALI'na bağlı değildir: kapanışı mekaniktir, erken kapanış
(`fikir_kapat`) fikirlerin ayrı yamasında yazılır ve bir sonraki sayının karnesine girer.

**6. Türkiye: piyasalar.** Haftalık hareketin kendisi (USD/TRY'nin, 2 ve 10
yıllığın haftalık farkı ve σ'sı) özetin evidir; bu bölüm onun üzerine YENİ bir
işlem yapar. Alt bölümler: **TL faizi ve DİBS** (eğimin ve forward'ın değişimi,
vade vade dağılımın biçimi; başabaş ile reel bacağın ayrıştırması, TÜFEX
sığlığı varsa "kayda değer işlem görmedi" diye; Hazine ihale faizinin ikincil
piyasaya geçişi tek cümleyle) · **Kur ve taşıma** (euro/TL ve sepet — euro/TL'nin
TEK evi burasıdır —, devalüasyon hızı beş günlük ortalamasıyla, taşıma makası,
çok günlü birikim) · **Akımlar** (yabancının haftalık, 4 ve 13 haftalık net
alımı; YP mevduatı gerçek ve tüzel kişi, parite arındırılmış) · **BIST**
(sektör kırılımı, dolar bazlı hareket, bankalar). Kaynak: sayfanın "Bu hafta
gelen veriler" bloğu ve onun katlı tablosu ("Bu hafta güncellenen öbür
seriler"), `grafikler.egri`nin 7 gün önceki eğrisi, piyasa satırlarının
`h1`/`h1_sigma` alanları.

**7. Türkiye: makro, politika ve maliye.** Yayımlanan verinin SONUCU (sayı,
önceki değer, kıyas) özetin evidir; bu bölüm aynı rakamı yinelemez, onun alt
kırılımını ve mekanizmasını yazar. Alt bölümler: **Haftanın verileri** (alt
kırılım, çekirdek–manşet ayrışması, beklentiden sapmanın kaynağı — kaynağıyla)
· **Para politikası** (PPK kararı ve metni, TCMB iletişimi; kararın piyasa
fiyatlaması bölüm 6'dadır) · **TCMB bilançosu, rezerv ve döviz akımı** (resmî
haftalık seri, günlük bilanço tahmini ve tahmini döviz akımı TEK alt bölümde) ·
**Kredi ve makroihtiyati** (büyüme alt kırılımı, faizler, makas) · **Maliye ve
Hazine** (bütçe; ihale sonucu — tutar, faiz, modelle kıyas — ve strateji) ·
**Düzenleme** (kurum adı, ölçek, tavan, yürürlük tarihi). Piyasa fiyatlaması
bölüm 6'nın evidir; burada yalnız verinin piyasaya geçiş mekanizması tek
cümleyle anılır.

**8. Küresel.** Alt bölümler: **ABD faizi ve Fed** (eğri şekli, çok günlü
birikim, konuşmacılar adıyla) · **Öbür merkez bankaları** (ECB, BoJ, BoE ve
gelişen piyasalar) · **Dolar ve G10** (EUR/USD ve G10; euro/TL bölüm 6'nın
evidir, burada yalnız geçiş mekanizması) · **Hisse ve
kredi** (HY, IG ve EMBI ayrışması; Avrupa ve Asya) · **Jeopolitik ve ticaret**.
Pazar akşamı yazılır: "bu sabah" alt konusu haftalıkta yoktur.

**9. Emtia ve enerji.** Alt bölümler: **Petrol ve ürünler** (Brent/WTI, ürün
marjları; vade devri haftasında haftalık fark kurulamaz — sayfa dipnotu söyler,
düzyazı söylemez) · **Doğal gaz** · **Değerli ve sanayi metalleri** ·
**Türkiye'ye geçiş** (pompa fiyatı, ithalat faturası, TÜFE kalemi).

### Ev tablosu (haftalık)

| konu | ev |
|---|---|
| haftanın rakamları: haftalık hareket ve σ, yayımlanan verinin sonucu ve kıyası | `ozet.ne_oldu` |
| TL faizinin ve DİBS eğrisinin biçimi, euro/TL ve sepet, taşıma, akımlar, BIST, ihale faizinin ikincil piyasaya geçişi | `turkiye` |
| verinin alt kırılımı ve mekanizması, PPK kararı ve TCMB iletişimi, TCMB bilançosu, rezerv ve döviz akımı, kredi ve makroihtiyati, bütçe, ihale sonucu ve strateji, düzenleme | `turkiye_makro` |
| Fed, ECB, BoJ, EUR/USD ve G10, küresel hisse ve kredi, jeopolitik | `kuresel` |
| petrol, gaz, metaller | `emtia` |
| gelecek yayım, ihale, toplantı: yayım yayım sonuç → anlam | `takvim` |
| birleşik patika, koşul (ne olursa ne olur) | `risk` |
| geçmiş çağrının hesabı | `karne` |
| patikanın işlem yapısı: bacaklar, yön, hedef, stop, ufuk, görüşü ne bozar | `fikirler` (gündem bölümü değil; seviyeleri düzyazıda yinelenmez) |

Bir konu kendi evinde tam anlatılır; başka bölümde en çok tek cümleyle anılır.
Hürmüz'ün yeri `kuresel`dir, `emtia` onun fiyat etkisini tek cümleyle anar.
Bir bölüm, bir madde rakamını ancak üzerinde YENİ bir işlem yapıyorsa anar
(ayrıştırma, çapraz varlık bağı, birikim).

### Kurallar (haftalık)

1. **Pencere haftalıktır.** Haftalık değişim (`h1`), haftalık σ ve haftalık
   birikim; "bugün sınanacak" gibi günlük dil yok.
2. **Kıyas noktası bir önceki pazardır.** Söz defteri, rejim farkı, gösterge
   şeridi, "Bu hafta güncellenen öbür seriler" tablosu ve tekrar ölçüleri
   (günler arası, kronik olgu, açılış) bir önceki YAZILMIŞ haftalık sayıyla
   kıyaslanır; "bu hafta yeni" o sayının ölçüm anından sonra gelen sürümdür.
3. **Olağandışılık haftalık okunur.** Asıl bilgi çoğu zaman ham listeyle σ
   listesinin ayrışmasıdır.
4. **Veri kısıtı dipnottadır** (vade devri, bayat seri, boş bar); düzyazıya
   girmez.
5. **Tema metinleri haftalık kesitle** ve TEK alanda: tezin bu hafta
   doğrulanıp doğrulanmadığı (doğruladı / zayıflattı / çürüttü) ve izlenecek
   gösterge; gövdedeki rakamları yinelemez.
6. **Piyasa etkisi olmayan haber yazılmaz**; kaynak ve kişi adıyla.
7. **Formasyon ve seviye haritası yazılmaz.** Haftalık teknik analiz bülteni
   sona erdi; haftaya bakış teknik içeriği devralmaz.
8. **Haftanın günlüklerini yeniden yazma.** Haftalık sayı haftanın olgularını
   taşır, ama günlük notların cümlelerini taşımaz: aynı olgu haftalık bağlamla
   (birikim, sonuç, sonraki sınav) yeniden kurulur. Denetim haftalık sayıyı
   haftanın yazılmış günlükleriyle ayrıca kıyaslar; örtüşme günler arası
   eşiği aşarsa UYARI verir.
9. **X gönderisi sayfadan kurulur.** Haftalık gönderi manşeti, özetin
   maddelerini (haftalık bütçeyle), okumanın başını ve ANA SENARYOYU taşır;
   alternatif ve kuyruk gönderiye girmez. Ana senaryonun ilk cümlesi tetiği ve
   etkisini tek başına söyleyecek biçimde yazılır — gönderide kesildiği yer
   orasıdır. İşlem fikirleri gönderiye GİRMEZ; ana senaryonun gönderiye giden
   cümlesi bu yüzden bir fikre atıf yapmaz, yapı dili de taşımaz.
10. **Fikirler patikadan türer.** Haftalık sayı 3–6 işlem fikri taşır, en az
    iki varlık sınıfında, her biri `senaryo` alanıyla bir patikaya bağlı (bkz.
    "Senaryodan işlem fikrine" ve "İşlem fikirleri (biçim 3)").

## İşlem fikirleri (biçim 3)

Karar (04.10.2026, kullanıcı): "bültenlere yazdığımız bültene göre trade idea
ekleyebilir miyiz? bu sadece eurusd long short gibi değil de daha kompleks try
OIS steepener, OIS-Londra basis'i tarzı profesyonel ifadeler de olabilir … fx
veya rate tarafında opsiyon vanilla spread her türlü trade idea olabilir" ve
"hisse tarafı da olabilir bültendeki yazılara senaryolara göre". **Bülten piyasayı okur; işlem fikri o
okumayı bir YAPIYA çevirir**: hangi bacaklar, hangi yön, referans seviye, hedef,
stop, ufuk ve görüşü ne bozar. Fikir bir düzyazı bölümü değil yapılandırılmış
bir listedir (`fikirler`). Sayfa onu kendi bölümünde basar — günlükte yazı
bölümlerinin sonunda, rejim panosundan önce; haftalıkta senaryoların hemen
ardında — ve bölüm kendi uyarı metnini taşır (fikir kişiye özel değildir,
yatırım danışmanlığı kapsamında değildir; referans seviyeler ölçüm anındaki
kapanışlardır, karne kapanış bazında tutulur). Bölüm yalnız biçim 3 sayıda ve
yeni fikir ya da karnede kayıt varsa basılır; gönderiye ve ana sayfaya girmez.
Sözleşmenin tek tanımı `bulten/fikir.py`dir (`dogrula`); bu bölüm onun yazar
için okunuşudur — ikisi çelişirse araç kazanır ve rehber düzeltilir.

Üç ilke biçimi belirler:

1. **Giriş seviyesini yazar değil ölçüm verir.** Yazar bacakları, yönü ve
   seviyeleri yazar; referans seviye (`giris`) sayının ölçülen katmanından
   okunur — fiyat bacağı piyasa fotoğrafının o sayıdaki kapanışından, TL faiz
   bacağı DİBS eğrisinin ölçüm anındaki düğümünden. Yamada `giris` yazılırsa
   yok sayılır.
2. **Karne mekaniktir ve kapanış bazındadır.** Karne yayımdan sonraki ilk
   kapanıştan (fiili giriş) başlar; ondan sonraki her kapanışta
   yapının değeri yeniden kurulur; hedef ya da stop bir kapanışta aşılırsa fikir
   o gün kapanır, ufuk dolarsa son kapanışla kapanır. Gün içi dokunuş ölçülmez.
   Söz defterinin isabeti yazarın notudur; fikrin sonucu seriden ölçülür.
3. **Ölçülemeyen fikir açılmaz** (karar 05.10.2026, kullanıcı: "ölçemeyeceğimiz
   trade'i açmamamız gerekli"). TRY OIS, çapraz kur swap bazı, örtük oynaklık ve
   tek hisse fiyatı elimizde yok: böyle bir görüş ya ölçülebilir bir vekille
   yazılır ya da HİÇ yazılmaz. Karnesi tutulamayan bir fikir okura hesap
   vermez; yazma kapısı `olculemez` türünü reddeder, denetim ENGEL sayar. Tür
   yalnız bu karardan önce açılmış bir kayıt için tanımlı kalır.

### Sayı

- **Her sayıda en az bir fikir: günlük 1–3** (karar 05.10.2026, kullanıcı: "her
  bültende en az 1 trade fikri oluşturmaya çalışalım"). Okuma her sabah bir
  yapıya çevrilmeye ÇALIŞILIR. Fikir yine de temiz olmak zorundadır ve temiz
  fikrin dört şartı var: okumanın bir mekanizması var; **o mekanizmanın
  gerekçesi bugünkü veride ya da akışta görünüyor**; mekanizmayı ölçülebilir bir
  yapı taşıyor; görüşü bozacak ölçülebilir, tarihli bir koşul yazılabiliyor.
  Biri eksikse fikir yoktur ve zorla yazılmaz — o sabah denetim UYARI verir,
  yazar sebebini bildirimde tek cümleyle yazar. İkinci şart kuyruk fikrini
  ayırır: "kur ritmi bozulursa", "Londra'da fonlama sıkışırsa" diye kurulan
  bir fikrin tetiği henüz görünmüyorsa fikir değil İZLEMEDİR — söz defterine
  ya da risk bölümüne yazılır, tetik veride görününce fikre çevrilir (04.10'da
  böyle açılan iki fikir 05.10'da kullanıcı kararıyla sayıdan silindi). 3'ün üstü
  UYARI.
- **Haftalık: 3–6 fikir, en az iki varlık sınıfında** (`sinif`: faiz · fx ·
  hisse · emtia · kredi), **her biri bir senaryoya bağlı** (`senaryo`; bkz.
  "Haftaya bakış" → "Senaryodan işlem fikrine"). Fikirsiz ya da aralık dışı
  haftalık sayı, tek sınıflı küme ve senaryosuz fikir UYARI alır. Aralık
  dört şartı gevşetmez: aralığı doldurmak için kuyruk fikri açılmaz; temiz
  fikir üçten azsa az yazılır ve aralık uyarısı bildirimde gerekçesiyle anılır.
- **Açık fikir tavanı 12**, önceki sayılardan açık kalanlarla birlikte; aşılırsa
  UYARI — eskiyen fikir `fikir_kapat` ile kapatılır, üstüne yenisi yazılmaz.
- **Aynı görüş iki kez açılmaz.** Açık bir fikir aynı yapıyı aynı yönde
  taşıyorsa yenisi yazılmaz; görüş değiştiyse eskisi kapatılır. Karne aynı
  görüşü iki kayıtla sayardı (söz defterindeki "aynı tetiğe bağlı açık kayıt"
  kuralının eşi).
- **Ölçülemeyen fikir açılmaz** (yukarıda 3. ilke): önce vekil denenir, vekil
  yoksa fikir yazılmaz.

### Anatomi: alan alan

Sözleşme `fikir.dogrula()`dır. Yazar şu alanları yazar:

| alan | ne yazılır | kural |
|---|---|---|
| `baslik` | yapının adı ve yönü; düz metin, en çok 80 karakter | "TL eğrisinde 2y–5y dikleştirici", "BIST Bankacılık / BIST 100 göreli"; emir kipi yok |
| `tur` | `yalin` · `egri` · `kelebek` · `goreli` · `opsiyon` | bkz. "Yapı kataloğu" (`olculemez` yalnız 05.10.2026'dan önce açılmış kayıtlarda) |
| `bacaklar` | `[{"seri": …, "katsayi": …}]` | `seri` ölçülebilir evrenin kimliğidir (`--evren`); `katsayi` yalnız eğri ve kelebekte, verilmezse varsayılan; bacağın değeri ve tarihi YAZILMAZ |
| `yon` | `yukari` · `asagi` | yapının DEĞERİ yükselirse mi düşerse mi kazanır — fiyatın değil, yapının; konvansiyon katalogda |
| `hedef`, `stop` | sayı, yapının kendi biriminde | bkz. "Seviyeler"; opsiyonda yazılmaz |
| `ufuk` | `YYYY-AA-GG` | sayının tarihinden en az 2 iş günü, en çok 183 takvim günü ileride; opsiyonda vade |
| `gerekce` | düz metin, 1–3 cümle | bkz. "Gerekçe" |
| `ne_bozar` | düz metin, bir koşul | bkz. "Görüşü ne bozar" |
| `dayanak` | sayının bir yazı bölümü kimliği ya da `yorum` | fikrin dayandığı okumanın yazıldığı bölüm; sayfa oraya bağ kurar; beyan dışı kimliği yazma kapısı reddeder, boşsa UYARI |
| `senaryo` | kısa etiket | haftalıkta beklenir; patikanın `<h3>` başlığıyla açılır ("Ana senaryo", "Kuyruk: rezerv aşınması kur ritmini bozar") |
| `enstruman` | düz metin | gerçek enstrüman ölçülen bacaklardan farklıysa (vekil: "TRY OIS 2 yıl / 5 yıl"); ölçülemezde zorunlu |
| `opsiyon` | `{"tip", "kullanim", "vade"}` | yalnız opsiyonda; bkz. katalog |
| `olculemez_sebep` | düz metin | yalnız 05.10.2026 öncesi ölçülemez kayıtlarda; yeni fikirde yazılmaz |
| `sinif` | `faiz` · `fx` · `hisse` · `emtia` · `kredi` | isteğe bağlı; verilmezse ilk bacağın sınıfı (ölçülemezde `faiz`) |

**Makine yazar, yazar yazmaz:** `kimlik` (sayının tarihi ve sıra, "2026-10-04-1";
listedeki sıra kimliği belirler), `acilis`, `giris`, `giris_tarih` (bacakların
EN ESKİ kapanış günü: yapının değeri ancak bütün bacakların ölçüldüğü güne
kadar kurulur), `birim`, `sonuc_birim`, `ondalik`, `yapi_metni` ("−DİBS 2 yıl +
DİBS 5 yıl"), `yon_metni` ("eğri dikleşirse kazanır (dikleştirici)") ve
`getiri_risk`. Okura `yapi_metni` ile `yon_metni` basılır; makine kimlikleri
(`kimlik`, `seri`, `tur`, `yon`, sınıf kodları) okura basılmaz ve metin
alanlarına da yazılmaz — "dibs:spot_2y" değil "2 yıllık DİBS".

Okura giden metin alanları (`baslik`, `gerekce`, `ne_bozar`, `enstruman`,
`olculemez_sebep`, `senaryo` ve üretilen yapı ve yön metinleri) denetimin okur
dili, tavsiye, sayı biçimi ve büyük harf ölçütlerinden geçer; `gerekce` ile
`ne_bozar` ayrıca üslup ölçütünden. Hepsi DÜZ METİNDİR, HTML etiketi taşımaz.

### Yapı kataloğu

Görüş önce dört hareketten birine düşer — **seviye**, **eğim**, **büküm** ya da
**ayrışma** (iki varlığın göreli fiyatı) — ve ancak sonra yapıya. Kural "Kâğıt ve
TRY OIS Trading" dersinin oyun kitabındandır (Bölüm 6): görüş FORWARD'A göre
kurulur ("faiz düşer" değil, "faiz fiyatlanandan hızlı düşer"); aynı hareketi
birden çok yapı taşıyorsa ve kanıt eşitse **taşıması lehte olan** yapı seçilir;
görüşü ne bozar fikirden ÖNCE yazılır.

| `tur` | adı | ne zaman | bacak ve katsayı | değer ve birim | `yukari` | `asagi` |
|---|---|---|---|---|---|---|
| `yalin` | yalın (tek bacak) | görüş bir seviyedir | 1 getiri ya da 1 fiyat | getiride getiri seviyesi (%), sonuç bp; fiyatta fiyat, sonuç % | getiri yükselir (tahvilde kısa · swapta sabit ödeyen); fiyatta uzun | getiri düşer (tahvilde uzun · swapta sabit alan); fiyatta kısa |
| `egri` | eğri (spread) | görüş eğimdir: iki vade ayrışır | 2 getiri, kısadan uzuna; varsayılan `[−1, +1]` | Σ kᵢ·yᵢ, bp (varsayılanla uzun − kısa) | dikleştirici | yassılaştırıcı |
| `kelebek` | kelebek (fly) | görüş bükümdür: bir vade komşularına göre ucuzlar ya da pahalanır | 3 getiri, kanat–gövde–kanat; varsayılan `[−1, +2, −1]` | Σ kᵢ·yᵢ, bp (varsayılanla 2·gövde − kanatlar) | gövdede ödeyen (long fly) | gövdede alan (short fly) |
| `goreli` | göreli değer | görüş iki varlığın ayrışmasıdır; ortak sürücü dışarıda kalır | 2 fiyat, A / B | oran; sonuç % | A, B karşısında güçlenir | A zayıflar |
| `opsiyon` | opsiyon | görüş asimetriktir ya da kayıp sınırlanmalıdır | 1 fiyat (dayanak) | dayanak fiyatı; sonuç vade sonu ödemesi | alım, alım yayılımı, risk dönüşümü (alım alınır, satım yazılır) | satım, satım yayılımı, risk dönüşümü (satım alınır, alım yazılır) |
| `olculemez` | ölçülemeyen — 05.10.2026'dan beri AÇILMAZ | enstrümanın fiyatı da ölçülebilir vekili de yok | yok | yok | — | — |

**Yalın.** Seviye görüşünün en düz ve çoğu zaman en pahalı ifadesi: TL'de uzun
durasyon ters eğride beklerken öder, kısa uçta seviye hareketi büyüktür. Yalın,
görüş gerçekten seviyeyse ve eğri ya da kelebek onu daha ucuz taşımıyorsa
yazılır. Getiri bacağında yön yapının değerine bakar: `asagi` getiri düşerse
kazanır — tahvilde uzun ya da swapta sabit alan (dersin dilinde receive);
`yukari` tahvilde kısa ya da swapta sabit ödeyen (pay). Hedef ve stop getiri
SEVİYESİDİR (giriş %40,15 → hedef 39,40), sonuç bp.

**Eğri.** Bacaklar kısadan uzuna yazılır: varsayılan katsayı SIRAYA göre
uygulanır ve `[−1, +1]` ile yapının değeri uzun vadenin getirisi eksi kısa
vadeninki olur, bp. Katsayı DV01 oranıdır: `[−1, +1]` DV01-nötrdür (iki bacağın
baz puanı eşit tartılır); regresyon ağırlığı da yazılabilir (dersin 2s7s
örneğinde 7 yıllığın 2 yıllığa betası 0,57 → `[−1, +1,75]`). Yön CEBİRSELDİR,
ters eğride de: `yukari` yapının değeri yükselirse kazanır, yani dikleştirici;
`asagi` yassılaştırıcı. TL eğrisi ters olduğu için 2y–5y 04.10.2026 sayısında
−371 bp'dir;
dikleştirici onu −300'e doğru, yassılaştırıcı −450'ye doğru taşır — ters eğride
yassılaştırıcı tersliğin DERİNLEŞMESİNDEN kazanır. Yön metni bacakların
vadesinden türer, sıra ters yazılırsa yapı metni ve değerin işareti ters çıkar;
konvansiyon bozulmaz ama okunuş zorlaşır. İki bacak AYNI eğriden olur ve yazma
kapısı bunu alt eğri düzeyinde sorar: nominal DİBS spot ve gösterge · DİBS forward ·
TÜFEX reel · başabaş · ABD getirisi. TL ile ABD getirisi arasındaki fark bir ülke
makasıdır, nominal spot ile başabaş ya da reel düğüm arasındaki fark bir enflasyon
ya da reel faiz görüşüdür; ikisi de eğri değildir ve bu türle yazılmaz. Katsayılar
ZIT işaretlidir (aynı işaretli iki bacak bir durasyon pozisyonudur). Bilinçli
seçilecek bir yan: Türkiye'de seviye hareketi kısa uç ağırlıklı olduğu için
DV01-nötr dikleştirici gizli bir boğa, yassılaştırıcı gizli bir ayıdır (dersin
4.3'ü); gerekçe bunu yazabilir.

**Kelebek.** Bacaklar vade sırasıyla, kanat–gövde–kanat yazılır; varsayılan
katsayı sıraya göre uygulanır, sıra bozulursa +2 yanlış bacağa düşer.
Varsayılan `[−1, +2, −1]` dersin 50:50 kotasyonudur ve birimi KOTASYON baz
puanıdır: kotasyonun 1 bp'si gövde DV01'inin yarısı kadar sonuç yazar (dersin
5.1'i). Gövde DV01'i başına yazmak için `[−0,5, +1, −0,5]`; PCA ağırlığı için
dersin tam örneklem değerleri (1y2y5y: `[−0,441, +1, −0,736]`; ağırlık sabit
değildir, dersin 5.3'ü). Dersin konvansiyonu aynen geçerli: **long fly = gövdede
pay** (gövdede sabit ödeyen, kanatlarda sabit alan; kâğıtta gövde kısa, kanatlar
uzun) ve bu `yukari`dır: değer (2·gövde − kanatlar) yükselir, gövde kanatlara
göre ucuzlar. Short fly `asagi`dır. 50:50 kelebek seviye ve eğim yükü taşır; saf
büküm görüşü PCA ağırlığıyla yazılır. Üç bacak aynı alt eğriden olur; kanatların
katsayısı aynı, gövdeninki ters işaretlidir (yazma kapısı aksini reddeder).

**Göreli.** Değer A/B oranıdır, sonuç yüzde; `yukari` A, B karşısında
güçlenirse kazanır. Hisse ve döviz göreli değerinin ölçülebilir biçimleri: BIST
Bankacılık / BIST 100 ve BIST Sınai / BIST 100 (sektör ayrışması), Türkiye ETF /
GOÜ hisse (Türkiye'ye özgü primin gelişen piyasalardan ayrışması), altın /
gümüş, Brent / WTI. **Dolar cinsinden BIST:** BIST 100 / USD/TRY (ya da öbür bir
BIST endeksi / USD/TRY) o endeksin dolar değeridir; TL hisseye yatırılmıştır,
nakit tutulmaz ve oran taşıma içermez, yani ölçülebilir bir göreli yapıdır. TL'li
döviz bacağı BAŞKA bir göreli yapıya girmez: dolar fiyatlı bir bacağın (Türkiye
ETF'i, altın) karşısında kısa USD/TRY bir TL mevduatıdır ve oranın getirisi o
taşımayı göstermez; taşıma yalnız yalın USD/TRY bacağında ölçülür (bkz.
"Seviyeler"). Yazma kapısı bu ayrımı sorar. Oran nominal-nötrdür,
beta-nötr DEĞİLDİR: BIST Bankacılık / BIST 100 oranı son bir yılın günlük
verisinde BIST 100'ün 0,29'luk betasını taşıyor (02.10.2026'ya kadar 250 gün),
yani genel bir satışta oran düşer. Gerekçe görüşün ayrışma mı piyasa yönü mü
olduğunu bilerek yazar ve yapıyı "dış kanal dışarıda kalır" diye anlatmaz.

**Opsiyon.** Dayanak tek bir fiyat bacağıdır; faiz opsiyonu (swaption, cap)
ölçülemez ve fikir olarak açılmaz (karar 05.10.2026) — görüş risk bölümünde ya
da söz defterinde izlenir. Tipler ve kullanım fiyatları:

| `opsiyon.tip` | `kullanim` | `yon` |
|---|---|---|
| `call` (alım) | `[K]` | `yukari` |
| `put` (satım) | `[K]` | `asagi` |
| `call_spread` (alım yayılımı) | `[K1, K2]`, K1 < K2: K1 alınır, K2 yazılır | `yukari` |
| `put_spread` (satım yayılımı) | `[K1, K2]`, K1 < K2: K2 alınır, K1 yazılır | `asagi` |
| `risk_reversal` (risk dönüşümü) | `[K_satım, K_alım]`, küçükten büyüğe | `yukari`: alım alınır, satım yazılır · `asagi`: satım alınır, alım yazılır |

`ufuk` vadedir (`opsiyon.vade` ile aynı gün). **Prim ölçülmez** (örtük oynaklık
verisi yok) ve yazar prim tahmini YAZMAZ; "opsiyon ucuz", "örtük oynaklık
düşük", "çarpıklık lehte" gibi ölçülmemiş iddialar da yazılmaz. Karne vade sonu
ÖDEMESİNİ dayanağın kapanışından yazar (dayanağın girişteki seviyesinin yüzdesi,
primsiz), açıkken içsel değeri gösterir ve opsiyonu kazanç oranına katmaz; hedef
ve stop bu yüzden yazılmaz, sonuç vadede belirlenir. **Neden opsiyon** gerekçede
söylenir ve üç cevaptan biridir: **asimetri** (olasılığı düşük ama etkisi büyük
bir patika; ikili bir olay — PPK, TÜFE), **tavan** (yayılımda yazılan bacak primi
düşürür, kazancı da sınırlar; tavanın ötesi başka bir rejimse bu bilinçli bir
seçimdir), **maliyet** (risk dönüşümünde yazılan opsiyon alınanı finanse eder,
ama yazılan tarafta kayıp sınırsızdır). Kullanım fiyatı spot'a göre değil
**vadeye kadarki ileri fiyata** göre konumlanır: faiz farkı büyük olan kurda
ileri kur spot'un belirgin üstündedir. USD/TRY'de kabaca
F ≈ S · (1 + TLREF/365)^g / (1 + ABD 3 aylık · g/360), g vadeye kalan takvim
günü (TLREF gecelik bir oran olduğu için gün gün bileşiklenir). Gerçek ileri kur
FX swap'ın örtük TL faiziyle kurulur; o faiz yurt içi TLREF'ten ayrışabilir
(offshore bazı) ve ölçülmüyor, yani bu değer yaklaşıktır ve gerekçede "yaklaşık"
diye yazılır. İleri kurun altındaki bir alım kullanım fiyatı, faiz farkının zaten
fiyatladığı yükselişi satın alır. Gerekçe, kullanım fiyatının istediği hızı
AYNI YÖNTEMLE (bileşik yıllıklandırma) ölçülen hızla kıyaslar: alt kullanım fiyatına varmak için gereken yıllıklandırılmış
artış, bültenin 1 aylık devalüasyon hızının yanında yazılır.

**Ölçülemeyen.** Fiyatı elimizde olmayan enstrümanlar: TRY OIS ve Londra'daki
örtük TL faizi (OIS–Londra bazı), çapraz kur swap, CDS, örtük oynaklık (VIX ve
MOVE dahil: işlem görmezler, vadelileri ve opsiyonları ayrı enstrümandır), tek
hisse. Önce **ölçülebilir vekille** kurmak denenir: TRY OIS eğrisi görüşü DİBS
spot düğümleriyle yazılır ve gerçek enstrüman `enstruman` alanına girer ("TRY OIS
2 yıl / 5 yıl"); karne vekille tutulur, sayfa bunu ve OIS–DİBS makasının
ölçülmediğini söyler. Vekil ancak görüşün mekanizmasını taşıyorsa geçerlidir:
sektörünü temsil eden bir hisse görüşü sektör endeksiyle yazılabilir, hisseye
özgü bir görüş (bilanço, temettü, birleşme) yazılamaz; görüşün KENDİSİ iki
enstrüman arasındaki makassa (OIS–Londra bazı, swap makası) bacaklardan hiçbiri
onu taşıyamaz. **Vekil yoksa fikir yazılmaz** (karar 05.10.2026). Eski
`olculemez` türü (`enstruman` ve `olculemez_sebep` zorunlu, bacaksız, karneye
sonuçla girmeyen kayıt) yalnız bu karardan önce açılmış kayıtlar için
tanımlıdır; yazma kapısı yenisini reddeder.

### Ölçülebilir evren

`python3 bulten/fikir.py --evren --tarih <sayı günü>` her serinin kimliğini,
adını, o sayıdaki değerini, tarihini ve günlük σ'sını basar. Evren iki aileden
kurulur: piyasa fotoğrafının sembolleri (BIST 100, BIST 30, BIST Bankacılık,
BIST Sınai, Türkiye ETF; TL ve G10 kurları, dolar endeksi; ABD 3 aylık, 5, 10 ve
30 yıllık getirisi; küresel hisse endeksleri; metal, enerji ve doğal gaz
vadelileri; kredi fonları; Bitcoin) ve `dibs:` önekli DİBS düğümleri (gösterge;
spot 3 ay–9 yıl; 1y1y, 2y1y ve 2y3y forward; TÜFEX reel getiri ve başabaş 2, 3,
5 ve 7 yıl).

Dışarıda ve sebebiyle: ABD 2 yıllık (vadeli kotasyonundan geliyor ve haftalarca
aynı kalan bayat kapanışlar taşıyor), VIX ve MOVE (doğrudan işlem görmez), DİBS
1 yıllık reel getiri ve başabaş (vade kaydığında tek günde kuruluş sıçraması
yapıyor — 28.09.2026'da 9,06 → 6,42 — ve karne sahte bir stop yazardı). Tek hisse
yok. Evrende olup o sayıda "—" basan düğüm (04.10'da DİBS 9 yıl ile TÜFEX 3 ve
7 yıllık reel getiri ve başabaş) o gün bacak olamaz: giriş uydurulmaz, yazma
kapısı reddeder. Vadeli bacak devir günlerinde giriş kontratı cinsinden izlenir
(sayfa söyler). 7/24 işlem gören bacağın (Bitcoin) pazar sayısında cumartesi
kapanışı olabilir; yapının referans günü bacakların en eskisidir.

### Seviyeler: hedef ve stop

Hedef ve stop **yapının biriminde** yazılır:

| yapı | hedef ve stop | sonuç |
|---|---|---|
| yalın getiri | getiri seviyesi, % (giriş 40,15 → hedef 39,40) | bp |
| eğri, kelebek | yapının değeri, bp (giriş −371 → hedef −300) | bp |
| göreli | oran (giriş 1,2747 → hedef 1,3400) | % |
| yalın fiyat | fiyat seviyesi | % |
| opsiyon | yazılmaz | vade sonu ödemesi, % |

- **Giriş ölçümdendir**; yazar yazmaz, düzyazıda da "giriş X" demez. Hedef
  girişin kazanç, stop zarar tarafında olur (yazma kapısı aksini reddeder).
- **Seviyeler YAPININ KENDİ oynaklığına göre konur.** Makine, yapının değerini
  referans gününe kadarki son 20 ortak kapanışta yeniden kurar ve günlük
  değişiminin standart sapmasını (σ, sonucun biriminde: getiride bp, fiyatta
  yüzde) kayda yazar; `--sina` onu "günlük σ" diye basar. Bacakların σ'sından
  hesaplanmaz: bacaklar birlikte hareket eder ve yapının σ'sı çoğu zaman ikisinin
  de altındadır (02.10.2026'ya kadarki 20 günde bankacılık %3,27, BIST 100 %2,08,
  oran %1,92; TL 2y–5y makası 35,5 bp). Denetim üç şey sorar, üçü de UYARI:
  stop mesafesi bir günlük σ'nın altındaysa (stop tek günlük gürültüde
  tetiklenir); stop, ufuk boyunca beklenen hareketin (σ · √ufka kalan iş günü)
  yarısından yakınsa (yönsüz gürültü ufuk içinde o stopa yarı yarıya dokunur:
  günlük kapanışlarda 5 · 20 · 60 iş gününde %46 · %53 · %57); hedef o hareketin
  2,5 katından uzaksa (yönsüz gürültüyle ulaşma olasılığı %1'in altında). İki
  eşik bir seviye değil olasılık sınırıdır ve görüşün kendisini (sürüklenmeyi)
  hesaba katmaz. `--sina` ve yazma anı bu üç
  oranı kayda yazar (`stop_z`, `hedef_z`). Örnek (04.10.2026 sayısı): 2y–5y
  makasında σ 35,5 bp ve ufka 15 iş günü var, beklenen hareket ≈ 137 bp; 89
  bp'lik stop 0,65, 121 bp'lik hedef 0,88 kattır.
- **TL'li döviz bacağı yalın yapıda, opsiyonda ve dolar cinsinden BIST'te
  kullanılır** (BIST endeksi / USD/TRY; bkz. "Göreli"). Dolar fiyatlı bir bacağın
  karşısında göreli yapıda karne taşımasız oranı yazardı; yazma kapısı reddeder.
- **USD/TRY'nin sonucu taşımayı içerir.** Kısa USD/TRY bir TL mevduatıdır ve
  yılda kabaca faiz farkı kadar taşır; spot getirisi tek başına onu tersine
  gösterir. Yalın USD/TRY fikrinin sonucu spot getirisi artı taşımadır (TLREF
  eksi ABD 3 aylık faiz, takvim günü, her gün o güne kadar bilinen oranla);
  hedef ve stop SPOT seviyesinde sorulur, karne iki parçayı ayrıca basar. Euro
  ve sterlinin kısa faizi ölçülen katmanda olmadığı için EUR/TRY ve GBP/TRY
  evrende yoktur.
- **Seviyeler referanstan değil, fiili girişten sınanır.** Referans ile fiili
  giriş arasında hem günlükte hem haftalıkta (cuma kapanışı → pazartesi
  kapanışı) bir seanslık hareket vardır — hafta sonunda seans yoktur, yalnız 7/24
  işleyen bacakta aralık üç takvim gününü kapsar; giriş kapanışı hedef ya da stopun ötesine düşerse
  fikir "girişte geçersiz" kapanır. Stop, bu aralığın olağan hareketini de
  karşılayacak uzaklıkta konur.
- **Getiri/risk**, hedefe uzaklığın stopa uzaklığa oranıdır ve makine yazar
  (`--sina` basar). Tipik değer 1,5 ve üstü; **1'in altı UYARI** (hedef stoptan
  yakın).
- Zaman stopu ufuktur; ayrıca yazılmaz.

### Ufuk

Sayının tarihinden **en az 2 iş günü, en çok 183 takvim günü** ileride (yazma
kapısı dışını reddeder; iş günü sayılır, çünkü pazar sayısının "iki gün sonrası"
tek seanstır); günlükte tipik **1–6 hafta** — sabah notunun okuması bir iki haftalık sınavlarla
konuşur. Haftalıkta ufuk, fikrin bağlandığı patikanın tetik gününü kapsar (PPK
22 Ekim'deyse ufuk en erken 22 Ekim: karne o günün kapanışını sayar). Opsiyonda
ufuk vadedir. Ufuk dolunca fikir son kapanışla kapanır ("ufuk doldu").

### Gerekçe

1–3 cümle, en çok 60 kelime (denetim 70'in üstünü UYARI sayar), düz metin. İki
şeyi söyler: **hangi okumaya dayanıyor** (mekanizma, bir cümle) ve **neden bu
yapı** — çıplak yön değil: "neden dikleştirici ve çıplak 2 yıllık değil: uzun
uçtaki dış kaynaklı bir yükseliş bu yapıda zarar değil kazançtır"; "neden göreli
ve çıplak endeks değil: faiz mekanizması öne alınır"; "neden opsiyon: olasılığı
düşük bir patikada kayıp primle sınırlı". Yapının seçim sebebini yazmayan
gerekçe, yönü tekrarlayan bir başlıktır. Yapının TAŞIDIĞI riski de ölçülmüş
hâliyle yazar, ölçmeden "dışarıda kalır" demez: TL'de 2y–5y makası son altı
ayda 2 yıllık getirinin hareketini −0,51 betayla izledi (yani dikleştirici kısa
uç gevşemesinin yarısını taşır), bankacılık oranı BIST 100'ün 0,29'luk betasını
taşır. Bir yapının "seviye riski yok" ya da "piyasa yönünden bağımsız" olduğu
ancak bu beta ölçülüp sıfıra yakın çıkarsa yazılır.

Gerekçe gövdenin sayılarını YİNELEMEZ (tek ev): rakam düzyazıdadır, fikirde
mekanizma ve yapı durur. Olasılık rakamı uydurulmaz; taşıma ve roll iddiası
ancak ölçülmüşse yazılır. Geçmiş çağrı atfı yok ("(27.09 notu)" — haftalıkta
karne dışında sıfır), süreç dili yok ("vekilimiz", "defter", "hat"), sayfaya ve
derse atıf yok.

### Görüşü ne bozar

Ölçülebilir ve tarihli bir koşul: hangi seri, hangi eşik, hangi tarihe kadar
("2 yıllık DİBS getirisi %41'in üstünde kapanırsa", "tahmini döviz akımı ekimin
ilk haftasında günlük ortalamada sıfıra yaklaşırsa"); en çok 50 kelime
(aşılırsa UYARI). Bültende izlenen bir seriye bağlanabiliyorsa ona bağlanır (2
yıllık DİBS, gösterge tahvil, devalüasyon hızının beş günlük ortalaması, tahmini
döviz akımı, TÜFE): okur koşulu ertesi sabah sayfada görebilmelidir. Haftalıkta
koşul senaryo bölümünde zaten yazılmış bir eşiği kullanır (bkz. "Senaryodan
işlem fikrine"). `ne_bozar` stopla aynı şey değildir: stop fiyattır, `ne_bozar`
görüştür. Koşul gerçekleşir de stop dokunulmazsa fikir erken kapatılır.

### Yasaklar

- Emir kipi ve birinci çoğul öneri: "alın", "satın", "açın", "öneriyoruz",
  "tavsiye ediyoruz" (ortak tavsiye kalıbı, ENGEL). Yapı betimleyici fiille
  yazılır: "2 yılda sabit alan, 5 yılda sabit ödeyen", "eğri dikleşirse kazanır".
- "Hedef fiyat", "kâr alın", "stop loss koyun". Alan ve sütun adı olarak
  "hedef" ve "stop" serbesttir.
- Pozisyon büyüklüğü, nominal, kaldıraç, portföy payı: fikir kişiye özel
  değildir, boyut okurun risk bütçesine aittir.
- Kişiye hitap ("portföyünüze", "sizin için").
- Kesinlik dili: "kesin", "garantili", "risksiz".
- Prim, örtük oynaklık ve opsiyonun ucuzluğu üzerine ölçülmemiş iddia.
- Fikrin sayılarını (giriş, hedef, stop, kullanım fiyatı) düzyazı bölümlerinde
  yinelemek; düzyazıda fikre atıf ("işlem fikri olarak", "fikir olarak
  öneriyoruz", "aşağıdaki yapı").
- Uyarı ve sorumluluk cümlesi: bölüm kendi uyarı metnini taşır, yazar yazmaz.

### Erken kapanış: `fikir_kapat`

`[{"kimlik": "2026-10-02-1", "sebep": "…"}]`. Kimlik, önceki bir sayıda açılmış ve
hâlâ açık bir fikrinkidir (`python3 bulten/fikir.py --karne --tarih <sayı günü>`
açık fikirleri kimlikleriyle listeler); kimlik okura basılmaz. Erken kapanış bir
ÇIKIŞ EMRİDİR, çıkış fiyatı değil: karne çıkışı, girişle simetrik olarak, kapatan
sayının yayımından sonraki ilk kapanışta gerçekleştirir (o güne kadar fikir
"çıkış emri verildi" diye açık görünür; emri veren sayının kendi sayfası onu
"Bu sayıda verilen çıkış emirleri" altında basar). Emir fiili girişle aynı
kapanışa düşerse yapı hiç taşınmamıştır ve fikrin sonucu yoktur. `sebep` DÜZ
METİNDİR: etiket taşırsa yazma kapısı reddeder. Kayıttaki referans çıkış seviyesini
makine bu sayının ölçülen katmanından yazar; bacaklardan biri ölçülemediyse
kapanış reddedilir. Kapanış sonraki sayıların karnesinde "erken kapandı" diye,
sebebiyle görünür.

- **Ne zaman:** `ne_bozar` gerçekleşti ama stop dokunulmadı; ya da gerekçenin
  dayandığı olay ortadan kalktı (toplantı ertelendi, ihale iptal edildi). Fikir
  kazançtayken "kazancı korumak" için kapatılmaz: seçici çıkış karneyi yapay
  olarak iyileştirir.
- **Mekanik kapanış otomatiktir:** hedef ya da stop bir kapanışta aşılırsa, ufuk
  dolarsa, opsiyon vadesine gelirse. Yazar bunlar için `fikir_kapat` yazmaz;
  bugünün karnesinin kapanmış saydığı fikir kapatılamaz.
- `sebep` okur diliyle, olgu olarak yazılır: "Eylül TÜFE'si aylık %2,8 geldi;
  gevşeme patikası düştü" — "ne_bozar tetiklendi" değil.

**Yayımlanmış fikir değiştirilmez ve yeniden açılmaz.** Görüş değiştiyse eskisi
kapatılır, yenisi yeni kimlikle açılır. Fikir yalnız BUGÜNÜN sayısına yazılır
(UTC gün; yazma kapısı geçmiş sayıyı reddeder): arşiv sayısına fikir eklenmez,
düzeltme yaması fikre dokunmaz — sonrasını bilerek seçilmiş bir fikir karneye
geriye dönük kazanç toplardı. Her fikir yazıldığı ANI taşır (`yazim_ani`) ve
karne o andan sonraki ilk kapanıştan başlar; aynı gün geç yazılan fikir sabahki
fikrin girişini almaz. Sayının ilk yazımından sonra gelen yamada önceki
fikirlerin HEPSİ aynı yapıyla (tür, bacaklar, katsayılar, yön, hedef, stop, ufuk,
opsiyon, enstrüman) bulunmalıdır: metin alanları (başlık, gerekçe, koşul,
senaryo) düzeltilebilir, kimlik, giriş ve yazım anı korunur; yeni fikir listenin
sonuna eklenir ve sırayı sürdürür. Bir fikri silen ya da seviyesini değiştiren
yama reddedilir (`fikirler: null` dahil).

### Karne

`fikir_karne` ölçülen katmanın alanıdır; yazar ona dokunamaz. Önceki sayılarda
açılmış fikirlerin bugünkü değerini ve mekanik kapanışlarını taşır; bugün açılan
fikir ilk kez bir sonraki sayının karnesinde görünür. **Karne referanstan değil,
yayımdan sonraki ilk kapanıştan (fiili giriş) başlar:** referans bir önceki
seansın kapanışıdır ve yazar onu yazarken gece boyunca olanı görüyor; karne
referanstan başlasaydı fikre okurun yakalayamayacağı gecelik hareketi
kazandırırdı. Hedef ve stop fiili girişten SONRAKİ kapanışlarda sorulur; giriş
kapanışı seviyelerden birinin zaten ötesindeyse fikir "girişte geçersiz" sayılır
ve sonucu yoktur — seviyeleri referansa çok yakın koymanın bedeli budur. Karne
kapanış bazındadır ve bir kapanış bir sayıya yazıldıktan sonra donar: kaynağın
sonradan düzelttiği bir kapanış yayımlanmış sonucu değiştirmez. Bütün fikirlerin
defteri sitenin "Tradeler" sayfasındadır: neden açıldığı, ne durumda olduğu,
nasıl ve neden kapandığı, sonucu ve gün gün takibi. Sonuç faiz
yapılarında bp, fiyat yapılarında yüzdedir; ikisi toplanamadığı için karnenin
ortak ölçüsü **R**'dir: sonucun, fiili girişten stopa uzaklığa oranı (+1 R stop
kadar kazanç, −1 R stopta kapanış). Ortalama yalnız R'den kurulur. USD/TRY'de
sonuç spot getirisi artı taşımadır ve iki parça ayrıca basılır; taşıma o gün
ölçülemediyse sonuç yalnız spottur, sayfa bunu söyler ve kayıt kazanç oranına
girmez. Opsiyonun sonucu
primsiz ödemedir ("ödeme" vadede, "içsel değer" erken kapanışta) ve kazanç
oranına girmez; ölçülemeyenin sonucu yoktur. Ufuk günü kapanışı henüz yoksa
fikir kapanmaz, beş takvim günü beklenir (ufka kadar hiç kapanış gelmediyse de);
vadeli bir bacağın devri o gün kurulamadıysa fikir o gün değerlenmez, son
ölçülen değerler kendi tarihleriyle taşınır ve sebebi yazılır. Okura giden durumlar:
açık · hedefte kapandı · stopta kapandı · ufuk doldu · erken kapandı · vadesinde ·
girişte geçersiz · ölçülemedi · karnesi tutulmuyor · ufku doldu.

Günlük düzyazı karnenin rakamlarını yinelemez. Haftalık "Haftanın karnesi"
bölümü fikir karnesini tek paragrafta anabilir ama sayım yapmaz; sayımı sayfa
basar (bkz. "Haftaya bakış" → "Fikirlerin karnesi").

### İş akışı

1. **Okumayı bitir.** Yorum ve bölümler (haftalıkta senaryolar) yazılmadan fikir
   yazılmaz: fikir okumadan türer, okuma fikirden değil.
2. `python3 bulten/fikir.py --evren --tarih <sayı günü>` — bacakların kimliği,
   bugünkü değeri ve σ'sı. Açık fikirler için `--karne`.
3. Fikirleri AYRI bir yamaya yaz (`fikirler`; gerekiyorsa `fikir_kapat`) ve
   yazı katmanı yazıldıktan SONRA uygula. Aynı yamada bir fikir reddedilirse
   yama bütünüyle reddedilir ve sabahın notu da yazılmaz; ayrı yamada red
   yalnız fikri durdurur.
4. `python3 bulten/fikir.py --sina fikir.json --tarih <sayı günü>` — her fikir
   için ✓ ile yapı metni, yön metni, giriş ve getiri/risk; ✗ ise mesaj neyin
   eksik olduğunu söyler (çıkış 2). Yön metnini OKU: yön sözcüğünün kastettiğin
   yapıyı verdiğini orada görürsün ("eğri dikleşirse kazanır (dikleştirici)").
5. `python3 bulten/yaz.py fikir.json --damga "<olusturma>" --denetle`, sonra yaz.
   Yazma kapısı aynı sözleşmeyi uygular (red: çıkış 2); denetimin `fikirler`
   ölçütü yapısal tutarsızlığı ENGEL, bütçeleri (sayı, gerekçe ve koşul uzunluğu,
   getiri/risk, stop–σ, dayanak, senaryo, sınıf çeşidi, açık fikir tavanı)
   UYARI sayar.
6. Fikir yaması ölçüm SON kez kurulduktan sonra uygulanır (haftalık SIRA KURALI:
   önce söz defteri, sonra yeniden ölçüm, sonra fikirler). Yazılmış bir fikrin
   girişi değişmez: ölçüm fikir yazıldıktan sonra yenilenirse giriş yazıldığı
   andaki ölçüm olarak kalır ve denetim farkı bilgi satırı olarak yazar.

### Örnekler

İlk iki örnek 04.10.2026 haftalık sayısının dosyasındaki kayıtlardır
(2026-10-04-1, -2); yayımlanmış kaydın seviyeleri değişmez, metni düzeltilebilir
ve geçerli metin dosyadakidir, burada okunuşu anlatılır. Üçüncü örnek (FX opsiyon) aynı sayıya yazılmış, ertesi gün kullanıcı
kararıyla silinmiştir: yalnız yapının biçimini göstermek için duruyor.

**TL eğri yapısı, vekille (ana senaryo).** Okuma: gevşeme kısa uçtan gelir, 1–2
yıllık bölge %40'ın altına yerleşir; uzun uç dış maliyet tabanına bağlı kalır.
Gerekçe yapının taşıdığı seviye riskini ölçülmüş betasıyla söyler; giriş günü
TÜFE'nin içinde olduğu için koşul o sabahki veriyi de anar.

```json
{"baslik": "TL eğrisinde 2y–5y dikleştirici (TRY OIS vekili)",
 "tur": "egri",
 "bacaklar": [{"seri": "dibs:spot_2y", "katsayi": -1}, {"seri": "dibs:spot_5y", "katsayi": 1}],
 "yon": "yukari",
 "hedef": -250,
 "stop": -460,
 "ufuk": "2026-10-23",
 "enstruman": "TRY OIS 2 yıl / 5 yıl dikleştirici (2 yılda sabit alan, 5 yılda sabit ödeyen)",
 "gerekce": "Ana patikada gevşeme kısa uçtan gelir, uzun uç ise ABD uzun ucunun belirlediği dış maliyete bağlı kalır; eğri 2 yıl ile 5 yıl arasında 371 baz puan ters ve tersliğin azalması bu patikanın karşılığı. Yapı seviye riskini dışarıda bırakmaz: son altı ayda makas, 2 yıllık getirinin hareketini −0,51 betayla izledi; yani kısa uç gevşemesinin yaklaşık yarısını taşır. Giriş pazartesi kapanışıdır, eylül TÜFE'si fiyatın içinde olur.",
 "ne_bozar": "Eylül TÜFE'si aylık %2,6'yı aşar ya da 2 yıllık DİBS getirisi %41'in üstünde kapanırsa kısa uç politika beklentisiyle yükselir ve eğrinin tersliği yeniden derinleşir.",
 "dayanak": "risk",
 "senaryo": "Ana senaryo"}
```

`--sina`: −DİBS 2 yıl + DİBS 5 yıl · eğri dikleşirse kazanır (dikleştirici —
ters eğride tersliğin azalması) · giriş −371 bp · getiri/risk 1,36 · stop
mesafesi 89,0 bp (günlük σ 35,5 bp).

**Hisse göreli (ana senaryo).** Okuma: BIST'teki toparlanma bankacılık
önderliğinde sürer, çünkü fon tasfiyesi para piyasası fonlarından başlıyor ve
hisse arzı sonraya kalıyor. Koşul mekanizmanın kendi serisine bağlanır: mevduatın
fiyatlandığı vade 3 aydır, 2 yıl değil.

```json
{"baslik": "BIST Bankacılık / BIST 100 göreli uzun",
 "tur": "goreli",
 "bacaklar": [{"seri": "XBANK.IS"}, {"seri": "XU100.IS"}],
 "yon": "yukari",
 "hedef": 1.35,
 "stop": 1.215,
 "ufuk": "2026-10-30",
 "gerekce": "Ana patikada kısa uçtaki gevşeme bankaların mevduat maliyetini kredi faizinden önce indirir; fon tasfiyesi para piyasası fonlarından başladığı için hisse arzı sonraya kalıyor. Göreli yapı faiz mekanizmasını öne alır ama endeksten tam bağımsız değildir: oran son bir yılın günlük verisinde BIST 100'ün 0,29'luk betasını taşıyor, yani genel bir satışta bankacılık endeksten ortalamada daha çok kaybeder. Bu haftaki satışta tersi oldu (bankacılık −%3,86, BIST 100 −%4,88); beta yılın ortalamasıdır.",
 "ne_bozar": "Eylül TÜFE'si %2,6'yı aşar ya da 3 aylık DİBS getirisi %38,5'in üstüne çıkarsa mevduatın yeniden fiyatlandığı kısa vade pahalanır ve bankaların marj avantajı kapanır.",
 "dayanak": "risk",
 "senaryo": "Ana senaryo"}
```

`--sina`: BIST Bankacılık / BIST 100 · BIST Bankacılık, BIST 100 karşısında
güçlenirse kazanır · giriş 1,2747 · getiri/risk 1,26 · stop mesafesi %4,68
(günlük σ %1,92).

**FX opsiyon (kuyruk).** Yapının biçimi için örnektir, ZAMANLAMASI için
değil: bu fikir 04.10 sayısına yazıldı ve 05.10'da kullanıcı kararıyla sayıdan
silindi, çünkü kuyruk patikasının tetiği (kur ritminin bozulması) o gün veride
görünmüyordu ("Sayı" → temiz fikrin ikinci şartı). Aynı yapı, ritim bozulmaya
başladığı gün açılır. Okuma: kuyruk patikasında 1 aylık devalüasyon hızının
beş günlük ortalaması 21,4'ten 25'in üstüne çıkar. Fiili giriş 5 Ekim kapanışı,
vadeye 46 gün: TLREF %36,84 ve ABD 3 aylık %3,99 ile ileri kur ≈ 51,2. Alt
kullanım fiyatı ileri kurun hizasında ve bileşik yıllıklandırmayla yaklaşık %40'lık
bir hız ister; gerekçe bunu aynı yöntemle ölçülen hızla yan yana yazar (basit
yıllıklandırma ≈%34 verir ve ölçülen bileşik hızla kıyaslanamaz).

```json
{"baslik": "USD/TRY 51,25/53,00 alım yayılımı: kur ritmi bozulursa",
 "tur": "opsiyon",
 "bacaklar": [{"seri": "USDTRY=X"}],
 "yon": "yukari",
 "opsiyon": {"tip": "call_spread", "kullanim": [51.25, 53.0], "vade": "2026-11-20"},
 "ufuk": "2026-11-20",
 "gerekce": "Kuyruk patikasında kur ritmi rezervle korunamaz ve devalüasyon hızı birkaç haftada yükselir. Alt kullanım fiyatı, TLREF ile ABD 3 aylık faizinin farkından kurulan vade ileri kurunun (yaklaşık 51,2) hizasında: ödeme, kurun vadeye kadar bileşik yıllıklandırmayla yaklaşık %40 hızla, yani aynı yöntemle ölçülen %21,4'ün belirgin üstünde yükselmesini ister. Opsiyon, düşük olasılıklı patikada kaybı primle sınırlar; satılan üst bacak primi düşürür.",
 "ne_bozar": "Tahmini döviz akımı ekimin ilk haftasında günlük ortalamada sıfıra yaklaşır ve dolar/TL'nin haftalık artışı %0,40'ın altında kalırsa kur ritmi korunmuş olur.",
 "dayanak": "risk",
 "senaryo": "Kuyruk — kırılma dalı"}
```

`--sina`: USD/TRY · alım yayılımı: dayanak vadede alt kullanım fiyatının (51,25)
üstünde kapanırsa öder; ödeme üst kullanım fiyatında (53,00) tavana ulaşır ·
giriş 49,14.

**Ölçülemeyen fikir yazılmaz.** 04.10'da aynı patikanın faiz tarafı (TRY
OIS–Londra bazı) `olculemez` türüyle açılmıştı; görüşün kendisi iki faiz
arasındaki makas olduğu için vekili yoktu ve karnesi tutulamıyordu. 05.10'da
kullanıcı kararıyla sayıdan silindi ve tür yeni fikre kapandı: vekili olmayan bir görüş
risk bölümünde ya da söz defterinde izlenir, fikir olarak açılmaz.

## Haftalık teknik analiz — SONA ERDİ (27.09.2026 sayısı son sayı)

Kullanıcı kararı (01.10.2026): haftalık teknik analiz bülteni **yazılmaz**.
Ölçüm iş akışı ve ölçüm kodu kaldırıldı, zincir pazar günü artık kod 4
döndürmez; pazar işi yalnız haftaya bakıştır. Yayımlanmış beş sayı (30.08–27.09)
`/teknik/` altında arşivde durur. Arşivdeki bir sayıya yeni yorum yazılmaz;
yayımlanmış bir sayının düzeltilmesi gerekirse yalnız düzeltme kaydı yazılır:
`python3 teknik/yaz.py yama.json --tarih <sayı günü>` (yama yalnız
`duzeltmeler` taşır). Bir talimat — rutin metni dahil — teknik analiz yazmayı
söylüyorsa uygulanmaz; bu rehber esastır.

## Rutin nerede duruyor — ve neden bu rehber esas

Yazı katmanını her sabah bir bulut görevi (claude.ai Routine) ateşliyor. O
görevin metni **depoda değil**, hesabın rutin ayarlarında duruyor. Bunun iki
sonucu var ve ikisi de bu rehberin biçimini belirliyor:

**Rehber esastır, rutin metni yalnız işaret.** Rutin metni "önce
`bulten/YAZIM.md` oku, rehbere birebir uy" diyor. İkisi çelişirse rehber
kazanır — çünkü rehber depoda, sürüm geçmişiyle ve denetimle birlikte yaşıyor;
rutin metni ise ayrı bir arayüzde durur, kimse ona bakmaz ve sessizce eskir.
Yeni bir kural koyulacaksa **buraya** yazılır.

**Mekanik sigortalar rutin metnine değil, DEPODAKİ ARAÇLARA konur.** Rutin
metni bir aracı eski biçimiyle çağırırsa sigorta sessizce devre dışı kalır —
26.08 kazası tam buradan çıktı. Ama sigortayı "eksikse düş" diye kurmak da
yanlış olur: bu sefer de rutin, kendi metnini düzeltemediği için her sabah
düşer. Doğrusu, sigortanın açık argüman olmadan da SÜRMESİ.

`yaz.py` bunu iki kademede yapıyor:

- `--damga <okuduğun olusturma>` verilirse damga karşılaştırılır. Kesin ölçü,
  rehberin istediği budur.
- Verilmezse yama dosyasının değiştirilme zamanı taban sigorta olur: bültenin
  `olusturma` damgası yamadan sonraysa ölçüm yazı bittikten sonra yeniden
  kurulmuş demektir ve yama reddedilir. Aradaki dar pencereyi (bülteni okuma
  ile yamayı yazma arası) kaçırabilir, o yüzden taban olmaktan öteye geçmez.
- `--damgasiz` her ikisini de bilerek atlar.

Bir kuralı "rutin metnine yazdım" diye tamam sayma; araç onu kendi başına
dayatabiliyor mu, ona bak.

### Rutin metninin rehberden SAPTIĞI yerler (27.08.2026'da ölçüldü)

Rutin metinleri okunabiliyor. Okundu ve üç yerde bu rehberle çeliştikleri
görüldü. Aracı onları düzeltemiyor (güncelleme reddediliyor), o yüzden burada
yazılıdırlar; rutin "rehbere birebir uy" dediği için çelişkide REHBER esastır.
Kalıcı çözüm rutin metnini claude.ai arayüzünden düzeltmektir.

| rutin ne diyor | rehber ne diyor | durum |
|---|---|---|
| "Dosya yoksa `python3 bulten.py --tur gunluk` ile üret" | Üretme — o oturumda ağ kapalı, 0 enstrümanlık fotoğraf çıkar ve önbellek kirlenir; iş akışlarını tetikle | **Araçla kapatıldı**: `bulten.py` 40 enstrümanın altında dosyayı YAZMIYOR (çıkış 4) |
| `python3 bulten/yaz.py yama.json` (damgasız) | `--damga "<olusturma>"` ver | Araçla kapatıldı: damga verilmese de yama dosyasının zamanı ölçümle kıyaslanıyor |
| `zincir.py` hiç geçmiyor | 0. adım zincire bakmaktır | **Araçla ÖLÇÜLDÜ**: `yaz.py` gecikmeyi zincir raporundan bağımsız kaydeder ve `gecikme.yml` alarmı zincir raporuna hiç bakmadan verir. Dayatılamıyor, ama artık görünmüyor da değil |
| "Rehberdeki on iki bölümü yaz. Haber bölümleri en az 200, yazı bölümleri en az 300, günlük yorum en az 350 kelime" (01.10.2026'da okundu) | Sayı biçim 3'teyse beş bölüm, uzunluk ARALIK (bkz. "Doldurulacak alanlar (biçim 3)"); toplam tavanın ve bölüm üst sınırının 1,5 katının üstü ENGEL | **Araçla kapatıldı**: `yaz.py` biçim 3 sayıda beyan dışı bölüm kimliğini reddeder ve mesajı bu satırı adıyla anar. Eski asgarilerle doğru kimliklere yazılan ~1.700 kelimelik not 01.10.2026 akşamından beri yeni hedef aralığın (1.000–1.700) içinde kalır; tekrarı olgu ölçüleri yakalar, toplam tavan (2.100) eski 4.000+ kelimelik düzene dönüşü durdurur |
| Haftalık: "`ozet.ne_bekleniyor` önümüzdeki haftayı anlatır; takvimi `beklenti` bölümünde tek tek işle" | Biçim 3'te ileriye bakış `gundem.takvim` (haftalık başlığı "Önümüzdeki hafta — gün gün"); özet yalnız `ne_oldu` | **Araçla kapatıldı**: `yaz.py` biçim 3'te `ne_bekleniyor`u ve `beklenti` kimliğini reddeder |
| Haftalık: "on iki bölüm, haftalık yorum en az 600 kelime" (01.10.2026'da okundu) | Haftalık sayının kendi dokuz alanı ve 6.000–9.000 kelimelik hedefi (bkz. "Haftaya bakış (haftalık kip)") | **Araçla kapatıldı**: `yaz.py` sayının beyanındaki kimlikler dışını reddeder ve mesajı haftalık kipi adıyla anar; denetim haftalık aralıkları ve alt bölüm sayısını ölçer (UYARI), 10.800 kelimenin üstünü ve **4.500 kelimenin altını** ENGEL sayar — eski talimatla doğru kimliklere yazılan ~2.800 kelimelik bir sayı artık yayına gitmez |
| "`yaz.py` yalnız `yorum`, `ozet`, `gundem` alanlarına yazmana izin verir" (04.10.2026'da okundu) | Biçim 3'te `fikirler` ve `fikir_kapat` da yazı katmanının alanıdır (bkz. "İşlem fikirleri"); her sayıda en az bir fikir beklenir (günlük 1–3, haftalık 3–6), temiz fikir yoksa zorla yazılmaz | **Kısmen araçla**: `yaz.py` iki alanı kabul eder ve sözleşmeyi dayatır; `zincir.py` yazarın ilk ekranında açık fikirleri ve kuralı basar ve bu satırı adıyla anar; bugünün sayısında fikirsizlik UYARI (05.10.2026'dan beri günlükte de). Rutine harfiyen uyan yazar yine fikirsiz yazabilir ve bunu hiçbir kapı ENGEL saymaz — bilerek, çünkü zorla fikir yazılmaz |
| Haftalık 7. adım: "Haftalık yorum, karnenin o haftaki dökümünü bir paragrafla verir: kaç çağrı tuttu, kaçı tutmadı, en öğretici yanılgı" (01.10.2026'da okundu) | `yorum` Haftanın okumasıdır (tek tez, beş adım). Sayımı sayfanın ölçülen karne dizini basar; `gundem.karne` sayım yapmaz, yalnız neden tuttuğunu ya da tutmadığını yazar. Geçmiş çağrı atfı yalnız karnede; kapatılacak kayıt ölçümden önce deftere işlenir (karne SIRA KURALI) | **Kısmen araçla**: üslup Y03 haftalık sayıda karne dışındaki her geçmiş çağrı atfını ("yazmıştık", "(27.09 notu)") UYARI'yla sayar; okumadaki sayım paragrafı ölçülmüyor |

**Silip yeniden kurmak da çözüm değil.** 27.08.2026'da denendi: aracının
kurduğu bir rutin ateşlendiğinde depoya erişemiyor (sınama koşusu 24 saniyede,
tek bir dosyaya dokunamadan bitti). Mevcut rutinlerin taşıdığı kaynak depo
bağlantısının `create_trigger`'da karşılığı yok. Yani düzeltme yalnız
claude.ai arayüzünden yapılabilir.

Üçüncü satır hâlâ DAYATILAMIYOR: rutinin bu aracı koşturmasını sağlayacak bir
karşılık yok. Zincire bakmayan bir koşu, eksik halkayı fark etmeden yazmaya
kalkışır; o durumda da ilk satırdaki kapı devreye girer ve sakat ölçü
yazılmaz. Yani en kötü hâlde bülten çıkmaz — yanlış bülten çıkmaz.

Ama satırın maliyeti artık GÖRÜNÜYOR ve bu bilerek araca bağlandı: gecikme
kaydı `yaz.py`nin yan etkisidir (bülteni yazmanın başka yolu yok, hiçbir
bayrak gerekmiyor), alarmı taşıyan iş akışı zincir raporuna hiç bakmıyor ve
uyandırıcısı bir cron değil. Yani rutin bu rehberin tek satırını okumasa bile
gecikme ölçülür, kaydedilir ve haber verilir. Rehbere yazılmış bir kural,
"rutin metnine yazıldı" kadar zayıftır; bu bölümün varlık sebebi de zaten o.

**Rutini bir aracı yeniden kuramaz.** Mevcut iki rutin (hafta içi 04:15 UTC,
pazar 14:45 UTC) hesabın kendisi tarafından oluşturuldu; aracının onları
güncelleme ya da silme yetkisi yok. 05.10.2026'da yeniden denendi ve ret
gerekçesi adıyla geldi: rutin "aracı tarafından değil, hesap tarafından
kuruldu; aracı yalnız kendi kurduğu rutini güncelleyebilir". Metni OKUMAK ise
mümkün (`get_trigger`): bir oturum rutinin bugünkü metnini bu tabloyla
kıyaslayıp sapmayı bildirebilir. Aracının kurduğu bir rutin depoya erişemez:
yeni oturuma depo bağlanmadığı için özel depo klonlanamaz. Yani rutin metnini
değiştirmenin tek yolu **claude.ai arayüzü** (Routines sayfası, rutinin kendi
düzenleme ekranı); oradan değiştirilecek bir şey yoksa yeni kural buraya
yazılır ve rutin onu okuyarak öğrenir.

## Tekrar — iki eksen

Bültenin tekrarı iki ayrı yerde ölçülür ve ikisi ayrı kusurdur. Tekrar çoğu
zaman birebir cümlede değil OLGUDADIR: aynı rakamın başka sözcüklerle yeniden
sayılması. Denetim (biçim 3) bunu olgu düzeyinde ölçer: aynı ondalık üç
bölümde, madde ile okumanın ikiden fazla ortak rakamı, bugün ve önceki iki
sayının üçünde de yazılmış değerler ("kronik olgu") ve dünkü okumayla aynı
açılış cümlesi — hepsi UYARI, adıyla listelenir.

**Sayı içi.** Aynı olgu birden çok bölümde yeniden ANLATILMAZ. Bir olgu kendi
evinde (bkz. "her konunun tek evi") bir kez tam anlatılır; ikinci geçişinde ya
üzerine yeni bir işlem yapılır (aynı faiz taşıma hesabına girer) ya da tek
cümleyle anılıp geçilir.

**Günler arası.** *Bir sayı, önceki sayıyı özetlemez.* Okur dünkü bülteni
okudu; bugünkü sayı DEĞİŞENİ anlatır. Ölçüldü (07.09.2026, 13 sayı): senin
yazdığın düzyazı bu sınavı zaten geçiyor — gündem %0,6, yorum %0,3 birebir
örtüşüyor. Tökezlediğimiz iki yer şunlar oldu:

- **Söz defteri** ardışık iki sayı arasında %91,4 örtüşüyordu, çünkü 4.816
  sözcüklük bölüm her sabah yeniden basılıyordu. Artık ölçüm katmanı kaydı
  `degisti`/`duran` diye işaretliyor ve sayfa yalnız DEĞİŞENİ tam metinle
  basıyor. Sana düşen: bir kaydın metnini ancak gerçekten değiştiyse güncelle.
  Aynı sözü yeni sözcüklerle yeniden yazmak, kaydı "değişti" diye işaretler ve
  tekrarı geri getirir.
- **Özet** 24–25.08'de önceki sayıdan %97–100 aynen kopyalanmıştı. Özet, o
  günün özetidir; dünkü özetin üzerine tarih atmak değil.

Kapı `bulten/denetim.py`de ve ENGEL DEĞİL UYARI: sakin bir haftada iki sayının
benzemesi meşrudur, vadesi gelen bir söz yeniden anılmalıdır. Uyarı hangi
bölümün sürüklediğini adıyla söyler — hedef, sayfa düzyazısının %30'unun
altında.

## Kurallar

**Atıf disiplini.** Sayının penceresinde (günlükte günün, haftalıkta haftanın)
en büyük üç hareketi `%1,5`'i aşıyorsa ve 2σ'yı aşan her hareket metinde BİR
KEZ anılır ve sebebi yazılır — bir madde de sayılır, aynı hareketi ikinci bir
bölümde yeniden anlatma. Biçim 3'te yüzdesi büyük ama kendi oynaklığına göre
sıradan (|σ| < 1) hareket anılmak zorunda değildir (kural 6: 1σ altı
düzyazıya girmez). Sebebi bilinmiyorsa bir kez "sebebi netleşmedi" yaz —
en görünür manşeti sürücü diye göstermek en kötü seçenek. (2026-08-17 haftasında ABD Hazinesi'nin
tahvil geri alımı USD ve faizlerdeki asıl sürücüydü ve bülten bunu tamamen
atlamıştı; `onem_puani` ve ABD Hazine kaynağı bu yüzden eklendi.)

**Metin kendi ayakları üstünde dursun.** Yazdığın `yorum` ve `gundem`
bölümleri yalnız sitede okunmuyor: aynı metin X'e tek gönderi olarak da çıkıyor
ve orada ne sayfa, ne tablo, ne de başka bir bölüm var. Biçim 3'te gönderi
başlığın altında `manset` ile, sonra `ozet.ne_oldu` maddeleriyle açılır (madde
başına ~330 karakter), okuma ondan sonra ve kısaltılmış gelir; "öne çıkanlar"
satırı maddelerin saydığı hareketi yinelemez. Maddeler gönderinin gövdesidir:
olgu ve rakam oradadır, okuma onları yeniden saymaz. Gönderi
`tweet/denetim.py` kapısından geçer (tavsiye dili, link — tweetlerde HİÇ link
kullanılmaz, çıplak alan adı dahil —, HTML kalıntısı, site
atfı, sayı ortasında kesik cümle, sorumluluk notu); kapı düşerse gönderim
durur ve o sabah X'te hiçbir şey çıkmaz — yani metnin tweete uygunluğu senin
sorumluluğun. Gönderiyi önceden görmek için: `python3 tweet/gonder.py --kuru`. Bu yüzden sayfa
mobilyasına atıf yapma — "bu sayfadaki piyasa fotoğrafında", "yukarıdaki pano",
"ayrıntısı jeopolitik bölümünde", "bu bültenin takip ettiği" gibi ifadeler
kullanma. Söylemek istediğin şeyi kendi cümlesi içinde tamamla: "jeopolitik
bölümünde" yerine gelişmeyi orada bir cümleyle söyle; "fotoğraftaki satır"
yerine varlığın adını ve hareketini yaz. İşlem fikirleri gönderiye hiç girmez;
düzyazı onlara atıf yapmaz ("aşağıdaki fikir", "işlem fikri olarak") ve
seviyelerini yinelemez — gönderiye giden bir cümle, okurun göremeyeceği bir
fikri anmış olurdu.

Sigorta araçta: `tweet/uret.py` bu izleri taşıyan CÜMLEYİ düşürür (ve
göndergesi silindiği için öksüz kalan devamını da). Yani kural çiğnendiğinde
tweet bozulmaz — ama SENİN cümlen kaybolur ve okur onu X'te hiç görmez.
Metni baştan bağlamsız yazmak, cümleni kurtarmanın tek yolu.

**Kod dili yasak.** Okuyucuya hiçbir şey söylemeyen geliştirici dili sayfaya
girmez: dosya adı, alan adı, "eşikler ayar.py içinde", "itp_b_sabit" gibi.
Denetim bunu ölçer ve engeller (`ortak/okur_dili.py`, tek tanım). "Koşu" ve
"veri tarihi" okura verilen kayıt adlarıdır, yasak değildir.

**Vurgu büyük harfle yapılmaz.** "Eğriyi YATAYLAŞTIRIR", "FİNANSMAN kararıdır"
gibi yazımlar kurumsal bir notta bağırma gibi okunur ve aynı sayfadaki
`<strong>` vurgusuyla tutarsızdır. Vurgu gerekiyorsa `<strong>`, paragraf başına
en çok bir kez. Kısaltmalar (TCMB, TÜFE, BIST) elbette büyük harfle kalır.
Denetim büyük harfli Türkçe sözcüğü UYARI olarak listeler (`buyuk_harf`).

**Aynı sayıyı iki bölümde anlatma.** "Ne oldu" günün hareketlerini sayısıyla
kısaca verir; "Günün okuması" o sayıları tekrar sıralamaz, aralarındaki
ilişkiyi kurar. Aynı rakam iki bölümde geçiyorsa birinde kalır — okur ikincisinde
yeni bir şey öğrenmiyor.

**Tavsiye dili yasak.** "Alın", "satın", "hedef fiyat", "pozisyon açın",
"öneriyoruz" hiçbir alanda yazılmaz — işlem fikirleri dahil (denetim fikrin metin
alanlarını da aynı ortak kalıpla tarar ve ENGEL sayar). Site analiz yayımlar,
yatırım tavsiyesi vermez. İşlem fikri bu ilkenin istisnası değil, onun içinde
durur: bir okumanın kişiye özel olmayan bir işlem YAPISINA çevrilmiş hâlidir ve
yalnız `fikirler` alanında, betimleyici dille (bacak, yön, seviye) yazılır.
Düzyazıda yapı dili de yok: "eğri dikleşir" bir okumadır, "dikleştirici
kurulur" bir yapıdır ve fikirde durur. Uyarı ve sorumluluk cümlesini yazar
yazmaz; sayfanın fikir bölümü kendi uyarı metnini taşır.

**Rejim panosunu omurga yap.** `rejim` alanı günün "neredeyiz" cevabını dokuz
satırda verir (reel faiz ileri/geri, taşıma makası, reel kredi, REDK sapması,
eğri eğimi, **enflasyon risk primi**, **makroihtiyati ayrışma**, rezerv
kalitesi). Yorumun tezi bu satırların GERİLİMİNDEN kurulur: hangi ikisi
birbiriyle çelişiyor, hangisi önce kırılır. Panoyu sayı sayı kopyalama — sayfada
zaten duruyor; senin işin çelişkiyi cümleye çevirmek.

Panonun iki yeni satırı, geri kalanının SORAMADIĞI soruyu soruyor:

- **Enflasyon risk primi (2y)** — diğer satırlar politikanın ne kadar SIKI
  olduğunu ölçer; bu satır piyasanın o sıkılığın SONUCUNA inanıp inanmadığını.
  İkisi aynı anda birbirine zıt olabilir ve bültenin en verimli gerilimi orada:
  reel faiz tarihî yüksekliğinde dururken piyasa hedefin tutmayacağını
  fiyatlıyorsa, sıkılık henüz beklentiyi çevirmemiş demektir.
- **Makroihtiyati ayrışma** — "reel kredi büyümesi" toplamın ne yaptığını
  söyler; bu satır sınırın İÇİNDE kalanla DIŞINA taşan arasındaki farkı. Fark
  açıldıkça toplamdaki yavaşlama politikadan değil bileşim kaymasından geliyor
  olabilir; freni toplam kredi büyümesinden okumak yanıltır.

**Söz kapatırken not düş.** Bir izleme kaydını kapatıyorsan `isabet` alanını
doldur (tuttu | tutmadi | kismen) ve `kapanis` alanına kapattığın günü yaz
(`YYYY-AA-GG`); ölçülemeyen kayıtlar notsuz kapanabilir ama bunu bilinçli seç.
Kapanış günü yazılmazsa sayfa "bugün kapandı"yı önceki sayıdan türetir. `sonuclar` bölümünde "geldi" görünen her satırın sürprizini
metinde yorumla — tablo ne olduğunu söyler, neden olduğunu sen söylersin.

**FX haber endeksi bültenden ÖNCE tazelenir — bak.** Hat hafta içi her sabah
04:53'te koşuyor, yani ölçümden 90 dakika önce. Sepet spread'i 01.10.2026'dan
beri gösterge şeridinde YOK (birimsiz ve ölçeksiz bir sayıydı); haber tonunun
2σ'yı aşan hareketleri sayfanın olağandışı bölümünde cümleyle basılır. Günün
tonunda anlatmaya değer bir şey olup olmadığını görmek için proje sayfasına
bak: hangi varlık uçta, kaç makaleyle, bir önceki okumaya göre ne kadar döndü.

**Haber tonunda 2σ'yı aşan hareket ANILMAK ZORUNDA.** Ölçüm katmanı FX haber
endeksinin günün en büyük üç hareketini sıralayıp sayfada basar; denetim
(biçim 3) yalnız |z| ≥ 2 olanları metinde ARAR ve bulamazsa ENGEL üretir.
2σ'nın altındaki ton oynaması yazılmaz — sayfa onu zaten gösteriyor, 1σ'lık
bir oynamayı her sabah düzyazıya taşımak dolgudur. 2σ'yı aşanın sebebini
haber akışından bul; netleşmiyorsa bir kez "sebebi netleşmedi" yaz.

Üç şeye dikkat: (1) **Kıyas penceresi sabit değil.** Hat günlük koşmaya yeni
geçti; tarihçedeki eski aralıklar haftalarca. Olay cümlesi kaç günlük dönüş
olduğunu yazar, sen de metinde yaz — "endeks döndü" demek, ne kadar sürede
döndüğünü söylemeden yanıltır. (2) **Sıralama eşikle yapılmıyor.** Sabit eşik
denendi ve ölçüldü: snapshot'tan snapshot'a 15 varlığın 9-12'si kategori
değiştiriyor, yani eşik her gün on sahte olay üretirdi. Listede olmak "büyük
hareket" demek değil, "bugünün en büyüğü" demektir. (3) **σ henüz yok.** Hattın
oynaklık tarihçesi standart sapma için yetene kadar sıralama ham büyüklüğe göre
yapılır ve olay cümlesi bunu söyler; o hâlde "olağandışı" değil "en büyük" diye
yaz.

**Temalara bağla — sınandıysa.** Günün gelişmesi `temalar` defterindeki canlı
bir tezi doğruladı ya da zayıflattıysa bunu bir cümleyle söyle; tema her gün
anılmak zorunda değildir.

**Kıyas noktası.** Her sayının yanında neye göre değiştiği yazar: bir gün mü,
bir hafta mı, yıl başından beri mi.

**Tekrar.** Bin kelimede en fazla 7 ağır tekrar. Aynı cümleyi bölümden bölüme
taşıma.

**Denetimin veri uyarılarını ciddiye al.** Denetim artık ölçüm katmanının
CANLILIĞINI de ölçüyor: veri iş akışı her koşuda nabzını atıyor ve denetim o
damganın yaşına bakıyor. İki uyarı doğrudan sana:

- *"Veri iş akışı N saattir koşmadı"* — ölçüm katmanı bayat olabilir. Yazmadan
  önce hatların veri tarihlerini (pano ve "dünden bu yana gelen veriler") gözden geçir;
  bayat bir hattın sayısını günün haberi gibi anlatma.
- *"Son veri koşusunun tazeleme adımı 'failure' ile bitti"* — bazı hatlar
  çekilememiş. Hangilerinin eski kaldığını veri tarihlerinden bul ve metinde
  o hatlara dayanan hüküm kurma.
- *"Bugün tazelenmesi gereken ama tazelenemeyen hatlar: …"* — bu hatların
  sayısı dünkü sürümde. Günün haberini onların üstüne kurma; kullanacaksan
  kendi tarihiyle kullan ("kredi büyümesi 18 Eylül haftasında %20,1").
  Koşunun geciktiği, hangi iş akışının düştüğü ya da bir serinin "donduğu"
  okuru ilgilendirmez ve okur diline girmez: bayat bir değeri ya kendi
  tarihiyle kullan ya hiç kullanma.

Üçüncü uyarı seri düzeyinde:

- *"Hattın saati ilerlerken donmuş N seri"* — bir hattın ana tarihi her gün
  ilerlerken İÇİNDEKİ bir seri donmuş. Sayfada o değer hattın güncel tarihiyle
  aynı başlığın altında duruyor ama ait olduğu gün çok daha eski. Böyle bir
  sayıyı metne alacaksan **kendi tarihiyle** al ("12 Haziran'dan bu yana
  fiyatlanmayan üç yıllık nokta"), günün kesiti gibi değil.

  Bu uyarı yalnız SEBEBİ BİLİNMEYEN seriler için çıkar. Bir seriyi araştırıp
  sebebini bulduğunda ilgili proje sayfasına yaz ve `ayar.KARANLIK_BILINEN`e
  ekle; denetim onu bundan sonra sebebiyle birlikte geçen ölçüt olarak yazar.
  Susturmanın tek yolu önce anlamaktır — açıklaması olmayan hiçbir donuk seri
  listeden düşmez.

**Her satırın kendi bar tarihine bak.** Piyasa fotoğrafındaki her satır hangi
GÜNÜN kapanışını taşıdığını yazar. Bugünün tarihini taşıyan bir satır, ancak o
piyasa kapandıysa kullanılabilir; kapanmadıysa o satırın "günlük değişim"i dünkü
seansı değil geceliği ölçer ve işareti dünküyle ters olabilir. Denetim bunu artık
ENGEL sayıyor (`kapanmamış seansın barı`), ama engelin çıkmaması satırların hepsi
aynı güne aittir demek değildir: bülten 26 Ağustos kapanışlarıyla 27 Ağustos'ta
kapanmış bir Asya seansını aynı sayfada taşıyabilir. Sayfa her satırın tarihini
ve karma seansı kendisi basar; sen yalnız TEZİN dayandığı satırı doğru güne
yaz ("Bitcoin pazartesi kapanışında %2 düştü"). Tesisatı anlatma: "satır X
kapanışını taşıyor", "kaynak barı boş verdi" türü cümleler yazılmaz (üslup
ölçütü ENGEL).

Geride kalan bir satırın SEBEBİNİ tahmin etme; ölçüm katmanı yazıyor
(`piyasa.seans_ozeti`, 23.09.2026'dan beri). `kaynak_bos`: kaynak o tamamlanmış
seansı boş verdi ve kurulamadı — satırın "1 gün"ü o seansa ait değildir, hareketi
o güne yazma. `son_islemden`: kaynağın günlük barı boştu, kapanış kaynağın aynı
günkü son işlem fiyatından kuruldu — sayı o günün kapanışıdır, kullanılabilir.
`kaynak_bos`da bir satır "satırın son aralığının içinde kalan" boş gün de
taşıyabilir: satır bugüne kurulmuş ama aradaki bir seans kaynakta boştu, yani
"1 gün" değişimi İKİ seansı kapsıyor — tek günlük hareket diye yazma.
Geride kalmış bir satır ancak HİÇBİR listede yoksa tatil sayılabilir; önce
`seans_sinanamadi`ye bak: oradaysa o sembol bu koşuda SINANMADI (meta alınamadı,
çekimden dönmedi ya da anlık görüntü bu denetimden önce yazıldı) ve sebebi
bilinmiyor — sebep YAZMA; varlığın gününü cümlenin kendisinde ver ("Nikkei
29 Eylül'de …"), "satırı … kapanışını taşıyor" diye değil (üslup ENGEL). TLREF
satırı kendi gününü taşır ve o güne BAK, varsayma: Borsa İstanbul T'yi aynı gün
13:00 UTC'de yayımlar ve fonlama hattı onu günlük dosyadan alır, EVDS ertesi
sabah; hat o gün BIST'e ulaşamadıysa (ya da EVDS donduysa) satır bir seans
geride kalır ve hattın uyarısı sebebini söyler.

**Bir düzeltme yaptıysan GENELLEŞTİR.** Bu, 27.08.2026'nın asıl dersi. O sabahki
metin enerjide bir ölçü hatası fark etti, doğru teşhis etti ve düzgün bir geri
alma yazdı — sonra aynı paragrafın devamında, aynı hatayı taşıyan metal
rakamlarını düzeltmeden yayımladı. Aradaki tek fark, enerjide korumanın var
olması ve hatanın bir gün önce göze çarpmış olmasıydı. Bir ölçü kusuru
bulduğunda soru "bu seriyi düzelttim mi" değil, **"bu kusur başka nerede
olabilir"** olmalı: aynı kaynaktan gelen, aynı yoldan geçen bütün satırları
gözden geçir.

**Haber başlığı ölçüyü DOĞRULAMAZ.** Aynı sabah, yanlış ölçüyü destekleyen bir
başlık bulundu ("Gold Rises…") ve teyit sayıldı; oysa o başlık iki gün önceki
harekete aitti. Bir başlığın hangi güne ait olduğunu kontrol etmeden ölçüyle
eşleştirme. Ölçü ile haber çelişiyorsa varsayılan, ÖLÇÜYÜ sorgulamaktır — haberi
ölçüye uydurmak değil.

**"YAYIMLANAN SAYI DEĞİŞTİ" uyarısı ciddidir.** Denetim, aynı SERİNİN aynı güne
ait değerini önceki üç bültende yayımladığımızla karşılaştırır — piyasa
satırlarının günlük değişimi, TL faiz seti, gösterge şeridi, türev büyüklükler
(bacak bar günleri aynıysa) ve rejim panosu (girdi günleri aynıysa). Temiz
geçtiğinde seri başına kaç çift kıyaslandığını da yazar: "türev 0/9" kıyas
yapılmadığı, "temiz" olmadığı anlamına gelir.
Listelenen her sayı için ya sebebi bul (meşru revizyon) ya da metinde
"yayımlanan X yerine gerçek hareket Y" kalıbıyla geri al **ve aynı düzeltmeyi
`duzeltmeler` alanına yapısal kayıt olarak yaz** (yukarıda). Metinde kalıp var
ama kayıt yoksa denetim uyarı düşer. Listenin uzun olması tek bir ölçüm
kusuruna işaret eder; tek tek değil, KAYNAĞINI ara.

**Bir ölçüyü kendi içinde ÇAPRAZLA.** 31.08.2026'da denetimin "yayımlanan sayı değişti"
uyarısı on iki satır listeledi ve liste tek bir sebebe çıkmadı — İKİ ayrı kusur vardı,
ikisi de ancak ölçünün kendi içindeki tutarlılığa bakılarak ayrıldı:

- **Dolar endeksi çaprazları tutuyor mu?** Endeks (DX-Y.NYB) ile `=X` çaprazları AYNI
  günü ölçer; endeksin günlük değişimi kabaca ağırlıklı çapraz değişimlerine eşit
  olmalıdır (EUR %57,6 · JPY %13,6 · GBP %11,9 · CAD %9,1 · SEK %4,2 · CHF %3,6; euro ve
  sterlin ters işaretle). O sabah endeks %0,54 yükselmişken çaprazların ima ettiği hareket
  ≈ %0,00'dı; pazar günkü ölçüde ise ≈ %0,44 ile tutarlıydı. Yani BUGÜNKÜ çapraz okumaları
  açık seansın etkisini taşıyordu. Dolar tarafı çaprazlarla değil endeksin kendisiyle
  anlatıldı; gerekçe düzyazıya değil sayfanın dipnotuna aittir.
- **Günlük ve haftalık kayma AYNI büyüklükte mi?** Bir satırda `d1` ile `h1` aynı miktarda
  kaydıysa değişen şey kıyas barı değil SON FİYATTIR. Metallerde ikisi de birebir aynı
  kaydı (altın −1,12 puan, gümüş −1,14, bakır −1,48); yani pazar günkü kapanış eksikti,
  bugünkü tam. Orada geri alma kalıbı kullanıldı.

Kural: liste uzunsa önce "hangi satırlar aynı aileden" diye bak, sonra o ailenin İÇ
tutarlılığını sına. Tek sebep aramak, iki kusuru birbirine karıştırmaya yol açar.

**"Vadeli devir düzeltmesi kurulamadı" uyarısı seviyeleri iptal eder.** O
satırlarda gösterilen fiyat ham kontrat kapanışıdır; önceki yayımla
kıyaslanamaz ve seviyeden türeyen rafineri marjları üzerinden yorum kurulamaz.
Günlük yüzde değişimler etkilenmez — onları kullan, seviyeyi kullanma.

Bu uyarılar engel değildir — bayat veriyle de bülten yazılır, yeter ki bayatlık
BİLİNEREK yazılsın. 26.08'de veri hattı düştü ve aşağı akıştaki hiçbir katman
bunu bilemiyordu; bu ölçütler o boşluğu kapatıyor.

**Beklenti halkası kapanıyor.** Bülten artık vakti geçmiş takvim olayları için
"ne bekleniyordu, ne geldi" bölümü basıyor. Üç kural:

- **Beklenti sütunu o gün yayımladığımız beklentidir.** `takvim_arsiv.json` her
  koşuda görülen takvim kaydının İLK hâlini saklar ve ezmez; sonradan
  güncellenmiş bir anketi geriye dönük yazmak, kendi çağrımızı düzeltmek olur.
- **Sürpriz yalnız sayısal beklenti varsa hesaplanır.** Serbest metin beklenti
  ("anket: yıl sonu %29,43 · 12 ay sonrası %23,69") sayıya ÇEVRİLMEZ; ayrıştırma
  tahmin üretir, tahminden hesaplanan sürpriz uydurma olur. Sayısal beklentin
  varsa takvim kaydının `beklenti_sayi` alanına yaz.
- **Gerçekleşme hattın kendi saatinden okunur.** Yayım anı ile verinin hatta
  düşmesi arasında saatler geçer; alanın veri tarihi olay gününden eskiyse bölüm
  "veri henüz hatta düşmedi" der. Elimizdeki eski sayıyı yeni yayım diye sunmak
  bu bölümün var oluş sebebine aykırıdır.

Bölüm otomatik dolar; yazan tarafın işi GELEN bir yayının sürprizini metinde
yorumlamaktır — tablo ne olduğunu söyler, neden olduğunu söylemez. Beklentinin
OLMADIĞINI ya da sürprizin ölçülemeyeceğini metinde anlatma; tablo "—" basar.

**Söz defteri artık okura açık.** `izleme.json` bültenin JSON'una giriyor ve
sayfada "Söz defteri" bölümü olarak basılıyor: açık sözler vadeleriyle, yakın
zamanda kapananlar sonuçlarıyla. İki sonucu var. Birincisi, bir kaydın `soz` ve
`ne_bakilacak` alanları artık iç not değil **yayımlanan metindir** — okurun tek
başına anlayacağı şekilde yazılır — ve **kısa** (biçim 3: `soz` en çok 80
kelime; tez, teyit ölçüsü, vade; olgular yazıda kalır, denetim uzun kaydı
uyarır). İkincisi, bir kaydı kapatırken `isabet`
alanı doldurulur:

| değer | ne zaman |
|---|---|
| `tuttu` | söz verilen beklenti gerçekleşti |
| `tutmadi` | gerçekleşmedi |
| `kismen` | yönü tuttu, büyüklüğü ya da zamanlaması tutmadı |

Alan boş bırakılırsa sayfa isabet oranını **vermez** — eksik veriyle övünmek
hesap vermenin tersidir. Ölçülemeyen kayıtlar (bir sorunun cevabının bulunması
gibi) notsuz kapatılabilir; denetim bunu uyarı olarak sayar, engel olarak değil.

**Defteri düzeltmek SAYFAYI düzeltmez.** Tema bölümü bültene ÖLÇÜM anında
işlenir; yazı katmanı `temalar.json`'u ondan sonra günceller. Yani defteri
düzeltip yazmak, sayfada eski metni bırakır. Bu iki kez yayına çıktı: 28.08.2026'da
sayfa bir gün önce geri alınmış rakamları yeniden bastı, 30.08.2026'da haftaya
bakış "çürütücü ölçüt bugün sınanacak — Warsh'ın Jackson Hole konuşması" dedi ve
konuşma iki gün önce yapılmıştı. Doğru sıra: **önce defteri güncelle, sonra
ölçümü `--yeniden-olc` ile yeniden kur, sonra yaz.** Denetim artık sayfadaki
görüntü ile defteri karşılaştırıyor ve ayrışıyorlarsa ENGEL üretiyor.

**Bir ölçünün BOŞ görünmesi, ölçülen şeyin OLMAMASI demek değildir.** Bu,
30.08.2026'nın dersi ve pahalıya mal oldu: bülten üç hafta boyunca "gevşemenin
resmî ölçüsü yok, ağırlıklı ortalama fonlama maliyeti donuk" yazdı. TCMB o seriyi
her gün yayımlıyordu ve 24 Ağustos'ta 40,00'dan 37,00'ye indirmişti; değeri
eleyen kendi geçerlilik kapımızdı (fonlama tabanı 5 mlr TL eşiğinin altında).
Panoda bir satır "güncel değil" diyorsa **sebebini oku** — satır artık sebebi
kendi üstünde taşıyor. Sebebi okumadan "ölçü yok" yazmak, okura yanlış bilgi
vermektir. Fazla likidite rejiminde TCMB parasının marjinal fiyatını fonlama
değil sterilizasyon belirler; faiz setindeki "Marjinal TCMB faizi" satırı o
rejimde hangi ölçünün geçerli olduğunu söyler.

**Sayıları uydurma.** Bültendeki her sayı ölçülen katmandan gelir. Ölçülmemiş
bir sayıya ihtiyaç varsa kaynağına in; hatırlayarak yazma.

Bu kural artık **ölçülüyor**. Denetim, ölçülen bir büyüklüğün adına yapışık her
sayıyı ölçülen katmanın tamamına karşı sınar ve karşılığı olmayanları listeler.
İşaret sözcükte taşınabilir ("%3,76 düşüşle" ile ölçülen −3,76 aynıdır),
yuvarlama serbesttir ("%36,9" ile 36,94 aynıdır), tarih ve süreler ("24
Ağustos", "52 haftalık") kapsam dışıdır. Liste **uyarıdır, engel değil**:
haberden gelen meşru bir sayının (bir eşik, bir tarife tutarı, ölçmediğimiz bir
alt endeks) ölçülen katmanda bulunmaması normaldir. Beklenen davranış listeye
bakıp her maddenin kaynağını doğrulamaktır — kalabalıksa büyük ihtimalle bir
şey ezberden yazılmıştır.

Bir istisna var ve onu bilerek kullanabilirsin: **geri alınan sayı**. Önceki
bir yayımın yanlış sayısını düzeltiyorsan "yayımlanan −%11,36 yerine gerçek
hareket −%1,74" biçiminde yaz — denetim `<yanlış> yerine <doğru>` kalıbını
tanıyor ve düzeltmenin doğrusu ölçülen katmanda bulunduğu sürece yanlış sayıyı
uyarıya çevirmiyor. Kalıbın dışına çıkarsan (araya cümle sınırı girerse ya da
düzeltilen değer de ölçülmemişse) uyarı geri gelir; bu kasıtlı.
