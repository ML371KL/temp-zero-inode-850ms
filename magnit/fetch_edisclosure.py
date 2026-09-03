"""Fetch e-disclosure company page (id=7671, Magnit) with session headers.
Saves raw HTML + extracts filing links/dates. Reconciliation vs registry released_at.
"""
import urllib.request, http.cookiejar, pathlib, re, json, datetime

OUT = pathlib.Path('magnit/data/ed')
OUT.mkdir(parents=True, exist_ok=True)
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
H = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36',
     'Accept': 'text/html,application/xhtml+xml', 'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'}

def get(url):
    return op.open(urllib.request.Request(url, headers=H), timeout=30).read()

main = get('https://www.e-disclosure.ru/portal/company.aspx?id=7671')
(OUT / 'company_7671.html').write_bytes(main)
t = main.decode('utf-8', 'ignore')
print('company page bytes:', len(main))
print('title:', (re.search(r'<title>(.*?)</title>', t, re.S).group(1).strip()[:120] if re.search(r'<title>(.*?)</title>', t, re.S) else '?'))
links = sorted(set(re.findall(r'href="([^"]+)"', t)))
for l in links:
    if re.search(r'event|file|report|fact|news|doc', l, re.I):
        print('  ', l[:160])
(OUT / 'fetch_meta.json').write_text(json.dumps(
    {"url": "https://www.e-disclosure.ru/portal/company.aspx?id=7671", "bytes": len(main),
     "fetched_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()},
    ensure_ascii=False, indent=1), encoding='utf-8')
