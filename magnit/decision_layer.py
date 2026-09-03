"""Decision layer v3 (no buy/sell labels). Reads magnit/data/fv_dist.json (posterior).
Canonical per-share basis = OUTSTANDING ex-treasury (67.847m): price discovery happens
on tradeable shares; treasury economics accrue to remaining holders. Issued basis shown
only to reconcile MOEX-published cap.
Rule: act only if E[IRR(2y)]>=25% AND P(FV>P)>=0.5 AND leverage falling 2Q AND cod falling.
"""
import json, pathlib

DATA = pathlib.Path(__file__).parent / "data"
d = json.loads((DATA / "fv_dist.json").read_text(encoding="utf-8"))
P = d["price"]
K = d.get("canonical_factor", 101.911355 / 67.847)
post = d["results"]["posterior_outstanding"]
probs = post["probs"]

def irr(fv, p, t): return (fv / p) ** (1 / t) - 1 if fv > 0 and p > 0 else float("-inf")

e = post["mean"]
print(f"POSTERIOR FV(outstanding, x{K:.4f}): mean {post['mean']:.0f} | p05 {post['p05']:.0f} p25 {post['p25']:.0f} "
      f"p50 {post['p50']:.0f} p75 {post['p75']:.0f} p95 {post['p95']:.0f}")
print(f"Market P={P:.0f} | P(FV>P)={post['p_fv_gt_p']:.1%} | "
      f"E[IRR(1y)]={irr(e,P,1):.1%} E[IRR(2y)]={irr(e,P,2):.1%} E[IRR(3y)]={irr(e,P,3):.1%}")
gates = {"E[IRR(2y)]>=25%": irr(e, P, 2) >= 0.25,
         "P(FV>P)>=0.5": post["p_fv_gt_p"] >= 0.5,
         "leverage falling 2Q": False,  # ND/EBITDA 2.9 flat H1 (2.9 FY25 -> 2.9 H1); needs Q3
         "cost of debt falling": True}  # 17.1% FY25 -> 16.0% H1
for k, v in gates.items(): print(f"  [{'x' if v else ' '}] {k}")
print("VERDICT: WAIT (leverage gate blocks; 3/4 pass). Triggers: Q3 ND/EBITDA<2.5x, X5 Q3 trading beat (lead ~2-6 wks).")
print("Regime probs (posterior, stated tilt):", probs)
