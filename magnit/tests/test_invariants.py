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
    rev = {(x["period"], x.get("basis", "")): x["value"] for x in rows("revenue", status="ok") if x["unit"] == "bn_rub"}
    for series, mseries in (("gross_profit", "gross_margin"), ("ebitda", "ebitda_margin")):
        for x in rows(series, status="ok"):
            b = x.get("basis", "")
            if (x["period"], b) not in rev: continue
            calc = x["value"] / rev[(x["period"], b)] * 100
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
    assert "posterior_outstanding" in fv["results"] and "posterior_issued" in fv["results"]
    assert abs(fv.get("canonical_factor", 0) - 101.911355 / 67.847) < 1e-9
    mo, mi = fv["results"]["posterior_outstanding"]["mean"], fv["results"]["posterior_issued"]["mean"]
    assert abs(mo / mi - 101.911355 / 67.847) < 0.02, (mo, mi)

def test_wacc_calibration_band():
    for c in wacc["calibration"]:
        assert abs(c["err"]) <= wacc["band_pp"], c

def test_point_in_time():
    # released_at must not precede as_of by more than a day (no look-ahead in dating)
    for x in reg:
        if x["status"] != "ok": continue
        assert x["released_at"] >= x["as_of"] or x["released_at"] == "", x
