"""Export model artifacts -> dashboard data bundle (magnit-850ms repo, web/data/).
Reads registry, fv_dist, market latest, nowcast, skill, wacc, credit, ma_layer, peers.
Writes data.json (single source for the static UI) + meta.
"""
import json, pathlib, datetime
from collections import Counter

M = pathlib.Path(__file__).parent / "data"
REPO_ROOT = pathlib.Path(__file__).parent.parent
OUT = REPO_ROOT / "web" / "data"
OUT.mkdir(parents=True, exist_ok=True)

def load(p, default=None):
    try: return json.loads((M / p).read_text(encoding="utf-8"))
    except Exception: return default

reg = load("registry.json", [])
mkt = load("market/latest.json", {})
fv = load("fv_dist.json", {})
nc = load("nowcast_q3_2026.json", {})
skill = load("skill_v1.json", {})
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
    "skill": {"mae_pp": skill.get("mae_pp"), "bias_pp": skill.get("bias_pp"),
              "direction": skill.get("direction"), "naive_x5_mae_pp": skill.get("naive_x5_mae_pp"),
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
}
# decision gates computed here (testable, canonical outstanding basis), UI only renders
P = bundle["market"]["price"]
post = (bundle["fv"] or {}).get("posterior_outstanding", {})
irr2 = (post.get("mean", 0) / P) ** 0.5 - 1 if P else float("-inf")
key_tail = [c["value"] for c in (bundle["wacc"].get("key_changes_tail") or [])]
cod_falling = len(key_tail) >= 2 and key_tail[-1] < key_tail[0]
bundle["gates"] = {
    "irr2": round(irr2, 4) if irr2 != float("-inf") else None,
    "irr2_pass": irr2 >= 0.25,
    "p_prob": post.get("p_fv_gt_p"), "p_pass": (post.get("p_fv_gt_p") or 0) >= 0.5,
    "leverage": {"value": "2.9x", "trend": "flat H1 (FY25 2.9x -> H1 2.9x)", "pass": False},
    "cod": {"falling": cod_falling, "note": f"key {key_tail[0] if key_tail else '?'}->{key_tail[-1] if key_tail else '?'}; cod 17.1->16.0", "pass": cod_falling},
    "verdict": "WAIT",
}
bundle["gates"]["verdict"] = "ACT" if all([bundle["gates"]["irr2_pass"], bundle["gates"]["p_pass"],
                                           bundle["gates"]["leverage"]["pass"], bundle["gates"]["cod"]["pass"]]) else "WAIT"
(OUT / "data.json").write_text(json.dumps(bundle, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"bundle: {len(json.dumps(bundle))//1024} KB, lfl pts={len(lfl)}, rev pts={len(rev)}, x5q={len(x5q)}")
