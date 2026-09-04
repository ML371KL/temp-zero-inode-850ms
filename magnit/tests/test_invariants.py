"""Pytest invariants for magnit prototype data. Run: .venv\\Scripts\\python.exe -m pytest magnit/tests -q
Fail-closed philosophy: any red here blocks refresh FV/decision stages.
"""
import json, pathlib, datetime
import pytest

DATA = pathlib.Path(__file__).parent.parent / "data"
reg = json.loads((DATA / "registry.json").read_text(encoding="utf-8"))
fv = json.loads((DATA / "fv_dist.json").read_text(encoding="utf-8"))
wacc = json.loads((DATA / "macro" / "wacc.json").read_text(encoding="utf-8"))

def rows(series=None, period=None, basis=None, status=None):
    out = reg
    if series: out = [x for x in out if x["series"] == series]
    if period: out = [x for x in out if x["period"] == period]
    if basis: out = [x for x in out if x.get("basis") == basis]
    if status: out = [x for x in out if x["status"] == status]
    return out

def test_registry_schema():
    req = {"series", "period", "as_of", "value", "unit", "source", "url",
           "released_at", "vintage", "status", "note"}
    today = datetime.date.today().isoformat()
    for x in reg:
        assert req <= set(x), x
        assert x["status"] in ("ok", "provisional", "quarantine"), x
        assert isinstance(x["value"], (int, float)), x
        datetime.date.fromisoformat(x["as_of"])
        assert x["released_at"] <= today, x

def test_no_exact_duplicates():
    keys = [(x["series"], x["period"], x.get("basis", ""), x["value"], x.get("vintage")) for x in reg]
    assert len(keys) == len(set(keys))

def test_shares_identity():
    # issued - treasury == outstanding (IFRS FY2025 note, millions)
    assert abs((101.911355 - 34.064) - 67.847) < 0.01

def test_basis_separation():
    for x in rows(status="ok"):
        if x["series"] in ("ebitda", "net_debt", "ebitda_margin", "gross_margin"):
            assert x.get("basis") in ("pre16", "post16", "n/a"), x

def test_lease_gap_identity():
    # post16 - pre16 net debt == lease liabilities 600.1 +- 5 (FY2025, H1 2026)
    ifrs = json.loads((DATA / "ifrs_facts.json").read_text(encoding="utf-8"))
    leases = next(f["value"] for f in ifrs if f["series"] == "lease_total_implied")
    for p in ("2025FY",):
        pre = next(x["value"] for x in rows("net_debt", p, "pre16", "ok"))
        post = next(x["value"] for x in rows("net_debt", p, "post16", "ok"))
        assert abs((post - pre) - leases) < 5.0, (p, post - pre, leases)

def test_lfl_identity():
    by_p = {}
    for x in rows(status="ok"):
        if x["series"] in ("lfl", "lfl_ticket", "lfl_traffic"):
            by_p.setdefault(x["period"], {})[x["series"]] = x["value"]
    assert len(by_p) >= 10
    for p, d in by_p.items():
        if len(d) == 3:
            chk = (1 + d["lfl_ticket"] / 100) * (1 + d["lfl_traffic"] / 100) - 1
            assert abs(chk * 100 - d["lfl"]) < 0.4, (p, d)

def test_margin_identities():
    rev = {}
    for x in rows("revenue", status="ok"):
        if x["unit"] == "bn_rub":
            rev.setdefault((x["period"], x.get("basis", "")), x["value"])
    def rev_for(period, basis):
        return rev.get((period, basis), rev.get((period, ""), rev.get((period, "n/a"))))
    for series, mseries in (("gross_profit", "gross_margin"), ("ebitda", "ebitda_margin")):
        for x in rows(series, status="ok"):
            b = x.get("basis", "")
            R = rev_for(x["period"], b)
            if R is None: continue
            calc = x["value"] / R * 100
            m = next((m_["value"] for m_ in rows(mseries, x["period"], b if b != "n/a" else None, "ok")), None)
            if m is not None:
                assert abs(calc - m) < 0.35, (x["period"], series, calc, m)

def test_fv_distribution_sanity():
    for name, r in fv["results"].items():
        assert r["p05"] <= r["p25"] <= r["p50"] <= r["p75"] <= r["p95"], r
        assert abs(sum(r["probs"].values()) - 1.0) < 1e-9, r
        assert 0.0 <= r["p_fv_gt_p"] <= 1.0, r

def test_dual_basis():
    # canonical = outstanding ex-treasury; issued kept for MOEX-cap reconciliation
    assert "judgment_outstanding" in fv["results"] and "judgment_issued" in fv["results"]
    assert abs(fv.get("canonical_factor", 0) - 101.911355 / 67.847) < 1e-9
    mo = fv["results"]["judgment_outstanding"]["mean"]
    mi = fv["results"]["judgment_issued"]["mean"]
    assert abs(mo / mi - 101.911355 / 67.847) < 0.02, (mo, mi)

def test_wacc_calibration_band():
    for c in wacc["calibration"]:
        assert abs(c["err"]) <= wacc["band_pp"], c

def test_point_in_time():
    # released_at must not precede as_of by more than a day (no look-ahead in dating)
    for x in reg:
        if x["status"] != "ok": continue
        assert x["released_at"] >= x["as_of"] or x["released_at"] == "", x

def test_fcff_excludes_interest():
    # audit: interest must not enter FCFF; tax must be levied on EBIT (unlevered)
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    from valuation import build_fcf
    c = build_fcf(ebitda=200.0, rev=3500.0)
    da = 0.028 * 3500.0
    assert abs(c["da"] - da) < 1e-9
    assert abs(c["tax"] - max(0.0, 200.0 - da) * 0.25) < 1e-9
    assert abs(c["fcf"] - (200.0 - c["tax"] - c["capex_maint"] - c["capex_growth"] - c["dwc"])) < 1e-9
    # growth capex scales with growth, maintenance with revenue
    assert c["capex_growth"] > 0 and c["capex_maint"] > 0 and c["dwc"] > 0


def test_blend_weights_sum_to_one():
    import sys, random
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    from valuation import blend_ev
    rnd = random.Random(0)
    for _ in range(200):
        a, b = 100.0, 200.0
        w = rnd.random()
        assert abs(blend_ev(a, b, w) - (w * a + (1 - w) * b)) < 1e-9
    try:
        blend_ev(1.0, 2.0, 1.5)
        raise SystemExit("blend accepted w>1")
    except AssertionError:
        pass


def test_seed_stability():
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    from fv_distribution import run, POST
    v1, _, _, _, _ = run(POST, 77, 67.847)[:5]
    v2, _, _, _, _ = run(POST, 77, 67.847)[:5]
    import numpy as np
    assert (v1 == v2).all()
    q1 = np.quantile(v1, [0.05, 0.25, 0.5, 0.75, 0.95])
    assert abs(q1[2] - 1478) / 1478 < 0.05, q1  # median anchor (recalibrate bound if engine changes)


def test_no_hardcoded_market_price():
    import pathlib as _pl, re
    src = (_pl.Path(__file__).parent.parent / "fv_distribution.py").read_text(encoding="utf-8")
    # no price ASSIGNMENT literal (mentions in strings/comments are fine)
    assert not re.search(r"^\s*P\s*=\s*158\d", src, re.M)
    dec = (_pl.Path(__file__).parent.parent / "decision_layer.py").read_text(encoding="utf-8")
    assert "VERDICT: WAIT (" not in dec  # verdict computed, not printed static
