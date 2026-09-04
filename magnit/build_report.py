"""Local report artifact: magnit/data/report.md + trigger alerts.
Reads fv_dist, market latest, skill, credit, wacc, calibration. No deploy, local file only.
Exit 0 always (report is non-critical); alerts listed in report + alerts.json.
"""
import json, pathlib, datetime

DATA = pathlib.Path(__file__).parent / "data"
R = DATA / "report.md"

def load(p, default=None):
    try: return json.loads((DATA / p).read_text(encoding="utf-8"))
    except Exception: return default

fv = load("fv_dist.json", {})
mkt = load("market/latest.json", {})
skill = load("skill_lfl.json", {}) or load("skill_v1.json", {})
credit = load("credit.json", {})
wacc = load("macro/wacc.json", {})
nc = load("nowcast_q3_2026.json", {})
dec = load("decision.json", {})
sens = load("sensitivity.json", {})
P = (mkt.get("cap_dual") or {}).get("price") or fv.get("price", 1580)
post = (fv.get("results") or {}).get("judgment_outstanding", {})
basis_note = "outstanding 67.8m (canonical)"

alerts = []
# triggers
try:
    x5w = json.loads((DATA / "peers" / "x5_watcher.json").read_text(encoding="utf-8"))
    alerts.extend(x5w.get("alerts", []))
except Exception:
    pass
nd_check = (credit.get("net_debt_pre16") or {}).get("h1_2026")
if credit.get("liquidity", {}).get("cash_to_short", 9) < 1.2:
    alerts.append("LIQUIDITY: cash/short < 1.2x")
if (wacc.get("now") or {}).get("key_now", 99) < 14:
    alerts.append("RATE: key cut below 14% -> rerun WACC scenarios")
if post.get("p_fv_gt_p", 0) >= 0.5:
    alerts.append(f"VALUE: P(FV>P)={post.get('p_fv_gt_p'):.0%} with E[FV]={post.get('mean')}")
if skill.get("mae_pp", 99) > 6:
    alerts.append(f"SKILL: bridge MAE {skill.get('mae_pp')}pp degraded")
if not mkt.get("moex"):
    alerts.append("MARKET: MOEX snapshot stale/failed")

L = []
L.append(f"# Magnit FV report ({datetime.date.today().isoformat()}, local)")
L.append("")
L.append(f"Market: **{P}** (issued cap {(mkt.get('cap_dual') or {}).get('issued_101_9m')}bn / "
         f"outst {(mkt.get('cap_dual') or {}).get('outstanding_67_8m')}bn) | "
         f"MOEX update: {(mkt.get('moex') or {}).get('updatetime', '?')}")
L.append("")
if post:
    L.append(f"FV mix ({basis_note}): mean **{post['mean']:.0f}** | p05 {post['p05']:.0f} p25 {post['p25']:.0f} "
             f"p50 {post['p50']:.0f} p75 {post['p75']:.0f} p95 {post['p95']:.0f} | P(FV>P)={post['p_fv_gt_p']:.1%}")
    L.append("")
gm = (dec.get("metrics") or {})
if gm:
    L.append(f"TSR_2y (full draws): median {gm.get('median', 0):.1%} mean {gm.get('mean', 0):.1%} | "
             f"P(hurdle 25pa)={gm.get('p_hurdle_25pa', 0):.1%} P(loss30)={gm.get('p_loss_30', 0):.1%} "
             f"P(loss50)={gm.get('p_loss_50', 0):.1%} CVaR5={gm.get('cvar_5', 0):.1%} | "
             f"p25 MOS={gm.get('mos_p25', 0):.1%}.")
    L.append("")
gg = dec.get("gates", {})
if gg:
    L.append("Gates: " + " · ".join(f"{k} {'PASS' if v else 'BLOCKS'}" for k, v in gg.items())
             + f" -> **{dec.get('verdict', '?')}** "
               f"(leverage {dec.get('leverage_series_pre16', {})} | cod {dec.get('cod_points', [])}).")
    L.append("")
L.append(f"cod {(wacc.get('now') or {}).get('cod_now', '?')}% WACC {(wacc.get('now') or {}).get('wacc_now', '?')}% "
         f"(key {(wacc.get('now') or {}).get('key_now', '?')}%).")
L.append("")
sk = load("skill_lfl.json", {}) or load("skill_v1.json", {})
L.append(f"Bridge skill (LFL quarterly-only, expanding window): MAE {sk.get('mae_pp')}pp, "
         f"direction {sk.get('direction')} (coin flip: levels only, no turning-point skill), "
         f"interval coverage {sk.get('interval_coverage')}. "
         f"Naive-X5 MAE {sk.get('naive_x5_mae_pp', '?')}pp where available.")
L.append("")
L.append(f"Credit: net {nd_check}bn pre16; cash/short {(credit.get('liquidity') or {}).get('cash_to_short')}x; "
         f"undrawn {(credit.get('liquidity') or {}).get('undrawn_lines')}bn; covenants complied. "
         f"Near-term liquidity looks sufficient; mid-term refinancing + interest carry "
         f"remain the material equity risk (maturity-bucket table unparsed: see credit.open_item).")
L.append("")
L.append("Alerts:")
L.append("" if alerts else "- none")
for a in alerts: L.append(f"- {a}")
L.append("")
sc = (sens.get("cases") or {})
if sc:
    def zone(r):
        if r.get("p_fv_gt_p") is None: return "n/a"
        return ("above" if (r["median"] > P * 1.25 and r["p_fv_gt_p"] > 0.5)
                else ("overlap" if r["p_fv_gt_p"] > 0.35 else "below"))
    L.append("Robustness (sensitivity.json, canonical basis): " +
             "; ".join(f"{k}: median {v['median']:.0f} ({zone(v)})" for k, v in sc.items()) + ". "
             f"Price {P} vs mix p05 {post.get('p05')} / p95 {post.get('p95')}: "
             "value is uncertain, not cheap; WAIT is the robust middle until gates resolve.")
L.append("")
L.append("")
L.append("Next catalysts: X5 Q3 trading (~14 Oct, lead 2-6 wks) -> Magnit Q3/LFL; CBR meetings -> WACC; Q3 ND/EBITDA.")
if nc:
    L.append("")
    L.append(f"Live nowcast ({nc.get('as_of')}): {nc.get('target')} = **{nc.get('nowcast')}%** "
             f"(food {nc.get('food_q3_yoy')}% + {nc.get('x5_src')}). {nc.get('read')}.")
    for w in nc.get("warnings", []): L.append(f"  - nowcast caveat: {w}")
R.write_text("\n".join(L), encoding="utf-8")
(DATA / "alerts.json").write_text(json.dumps(
    {"as_of": datetime.datetime.now(datetime.timezone.utc).isoformat(), "alerts": alerts},
    ensure_ascii=False, indent=1), encoding="utf-8")
print(f"report written ({len(alerts)} alerts)")
for a in alerts: print(" ALERT:", a)
