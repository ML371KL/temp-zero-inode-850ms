// Headless render test: stubs DOM, runs web/app.js logic against real data.json,
// asserts key outputs. Run: node 다르test/headless.js
const fs = require("fs");
const path = require("path");
const WEB = path.join(__dirname, "..", "web");
const store = {};
function mkEl() {
  return {
    children: [], _text: "", _html: "",
    setAttribute() {}, appendChild(c) { this.children.push(c); return c; },
    set textContent(v) { this._text = String(v); }, get textContent() { return this._text; },
    set innerHTML(v) { this._html = String(v); }, get innerHTML() { return this._html; },
    classList: { toggle() {} }, set onclick(f) { this._click = f; },
    getAttribute() { return "0 0 640 200"; },
  };
}
global.document = { getElementById: id => (store[id] ||= mkEl()), createElementNS: () => mkEl(),
  body: Object.assign(mkEl(), { insertAdjacentHTML(p, h) { this._err = h; } }) };
global.fetch = () => Promise.resolve({ ok: true, json: () => JSON.parse(fs.readFileSync(path.join(WEB, "data", "data.json"), "utf8")) });
let src = fs.readFileSync(path.join(WEB, "app.js"), "utf8");
eval(src);
setTimeout(() => {
  const need = { price: v => { const n = +v.replace(/[^0-9]/g, ""); return n > 1500 && n < 1700; },
    "fv-mean": v => { const n = +v.replace(/[^0-9]/g, ""); return n > 1400 && n < 1600; },
    pfv: v => { const n = parseFloat(v); return n > 45 && n < 52; },
    verdict: "WAIT", nc: v => /^~-?\d+%$/.test(v.trim()) };
  let fail = 0;
  for (const [id, exp] of Object.entries(need)) {
    const got = store[id] ? store[id]._text : "<missing>";
    const ok = typeof exp === "function" ? exp(got) : got === exp;
    console.log((ok ? "PASS" : "FAIL") + ` #${id} = ${JSON.stringify(got).slice(0, 80)}`);
    if (!ok) fail++;
  }
  for (const id of ["fvchart", "lflchart", "revchart", "mgnchart"]) {
    const n = store[id] ? store[id].children.length : 0;
    const ok = n > 5;
    console.log((ok ? "PASS" : "FAIL") + ` #${id} children=${n}`);
    if (!ok) fail++;
  }
  for (const id of ["fv-legend", "lfl-legend", "rev-legend", "mgn-legend", "skill", "consensus"]) {
    const n = (store[id] ? store[id]._html : "").length;
    const ok = n > 20;
    console.log((ok ? "PASS" : "FAIL") + ` #${id} html=${n}chars`);
    if (!ok) fail++;
  }
  // basis toggle simulation
  store["b-iss"]._click();
  const out = store["fv-mean"]._text;
  console.log((+out.replace(/[^0-9]/g, "") > 900 && +out.replace(/[^0-9]/g, "") < 1100 ? "PASS" : "FAIL") + ` toggle issued fv-mean=${out}`);
  if (!(+out.replace(/[^0-9]/g, "") > 900 && +out.replace(/[^0-9]/g, "") < 1100)) fail++;
  process.exit(fail ? 1 : 0);
}, 100);

// patched