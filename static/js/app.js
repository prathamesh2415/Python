/* Buffett Terminal — frontend */

const API = "";

const state = {
  view: "market",
  screenRows: [],
  screenSort: { key: "score", dir: -1 },
  lastAnalysis: null,
};

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

function fmtNum(v, digits = 2) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  const abs = Math.abs(n);
  if (abs >= 1e12) return `${(n / 1e12).toFixed(digits)}T`;
  if (abs >= 1e9) return `${(n / 1e9).toFixed(digits)}B`;
  if (abs >= 1e6) return `${(n / 1e6).toFixed(digits)}M`;
  return n.toFixed(digits);
}

function fmtPct(v, digits = 1, alreadyPct = false) {
  if (v == null || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  const pct = alreadyPct ? n : Math.abs(n) <= 5 ? n * 100 : n;
  return `${pct.toFixed(digits)}%`;
}

function fmtPrice(v, currency) {
  if (v == null) return "—";
  const prefix = currency === "INR" ? "₹" : currency === "USD" ? "$" : "";
  return `${prefix}${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function chgClass(v) {
  if (v == null) return "";
  return v >= 0 ? "up" : "down";
}

function scoreClass(score) {
  if (score >= 70) return "";
  if (score >= 50) return "mid";
  return "low";
}

function zoneClass(zone) {
  if (!zone) return "";
  if (zone.includes("SIGNIFICANTLY OVER")) return "hot";
  if (zone.includes("MODESTLY OVER") || zone.includes("FAIR")) return "warn";
  return "";
}

async function api(path, opts) {
  const res = await fetch(`${API}${path}`, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function setView(name) {
  state.view = name;
  $$(".nav button").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
}

function tickClock() {
  const el = $("#clock");
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }) + " IST";
}

function renderIndexTiles(container, rows) {
  if (!rows?.length) {
    container.innerHTML = `<div class="empty">No index data</div>`;
    return;
  }
  container.innerHTML = rows
    .map(
      (r) => `
    <div class="index-tile">
      <div class="label">${r.label || r.symbol}</div>
      <div class="price">${r.price != null ? Number(r.price).toLocaleString(undefined, { maximumFractionDigits: 2 }) : "—"}</div>
      <div class="chg ${chgClass(r.changePct)}">${
        r.changePct == null ? "—" : `${r.changePct >= 0 ? "+" : ""}${r.changePct.toFixed(2)}%`
      }</div>
    </div>`
    )
    .join("");
}

async function loadMarket() {
  const status = $("#market-status");
  status.textContent = "▶ fetching indices & Buffett Indicator…";
  status.className = "status-line loading";
  try {
    const [indices, bi] = await Promise.all([
      api("/api/indices"),
      api("/api/buffett-indicator"),
    ]);
    renderIndexTiles($("#us-indices"), indices.us);
    renderIndexTiles($("#india-indices"), indices.india);
    renderBuffettIndicator(bi);
    status.textContent = `● market pulse updated · ${bi.asOf || ""}`;
    status.className = "status-line";
  } catch (err) {
    status.textContent = "";
    $("#market-error").innerHTML = `<div class="error">${err.message}</div>`;
  }
}

function renderBuffettIndicator(bi) {
  const root = $("#bi-root");
  const mk = (side, title) => {
    const d = bi[side];
    return `
      <div class="bi-card">
        <h3>${title}</h3>
        <div class="bi-ratio">${d.ratioPct != null ? d.ratioPct.toFixed(0) + "%" : "—"}</div>
        <div class="bi-zone ${zoneClass(d.zone)}">${d.zone || "N/A"}</div>
        <div class="bi-meta">
          <div>Market Cap ≈ ${fmtNum(d.marketCap)}</div>
          <div>GDP ≈ ${fmtNum(d.gdp)}</div>
          <div>Ratio ${d.ratio != null ? d.ratio.toFixed(2) : "—"}×</div>
          <div style="margin-top:6px;color:var(--text-mute)">${d.source || ""}</div>
        </div>
      </div>`;
  };
  root.innerHTML = mk("us", "United States") + mk("india", "India");
  $("#bi-method").textContent = bi.methodology || "";
}

async function loadScreen() {
  const market = $("#screen-market").value;
  const status = $("#screen-status");
  status.textContent = "▶ running Buffett screen across universe…";
  status.className = "status-line loading";
  $("#screen-error").innerHTML = "";
  try {
    const data = await api(`/api/screen?market=${encodeURIComponent(market)}&limit=50`);
    state.screenRows = data.results || [];
    sortAndRenderScreen();
    status.textContent = `● ${state.screenRows.length} names scored · sorted by Buffett score`;
    status.className = "status-line";
  } catch (err) {
    status.textContent = "";
    $("#screen-error").innerHTML = `<div class="error">${err.message}</div>`;
  }
}

function sortAndRenderScreen() {
  const { key, dir } = state.screenSort;
  const rows = [...state.screenRows].sort((a, b) => {
    const av = a[key];
    const bv = b[key];
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (typeof av === "string") return av.localeCompare(bv) * dir;
    return (av - bv) * dir;
  });
  const tbody = $("#screen-body");
  if (!rows.length) {
    tbody.innerHTML = `<tr><td colspan="10" class="empty">No results — run screen</td></tr>`;
    return;
  }
  tbody.innerHTML = rows
    .map((r) => {
      const mos = r.marginOfSafetyPct;
      return `<tr data-symbol="${r.symbol}">
        <td><span class="score-pill ${scoreClass(r.score)}">${r.score?.toFixed?.(1) ?? "—"}</span></td>
        <td class="grade">${r.grade || "—"}</td>
        <td>${r.symbol}</td>
        <td>${r.name || "—"}</td>
        <td>${r.market}</td>
        <td>${fmtPrice(r.price, r.currency)}</td>
        <td>${fmtPct(r.roe)}</td>
        <td>${r.debtToEquity != null ? Number(r.debtToEquity).toFixed(2) : "—"}</td>
        <td>${r.pe != null ? Number(r.pe).toFixed(1) : "—"}</td>
        <td style="color:${mos != null && mos >= 0 ? "var(--green)" : "var(--red)"}">${
          mos != null ? `${mos >= 0 ? "+" : ""}${mos.toFixed(1)}%` : "—"
        }</td>
      </tr>`;
    })
    .join("");

  tbody.querySelectorAll("tr[data-symbol]").forEach((tr) => {
    tr.addEventListener("click", () => {
      $("#symbol-input").value = tr.dataset.symbol;
      setView("analyze");
      runAnalyze(tr.dataset.symbol);
    });
  });
}

async function runAnalyze(symbolOverride) {
  const raw = symbolOverride || $("#symbol-input").value.trim();
  if (!raw) return;
    let market = $("#symbol-market").value || "auto";
  let symbol = raw;
  if (market === "india" && !symbol.includes(".") && !symbol.startsWith("^")) {
    symbol = `${symbol.replace(/\.NS$/i, "")}.NS`;
  }
  const status = $("#analyze-status");
  const root = $("#analyze-root");
  status.textContent = `▶ analyzing ${symbol}…`;
  status.className = "status-line loading";
  root.innerHTML = "";
  try {
    const q = market && market !== "auto" ? `?market=${encodeURIComponent(market)}` : "";
    const data = await api(`/api/analyze/${encodeURIComponent(symbol)}${q}`);
    state.lastAnalysis = data;
    renderAnalysis(data);
    status.textContent = `● scorecard ready · ${data.analysis?.symbol || raw}`;
    status.className = "status-line";
    setView("analyze");
  } catch (err) {
    status.textContent = "";
    root.innerHTML = `<div class="error">${err.message}</div>`;
  }
}

function renderAnalysis(data) {
  const a = data.analysis;
  const m = a.metrics || {};
  const root = $("#analyze-root");
  const mos = a.margin_of_safety_pct;

  const criteriaHtml = (a.criteria || [])
    .map(
      (c) => `
    <div class="criterion">
      <div>
        <div class="name">${c.label}</div>
      </div>
      <div>${c.display}</div>
      <span class="badge ${c.pass_fail}">${c.pass_fail}</span>
      <div class="note">${c.note} · score ${c.score}/10 · wt ${c.weight}</div>
    </div>`
    )
    .join("");

  const metrics = [
    ["ROE", fmtPct(m.roe)],
    ["ROA", fmtPct(m.roa)],
    ["Net Margin", fmtPct(m.profitMargin)],
    ["Op. Margin", fmtPct(m.operatingMargin)],
    ["D/E", m.debtToEquity != null ? Number(m.debtToEquity).toFixed(2) : "—"],
    ["Current Ratio", m.currentRatio != null ? Number(m.currentRatio).toFixed(2) : "—"],
    ["P/E", m.pe != null ? Number(m.pe).toFixed(1) : "—"],
    ["P/B", m.pb != null ? Number(m.pb).toFixed(2) : "—"],
    ["EPS", m.eps != null ? Number(m.eps).toFixed(2) : "—"],
    ["FCF", fmtNum(m.freeCashflow)],
    ["Mkt Cap", fmtNum(m.marketCap)],
    ["Div Yield", fmtPct(m.dividendYield)],
    ["Beta", m.beta != null ? Number(m.beta).toFixed(2) : "—"],
    ["Sector", m.sector || "—"],
    ["Industry", m.industry || "—"],
    ["52W High", fmtPrice(m.fiftyTwoWeekHigh, a.currency)],
  ];

  root.innerHTML = `
    <div class="panel">
      <div class="analysis-head">
        <div class="score-hero">
          <div class="score-ring">
            <div style="text-align:center">
              <div class="num">${a.total_score?.toFixed?.(0) ?? "—"}</div>
              <div class="lbl">SCORE</div>
            </div>
          </div>
          <div class="meta-block">
            <div class="sym">${a.symbol} · ${a.market} · GRADE ${a.grade}</div>
            <h2>${a.name}</h2>
            <div style="color:var(--text-dim)">Last ${fmtPrice(a.price, a.currency)}</div>
            <div class="verdict">${a.verdict}</div>
          </div>
        </div>
        <div class="valuation-box">
          <div class="panel-title" style="margin-bottom:10px;border:0;padding:0">Margin of Safety</div>
          <div class="row"><span>Intrinsic (blend)</span><span>${fmtPrice(a.intrinsic_value, a.currency)}</span></div>
          <div class="row"><span>Market Price</span><span>${fmtPrice(a.price, a.currency)}</span></div>
          <div class="row"><span>Margin of Safety</span><span style="color:${
            mos != null && mos >= 0 ? "var(--green)" : "var(--red)"
          }">${mos != null ? `${mos >= 0 ? "+" : ""}${mos.toFixed(1)}%` : "—"}</span></div>
          <p class="methodology" style="margin-top:10px">Intrinsic blends Graham number, growth-capped EPS multiple, and FCF capitalization — a sanity check, not a DCF model.</p>
        </div>
      </div>
    </div>

    <div class="panel">
      <h3 class="panel-title">Buffett Checklist <span class="hint">quality · balance sheet · owner earnings · valuation</span></h3>
      <div class="criteria-list">${criteriaHtml}</div>
    </div>

    <div class="panel">
      <h3 class="panel-title">Fundamentals Snapshot</h3>
      <div class="metrics-grid">
        ${metrics
          .map(
            ([k, v]) => `<div class="metric"><div class="k">${k}</div><div class="v">${v}</div></div>`
          )
          .join("")}
      </div>
    </div>

    <div class="panel">
      <h3 class="panel-title">Price History · 1Y</h3>
      <div class="chart-wrap"><canvas id="price-chart" width="900" height="160"></canvas></div>
    </div>
  `;

  drawChart($("#price-chart"), data.history || []);
}

function drawChart(canvas, history) {
  if (!canvas || !history.length) return;
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const cssW = canvas.clientWidth || 900;
  const cssH = canvas.clientHeight || 160;
  canvas.width = cssW * dpr;
  canvas.height = cssH * dpr;
  ctx.scale(dpr, dpr);

  const prices = history.map((h) => h.close);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const pad = 8;
  const w = cssW - pad * 2;
  const h = cssH - pad * 2;

  ctx.clearRect(0, 0, cssW, cssH);
  ctx.strokeStyle = "rgba(110, 154, 124, 0.25)";
  ctx.beginPath();
  ctx.moveTo(pad, pad);
  ctx.lineTo(pad, pad + h);
  ctx.lineTo(pad + w, pad + h);
  ctx.stroke();

  const up = prices[prices.length - 1] >= prices[0];
  ctx.strokeStyle = up ? "#3dd68c" : "#e85d5d";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  prices.forEach((p, i) => {
    const x = pad + (i / (prices.length - 1 || 1)) * w;
    const y = pad + h - ((p - min) / (max - min || 1)) * h;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // fill
  ctx.lineTo(pad + w, pad + h);
  ctx.lineTo(pad, pad + h);
  ctx.closePath();
  ctx.fillStyle = up ? "rgba(61,214,140,0.08)" : "rgba(232,93,93,0.08)";
  ctx.fill();
}

function wireEvents() {
  $$(".nav button").forEach((btn) => {
    btn.addEventListener("click", () => {
      setView(btn.dataset.view);
      if (btn.dataset.view === "market" && !$("#us-indices").children.length) loadMarket();
      if (btn.dataset.view === "screen" && !state.screenRows.length) loadScreen();
    });
  });

  $("#btn-analyze").addEventListener("click", () => runAnalyze());
  $("#symbol-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") runAnalyze();
  });
  $("#btn-refresh-market").addEventListener("click", loadMarket);
  $("#btn-run-screen").addEventListener("click", loadScreen);

  $$("table.screen th[data-sort]").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (state.screenSort.key === key) state.screenSort.dir *= -1;
      else state.screenSort = { key, dir: key === "score" ? -1 : 1 };
      sortAndRenderScreen();
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  tickClock();
  setInterval(tickClock, 1000);
  wireEvents();
  setView("market");
  loadMarket();
});
