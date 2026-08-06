# -*- coding: utf-8 -*-
"""
TÜİK MEDAS'tan (biruni.tuik.gov.tr/medas) Tüketici Madde Fiyatları (2003=100)
serilerini indirir. TCMB EN 24/17 replikasyonu için madde düzeyi veri hasadı.

Kullanım:  python3 src/medas_harvest.py [--stage zaman|full] [--topic tufe]
Çıktı:     data/raw/medas_madde_fiyatlari.xls (veya csv) + data/log/medas_harvest.log
"""
import sys, time, json, re, pathlib, datetime

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
LOG = ROOT / "output" / "log"
RAW.mkdir(parents=True, exist_ok=True)
LOG.mkdir(parents=True, exist_ok=True)

MEDAS_URL = "https://biruni.tuik.gov.tr/medas/?kn=84&locale=tr"

# Hedef maddeler (eski sepet, 2003=100): kod -> kısa ad
HEDEF = {
    # Yemek hizmetleri maddeleri (fiyat tarafı)
    "1110101": "Çorbalar", "1110102": "Hazır Yemekler", "1110103": "Kebaplar",
    "1110104": "Pideler", "1110105": "Köfteler (Çiğ köfte)", "1110106": "Ekmekarası (Döner)",
    "1110108": "Burgerler", "1110110": "Pizza",
    # Tahıllar
    "0111101": "Pirinç", "0111209": "Bulgur", "0111201": "Buğday Unu", "0111301": "Ekmek",
    # Et
    "0112201": "Dana Eti", "0112501": "Tavuk Eti", "0112701": "Sucuk", "0112703": "Salam",
    # Süt-yumurta
    "0114101": "Süt", "0114301": "Yoğurt", "0114401": "Beyaz Peynir", "0114402": "Kaşar Peyniri", "0114501": "Yumurta",
    # Yağlar
    "0115101": "Tereyağı", "0115302": "Ayçiçek Yağı", "0115301": "Zeytinyağı",
    # Sebze-meyve
    "0117122": "Domates", "0117117": "Sivri Biber", "0117146": "Kuru Soğan", "0117130": "Havuç",
    "0117152": "Marul", "0117201": "Patates", "0117153": "Maydanoz", "0116130": "Limon",
    # Bakliyat
    "0117401": "Kuru Fasulye", "0117403": "Mercimek",
    # İşlenmiş / çeşni
    "0117505": "Salça", "0117504": "Turşu", "0119001": "Baharat", "0119002": "Tuz",
    "0119008": "Ketçap", "0119009": "Mayonez",
}

logf = open(LOG / "medas_harvest.log", "a", encoding="utf-8")
def log(msg):
    line = f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}"
    print(line, flush=True)
    logf.write(line + "\n"); logf.flush()

JS_CLICK = """(el) => { for (const t of ['mousedown','mouseup','click'])
  el.dispatchEvent(new MouseEvent(t, {bubbles:true, cancelable:true, view:window, button:0})); }"""

def zk_click(page, locator_or_handle):
    """ZK bileşenlerine üçlü mouse olayı gönderir."""
    h = locator_or_handle if hasattr(locator_or_handle, "evaluate") else None
    if h is None:
        raise ValueError("handle bekleniyor")
    h.evaluate(JS_CLICK)

def find_cell(page, exact_text):
    return page.evaluate_handle(
        """(txt) => [...document.querySelectorAll('.z-listcell-content')]
             .find(e => (e.textContent||'').trim() === txt) || null""", exact_text)

def body_match(page, pattern):
    return page.evaluate("(p) => (document.body.innerText.match(new RegExp(p))||[''])[0]", pattern)

def dump_state(page, tag):
    png = LOG / f"medas_{tag}.png"
    page.screenshot(path=str(png), full_page=True)
    txt = page.evaluate("() => document.body.innerText")
    (LOG / f"medas_{tag}.txt").write_text(txt, encoding="utf-8")
    log(f"durum kaydı: {png.name}")

