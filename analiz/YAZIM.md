# Analiz yazım rehberi

Bu dosya, `site/src/content/analiz/` altına giren **analiz yazılarının** görev
tarifidir — bültenin `bulten/YAZIM.md`si neyse analizin bu. Analiz, tek bir
piyasa gelişmesini mekanizmasına, tarihsel emsaline ve fiyat etkisine kadar
açan uzun yazıdır; bültenden farkı kapsam değil **derinlik**tir.

Rehber esastır; kural buraya yazılır ve araca konur. Buradaki her zorunluluk
`site/tools/analiz_sinavi.py` tarafından ölçülür ve sayfa sınavı düşer.
Rehberde olup araçta olmayan kural yoktur; araçta olup burada yazmayan da.

Hedef kitle profesyonel trader. Jargon açıklanır ama seviye düşürülmez.

---

## Dosya ve başlık

**Slug tarih taşır: `<konu>-<YYYY-AA-GG>.mdx`.** Aynı konu tekrar tekrar
analiz edilir — her çeyrek bir büyüme verisi, her ay bir enflasyon, her ihale
bir söküm — ve tarihsiz slug ikinci yazıda çakışır. Tarih `pubDate` ile aynı
gündür. Site, aynı konunun yazılarını slug'ın tarihsiz kökünden **seri**
olarak tanır ve sayfada "bu serinin diğer yazıları" kutusunu kendisi kurar;
konu kökü bu yüzden yazıdan yazıya **aynı** yazılmalıdır (`buyume`,
`ito-tufe-esleme`, `borclanma-programi-vade`).

**Başlık tarih taşır: `<GG Ay YYYY> <Konu> — <alt başlık>`.** Ör.
`31 Ağustos 2026 Büyüme Verisi — GSYH kırılımları, enflasyon ve faiz alanı`.
Tarih `pubDate`in Türkçe yazımıdır; kart ayrıca tarihi kendisi basar, yani
tarih iki yerde görünür ve listede hangi yazının hangi güne ait olduğu okunur.

## Ön bilgi (frontmatter)

| alan | zorunlu | ne yazılır |
|---|---|---|
| `title` | evet | yukarıdaki kalıp |
| `description` | evet | 2–6 cümlelik özet; bağlantı önizlemesinde (ilk 200 karakter) ve RSS'te görünür — **sayı taşısın**, ilk cümle tek başına anlaşılsın |
| `pubDate` | evet | yayın günü; slug ve başlıkla aynı |
| `updatedDate` | değişince | metin sonradan güncellenirse |
| `tags` | evet | **küçük harf**, konu etiketleri (ilk etiket RSS kategorisi olur; büyük harfli etiket sınavı düşürür) |
| `durum` | evet | `aktif`; taslak yayımlanmaz |
| `kaynak` | evet | veri kaynakları okur adıyla ("TCMB EVDS", "TÜİK TÜFE") — künye satırında görünür; seri kodları gövdedeki Kaynakça'ya, kod biçiminde |
| `veriTarihi` | evet | yazının dayandığı verinin son günü, `YYYY-AA-GG` — künyede "Veri" olarak ve bağlantı önizlemesinde görünür; yazının tarihi ile verinin tarihi ayrı şeylerdir |
| `duzeltmeler` | düzeltme varsa | yayımlanmış bir sayının düzeltme kaydı: `tarih`, `alan`, `eski`, `yeni`, `sebep` — sayfanın sonunda kutu olur, `/duzeltmeler/` sayfası toplar (bkz. "Yayımlanmış bir sayıyı düzeltmek") |
| `guncelleme` | veri canlıysa | serinin yayım ritmi ("aylık; TÜİK ayın 3'ü") |
| `ozet` | evet | TEK cümle: yazının tezi — kartta lede olur, X gönderisinin yedeğidir; iki cümleyi aşarsa uyarı |
| `seviye` | evet | `giris` · `orta` · `ileri` |
| `onkosul` | varsa | önce okunması gereken analizlerin slug listesi |

## Gövde iskeleti

