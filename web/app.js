/* Magnit FV dashboard — vanilla JS, no deps. Reads data/data.json */
const $ = id => document.getElementById(id);
const NS = "http://www.w3.org/2000/svg";
const el = (t, a) => { const e = document.createElementNS(NS, t); for (const k in a) e.setAttribute(k, a[k]); return e; };
const fmt = (v, d = 0) => v == null ? "—" : Number(v).toLocaleString("ru-RU", { maximumFractionDigits: d });

fetch("data/data.json").then(r => r.json()).then(D => {
  $("built").textContent = "built " + (D.meta.built_utc || "").slice(0, 16).replace("T", " ");
  $("mkt-update").textContent = "MOEX " + ((D.market.update || "?"));
  const P = D.market.price;
  $("price").textContent = fmt(P);
  $("cap").textContent = `cap ${D.market.cap.issued_101_9m} / ${D.market.cap.outstanding_67_8m} млрд`;
  const post = D.fv.posterior;
  $("fv-mean").textContent = fmt(post.mean);
  $("fv-band").textContent = `p05 ${fmt(post.p05)} · p25 ${fmt(post.p25)} · p50 ${fmt(post.p50)} · p75 ${fmt(post.p75)} · p95 ${fmt(post.p95)}`;
  $("pfv").textContent = (post.p_fv_gt_p * 100).toFixed(1) + "%";
  const irr2 = Math.sqrt(post.mean / P) - 1;
  const levGate = false, codGate = true; // leverage 2.9x flat (blocks); cod 17.1->16.0
  const gates = [`E[IRR(2y)] ${(irr2 * 100).toFixed(0)}% ${irr2 >= .25 ? "✓" : "✗"}`, `P(FV>P) ${(post.p_fv_gt_p * 100).toFixed(0)}% ${post.p_fv_gt_p >= .5 ? "✓" : "✗"}`, `leverage ✗ (2.9x flat)`, `cod ✓ (↓)`];
  $("verdict").textContent = (irr2 >= .25 && post.p_fv_gt_p >= .5 && codGate && !levGate) ? "WAIT" : "WAIT";
  $("verdict").textContent = "WAIT";
  $("gates").textContent = gates.join(" · ");
  $("robust").textContent = "Bear-приоры → 1611, mult −0.5 → 1802, долг +60 → 1834, joint bear → 139. Цена внутри жирной середины (p05 30 / p95 7525): неопределенность, не дешевизна.";
  // FV chart: quantile band + price
  const svg = $("fvchart"), lo = 0, hi = Math.max(post.p95, P) * 1.05, X = v => 40 + (v - lo) / (hi - lo) * 570;
  svg.appendChild(el("rect", { x: X(post.p05), y: 60, width: Math.max(2, X(post.p95) - X(post.p05)), height: 34, fill: "#2a3a55" }));
  svg.appendChild(el("rect", { x: X(post.p25), y: 60, width: Math.max(2, X(post.p75) - X(post.p25)), height: 34, fill: "#4da3ff88" }));
  [[post.p50, "#fff", 3]].forEach(([v, c, w]) => svg.appendChild(el("line", { x1: X(v), y1: 52, x2: X(v), y2: 102, stroke: c, "stroke-width": w })));
  const pl = el("line", { x1: X(P), y1: 30, x2: X(P), y2: 120, stroke: "#ffb84d", "stroke-width": 2, "stroke-dasharray": "5,3" });
  svg.appendChild(pl);
  const t = (x, y, s, c = "#8b98ab", sz = 11) => { const e = el("text", { x, y, fill: c, "font-size": sz }); e.textContent = s; svg.appendChild(e); };
  t(X(post.p05), 130, "p05 " + fmt(post.p05)); t(X(post.p95) - 60, 130, "p95 " + fmt(post.p95));
  t(X(post.p50) - 20, 44, "p50 " + fmt(post.p50), "#fff"); t(Math.min(X(P) + 6, 560), 24, "цена " + fmt(P), "#ffb84d");
  // nowcast
  const nc = D.nowcast || {};
  $("nc").textContent = nc.nowcast != null ? nc.nowcast + "%" : "—";
  $("nc-detail").textContent = `${nc.target || ""} · еда ${nc.food_q3_yoy}% + ${nc.x5_src || ""}. ${nc.read || ""}`;
  $("nc-warn").textContent = (nc.warnings || []).join(" | ");
  // LFL chart
  lineChart($("lflchart"), D.series.lfl, [
    { s: "sales", c: "#4da3ff", w: 2.5 }, { s: "ticket", c: "#3fce7a", w: 1.5 }, { s: "traffic", c: "#ffb84d", w: 1.5 }], v => v);
  // revenue chart: magnit vs x5
  const mg = D.series.revenue_yoy.filter(r => /Q|H|FY|9M/.test(r.p));
  lineChart($("revchart"), mg.map(r => ({ p: r.p, v: r.v })), [{ s: null, c: "#4da3ff", w: 2.5 }], v => v, "Магнит, % г/г");
  // margins
  lineChart($("mgnchart"), D.series.margins_pre16.filter(r => /FY/.test(r.p)).flatMap(r => [{ p: r.p + "/" + r.s.slice(0, 4), v: r.v }]), [{ s: null, c: "#3fce7a", w: 2 }], v => v, "маржа pre16, %");
  $("credit").textContent = `Чистый долг pre16 ${(D.credit.net_debt_pre16 || {}).h1_2026} млрд · кэш/короткий ${(D.credit.liquidity || {}).cash_to_short}x · неиспользованные линии ${(D.credit.liquidity || {}).undrawn_lines} млрд · ковенанты соблюдены · риск = carry, не solvency.`;
  // skill table
  const sk = D.skill.origins || [];
  let h = `<table><tr><th>origin</th><th>fact</th><th>pred</th><th>err</th><th>X5</th></tr>`;
  sk.slice(-10).forEach(r => { h += `<tr><td>${r.period}</td><td>${r.act}%</td><td>${r.pred}%</td><td class="${r.err >= 0 ? "pos" : "neg"}">${r.err > 0 ? "+" : ""}${r.err}</td><td>${r.x5}%</td></tr>`; });
  h += `</table><p class="note">MAE ${D.skill.mae_pp}pp vs naive-X5 ${D.skill.naive_x5_mae_pp}pp · direction ${D.skill.direction} · bias ${D.skill.bias_pp}pp</p>`;
  $("skill").innerHTML = h;
  // consensus
  $("consensus").innerHTML = `<div class="cons">${(D.market.consensus || []).map(c => `<div><b>${c.company || "?"}</b> ${c.rec || ""}<br>target ${c.target ? (c.target.units || "") + " " + (c.target.nanos || "") : "—"}</div>`).join("")}</div>`;
  $("fresh").textContent = `registry ${D.meta.registry_rows} rows (${Object.entries(D.meta.status_mix).map(([k, v]) => k + ":" + v).join(", ")}) · engine ${D.meta.engine} · ${D.meta.sources}`;
}).catch(e => { document.body.insertAdjacentHTML("afterbegin", `<p style="color:red">data load failed: ${e}</p>`); });

