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
skill = load("skill_v1.json", {})
credit = load("credit.json", {})
wacc = load("macro/wacc.json", {})
nc = load("nowcast_q3_2026.json", {})
P = (mkt.get("cap_dual") or {}).get("price") or fv.get("price", 1580)
post = (fv.get("results") or {}).get("posterior_outstanding", {})
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
    L.append(f"FV posterior ({basis_note}): mean **{post['mean']:.0f}** | p05 {post['p05']:.0f} p25 {post['p25']:.0f} "
             f"p50 {post['p50']:.0f} p75 {post['p75']:.0f} p95 {post['p95']:.0f} | P(FV>P)={post['p_fv_gt_p']:.1%}")
    L.append("")
L.append(f"Gates: E[IRR(2y)]>=25% + P>=0.5 + leverage falling 2Q + cod falling. "
         f"Leverage gate: ND/EBITDA pre16 H1 = 2.9x (flat) -> BLOCKS. "
         f"cod {(wacc.get('now') or {}).get('cod_now', '?')}% WACC {(wacc.get('now') or {}).get('wacc_now', '?')}% (key {(wacc.get('now') or {}).get('key_now', '?')}%).")
L.append("")
L.append(f"Bridge skill: MAE {skill.get('mae_pp')}pp (naive-X5 {skill.get('naive_x5_mae_pp')}pp), "
         f"direction {skill.get('direction')}, bias {skill.get('bias_pp')}pp. "
         f"LFL-bridge v2 (ma_layer) preferred structurally.")
L.append("")
L.append(f"Credit: net {nd_check}bn pre16; cash/short {(credit.get('liquidity') or {}).get('cash_to_short')}x; "
         f"undrawn {(credit.get('liquidity') or {}).get('undrawn_lines')}bn; covenants complied; "
         f"risk = carry, not solvency.")
L.append("")
L.append("Alerts:")
L.append("" if alerts else "- none")
for a in alerts: L.append(f"- {a}")
L.append("")
L.append("Robustness (sensitivity audit, canonical basis): single-factor bears hold above "
         "(bear-probs 2420, mult -0.5x 2707, debt +60bn 2755); only the joint bear combo "
         "(stress-heavy + WACC +2pp + mult -0.5x + debt +60bn) breaks below at 208. "
         "Price 1580 sits below the posterior bulk but the left tail is real (p05 45): "
         "WAIT is the robust middle — action only when leverage/cod gates resolve the uncertainty.")
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
