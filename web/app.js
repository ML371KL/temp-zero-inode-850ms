/* Magnit FV dashboard v2 — vanilla JS, no deps. Reads data/data.json.
   Time-axis charts with gridlines, legends, tooltips. Dual share-basis toggle. */
const $ = id => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const el = (t, a) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); return e; };
const fmt = (v, d = 0) => (v == null || !isFinite(v)) ? "—" : Number(v).toLocaleString("ru-RU", { maximumFractionDigits: d });
const C = { mut: "#8b98ab", grid: "#2a3446", acc: "#4da3ff", up: "#3fce7a", dn: "#ff6b6b", warn: "#ffb84d", txt: "#e8edf3" };
let BASIS_NAME = "outstanding"; // canonical; F already in chosen basis (no scaling)
const QL = iso => { const [y, m] = iso.split("-").map(Number); return `Q${Math.floor((m - 1) / 3) + 1}′${String(y).slice(2)}`; };

function niceTicks(lo, hi, n = 4) {
  const span = hi - lo || 1, step0 = span / n, mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const norm = step0 / mag;
  const step = (norm < 1.5 ? 1 : norm < 3.5 ? 2 : norm < 7.5 ? 5 : 10) * mag;
  const ticks = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) ticks.push(+v.toFixed(10));
  return ticks;
}
function legend(id, items) {
  $(id).innerHTML = items.map(([c, s]) => `<span><i style="background:${c}"></i>${s}</span>`).join("");
}
function txt(parent, x, y, s, fill = C.mut, sz = 11, anchor = "start") {
  const e = el("text", { x, y, fill, "font-size": sz, "text-anchor": anchor }); e.textContent = s; parent.appendChild(e); return e;
}
/* Generic time chart. series: [{key,label,color,width,dash?,pts:[{t:ms,v,tag}]}] */
function timeChart(svg, series, H, fmtY = v => v) {
  const all = series.flatMap(s => s.pts.map(p => p.v)).filter(v => v != null);
  if (!all.length) return;
  let lo = Math.min(...all), hi = Math.max(...all);
  if (lo > 0) lo = 0; if (hi < 0) hi = 0;
  const pad = (hi - lo) * 0.08 || 1; lo -= pad; hi += pad;
  const ts = series.flatMap(s => s.pts.map(p => p.t));
  const t0 = Math.min(...ts), t1 = Math.max(...ts), tsp = (t1 - t0) || 1;
  const L = 52, R = 10, T = 10, B = 24, W = 640;
  const X = t => L + (t - t0) / tsp * (W - L - R);
  const Y = v => T + (1 - (v - lo) / (hi - lo)) * (H - T - B);
  niceTicks(lo, hi).forEach(v => {
    svg.appendChild(el("line", { x1: L, y1: Y(v), x2: W - R, y2: Y(v), stroke: C.grid, "stroke-width": v === 0 ? 1.2 : 0.6 }));
    txt(svg, L - 5, Y(v) + 4, fmtY(v), C.mut, 10, "end");
  });
  series.forEach(s => {
    let d = "";
    s.pts.forEach((p, i) => { d += (i ? "L" : "M") + X(p.t).toFixed(1) + " " + Y(p.v).toFixed(1) + " "; });
    const path = el("path", { d, fill: "none", stroke: s.color, "stroke-width": s.width || 2 });
    if (s.dash) path.setAttribute("stroke-dasharray", s.dash);
    const ttl = el("title", {}); ttl.textContent = s.label; path.appendChild(ttl); svg.appendChild(path);
    if (s.pts.length <= 40) s.pts.forEach(p => {
      const c = el("circle", { cx: X(p.t), cy: Y(p.v), r: 2.6, fill: s.color });
      const tt = el("title", {}); tt.textContent = `${p.tag || ""}: ${fmtY(p.v)}`; c.appendChild(tt); svg.appendChild(c);
    });
    const last = s.pts[s.pts.length - 1];
    txt(svg, W - R, Y(last.v) - 5, s.label, s.color, 10, "end");
  });
  // x ticks: ~6 evenly
  const allT = [...new Set(series.flatMap(s => s.pts.map(p => p.t)))].sort((a, b) => a - b);
  const step = Math.max(1, Math.floor(allT.length / 6));
  allT.forEach((t, i) => { if (i % step === 0) txt(svg, X(t), H - 7, QL(new Date(t).toISOString().slice(0, 10)), C.mut, 10, "middle"); });
}