1. **Yönetici özeti** — 20 KB'ı aşan her yazı `<div class="yonetici">` ile
   açılır (bkz. şablon). İçinde üç parça vardır ve üçü de zorunludur:
   `p.tez` (tek paragraf tez), soru–cevap tablosu (gelir mi · ne zaman · ne
   kadar · faize etkisi · kanıtın gücü gibi 5–9 satır) ve `ul.rakamlar`
   (5–8 anahtar ölçüm). Rakam şeridinin her öğesi **aynı sözleşmeyle**
   yazılır: `<li><b>değer</b><span>etiket</span></li>` — X gönderisi ve
   bağlantı kartı bu ikiliyi okur; kalın değer ya da etiket eksikse sınav
   düşer. Özetteki her sayı `<Deger>` ile bağlanır: özet
   donarsa yazının geri kalanı tazelenirken okur yanlış sonucu okur. Özet,
   gövdedeki bir kutuyu tekrarlamaz; onu soğurur. **Tweet bu bloktan
   kurulur** — tez, tablo satırları ve rakamlar X'e olduğu gibi çıkar; bu
   yüzden özet kendi ayakları üstünde durmalı, "yukarıdaki grafik", "bu
   yazının 4. bölümü" gibi sayfa mobilyasına atıf içermemelidir.
2. **Giriş** — sorunun ne olduğu, neden şimdi.
3. **Bölümler** — `## ` başlıklarıyla; numaralı (`## Bölüm 3 — …` ya da
   `## 3. …`) ya da düz. Her bölüm önce mekanizma, sonra ölçüm. Her grafiğin
   hesabı anlatılır (kaynak, formül, dönüşüm, varsayım).
4. **`## Ne ölçmedik`** — zorunlu kapanış bölümü, adı **tek** ve tam bu
   (eski yazılardaki "bu yazının sınırları" / "bilinmeyenler" adları rehber
   sonrası yazılarda uyarı düşürür; okur her yazıda aynı başlığı arar).
   Ölçülmemiş bir şeyi ölçülmüş gibi göstermektense boş bırakılır, sebebi
   yazılır.
5. **İzleme listesi** — tarihli: hangi gün hangi veri neyi doğrular/çürütür.
   Zorunlu değil ama beklenen; yoksa sınav uyarı düşer.

İsteğe bağlı bloklar (şablonda yorumlu dururlar):

- `<div class="not gezinme">` — giriş paragrafından hemen önce, uzun yazıda
  "bu yazı nasıl okunur" kutusu (bölüm listesi; sayfa mobilyasına atıf
  yalnız burada serbesttir, çünkü tweet bu bloğu okumaz).
- `## Yöntem eki` — türetimler, alternatif tanımlar, sağlamlık sınamaları;
  ana anlatıyı kesmemesi gereken teknik ayrıntı. Kapanış bölümünden **önce**.
- `## Kaynakça` — veri serileri kod biçiminde (`TP.FG.IST1.23`), çalışmalar,
  yayım takvimi bağlantıları. En sonda, izleme listesinden sonra.

## Sayılar

- **Her oynak sayı `<Deger>` ile yazılır**: `<Deger proje="enflasyon"
  anahtar="br_b_merkez" ondalik={2}>1,48</Deger>`. Yedek metin derleme
  anındaki değerdir; sayfa açılınca hattın güncel dosyasından tazelenir.
  Tarihsel ve metodolojik sabitler (bir çalışmadan alıntı katsayı, bir bant
  tanımı) statik kalır ve gerekirse `{/* sinav-muaf: anahtar — gerekçe */}`
  ile işaretlenir.
- Türkçe yazım: ondalık virgül, binlik nokta, eksi işareti "−" (U+2212),
  yüzde işareti sayıdan önce ("%1,48"), baz puan sayıdan sonra ("−6,5 bp").
- Her sayının yanında **neye göre** ve **hangi tarihe ait** olduğu yazar.

## Dil

