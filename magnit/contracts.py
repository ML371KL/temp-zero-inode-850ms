"""Contracts for magnit model data (local prototype).
- registry.schema.json: every registry row shape.
- STATUS set, BASIS set, required keys.
"""
SCHEMA = {
    "required": ["series", "period", "as_of", "value", "unit", "source", "url",
                 "released_at", "vintage", "status", "note"],
    "status": ["ok", "provisional", "quarantine"],
    "value_types": [int, float],
}
# invariants (also enforced in tests/test_invariants.py)
SHARES_ISSUED_M = 101.911355
SHARES_TREASURY_M = 34.064
SHARES_OUTSTANDING_M = 67.847
LFL_IDENTITY_TOL_PP = 0.4
MARGIN_IDENTITY_TOL_PP = 0.35
WACC_BAND_PP = 1.5