fetch("data/data.json").then(r => { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); }).then(D => {
  const FOUT = D.fv.judgment_outstanding, FISS = D.fv.judgment_issued, P = D.market.price;
  let F = FOUT, BASIS_NAME = "outstanding";
  $("built").textContent = "built " + (D.meta.built_utc || "").slice(0, 16).replace("T", " ");
  $("mkt-update").textContent = "MOEX " + (D.market.update || "?");
  const setBasis = out => {
    F = out ? FOUT : FISS;
    BASIS_NAME = out ? "outstanding" : "issued";
    $("b-iss").classList.toggle("on", !out); $("b-out").classList.toggle("on", out);
    $("fv-basis").textContent = BASIS_NAME + (out ? " (canonical)" : " (MOEX cap recon.)");
    renderFV(); renderCards();
  };
  $("b-iss").onclick = () => setBasis(false); $("b-out").onclick = () => setBasis(true);

  const renderCards = () => {
    $("price").textContent = fmt(P); // per-share price is basis-invariant; cap below reflects basis
    const cap = BASIS_NAME === "issued" ? D.market.cap.issued_101_9m : D.market.cap.outstanding_67_8m;
    $("cap").textContent = `cap ${cap} млрд (${BASIS_NAME})`;
    const lh = D.market.last_history_close;
    $("daychg").textContent = lh ? `prev close ${fmt(lh)} (${D.market.last_history_date || ""}) · day ${(P / lh - 1 >= 0 ? "+" : "") + ((P / lh - 1) * 100).toFixed(2)}%` : "—";
    // median-led: median is the central message, mean is tail-dragged (healthy owns ~80%)
    $("fv-mean").textContent = fmt(F.p50);
    $("fv-band").textContent = `median ${fmt(F.p50)} · mean ${fmt(F.mean)} · p05 ${fmt(F.p05)} · p25 ${fmt(F.p25)} · p75 ${fmt(F.p75)} · p95 ${fmt(F.p95)}`;
    $("pfv").textContent = (F.p_fv_gt_p * 100).toFixed(1) + "%";
    const dec = D.decision || {}, gm = dec.metrics || {}, gg = dec.gates || {};
    const parts = [
      `P(hurdle 25% p.a.) ${((gm.p_hurdle_25pa || 0) * 100).toFixed(0)}% ${(gm.p_hurdle_25pa || 0) >= .5 ? "✓" : "✗"}`,
      `leverage ${Object.values(dec.leverage_series_pre16 || {}).slice(-1)[0] || "?"}x ${gg.leverage_below_2_5x ? "✓" : "✗"}`,
      `cod ${gg.cod_falling ? "✓" : "✗"}`];
    $("verdict").textContent = dec.verdict || "WAIT";
    $("gates").textContent = parts.join(" · ");
  };
  const renderFV = () => {
    const svg = $("fvchart"); svg.innerHTML = "";
    const q = ["p05", "p25", "p50", "p75", "p95"].map(k => F[k]);
    const Pv = P; // per-share price invariant to share-count basis
    const hi = Math.max(q[4], Pv) * 1.06, X = v => 52 + v / hi * 578;
    [0, hi / 2, hi].forEach(v => {
      svg.appendChild(el("line", { x1: X(v), y1: 34, x2: X(v), y2: 140, stroke: C.grid, "stroke-width": 0.6 }));
      txt(svg, X(v), 158, fmt(v), C.mut, 10, "middle");
    });
    const band = (a, b, fill, y = 62, h = 40) => svg.appendChild(el("rect", { x: X(a), y, width: Math.max(2, X(b) - X(a)), height: h, fill, rx: 4 }));
    band(q[0], q[4], "#22314a"); band(q[1], q[3], "#4da3ff55");
    svg.appendChild(el("line", { x1: X(q[2]), y1: 54, x2: X(q[2]), y2: 110, stroke: "#fff", "stroke-width": 3 }));
    const pl = el("line", { x1: X(Pv), y1: 30, x2: X(Pv), y2: 140, stroke: C.warn, "stroke-width": 2, "stroke-dasharray": "6,3" });
    const pt = el("title", {}); pt.textContent = `Цена ${fmt(Pv)}`; pl.appendChild(pt); svg.appendChild(pl);
    txt(svg, X(q[0]), 178, `p05 ${fmt(q[0])}`);
    txt(svg, X(q[4]), 178, `p95 ${fmt(q[4])}`, C.mut, 11, "end");
    txt(svg, X(q[2]), 46, `p50 ${fmt(q[2])}`, "#fff", 12, "middle");
    txt(svg, Math.min(X(Pv) + 7, 540), 24, `цена ${fmt(Pv)}`, C.warn, 12);
    legend("fv-legend", [["#22314a", "p05–p95"], ["#4da3ff55", "p25–p75"], ["#fff", "p50"], [C.warn, "цена"]]);
  };
  renderCards(); renderFV();
  // regime decomposition: mean is tail-dragged, show who owns it
  const rg = F.by_regime || {};
  let rh = `<table><tr><th>режим</th><th>вес</th><th>среднее</th><th>P(FV&gt;P)</th><th>вклад в mean</th></tr>`;
  Object.entries(rg).forEach(([k, v]) => { rh += `<tr><td>${k}</td><td>${(v.share * 100).toFixed(0)}%</td><td>${fmt(v.mean)}</td><td>${(v.p_fv_gt_p * 100).toFixed(0)}%</td><td>${(v.contrib_to_mean * 100).toFixed(0)}%</td></tr>`; });
  rh += `</table><p class="note">Взвешенная смесь суждений (не Bayes-posterior): веса режимов заданы вручную и заявлены. Terminal share DCF в среднем ${(F.terminal_share_mean * 100).toFixed(0)}%.</p>`;
  $("regimes").innerHTML = rh;
  const sens = D.sensitivity || {};
  const sc = [["base", "база"], ["bear_combo", "joint bear"], ["bull_combo", "joint bull"]];
  let sh = `<p class="note">Чувствительность (общий движок, single вес): `;
  sh += sc.filter(([k]) => sens[k]).map(([k, n]) => `${n}: медиана ${fmt(sens[k].median)}`).join(" · ") + ".</p>";
  $("robust").innerHTML = sh;

  const nc = D.nowcast || {};
  $("nc").textContent = nc.nowcast != null ? `~${nc.nowcast}%` : "—";
  $("nc-detail").textContent = `${nc.target || "—"} · еда ${nc.food_q3_yoy != null ? nc.food_q3_yoy + "%" : "—"} (${nc.food_basis || "?"}) + ${nc.x5_src || "—"}. ${nc.read || ""} [gap: ${nc.gap_src || "?"}]`;
  $("nc-warn").textContent = (nc.warnings || []).join(" | ");

  const T = iso => new Date(iso + "T00:00:00Z").getTime();
  // LFL: three series on time axis
  const lflS = ["sales", "ticket", "traffic"], lflC = { sales: "#4da3ff", ticket: "#3fce7a", traffic: "#ffb84d" },
    lflN = { sales: "продажи", ticket: "чек", traffic: "трафик" };
  timeChart($("lflchart"), lflS.map(s => ({
    key: s, label: lflN[s], color: lflC[s], width: s === "sales" ? 2.6 : 1.6,
    pts: D.series.lfl.filter(r => r.s === s).map(r => ({ t: T(r.as_of), v: r.v, tag: `${r.p} ${lflN[s]}` }))
  })), 250, v => v + "%");
  legend("lfl-legend", lflS.map(s => [lflC[s], `${lflN[s]} (LFL г/г)`]));
  // Revenue: Magnit (time axis) + X5 quarterly dashed
  const mg = D.series.revenue_yoy.map(r => ({ t: T(r.as_of), v: r.v, tag: `${r.p}: ${r.v}%` }));
  const x5 = (D.series.x5_quarterly || []).filter(q => q.rev_yoy != null).map(q => {
    const y = +q.q.slice(0, 4), qq = +q.q.slice(5);
    return { t: Date.UTC(y, qq * 3 - 1, 1), v: q.rev_yoy, tag: `X5 ${q.q}: ${q.rev_yoy}%` };
  });
  timeChart($("revchart"), [
    { key: "mg", label: "Магнит", color: "#4da3ff", width: 2.4, pts: mg },
    { key: "x5", label: "X5", color: "#b48cff", width: 1.6, dash: "5,3", pts: x5 }], 230, v => v + "%");
  legend("rev-legend", [["#4da3ff", "Магнит выручка г/г"], ["#b48cff", "X5 выручка г/г (IAS17)"]]);
  // Margins: two series
  const mm = s => D.series.margins_pre16.filter(r => r.s === s).map(r => ({ t: T(r.as_of), v: r.v, tag: `${r.p}: ${r.v}%` }));
  timeChart($("mgnchart"), [
    { key: "e", label: "EBITDA", color: "#3fce7a", width: 2.2, pts: mm("ebitda_margin") },
    { key: "g", label: "валовая", color: "#4da3ff", width: 1.6, pts: mm("gross_margin") }], 210, v => v + "%");
  legend("mgn-legend", [["#3fce7a", "EBITDA pre16"], ["#4da3ff", "валовая pre16"]]);
  const cr = D.credit || {}, liq = cr.liquidity || {}, nd = cr.net_debt_pre16 || {};
  $("credit").textContent = `Чистый долг pre16 ${nd.h1_2026} млрд (YE25 ${nd.ye2025}) · кэш/короткий ${liq.cash_to_short}x · линии ${liq.undrawn_lines} млрд · ковенанты соблюдены. Ближайшая ликвидность достаточна; риск — carry и рефинанс, не мгновенная solvency.`;
  // TSR line under verdict
  const dec = D.decision || {}, dm = dec.metrics || {};
  if (dm.median != null) {
    const tsr = el("div", {});
    $("gates").textContent += ` · TSR_2y median ${(dm.median * 100).toFixed(0)}% / mean ${(dm.mean * 100).toFixed(0)}% · P(hurdle 25% p.a.) ${((dm.p_hurdle_25pa || 0) * 100).toFixed(0)}% · P(loss>30%) ${((dm.p_loss_30 || 0) * 100).toFixed(0)}% · CVaR5 ${(dm.cvar_5 * 100).toFixed(0)}%`;
  }
  // dilution scenarios
  const dil = D.dilution || {};
  if ((dil.cases || []).length) {
    let dh = `<table><tr><th>сценарий</th><th>акций, млн</th><th>FV/акция</th></tr>`;
    dil.cases.forEach(c => { dh += `<tr><td>${c.case}</td><td>${c.shares_m}</td><td>${fmt(c.per_share)}</td></tr>`; });
    dh += `</table><p class="note">Equity total ${dil.equity_total_bn} млрд. ${dil.note || ""}</p>`;
    $("dilution").innerHTML = dh;
  }
  // skill (quarterly-only LFL backtest)
  const sk = (D.skill.origins || []);
  let h = `<table><tr><th>origin</th><th>fact</th><th>pred</th><th>err</th><th>proxy</th></tr>`;
  sk.slice(-10).forEach(r => { h += `<tr><td>${r.period}</td><td>${r.act}%</td><td>${r.pred}%</td><td class="${r.err >= 0 ? "pos" : "neg"}">${r.err > 0 ? "+" : ""}${r.err}</td><td>${r.x5}%${r.x5_kind === "lfl" ? "" : "*"}</td></tr>`; });
  h += `</table><p class="note">MAE ${D.skill.mae_pp}pp · direction ${D.skill.direction} (монета: развороты не ловит) · покрытие интервалом ${((D.skill.interval_coverage || 0) * 100).toFixed(0)}% · * = X5 total proxy (own expansion inside), LFL-бэктест quarterly-only, expanding window.</p>`;
  $("skill").innerHTML = h;
  // consensus
  const REC = { RECOMMENDATION_BUY: "Buy", RECOMMENDATION_HOLD: "Hold", RECOMMENDATION_SELL: "Sell" };
  const tp = t => t ? fmt(+t.units + (t.nano || 0) / 1e9) : "—";
  const rc = c => { const r = REC[c.rec] || c.rec || "?"; return r === "Buy" ? "pos" : r === "Sell" ? "neg" : ""; };
  $("consensus").innerHTML = `<div class="cons">${(D.market.consensus || []).map(c =>
    `<div><b>${c.company || "?"}</b> <span class="${rc(c)}">${REC[c.rec] || "?"}</span><br><span class="t">${tp(c.target)}</span></div>`).join("")}</div>`;
  $("fresh").textContent = `registry ${D.meta.registry_rows} rows (${Object.entries(D.meta.status_mix).map(([k, v]) => k + ":" + v).join(", ")}) · engine ${D.meta.engine} · ${D.meta.sources}`;
}).catch(e => { document.body.insertAdjacentHTML("afterbegin", `<p style="color:#ff6b6b;padding:12px">data load failed: ${e}</p>`); });