- **Okura yazılır, yapıma değil.** Dosya adı, anahtar adı, "hat koştu",
  "kodda düzeltildi", "ilk sürümde şöyleydi" sayfaya girmez
  (`ortak/okur_dili.py`; sayfa sınavı 9. ölçüt düşürür). Yapım kararları
  sohbette ve commit mesajında konuşulur.
- **Tavsiye dili yok.** "Alın", "satın", "hedef fiyat" yazılmaz; senaryo dili
  kullanılır. Yazı yatırım tavsiyesi değildir ve sayfa bunu söyler.
- **Uydurma yok.** Sürpriz yalnız sayısal beklenti varsa hesaplanır; kıyas
  eğrisi elde ne kadar tarihçe varsa o kadar geriye gider ve kendi tarihiyle
  etiketlenir.
- **Sınama örneklem dışı yapılır.** İkna edici bir tablo sınanmamış bir
  kuraldır; sıralama da bir sonuçtur ve hüküm metne değil koda yazılır.

## Yayımlanmış bir sayıyı düzeltmek

Okur eski sayıya göre karar vermiş olabilir; düzeltme **kalır**. Kayıt ön
bilgideki `duzeltmeler` listesine yazılır — bültenle aynı sözleşme:

```yaml
duzeltmeler:
  - tarih: '2026-09-03'
    alan: '2 yıllık başabaş'
    eski: '%29,4'
    yeni: '%28,9'
    sebep: 'kaynak seride revizyon; 3y bacağı yerine 2y bacağı okunmuştu'
```

Sayfa bunu sonda "Düzeltmeler" kutusu olarak basar, `/duzeltmeler/` sayfası
bütün yayınların kayıtlarını toplar. Metindeki sayı yeni değere çekilir,
`updatedDate` ilerletilir; sürüm tarihçesi anlatılmaz ("ilk sürümde şöyleydi"
yok — kayıt zaten söylüyor).

## Yayın akışı

1. Yazıyı şablondan kur: `analiz/sablon.mdx` → `site/src/content/analiz/<konu>-<tarih>.mdx`.
2. Grafikleri üreten hat varsa çıktıları `site/public/projeler/<slug>/` altına
   koyar ve `ozet.json`u yazar; yazı sayıları oradan `<Deger>` ile çeker.
3. Bağlantı kartı: `python3 site/tools/og_kart.py --analiz` — yalnız kartı
   olmayan analizler için 1200×630 görsel üretir (`site/public/og/analiz/
   <slug>.png`); X ve diğer önizleyiciler bu kartı gösterir. Kart yoksa bölüm
   kartı çıkar — yazı yayımlanır ama önizleme genel kalır.
4. Sınav: `python3 site/tools/sayfa_sinavi.py` (ya da `cd site && npm run
   sinav`) — analiz ölçütleri dahil, çıkış 0 olmalı. Tek yazıyı sınamak için
   `python3 site/tools/analiz_sinavi.py`.
5. Derleme: `cd site && npm run build` (ikisi birden: `npm run yayin-kontrol`)
   — yerelde, CI'ya güvenmeden.
6. Commit + push. Yayın iş akışı siteyi derler, sınavı koşturur ve public
   depoya çıkarır; sınav düşerse yayın durur.
7. **X gönderisi kendiliğinden çıkar:** tweet iş akışı, yayın günü `pubDate`
   bugüne eşit olan analizi yönetici özetinden kurar ve gönderir (defter aynı
   yazıyı ikinci kez göndermez; eski tarihli yazı gönderilmez). Metni önceden
   görmek için: `python3 tweet/gonder.py --tur analiz --kuru`.

## Dokunulmazlık

Yayımlanmış analizler ve dersler **değiştirilmez**; yalnız sayı düzeltmesi ve
`updatedDate` ile işaretlenmiş bilinçli güncellemeler yapılır. Bu rehberin
kuralları, rehberin yazıldığı günden (1 Eylül 2026) sonra yayımlanan yazılar
için bağlayıcıdır; daha eski yazılar biçim ölçütlerinden muaftır, dil ve
`<Deger>` ölçütleri her yazı için geçerlidir.
