#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OAT–BUND ANALİZİ — BİRİNCİL KAYNAK YOKLAMASI (kesif.yml ile bulutta koşar).

Yazıya girecek olay tarihleri, not kararları ve resmî sayılar bu oturumda
yalnız arama özetlerinden geldi; özet bir kaynak değildir. Bu betik her
iddianın aday kaynağını İNDİRİR, metne çevirir ve iddianın taşıdığı ifadeyi
(tarih, sayı, ad) metnin içinde ARAR. Çıktı ham girdidir: bulunan her ifade
±180 karakterlik bağlamıyla basılır, bulunamayan "YOK" der, açılamayan sayfa
durum koduyla yazılır. Hüküm kurmaz.

Sayfanın tam metni basılmaz (haber metni yeniden yayımlanmaz); yalnız
aranan ifadenin bağlamı ve metnin özü (sha256) basılır.

`python3 -u` ile koşar (tamponlu stdout iptalde gider).
"""
from __future__ import annotations

import hashlib
import html
import io
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError

UA = {"User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/124.0 Safari/537.36"),
      "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
      "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"}

# (kimlik, adres, aranacak ifadeler). İfadeler düzenli ifadedir, büyük/küçük
# harfe duyarsız ve boşluk esnek aranır.
HEDEFLER: list[tuple[str, str, list[str]]] = [
    # --- resmî ---
    ("aft_not", "https://www.aft.gouv.fr/en/frances-credit-ratings",
     [r"Moody", r"Standard", r"Fitch", r"DBRS", r"Scope", r"KBRA", r"23\s*(October|oct)", r"27\s*(November|nov)",
      r"next", r"Aa3", r"A\+"]),
    ("aft_not_fr", "https://www.aft.gouv.fr/fr/notation-de-la-france",
     [r"Moody", r"Fitch", r"Scope", r"23\s*octobre", r"27\s*novembre", r"prochaine"]),
    ("aft_ihale_0110", "https://www.aft.gouv.fr/en/publications/communiques-presse/01-october-2026-issuance-oats",
     [r"4[.,]93", r"11[.,]999", r"6[.,]271", r"2036", r"5[.,]40"]),
    ("aft_son_ihale", "https://www.aft.gouv.fr/fr/dernieres-adjudications",
     [r"1(er)?\s*octobre\s*2026", r"01/10/2026", r"2036", r"4[.,]93"]),
    ("aft_bulten", "https://www.aft.gouv.fr/en/publications/monthly-bulletins",
     [r"non[- ]resident", r"2026"]),
    ("insee_borc_en", "https://www.insee.fr/en/statistiques/9057140",
     [r"119[.,]0", r"3[ ,.]?595[.,]5", r"59[.,]6", r"117[.,]"]),
    ("insee_borc_fr", "https://www.insee.fr/fr/statistiques/9053525",
     [r"119[.,]0", r"3\s?595[.,]5", r"18\s*d[ée]cembre", r"111[.,]4"]),
    ("fed_0916", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm",
     [r"3-3/4\s*to\s*4", r"raise", r"unanim", r"voting"]),
    ("fed_0729", "https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm",
     [r"3-1/2\s*to\s*3-3/4", r"Voting against", r"Hammack", r"Kashkari", r"Logan"]),
    ("fed_takvim", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
     [r"October\s*27-28", r"December\s*8-9", r"2026"]),
    ("ecb_faizler", "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/html/index.en.html",
     [r"2026", r"2\.50", r"2\.25", r"16 Sep", r"17 Jun"]),
    ("ecb_takvim", "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html",
     [r"29 October 2026", r"17 December 2026", r"monetary policy meeting"]),
    ("ecb_tpi", "https://www.ecb.europa.eu/press/pr/date/2022/html/ecb.pr220721~973e6e7273.en.html",
     [r"Transmission Protection Instrument", r"fiscal framework", r"excessive deficit", r"sustainab"]),
    ("konsey_aap", "https://www.consilium.europa.eu/en/press/press-releases/2024/07/26/stability-and-growth-pact-council-launches-excessive-deficit-procedures-against-seven-member-states/",
     [r"France", r"Belgium", r"Italy", r"seven"]),
    ("konsey_tavsiye", "https://www.consilium.europa.eu/en/press/press-releases/2025/01/21/stability-and-growth-pact-council-adopts-recommendations-to-countries-under-excessive-deficit-procedure/",
     [r"France", r"2029", r"net expenditure"]),
    ("komisyon_paket", "https://commission.europa.eu/publications/2026-european-semester-autumn-package_en",
     [r"France", r"draft budgetary plan", r"November"]),
    ("istinaf_lepen", "https://www.cours-appel.justice.fr/sites/default/files/2026-07/20260707%20-%20CA%20Paris%20-%20CP.pdf",
     [r"Le Pen", r"in[ée]ligibilit", r"quarante[- ]cinq|45\s*mois", r"trente\s*mois|30\s*mois", r"100\s?000", r"7\s*juillet\s*2026"]),
    ("hcfp", "https://www.hcfp.fr/liste-des-avis",
     [r"2027", r"avis\s*n", r"projet de loi de finances"]),
    ("anayasa", "https://www.conseil-constitutionnel.fr/le-bloc-de-constitutionnalite/texte-integral-de-la-constitution-du-4-octobre-1958-en-vigueur",
     [r"soixante-dix jours", r"quarante jours", r"cinquante jours", r"ordonnance"]),
    ("lolf", "https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000006412902",
     [r"premier mardi d'octobre", r"projet de loi de finances"]),
    ("ekonomi_plf", "https://www.economie.gouv.fr/actualites/video-presentation-du-projet-de-budget-pour-2027",
     [r"5\s*%", r"54\s*milliards", r"43\s*milliards", r"1er\s*octobre", r"2027"]),
    ("bdf_fsr", "https://www.banque-france.fr/en/publications-and-statistics/publications/financial-stability-report-june-2026",
     [r"spread", r"8\s*(bp|basis)", r"3\.75", r"OAT"]),
    # --- haber (ikincil; yalnız tarih/sayı teyidi için) ---
    ("reuters_0110", "https://www.tradingview.com/news/reuters.com,2026:newsml_L6N45N0FA:0-france-s-government-bond-yields-hit-highest-since-2002-ahead-of-budget/",
     [r"4\.96", r"132\.8", r"2002", r"May 2012", r"127"]),
    ("reuters_fitch", "https://www.tradingview.com/news/reuters.com,2026:newsml_FWN44P1WS:0-fitch-affirms-france-at-a-outlook-stable/",
     [r"A\+", r"Stable", r"122\.7", r"5\.5", r"5\.2"]),
    ("f24_plf", "https://www.france24.com/en/live-news/20261001-france-unveils-cost-cutting-2027-budget-as-borrowing-costs-rise",
     [r"5\.4", r"5\.0|5 percent", r"54", r"121\.7", r"119\.3"]),
    ("f24_ihale_0309", "https://www.france24.com/en/live-news/20260903-france-sells-bonds-at-highest-rate-since-2008-amid-deficit-worries",
     [r"4\.23", r"2008", r"3\.90"]),
    ("f24_bardella", "https://www.france24.com/en/france/20260928-french-far-right-jordan-bardella-denies-alleged-2013-anti-semitic-comments-mediapart-lepen",
     [r"Mediapart", r"2013", r"forger|fake"]),
    ("f24_anket", "https://www.france24.com/fr/france/20260928-pr%C3%A9sidentielle-fran%C3%A7aise-selon-un-sondage-marine-le-pen-creuse-l-%C3%A9cart-au-second-tour",
     [r"57\s*%", r"43\s*%", r"69\s*%", r"Philippe"]),
    ("f24_borc", "https://www.france24.com/fr/france/20260919-dette-publique-2026-france-budget-pib-endettement-record",
     [r"119[,.]3", r"121[,.]7"]),
    ("f24_budget2026", "https://www.aljazeera.com/news/2026/2/2/france-adopts-2026-budget-after-two-no-confidence-votes-fail",
     [r"260", r"289", r"49\.3|49\(3\)|article 49"]),
    ("fi_lecornu54", "https://www.franceinfo.fr/economie/budget/pour-le-budget-2027-sebastien-lecornu-propose-un-effort-d-environ-54-milliards-d-euros_8197535.html",
     [r"54\s*milliards", r"5\s*%", r"4[,.]8", r"6[,.]5"]),
    ("fi_takvim", "https://www.franceinfo.fr/politique/parlement-francais/assemblee-nationale/les-dates-cles-du-calendrier-parlementaire-pour-le-projet-de-loi-de-finance-2027_8159534.html",
     [r"20\s*octobre", r"27\s*octobre", r"17\s*novembre", r"9\s*d[ée]cembre", r"70\s*jours"]),
    ("fi_lepen_butce", "https://www.franceinfo.fr/politique/marine-le-pen/marine-le-pen-prefere-un-budget-imparfait-operationnel-avant-la-presidentielle-plutot-qu-une-loi-speciale_8189900.html",
     [r"loi sp[ée]ciale", r"imparfait", r"Touquet"]),
    ("lcp_fesih", "https://lcp.fr/actualites/ce-ne-serait-pas-bon-pour-le-pays-emmanuel-macron-ecarte-l-hypothese-d-une-dissolution",
     [r"dissolution", r"pas bon pour le pays", r"septembre"]),
    ("lcp_amiel", "https://lcp.fr/actualites/budget-2027-face-au-poids-de-la-dette-le-gouvernement-esquisse-les-contours-d-un-budget",
     [r"12[,.]3", r"5[,.]9", r"7\s*%", r"Amiel"]),
    ("cnews_faure", "https://www.cnews.fr/france/2026-09-27/si-rien-ne-change-nous-censurerons-olivier-faure-balaie-un-possible-compromis-sur",
     [r"censurerons", r"Faure", r"Tribune"]),
    ("cnews_aft340", "https://www.cnews.fr/france/2026-09-29/dette-publique-letat-va-emprunter-340-milliards-deuros-en-2027-du-jamais-vu",
     [r"340\s*milliards", r"310", r"72[,.]9", r"339[,.]7"]),
    ("jdd_secim", "https://www.lejdd.fr/politique/presidentielle-lelection-se-tiendra-les-18-avril-et-2-mai-2027-177813",
     [r"18\s*avril", r"2\s*mai", r"Conseil des ministres"]),
    ("fx_lagarde", "https://www.fxstreet.com/news/ecbs-lagarde-warns-france-needs-a-credible-path-to-rein-in-debt-202609301625",
     [r"120", r"La Croix", r"credible"]),
    ("fx_ing_0110", "https://www.fxstreet.com/news/euro-french-spread-widening-threatens-eur-usd-range-ing-202610010853",
     [r"127", r"alarming", r"risk premium", r"1\.11"]),
    ("fx_mufg", "https://www.fxstreet.com/news/euro-fiscal-risks-point-lower-against-us-dollar-mufg-202609240833",
     [r"110", r"1\.1340", r"1\.10"]),
    ("fx_bbh", "https://www.fxstreet.com/news/euro-france-fiscal-risks-to-have-limited-drag-bbh-202609301256",
     [r"idiosyncratic|country-specific", r"periphery|peripheral", r"limited"]),
    ("usn_nagel", "https://money.usnews.com/investing/news/articles/2026-10-01/ecb-focuses-on-inflation-not-bond-spreads-nagel-says",
     [r"spread", r"price stability", r"TPI|Transmission"]),
    ("usn_lagarde_econ", "https://money.usnews.com/investing/news/articles/2026-09-28/measured-ecb-hikes-to-quell-inflation-remain-appropriate-lagarde-says",
     [r"measured", r"second-round"]),
    ("inv_cds", "https://www.investing.com/news/stock-market-news/five-french-market-hot-spots-on-investors-radars-4916597",
     [r"52", r"2017", r"Barclays", r"100 basis|100 bps|100bp"]),
    ("inv_barclays", "https://www.investing.com/news/economy-news/barclays-flags-french-election-as-a-potential-risk-for-euro-4914952",
     [r"beta", r"periphery|peripheral", r"generous", r"election"]),
    ("ing_zaman", "https://think.ing.com/articles/rates-spark-time-not-on-frances-side",
     [r"100", r"125", r"54"]),
    ("cnbc_fed", "https://www.cnbc.com/2026/09/16/fed-rate-decision-september-2026.html",
     [r"3\.75", r"4%", r"unanim", r"dot plot"]),
    ("cnbc_ecb", "https://www.cnbc.com/2026/09/10/ecb-interest-rate-hike-lagarde-iran.html",
     [r"2\.5", r"no.brainer", r"unanim"]),
    ("euronews_ecb_haz", "https://www.euronews.com/business/2026/06/11/ecb-raises-interest-rates-for-the-first-time-in-three-years-as-iran-war-fuels-inflation",
     [r"2\.25", r"3\.2"]),
    ("xinhua_moodys", "https://english.news.cn/20260411/cfcc4c9adf7349a4925638d8411ec0b8/c.html",
     [r"Aa3", r"negative", r"5\.1", r"5 percent|5%"]),
    ("f24_moodys25", "https://www.france24.com/en/europe/20251025-moody-s-keeps-france-s-credit-rating-but-warns-about-negative-outlook",
     [r"Aa3", r"negative"]),
    ("f24_sp25", "https://www.france24.com/en/business/20251018-s-p-cuts-france-s-credit-rating-to-a-over-political-instability-risking-deficit",
     [r"A\+", r"AA-"]),
    ("fitch_25", "https://www.fitchratings.com/research/sovereigns/fitch-downgrades-france-to-a-outlook-stable-12-09-2025",
     [r"A\+", r"AA-"]),
    ("newsquawk_scope", "https://www.newsquawk.com/headlines/scope-downgrades-frances-long-term-ratings-to-a-and-revises-the-outlooks-to-stable",
     [r"Scope", r"A\+", r"Stable"]),
    ("newsquawk_dbrs", "https://www.newsquawk.com/headlines/dbrs-lowers-french-outlook-to-negative-affirms-aa-ratings",
     [r"DBRS", r"AA", r"Negative"]),
    ("lalibre_anket", "https://www.lalibre.be/international/europe/elections-france/2026/10/01/edouard-philippe-devant-melenchon-la-confirmation-du-rn-voici-ce-que-revele-le-dernier-sondage-de-la-presidentielle-francaise-EN6ZEO2YYVE4ROQCVZHRVHP4TQ/",
     [r"Ifop", r"Le Pen", r"Philippe", r"M[ée]lenchon"]),
    ("europe1_lescure", "https://www.europe1.fr/economie/comptes-publics-la-france-aura-un-deficit-superieur-a-5-en-2026-estime-roland-lescure-la-croissance-revenue-a-la-baisse-1070618",
     [r"5[,.]4", r"0[,.]5", r"Lescure"]),
    ("europe1_hcfp", "https://www.europe1.fr/politique/budget-2027-le-haut-conseil-des-finances-publiques-appelle-a-reprendre-le-controle-de-la-dette-francaise-1116182",
     [r"optimiste", r"plausible", r"1\s*%", r"Montchalin|Moscovici|pr[ée]sident"]),
    ("ideal_spread", "https://www.ideal-investisseur.fr/en/markets/oat-bund-spread.html",
     [r"225", r"2011", r"spread"]),
    ("bis_2011", "https://www.bis.org/publ/qtrpdf/r_qt1112a.pdf",
     [r"France", r"Austria", r"200"]),
]

ARANAN_BAGLAM = 180


def al(url: str, sn: int = 25) -> tuple[int, bytes, str]:
    istek = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(istek, timeout=sn) as y:
            return y.status, y.read(), y.headers.get("Content-Type", "")
    except HTTPError as e:
        return e.code, b"", ""
    except (URLError, TimeoutError, OSError) as e:
        return -1, str(e).encode()[:200], ""


def metne(govde: bytes, tur: str, url: str) -> str:
    if govde[:4] == b"%PDF" or "pdf" in tur.lower() or url.lower().endswith(".pdf"):
        try:
            from pypdf import PdfReader
            okuyucu = PdfReader(io.BytesIO(govde))
            return " ".join((s.extract_text() or "") for s in okuyucu.pages)
        except Exception as e:  # noqa: BLE001
            return f"[PDF okunamadı: {e}]"
    t = govde.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def baslik(govde: bytes) -> str:
    m = re.search(rb"(?is)<title[^>]*>(.*?)</title>", govde)
    return html.unescape(m.group(1).decode("utf-8", "replace")).strip()[:160] if m else ""


def yokla(hedef):
    kimlik, url, ifadeler = hedef
    t0 = time.time()
    kod, govde, tur = al(url)
    if kod != 200 or not govde:
        return kimlik, url, kod, None, [], time.time() - t0, govde[:200].decode("utf-8", "replace")
    metin = metne(govde, tur, url)
    bulgular = []
    for ifade in ifadeler:
        desen = re.compile(ifade.replace(" ", r"\s*"), re.I)
        eslesmeler = list(desen.finditer(metin))
        if not eslesmeler:
            bulgular.append((ifade, 0, ""))
            continue
        # En çok iki bağlam: ilk ve (varsa) farklı bir yerdeki ikinci.
        parcalar = []
        for m in eslesmeler[:2]:
            a, b = max(0, m.start() - ARANAN_BAGLAM), min(len(metin), m.end() + ARANAN_BAGLAM)
            parcalar.append(metin[a:b])
        bulgular.append((ifade, len(eslesmeler), " ⟂ ".join(parcalar)))
    oz = hashlib.sha256(metin.encode()).hexdigest()[:16]
    return kimlik, url, kod, (len(metin), oz, baslik(govde)), bulgular, time.time() - t0, ""


def main() -> int:
    print(f"# {len(HEDEFLER)} hedef · {time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} UTC", flush=True)
    with ThreadPoolExecutor(max_workers=8) as havuz:
        sonuclar = list(havuz.map(yokla, HEDEFLER))
    acik = 0
    for kimlik, url, kod, bilgi, bulgular, sure, hata in sonuclar:
        print(f"\n=== {kimlik} · HTTP {kod} · {sure:.1f} sn · {url}", flush=True)
        if bilgi is None:
            print(f"    AÇILAMADI {hata}")
            continue
        acik += 1
        uzunluk, oz, bas = bilgi
        print(f"    başlık: {bas} · metin {uzunluk} karakter · öz {oz}")
        for ifade, n, baglam in bulgular:
            if n == 0:
                print(f"    [YOK] {ifade}")
            else:
                print(f"    [{n}] {ifade} :: {baglam}")
    print(f"\n# açılan {acik}/{len(HEDEFLER)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
