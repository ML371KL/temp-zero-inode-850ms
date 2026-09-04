"""Export model artifacts -> dashboard data bundle (magnit-850ms repo, web/data/).
Reads registry, fv_dist, market latest, nowcast, skill, wacc, credit, ma_layer, peers.
Writes data.json (single source for the static UI) + meta.
"""
import json, pathlib, datetime
from collections import Counter

M = pathlib.Path(__file__).parent / "data"
OUT = pathlib.Path("C:/Users/rodio/Documents/magnit-850ms/web/data")
OUT.mkdir(parents=True, exist_ok=True)

def load(p, default=None):
    try: return json.loads((M / p).read_text(encoding="utf-8"))
    except Exception: return default

reg = load("registry.json", [])
mkt = load("market/latest.json", {})
fv = load("fv_dist.json", {})
nc = load("nowcast_q3_2026.json", {})
skill = load("skill_lfl.json", {}) or load("skill_v1.json", {})
dec = load("decision.json", {})
sens = load("sensitivity.json", {})
wacc = load("macro/wacc.json", {})
credit = load("credit.json", {})
ma = load("ma_layer.json", {})
x5 = load("peers/x5_quarterly.json", {})
mult = load("peers/mult_history.json", {})
food = load("macro/food_monthly.json", {})
kr = load("macro/key_rate.json", {})

# LFL time series (verified splits)
lfl = sorted([{"p": x["period"], "as_of": x["as_of"], "s": {"lfl": "sales", "lfl_ticket": "ticket", "lfl_traffic": "traffic"}[x["series"]], "v": x["value"]}
              for x in reg if x["series"] in ("lfl", "lfl_ticket", "lfl_traffic") and x["status"] == "ok"],
             key=lambda z: z["as_of"])
# revenue yoy series
rev = sorted([{"p": x["period"], "as_of": x["as_of"], "v": x["value"]}
              for x in reg if x["series"] == "revenue_yoy" and x["status"] == "ok"],
             key=lambda z: z["as_of"])
# margins (pre16 FY/H1)
mgn = sorted([{"p": x["period"], "as_of": x["as_of"], "s": x["series"], "v": x["value"]}
              for x in reg if x["series"] in ("ebitda_margin", "gross_margin") and x.get("basis") == "pre16" and x["status"] == "ok"],
             key=lambda z: z["as_of"])
# X5 quarterly compact
x5q = [{"q": q, "rev_yoy": v.get("revenue_yoy"), "ebitda_m": v.get("ebitda_margin"),
        "lfl": v.get("x5_lfl"), "lfl_tr": v.get("x5_lfl_traffic")}
       for q, v in sorted(x5.get("quarters", {}).items())]

bundle = {
    "meta": {"built_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "engine": "magnit-v2", "registry_rows": len(reg),
             "status_mix": dict(Counter(x["status"] for x in reg)),
             "sources": "magnit.com IR (primary), Rosstat, CBR, x5.ru databook, MOEX ISS, T-invest"},
    "market": {"price": (mkt.get("cap_dual") or {}).get("price"), "cap": mkt.get("cap_dual"),
               "update": (mkt.get("moex") or {}).get("updatetime"),
               "last_history_close": (mkt.get("moex") or {}).get("last_history_close"),
               "last_history_date": (mkt.get("moex") or {}).get("last_history_date"),
               "outstanding_factor": round(101.911355 / 67.847, 4),
               "fundamentals": mkt.get("tinvest"),
               "consensus": (mkt.get("consensus") or [])[:8]},
    "fv": fv.get("results", {}),
    "nowcast": nc,
    "skill": {"mae_pp": skill.get("mae_pp"), "direction": skill.get("direction"),
              "interval_coverage": skill.get("interval_coverage"),
              "origins": skill.get("origins", [])},
    "wacc": {"now": wacc.get("now"), "scenarios": wacc.get("scenarios"),
             "key_now": (kr.get("current") or {}).get("value"),
             "key_changes_tail": (kr.get("changes") or [])[-6:]},
    "credit": credit,
    "series": {"lfl": lfl, "revenue_yoy": rev, "margins_pre16": mgn, "x5_quarterly": x5q,
               "food_quarterly": (food.get("quarterly_food_cumul_pct") or {}),
               "mult_history_pre16": ((mult.get("mults")) or {}),
               "peer_post16_mrq": mult.get("peer_multiple_context_post16_mrq") or {"lenta": 2.32, "magnit": 4.1, "x5": 5.2}},
    "ma_deals": (ma.get("deals") or []),
    "decision": {"metrics": (dec.get("metrics") or {}), "gates": (dec.get("gates") or {}),
                 "verdict": dec.get("verdict", "WAIT"), "rule": dec.get("rule", ""),
                 "leverage_series_pre16": dec.get("leverage_series_pre16", {})},
    "sensitivity": (sens.get("cases") or {}),
}
# decision gates: read from decision.json (computed from draws + data layer).
# No IRR-of-mean anywhere: TSR distribution metrics only. UI renders, never computes.
P = bundle["market"]["price"]
post = (bundle["fv"] or {}).get("judgment_outstanding", {})
gm = (dec.get("metrics") or {})
key_tail = [c["value"] for c in (bundle["wacc"].get("key_changes_tail") or [])]
cod_falling = len(key_tail) >= 2 and key_tail[-1] < key_tail[0]
lev_series = dec.get("leverage_series_pre16", {})
bundle["gates"] = {
    "tsr_median_2y": gm.get("median"), "tsr_mean_2y": gm.get("mean"),
    "p_hurdle_25pa": gm.get("p_hurdle_25pa"), "p_pass": (gm.get("p_hurdle_25pa") or 0) >= 0.5,
    "p_loss_30": gm.get("p_loss_30"), "p_loss_50": gm.get("p_loss_50"),
    "cvar_5": gm.get("cvar_5"), "mos_p25": gm.get("mos_p25"),
    "leverage": {"series": lev_series,
                 "last": list(lev_series.values())[-1] if lev_series else None,
                 "pass": bool((dec.get("gates") or {}).get("leverage_below_2_5x", False))},
    "cod": {"falling": cod_falling, "note": f"key {key_tail[0] if key_tail else '?'}->{key_tail[-1] if key_tail else '?'}; cod 17.1->16.0", "pass": cod_falling},
    "verdict": dec.get("verdict", "WAIT"),
}
# treasury dilution scenarios (BOTH sides move: shares AND cash/debt).
# E_total from mix mean (outstanding) -> per-scenario per-share.
E_bn = (post.get("mean", 0) * 67.847 / 1000) if post.get("mean") else 0
S0 = 67.847
dils = [{"case": "as-is (treasury held)", "shares_m": S0, "per_share": post.get("mean")}]
for label, add_m, px in (("repo 3.8m return (no cash)", 3.817, 0.0),
                         ("place 10m at market", 10.0, P or 0),
                         ("place all 34.1m at market", 34.064, P or 0),
                         ("place 10m at -20% discount", 10.0, (P or 0) * 0.8)):
    cash = add_m * px / 1000 if px else 0
    per = (E_bn + cash) / (S0 + add_m) * 1000 if (S0 + add_m) else 0
    dils.append({"case": label, "shares_m": round(S0 + add_m, 3), "per_share": round(per, 0)})
bundle["dilution"] = {"equity_total_bn": round(E_bn, 1), "note": "placement adds shares AND cash; at-market ~= neutral by construction", "cases": dils}
(OUT / "data.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"bundle: {len(json.dumps(bundle))//1024} KB, lfl pts={len(lfl)}, rev pts={len(rev)}, x5q={len(x5q)}")