function lineChart(svg, pts, series, fmtv, title) {
  // pts: [{p, s?, v}] — group by s (or single)
  const groups = {};
  pts.forEach(r => { const k = r.s || "_"; (groups[k] = groups[k] || []).push(r); });
  const all = pts.map(r => r.v).filter(v => v != null);
  if (!all.length) return;
  let lo = Math.min(...all), hi = Math.max(...all);
  if (lo > 0) lo = 0; if (hi < 0) hi = 0;
  const pad = (hi - lo) * 0.1 || 1; lo -= pad; hi += pad;
  const W = 640, H = +svg.getAttribute("viewBox").split(" ")[3];
  const X = i => 50 + i / Math.max(1, Object.values(groups)[0].length - 1) * 560;
  const Y = v => 14 + (1 - (v - lo) / (hi - lo)) * (H - 44);
  const zero = el("line", { x1: 44, y1: Y(0), x2: 624, y2: Y(0), stroke: "#3a4a63" }); svg.appendChild(zero);
  const order = Object.keys(groups);
  order.forEach(k => {
    const g = groups[k];
    const spec = series.find(s => s.s === k) || series[0];
    let d = "";
    g.forEach((r, i) => { d += (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(r.v).toFixed(1) + " "; });
    svg.appendChild(el("path", { d, fill: "none", stroke: spec.c, "stroke-width": spec.w }));
    const last = g[g.length - 1];
    const tx = el("text", { x: 626, y: Y(last.v), fill: spec.c, "font-size": 10, "text-anchor": "end" }); tx.textContent = k === "_" ? (title || "") : k; svg.appendChild(tx);
  });
  const n = Object.values(groups)[0].length;
  for (let i = 0; i < n; i += Math.ceil(n / 8)) {
    const tx = el("text", { x: X(i), y: H - 6, fill: "#8b98ab", "font-size": 10 }); tx.textContent = Object.values(groups)[0][i].p; svg.appendChild(tx);
  }
}