def main(stage="full"):
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
            accept_downloads=True, viewport={"width": 1600, "height": 1000})
        page = ctx.new_page()
        page.set_default_timeout(30000)
        log(f"MEDAS açılıyor: {MEDAS_URL}")
        for deneme in range(4):
            try:
                page.goto(MEDAS_URL, wait_until="domcontentloaded", timeout=60000)
                break
            except Exception as e:
                log(f"goto deneme {deneme+1} hata: {e}")
                time.sleep(25)
        time.sleep(8)

        # 1) Baz yılı = 2003 (önce uygulamanın yüklenmesini bekle)
        for deneme in range(3):
            try:
                page.wait_for_function(
                    """() => [...document.querySelectorAll('select')].some(s => [...s.options].some(o => o.text.trim()==='2003'))""",
                    timeout=60000)
                break
            except Exception as e:
                log(f"baz select bekleme {deneme+1} başarısız, sayfa yenileniyor: {e}")
                page.reload(wait_until="domcontentloaded"); time.sleep(10)
        page.evaluate("""() => {
            const s = [...document.querySelectorAll('select')].find(s => [...s.options].some(o => o.text.trim()==='2003'));
            s.value = [...s.options].find(o => o.text.trim()==='2003').value;
            s.dispatchEvent(new Event('change', {bubbles:true}));
        }""")
        time.sleep(3.5)
        log("baz yılı 2003 seçildi")
        page.wait_for_function(
            """() => [...document.querySelectorAll('.z-listcell-content')].some(e => (e.textContent||'').trim()==='Tüketici Madde Fiyatları (2003=100)')""",
            timeout=45000)

        # 2) Ölçüm: Tüketici Madde Fiyatları (2003=100)
        h = find_cell(page, "Tüketici Madde Fiyatları (2003=100)")
        assert page.evaluate("(e)=>!!e", h), "ölçüm satırı bulunamadı"
        zk_click(page, h); time.sleep(3)
        log("ölçüm seçildi: Tüketici Madde Fiyatları (2003=100)")

        # 3) COICOP kırılımı + Tamam
        h = find_cell(page, "COICOP")
        zk_click(page, h); time.sleep(2.5)
        page.evaluate("""() => {
            const bs = [...document.querySelectorAll('button, div')].filter(e => (e.innerText||'').trim()==='Tamam');
            const el = bs[bs.length-1];
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(3.5)
        toplam = body_match(page, r"\\[\\s*1\\s*-\\s*\\d+\\s*/\\s*(\\d+)\\s*\\]")
        log(f"kırılım listesi açıldı: {toplam}")

        # 4) Maddeleri seç (47 sayfa tara)
        hedef_json = json.dumps(list(HEDEF.keys()))
        page.evaluate(f"() => {{ window.__hedef = new Set({hedef_json}); window.__secilen = new Set(); }}")
        page.evaluate("""() => {
            window.__doPage = async () => {
                const w = ms => new Promise(r => setTimeout(r, ms));
                for (const c of [...document.querySelectorAll('.z-listcell-content')]) {
                    const t = (c.textContent||'').trim();
                    const mm = t.match(/^\\[(\\d{7})\\]/);
                    if (mm && window.__hedef.has(mm[1]) && !window.__secilen.has(mm[1])) {
                        for (const ev of ['mousedown','mouseup','click']) c.dispatchEvent(new MouseEvent(ev,{bubbles:true,cancelable:true,view:window,button:0}));
                        window.__secilen.add(mm[1]);
                        await w(400);
                    }
                }
                return window.__secilen.size;
            };
        }""")
        n = page.evaluate("() => window.__doPage()")
        for p in range(50):
            eksik = page.evaluate("() => [...window.__hedef].filter(k => !window.__secilen.has(k)).length")
            if eksik == 0:
                break
            moved = page.evaluate("""() => {
                const nb = document.querySelector('.z-paging-next');
                if (!nb) return false;
                for (const t of ['mousedown','mouseup','click']) nb.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
                return true;
            }""")
            if not moved:
                break
            time.sleep(0.9)
            n = page.evaluate("() => window.__doPage()")
            if p % 5 == 0:
                log(f"  sayfa {p+2}/47 tarandı, seçilen: {n}")
        secilen = page.evaluate("() => [...window.__secilen]")
        eksik = [k for k in HEDEF if k not in secilen]
        log(f"madde seçimi bitti: {len(secilen)}/{len(HEDEF)}; eksik: {eksik}")
        assert not eksik, f"eksik maddeler: {eksik}"

        # 5) Göstergeleri Ekle → İleri
        page.evaluate("""() => {
            const es = [...document.querySelectorAll('div, a, button')].filter(e => (e.innerText||'').trim()==='Göstergeleri Ekle' && e.id);
            const el = es[es.length-1];
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(4)
        cnt = body_match(page, r"Seçilen gösterge adedi[^\\n]*")
        log(f"göstergeler eklendi: {cnt}")
        page.evaluate("""() => {
            const es = [...document.querySelectorAll('button')].filter(e => (e.innerText||'').trim()==='İleri' && e.offsetParent);
            const el = es[es.length-1];
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(4)
        tabs = page.evaluate("""() => [...document.querySelectorAll('.z-tab')].map(t => ({t:(t.innerText||'').trim(), dis:t.className.includes('disabled'), sel:t.className.includes('selected')}))""")
        log(f"sekmeler: {tabs}")
        dump_state(page, "zaman_tab")
        if stage == "zaman":
            browser.close(); return

        # 6) Zaman: ZK sahte-checkbox'lar → önce başlık 'checkable' öğesi, olmazsa satır hücreleri
        env = page.evaluate("""() => ({
            checkable: [...document.querySelectorAll('[class*=checkable], [class*=z-listheader] [class*=check], .z-listheader-checkable')].map(e => ({tag:e.tagName, cls:(e.className||'').toString().slice(0,60), vis:!!e.offsetParent})).slice(0,8),
            satirOrnek: [...document.querySelectorAll('.z-listitem')].slice(0,3).map(r => (r.innerText||'').replace(/\\s+/g,' ').trim().slice(0,30)),
            nSatir: document.querySelectorAll('.z-listitem').length
        })""")
        log(f"zaman panel envanteri: {env}")
        ok = page.evaluate("""() => {
            const el = document.querySelector('.z-listheader-checkable, [class*=listheader][class*=check]');
            if (!el) return false;
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
            return el.className.toString().slice(0,50);
        }""")
        time.sleep(4)
        cnt = body_match(page, r"Seçilen zaman adedi[^\\n]*")
        log(f"zaman başlık-checkable: {ok}; sayaç: {cnt}")
        if "zaman adedi: 0" in (cnt or ""):
            log("başlık işe yaramadı — yıl-ay satırları tek tek tıklanıyor")
            n = page.evaluate("""async () => {
                const w = ms => new Promise(r => setTimeout(r, ms));
                const rows = [...document.querySelectorAll('.z-listitem')].filter(r => {
                    const cells = r.querySelectorAll('.z-listcell-content');
                    return cells.length >= 2 && /^\\d{4}$/.test((cells[0].textContent||'').trim());
                });
                let n = 0;
                for (const r of rows) {
                    const c = r.querySelector('.z-listcell-content');
                    for (const t of ['mousedown','mouseup','click']) c.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
                    n++; await w(110);
                }
                return n;
            }""")
            time.sleep(5)
            cnt = body_match(page, r"Seçilen zaman adedi[^\\n]*")
            log(f"satır satır tıklandı: {n}; sayaç: {cnt}")
        # İleri
        page.evaluate("""() => {
            const es = [...document.querySelectorAll('button')].filter(e => (e.innerText||'').trim()==='İleri' && e.offsetParent);
            const el = es[es.length-1];
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(4)
        dump_state(page, "duzey_tab")

        # 7) Düzey: açılır listeden düzey tipini seç → listelenen satırı işaretle
        opts = page.evaluate("""() => [...document.querySelectorAll('select')]
            .filter(s => s.offsetParent)
            .map(s => ({id: s.id, opts: [...s.options].map(o => o.text.trim())}))""")
        log(f"düzey select envanteri: {opts}")
        secilen_opt = page.evaluate("""() => {
            const sels = [...document.querySelectorAll('select')].filter(s => s.offsetParent);
            if (!sels.length) return null;
            const s = sels[0];
            // 'Türkiye' içeren seçenek; yoksa dolu ilk seçenek
            let o = [...s.options].find(o => /Türkiye|İBBS/i.test(o.text)) || [...s.options].find(o => o.text.trim());
            if (!o) return null;
            s.value = o.value;
            s.dispatchEvent(new Event('change', {bubbles:true}));
            return o.text.trim();
        }""")
        time.sleep(3.5)
        log(f"düzey tipi seçildi: {secilen_opt}")
        # Büyüteç/ara düğmesine bas → liste yüklensin
        arama = page.evaluate("""() => {
            const imgs = [...document.querySelectorAll('img, .z-image, a, button')].filter(e => e.offsetParent && (
                /search|find|ara|magnif|sorgu/i.test((e.src||'')+(e.title||'')+(e.alt||'')+(e.className||''))));
            if (!imgs.length) return false;
            const el = imgs[imgs.length-1];
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
            return (el.src || el.className || '').toString().split('/').pop().slice(0,40);
        }""")
        time.sleep(3.5)
        log(f"düzey arama tıklandı: {arama}")
        satirlar = page.evaluate("""() => [...document.querySelectorAll('.z-listitem, .z-row')]
            .map(r => (r.innerText||'').replace(/\\s+/g,' ').trim()).filter(Boolean).slice(0,5)""")
        log(f"düzey listesi: {satirlar}")
        ok = page.evaluate("""() => {
            let el = document.querySelector('.z-listheader-checkable:not(.z-listheader-checked)') || document.querySelector('.z-listheader-checkable');
            const trk = [...document.querySelectorAll('.z-listcell-content')].find(e => (e.textContent||'').trim() === 'Türkiye');
            if (trk) el = trk;
            if (!el) return false;
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
            return (el.className || el.textContent || '').toString().slice(0,50);
        }""")
        time.sleep(3.5)
        cnt = body_match(page, r"Seçilen düzey adedi[^\\n]*")
        log(f"düzey satır seçimi: {ok}; sayaç: {cnt}")
        dump_state(page, "duzey_secim")
        # İleri (varsa) → Rapor sekmesi
        moved = page.evaluate("""() => {
            const es = [...document.querySelectorAll('button')].filter(e => (e.innerText||'').trim()==='İleri' && e.offsetParent);
            if (!es.length) return false;
            const el = es[es.length-1];
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
            return true;
        }""")
        if not moved:
            # Rapor sekmesine doğrudan tıkla
            page.evaluate("""() => {
                const t = [...document.querySelectorAll('.z-tab')].find(t => (t.innerText||'').trim()==='Rapor');
                const el = t.querySelector('.z-tab-text') || t;
                for (const ev of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(ev,{bubbles:true,cancelable:true,view:window,button:0}));
            }""")
        time.sleep(4)
        cnt = body_match(page, r"Seçilen gösterge adedi[^\\n]*")
        log(f"rapor öncesi sayaç: {cnt}")
        dump_state(page, "rapor_tab")

        # 8a) Rapor Oluştur → raporun ekranda oluşmasını bekle
        ok = page.evaluate("""() => {
            const es = [...document.querySelectorAll('button, div, a')].filter(e => (e.innerText||'').trim()==='Rapor Oluştur' && e.offsetParent);
            if (!es.length) return false;
            const el = es[es.length-1];
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
            return true;
        }""")
        log(f"Rapor Oluştur tıklandı: {ok}")
        time.sleep(20)  # rapor 8.320 hücre — sunucu tarafında oluşsun
        dump_state(page, "rapor_olustu")
        rapor_txt = page.evaluate("() => document.body.innerText")
        log("rapor sonrası metin (ilk 400): " + rapor_txt.replace("\n", " | ")[:400])

        # 8b) Excel/CSV dışa aktarma düğmesini bul ve indirme olayını yakala
        try:
            with page.expect_download(timeout=90000) as dl_info:
                clicked = page.evaluate("""() => {
                    const cands = [...document.querySelectorAll('button, a, div, img, span')].filter(e => {
                        const t = ((e.innerText||'') + ' ' + (e.title||'') + ' ' + (e.alt||'') + ' ' + (e.src||'') + ' ' + (e.className||'')).toLowerCase();
                        return /excel|xls|csv|indir|export|aktar/.test(t) && e.offsetParent;
                    });
                    if (!cands.length) return null;
                    // xls/excel içeren en spesifik adayı seç
                    const best = cands.find(e => /xls|excel/.test(((e.src||'')+(e.title||'')+(e.alt||'')).toLowerCase())) || cands[cands.length-1];
                    for (const t of ['mousedown','mouseup','click']) best.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
                    return ((best.innerText||best.title||best.alt||best.src||'')+'').slice(0,80);
                }""")
                log(f"dışa aktarma adayı tıklandı: {clicked}")
            dl = dl_info.value
            ek = pathlib.Path(dl.suggested_filename).suffix or ".xls"
            hedef_dosya = RAW / ("medas_madde_fiyatlari" + ek)
            dl.save_as(str(hedef_dosya))
            log(f"İNDİRİLDİ: {hedef_dosya} ({hedef_dosya.stat().st_size} B)")
        except Exception as e:
            log(f"indirme başarısız: {e}")
            dump_state(page, "rapor_fail")
        browser.close()

if __name__ == "__main__":
    stage = "full"
    if "--stage" in sys.argv:
        stage = sys.argv[sys.argv.index("--stage") + 1]
    main(stage)
