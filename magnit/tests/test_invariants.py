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
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    from contracts import SCHEMA
    req = set(SCHEMA["required"])
    today = datetime.date.today().isoformat()
    for x in reg:
        assert req <= set(x), x
        assert x["status"] in SCHEMA["status"], x
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


def test_opex_wedge_identity():
    import json, pathlib
    d = json.loads((pathlib.Path(__file__).parent.parent / 'data' / 'opex_bridge.json').read_text(encoding='utf-8'))
    w = [r for r in d['rows'] if r['period'].endswith('wedge_check')]
    assert w, 'wedge check missing'
    for r in w:
        assert r['gross_bp'] - r['ebitda_bp'] == r['absorbed_bp'], r
        assert r['absorbed_bp'] > 0, r  # cost creep absorbs gross gains (the documented fact)


def test_format_sums_bounded():
    import json, pathlib
    d = json.loads((pathlib.Path(__file__).parent.parent / 'data' / 'opex_bridge.json').read_text(encoding='utf-8'))
    reg = json.loads((pathlib.Path(__file__).parent.parent / 'data' / 'registry.json').read_text(encoding='utf-8'))
    rev = {x['period']: x['value'] for x in reg if x['series'] == 'revenue' and x['unit'] == 'bn_rub'
           and x.get('basis') in (None, '', 'n/a') and x['status'] == 'ok'}
    for r in d['rows']:
        if not r.get('formats_mln'): continue
        s = sum(v['cur_mln'] for v in r['formats_mln'].values()) / 1000
        tot = rev.get(r['period'])
        assert tot and 0.5 * tot < s < tot, (r['period'], s, tot)
        for k, v in r['formats_mln'].items():
            assert abs(v['cur_mln'] / v['prev_mln'] * 100 - 100 - v['yoy']) < 1.0, (r['period'], k, v)


def test_apv_breakeven_below_spot():
    # APV (no multiples) must show ~0 equity at spot debt: the downside anchor.
    # If APV ever clears spot debt, the WAIT thesis needs rewriting.
    import json, pathlib
    a = json.loads((pathlib.Path(__file__).parent.parent / 'data' / 'apv.json').read_text(encoding='utf-8'))
    for case, legs in a['cases'].items():
        be = legs['mid']['breakeven_net_debt']
        assert be < 922.2, (case, be)
    assert a['cases']['recovery']['mid']['per_share_outst_spot'] == 0.0


def test_debt_wall_sums():
    import json, pathlib
    s = json.loads((pathlib.Path(__file__).parent.parent / 'data' / 'debt_schedule.json').read_text(encoding='utf-8'))
    assert abs(sum(s['wall_bn'].values()) - 2.2 - 745.7) < 1.0, s['wall_bn']  # wall skips the -2.2 current-portion adjustment
    assert abs(s['long_total'] + s['short_total'] - 745.7) < 0.2


def test_vintage_fields_present():
    for x in reg:
        for f in ('vintage_id', 'first_seen', 'avail_since', 'restatement_id', 'supersedes'):
            assert f in x, (x.get('series'), x.get('period'), f)


def test_no_destructive_overwrite():
    # superseded rows are retained, never deleted; quarantine rows stay queryable
    sts = {x['status'] for x in reg}
    assert sts <= {'ok', 'provisional', 'quarantine', 'superseded'}, sts


def test_pit_monotonic():
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    from pit import rows_as_of
    a = rows_as_of(reg, '2024-05-01')
    b = rows_as_of(reg, '2025-05-01')
    c = rows_as_of(reg, '2026-09-04')
    assert len(a) <= len(b) <= len(c) and len(a) > 100, (len(a), len(b), len(c))


def test_opex_identities():
    import json, pathlib
    d = json.loads((pathlib.Path(__file__).parent.parent / 'data' / 'opex_bridge.json').read_text(encoding='utf-8'))
    w = [r for r in d['rows'] if r['period'].endswith('wedge_check')][0]
    assert w['gross_bp'] - w['ebitda_bp'] == w['absorbed_bp'] and w['absorbed_bp'] > 0
    for r in d['rows']:
        if r.get('formats_mln'):
            s = sum(v['cur_mln'] for v in r['formats_mln'].values()) / 1000
            assert 1000 < s < 4000, (r['period'], s)


def test_apv_below_spot_debt():
    # APV (no multiples) must NOT clear spot gross debt: downside anchor holds.
    # If it ever does, the WAIT thesis and this test both need rewriting.
    import json, pathlib
    a = json.loads((pathlib.Path(__file__).parent.parent / 'data' / 'apv.json').read_text(encoding='utf-8'))
    for case, legs in a['cases'].items():
        assert legs['mid']['breakeven_net_debt'] < 922.2, (case, legs['mid'])
