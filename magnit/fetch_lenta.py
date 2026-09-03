"""Lenta (LNTA) via secondary sources (lenta.com blocked 401): SmartLab fund table + T-invest.
Flagged secondary; used only for peer-context, never for Magnit levels.
Saves magnit/data/peers/lenta_secondary.json
"""
import urllib.request, re, json, pathlib
import sys
sys.path.insert(0, 'magnit')

out = {"source_status": "secondary (lenta.com 401); SmartLab + T-invest", "series": {}}
# 1. SmartLab yearly
req = urllib.request.Request('https://smart-lab.ru/q/LNTA/f/y/',
                             headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
try:
    t = urllib.request.urlopen(req, timeout=25).read().decode('utf-8', 'ignore')
    rows = {}
    for m in re.finditer(r'<tr field="([a-z_]+)">(.*?)</tr>', t, re.S):
        vals = [v.strip() for v in re.findall(r'<td[^>]*>([^<]*?)</td>', m.group(2))
                if v.strip() and 'chart' not in v]
        rows[m.group(1)] = vals
    # year headers: find 4-digit cells near top of table
    years = re.findall(r'<td[^>]*>(\d{4})</td>', t)[:8]
    out["series"]["smartlab_years_hint"] = years
    for f in ("revenue", "ebitda", "ebitda_margin", "net_income"):
        out["series"][f] = rows.get(f)
    print('smartlab years hint:', years)
    for f in ("revenue", "ebitda", "ebitda_margin", "net_income"):
        print(f, rows.get(f))
except Exception as e:
    print('smartlab FAIL', repr(e)[:200])
    out["series"]["smartlab_error"] = repr(e)[:200]

# 2. T-invest snapshot
try:
    import os
    import pathlib as pl
    tok = (os.environ.get("TINVEST_TOKEN")
           or pl.Path(r'C:\Users\rodio\.secrets\some-service.token').read_text().strip())

    def post(svc, payload):
        u = 'https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.' + svc
        req = urllib.request.Request(u, data=json.dumps(payload).encode(),
                                     headers={'Authorization': 'Bearer ' + tok,
                                              'Content-Type': 'application/json'}, method='POST')
        return json.loads(urllib.request.urlopen(req, timeout=20).read().decode())

    s = post('InstrumentsService/ShareBy', {'idType': 'INSTRUMENT_ID_TYPE_TICKER', 'classCode': 'TQBR', 'id': 'LNTA'})
    auid = s['instrument']['assetUid']
    f = post('InstrumentsService/GetAssetFundamentals', {'assets': [auid]})['fundamentals'][0]
    out["series"]["tinvest"] = {k: f.get(k) for k in (
        'marketCapitalization', 'revenueTtm', 'ebitdaTtm', 'netIncomeTtm', 'evToEbitdaMrq',
        'netDebtToEbitda', 'priceToSalesTtm', 'dividendYieldDailyTtm')}
    print('tinvest:', out["series"]["tinvest"])
except Exception as e:
    print('tinvest FAIL', repr(e)[:200])
    out["series"]["tinvest_error"] = repr(e)[:200]

pathlib.Path('magnit/data/peers/lenta_secondary.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print('saved lenta_secondary.json')
