# -*- coding: utf-8 -*-
"""
MEDAS'tan Tarım Ürünleri ÜFE (2020=100) tür bazlı endeksleri indirir
(sığır, koyun, kümes hayvanları...). 2022/05 sonrası dana/tavuk tüketici
fiyatı ayrıştırması için görece dinamik kaynağı.

Çıktı: data/raw/medas_tarim_ufe.xls + output/log/medas_tarim.log
"""
import time, json, re, pathlib, datetime
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"; LOG = ROOT / "output" / "log"
RAW.mkdir(parents=True, exist_ok=True); LOG.mkdir(parents=True, exist_ok=True)

logf = open(LOG / "medas_tarim.log", "a", encoding="utf-8")
def log(m):
    line = f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {m}"
    print(line, flush=True); logf.write(line + "\n"); logf.flush()

HEDEF_DESEN = re.compile(r"sığır|koyun|kümes|manda|keçi|canlı hayvan", re.IGNORECASE)

CLICK = """(el) => { for (const t of ['mousedown','mouseup','click'])
  el.dispatchEvent(new MouseEvent(t, {bubbles:true, cancelable:true, view:window, button:0})); }"""

def main():
    with sync_playwright() as pw:
        b = pw.chromium.launch(headless=True)
        ctx = b.new_context(accept_downloads=True, viewport={"width": 1600, "height": 1000})
        pg = ctx.new_page(); pg.set_default_timeout(60000)
        for d in range(4):
            try:
                pg.goto("https://biruni.tuik.gov.tr/medas/?kn=84&locale=tr", wait_until="domcontentloaded"); break
            except Exception as e:
                log(f"goto {d+1}: {e}"); time.sleep(20)
        time.sleep(8)
        # Konu değiştir
        pg.evaluate("""() => {
            const s = [...document.querySelectorAll('select')].find(s => [...s.options].some(o => o.text.includes('Tarım Ürünleri Üretici Fiyat')));
            s.value = [...s.options].find(o => o.text.includes('Tarım Ürünleri Üretici Fiyat')).value;
            s.dispatchEvent(new Event('change', {bubbles:true}));
        }""")
        time.sleep(6)
        log("konu: Tarım Ürünleri ÜFE")
        # Ölçüm: endeks (2020=100)
        pg.evaluate("""() => {
            const c = [...document.querySelectorAll('.z-listcell-content')].find(e => (e.textContent||'').trim() === 'Tarım Ürünleri Üretici Fiyat Endeksi (2020=100)');
            for (const t of ['mousedown','mouseup','click']) c.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(3)
        # Kırılım TAORBA + Tamam
        pg.evaluate("""() => {
            const c = [...document.querySelectorAll('.z-listcell-content')].find(e => (e.textContent||'').trim() === 'TAORBA');
            if (c) for (const t of ['mousedown','mouseup','click']) c.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(2.5)
        pg.evaluate("""() => {
            const bs = [...document.querySelectorAll('button, div')].filter(e => (e.innerText||'').trim()==='Tamam');
            const el = bs[bs.length-1];
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(3.5)
        pag = pg.evaluate("""() => (document.body.innerText.match(/\\[\\s*1\\s*-\\s*\\d+\\s*\\/\\s*(\\d+)\\s*\\]/)||['',''])[1]""")
        log(f"kırılım listesi: {pag} girdi")
        # Sayfalarda desene uyanları seç ve tüm listeyi topla
        pg.evaluate("""() => { window.__sec = []; window.__tum = []; }""")
        for p in range(60):
            yeni = pg.evaluate("""() => {
                const out = [];
                for (const c of [...document.querySelectorAll('.z-listcell-content')]) {
                    const t = (c.textContent||'').trim();
                    if (/^\\[/.test(t) && !window.__tum.includes(t)) { window.__tum.push(t); out.push(t); }
                }
                return out;
            }""")
            for t in yeni:
                if HEDEF_DESEN.search(t):
                    tik = pg.evaluate("""(txt) => {
                        const c = [...document.querySelectorAll('.z-listcell-content')].find(e => (e.textContent||'').trim() === txt);
                        if (!c) return false;
                        for (const ev of ['mousedown','mouseup','click']) c.dispatchEvent(new MouseEvent(ev,{bubbles:true,cancelable:true,view:window,button:0}));
                        window.__sec.push(txt);
                        return true;
                    }""", t)
                    log(f"  seçildi ({tik}): {t[:70]}")
                    time.sleep(0.5)
            ilerledi = pg.evaluate("""() => {
                const nb = document.querySelector('.z-paging-next');
                if (!nb) return false;
                for (const t of ['mousedown','mouseup','click']) nb.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
                return true;
            }""")
            if not ilerledi: break
            time.sleep(0.9)
            son = pg.evaluate("() => (document.body.innerText.match(/\\[\\s*(\\d+)\\s*-\\s*(\\d+)\\s*\\/\\s*(\\d+)\\s*\\]/)||[]).slice(1)")
            if son and len(son) == 3 and son[1] == son[2]:
                # son sayfa: bir tur daha topla
                yeni = pg.evaluate("""() => {
                    const out = [];
                    for (const c of [...document.querySelectorAll('.z-listcell-content')]) {
                        const t = (c.textContent||'').trim();
                        if (/^\\[/.test(t) && !window.__tum.includes(t)) { window.__tum.push(t); out.push(t); }
                    }
                    return out;
                }""")
                for t in yeni:
                    if HEDEF_DESEN.search(t):
                        pg.evaluate("""(txt) => {
                            const c = [...document.querySelectorAll('.z-listcell-content')].find(e => (e.textContent||'').trim() === txt);
                            if (c) { for (const ev of ['mousedown','mouseup','click']) c.dispatchEvent(new MouseEvent(ev,{bubbles:true,cancelable:true,view:window,button:0})); window.__sec.push(txt); }
                        }""", t)
                        log(f"  seçildi(son): {t[:70]}")
                        time.sleep(0.5)
                break
        secilen = pg.evaluate("() => window.__sec")
        tum = pg.evaluate("() => window.__tum")
        json.dump(tum, open(RAW / "medas_taorba_listesi.json", "w"), ensure_ascii=False, indent=1)
        log(f"toplam kırılım {len(tum)}; seçilen {len(secilen)}")
        if not secilen:
            log("HİÇBİR ŞEY SEÇİLMEDİ — liste kaydedildi, desen gözden geçirilecek")
            b.close(); return
        # Göstergeleri Ekle → İleri
        pg.evaluate("""() => {
            const es = [...document.querySelectorAll('div, a, button')].filter(e => (e.innerText||'').trim()==='Göstergeleri Ekle' && e.id);
            const el = es[es.length-1];
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(3.5)
        log(pg.evaluate("() => (document.body.innerText.match(/Seçilen gösterge adedi[^\\n]*/)||[''])[0]"))
        pg.evaluate("""() => {
            const es = [...document.querySelectorAll('button')].filter(e => (e.innerText||'').trim()==='İleri' && e.offsetParent);
            const el = es[es.length-1];
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(4)
        # Zaman: başlık checkable
        pg.evaluate("""() => {
            const el = document.querySelector('.z-listheader-checkable');
            if (el) for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(3.5)
        log(pg.evaluate("() => (document.body.innerText.match(/Seçilen zaman adedi[^\\n]*/)||[''])[0]"))
        pg.evaluate("""() => {
            const es = [...document.querySelectorAll('button')].filter(e => (e.innerText||'').trim()==='İleri' && e.offsetParent);
            const el = es[es.length-1];
            for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(4)
        # Düzey: tip seç + ara + satır
        pg.evaluate("""() => {
            const sels = [...document.querySelectorAll('select')].filter(s => s.offsetParent);
            if (sels.length) {
                const s = sels[0];
                const o = [...s.options].find(o => /Türkiye/i.test(o.text)) || [...s.options].find(o => o.text.trim());
                if (o) { s.value = o.value; s.dispatchEvent(new Event('change', {bubbles:true})); }
            }
        }""")
        time.sleep(3)
        pg.evaluate("""() => {
            const imgs = [...document.querySelectorAll('img, .z-image, a, button')].filter(e => e.offsetParent && /search|find|toolbarbutton/i.test((e.src||'')+(e.className||'')));
            if (imgs.length) { const el = imgs[imgs.length-1];
              for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0})); }
        }""")
        time.sleep(3)
        pg.evaluate("""() => {
            let el = [...document.querySelectorAll('.z-listcell-content')].find(e => (e.textContent||'').trim() === 'Türkiye');
            if (!el) el = document.querySelector('.z-listheader-checkable');
            if (el) for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
        }""")
        time.sleep(3)
        log(pg.evaluate("() => (document.body.innerText.match(/Seçilen düzey adedi[^\\n]*/)||[''])[0]"))
        # Rapor sekmesi / İleri
        pg.evaluate("""() => {
            const es = [...document.querySelectorAll('button')].filter(e => (e.innerText||'').trim()==='İleri' && e.offsetParent);
            if (es.length) { const el = es[es.length-1];
              for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0})); }
            else {
              const t2 = [...document.querySelectorAll('.z-tab')].find(t => (t.innerText||'').trim()==='Rapor');
              const el = t2.querySelector('.z-tab-text') || t2;
              for (const ev of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(ev,{bubbles:true,cancelable:true,view:window,button:0}));
            }
        }""")
        time.sleep(4)
        pg.evaluate("""() => {
            const es = [...document.querySelectorAll('button, div, a')].filter(e => (e.innerText||'').trim()==='Rapor Oluştur' && e.offsetParent);
            if (es.length) { const el = es[es.length-1];
              for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0})); }
        }""")
        log("Rapor Oluştur tıklandı; bekleniyor")
        time.sleep(15)
        try:
            with pg.expect_download(timeout=90000) as dl_info:
                pg.evaluate("""() => {
                    const cands = [...document.querySelectorAll('img, a, button')].filter(e => /xls|excel/i.test((e.src||'')+(e.title||'')+(e.alt||'')) && e.offsetParent);
                    const el = cands[cands.length-1];
                    for (const t of ['mousedown','mouseup','click']) el.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true,view:window,button:0}));
                }""")
            dl = dl_info.value
            hedef = RAW / ("medas_tarim_ufe" + (pathlib.Path(dl.suggested_filename).suffix or ".xls"))
            dl.save_as(str(hedef))
            log(f"İNDİRİLDİ: {hedef} ({hedef.stat().st_size} B)")
        except Exception as e:
            log(f"indirme hatası: {e}")
            pg.screenshot(path=str(LOG / "tarim_fail.png"), full_page=True)
        b.close()

if __name__ == "__main__":
    main()
