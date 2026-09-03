"""Market snapshot job: MOEX ISS (free) + T-invest (token) -> data/market/latest.json
Price, cap (both share bases), TTM fundamentals, consensus targets, dividends meta.
Fail closed: on network error writes data/market/failed_*.json, keeps latest.json.
"""
import urllib.request, json, pathlib, datetime, sys, os

DATA = pathlib.Path(__file__).parent / "data" / "market"
DATA.mkdir(parents=True, exist_ok=True)
OUT = DATA / "latest.json"
H = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def jget(url, timeout=25):
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=timeout))

def main():
    snap = {"as_of_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "ticker": "MGNT"}
    try:
        md = jget("https://iss.moex.com/iss/engines/stock/markets/shares/securities/MGNT.json?iss.meta=off&iss.only=marketdata,securities")
        cols = md["marketdata"]["columns"]
        tqbr = [r for r in md["marketdata"]["data"] if r[cols.index("BOARDID")] == "TQBR"][0]
        g = lambda k: tqbr[cols.index(k)]
        snap["moex"] = {"last": g("LAST"), "open": g("OPEN"), "high": g("HIGH"), "low": g("LOW"),
                        "vol_today": g("VOLTODAY"), "val_today": g("VALTODAY"),
                        "cap_issued": g("ISSUECAPITALIZATION"), "updatetime": g("UPDATETIME")}
        # history: last close for continuity
        h = jget("https://iss.moex.com/iss/history/engines/stock/markets/shares/securities/MGNT.json?iss.meta=off&limit=1&sort_order=desc")
        hc = h["history"]["columns"]
        snap["moex"]["last_history_close"] = h["history"]["data"][0][hc.index("CLOSE")]
        snap["moex"]["last_history_date"] = h["history"]["data"][0][hc.index("TRADEDATE")]
    except Exception as e:
        snap["moex_error"] = repr(e)[:300]
    # T-invest
    try:
        tok = os.environ.get("TINVEST_TOKEN") or pathlib.Path(
            r"C:\Users\rodio\.secrets\some-service.token").read_text().strip()

        def post(svc, payload):
            u = "https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1." + svc
            req = urllib.request.Request(u, data=json.dumps(payload).encode(),
                                         headers={"Authorization": "Bearer " + tok,
                                                  "Content-Type": "application/json"}, method="POST")
            return json.loads(urllib.request.urlopen(req, timeout=20).read().decode())

        auid = "4833e124-265f-4879-adc8-58bdf983f54e"  # MGNT assetUid (verified)
        f = post("InstrumentsService/GetAssetFundamentals", {"assets": [auid]})["fundamentals"][0]
        snap["tinvest"] = {k: f.get(k) for k in (
            "marketCapitalization", "revenueTtm", "ebitdaTtm", "netIncomeTtm", "freeCashFlowTtm",
            "totalEnterpriseValueMrq", "evToEbitdaMrq", "netDebtToEbitda", "totalDebtMrq",
            "priceToBookTtm", "fiveYearsAverageDividendYield", "sharesOutstanding")}
        fc = post("InstrumentsService/GetForecastBy",
                  {"instrumentId": "ca845f68-6c43-44bc-b584-330d2a1e5eb7"}).get("targets", [])
        snap["consensus"] = [{"company": t.get("company"), "rec": t.get("recommendation"),
                              "target": t.get("targetPrice")} for t in fc[:12]]
    except Exception as e:
        snap["tinvest_error"] = repr(e)[:300]
    if "moex" not in snap and "tinvest" not in snap:
        (DATA / f"failed_{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')}.json").write_text(
            json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
        print("RED: both sources failed, latest.json untouched")
        return 1
    # dual-basis cap
    if "moex" in snap and snap["moex"].get("last"):
        px = snap["moex"]["last"]
        snap["cap_dual"] = {"price": px, "issued_101_9m": round(101.911355 * px / 1000, 1),
                            "outstanding_67_8m": round(67.847 * px / 1000, 1), "unit": "bn_rub"}
    OUT.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"market snapshot ok: price={snap.get('moex', {}).get('last')} cap={snap.get('cap_dual')}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
