const PACK_KEY = "eco-ai-pack";

const state = {
  metric: "co2",
  pack: null,
  packs: [],
  settings: null,
  file: null,
  dateBounds: { min: null, max: null },
};

const $ = (id) => document.getElementById(id);

function showError(msg) {
  const el = $("error");
  if (!msg) {
    el.hidden = true;
    el.textContent = "";
    return;
  }
  el.hidden = false;
  el.textContent = msg;
}

function rememberedPack() {
  try {
    return localStorage.getItem(PACK_KEY);
  } catch {
    return null;
  }
}

function rememberPack(pack) {
  try {
    localStorage.setItem(PACK_KEY, pack);
  } catch {
    /* ignore quota / private mode */
  }
}

function fillPackSelects() {
  for (const id of ["pack", "pack-params"]) {
    const sel = $(id);
    const current = sel.value;
    sel.innerHTML = "";
    for (const pack of state.packs) {
      const opt = document.createElement("option");
      opt.value = pack;
      opt.textContent = pack;
      sel.appendChild(opt);
    }
    sel.value = state.pack && state.packs.includes(state.pack)
      ? state.pack
      : current && state.packs.includes(current)
        ? current
        : state.packs[0] || "";
  }
}

async function loadSettings(pack) {
  const wanted = pack || rememberedPack() || "";
  const url = wanted ? `/api/settings?pack=${encodeURIComponent(wanted)}` : "/api/settings";
  let res = await fetch(url);
  let body = await res.json();
  if (!res.ok && wanted) {
    res = await fetch("/api/settings");
    body = await res.json();
  }
  if (!res.ok) {
    showError(typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail));
    return;
  }
  state.pack = body.pack;
  state.packs = body.packs;
  state.settings = body.settings;
  rememberPack(state.pack);
  fillPackSelects();
  renderModelPicks();
  renderSettingsEditor();
}

function renderModelPicks() {
  const box = $("model-picks");
  box.innerHTML = "";
  if (!state.settings) return;
  for (const model of state.settings.models) {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = true;
    cb.value = model.id;
    cb.addEventListener("change", () => {
      if (state.file) analyze();
    });
    label.append(cb, document.createTextNode(" " + model.id));
    box.appendChild(label);
  }
}

function selectedModelIds() {
  return [...document.querySelectorAll("#model-picks input:checked")].map((el) => el.value);
}

function providerCard(p, index) {
  return card(
    [
      field("id", p.id, index, "providers"),
      field("name", p.name, index, "providers"),
      field("mu_L_per_kWh", p.mu_L_per_kWh, index, "providers", "number"),
      field("sigma_L_per_kWh", p.sigma_L_per_kWh, index, "providers", "number"),
      field("mu_kg_per_kWh", p.mu_kg_per_kWh, index, "providers", "number"),
      field("sigma_kg_per_kWh", p.sigma_kg_per_kWh, index, "providers", "number"),
    ],
    () => {
      state.settings.providers.splice(index, 1);
      renderSettingsEditor();
    }
  );
}

function modelCard(m, index) {
  return card(
    [
      field("id", m.id, index, "models"),
      field("provider_id", m.provider_id, index, "models"),
      field("match_prefixes", (m.match_prefixes || []).join(", "), index, "models"),
      field("input", m.input, index, "models", "number"),
      field("output", m.output, index, "models", "number"),
      field("cache_read", m.cache_read, index, "models", "number"),
      field("cache_write", m.cache_write, index, "models", "number"),
      field("mu_kWh_per_usd", m.mu_kWh_per_usd, index, "models", "number"),
      field("sigma_kWh_per_usd", m.sigma_kWh_per_usd, index, "models", "number"),
    ],
    () => {
      state.settings.models.splice(index, 1);
      renderSettingsEditor();
      renderModelPicks();
    }
  );
}

function field(name, value, index, kind, type = "text") {
  const wrap = document.createElement("label");
  wrap.textContent = name;
  const input = document.createElement("input");
  input.type = type === "number" ? "number" : "text";
  if (type === "number") {
    input.step = "any";
  }
  input.value = value ?? "";
  input.dataset.kind = kind;
  input.dataset.index = String(index);
  input.dataset.field = name;
  wrap.appendChild(input);
  return wrap;
}

function card(fields, onDelete) {
  const div = document.createElement("div");
  div.className = "card";
  for (const f of fields) div.appendChild(f);
  const del = document.createElement("button");
  del.type = "button";
  del.textContent = "Supprimer";
  del.className = "span";
  del.addEventListener("click", onDelete);
  div.appendChild(del);
  return div;
}

function readEditor() {
  const settings = { providers: [], models: [] };
  for (const input of document.querySelectorAll("#providers input, #models input")) {
    const kind = input.dataset.kind;
    const i = Number(input.dataset.index);
    const fieldName = input.dataset.field;
    if (!settings[kind][i]) settings[kind][i] = {};
    let value = input.value;
    if (fieldName === "match_prefixes") {
      value = value.split(",").map((s) => s.trim()).filter(Boolean);
    } else if (input.type === "number") {
      value = value === "" ? 0 : Number(value);
    }
    settings[kind][i][fieldName] = value;
  }
  settings.providers = settings.providers.filter(Boolean);
  settings.models = settings.models.filter(Boolean);
  return settings;
}

function renderSettingsEditor() {
  const pBox = $("providers");
  const mBox = $("models");
  pBox.innerHTML = "";
  mBox.innerHTML = "";
  state.settings.providers.forEach((p, i) => pBox.appendChild(providerCard(p, i)));
  state.settings.models.forEach((m, i) => mBox.appendChild(modelCard(m, i)));
}

async function saveSettings() {
  const payload = readEditor();
  const res = await fetch(`/api/settings?pack=${encodeURIComponent(state.pack)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.json();
  if (!res.ok) {
    $("save-status").textContent = body.detail ? JSON.stringify(body.detail) : "Erreur";
    return;
  }
  state.pack = body.pack;
  state.packs = body.packs;
  state.settings = body.settings;
  $("save-status").textContent = "Enregistré.";
  fillPackSelects();
  renderModelPicks();
  renderSettingsEditor();
  if (state.file) analyze();
}

function isoDateValue(id) {
  const value = $(id).value.trim();
  if (!value) return "";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  return value;
}

async function analyze() {
  if (!state.file) return;
  showError("");
  const from = isoDateValue("date-from");
  const to = isoDateValue("date-to");
  if (from === null || to === null) {
    showError("Date invalide : utilisez le sélecteur (AAAA-MM-JJ).");
    return;
  }
  const fd = new FormData();
  fd.append("file", state.file);
  fd.append("metric", state.metric);
  if (from) fd.append("date_from", from);
  if (to) fd.append("date_to", to);
  fd.append("model_ids", selectedModelIds().join(","));
  if (state.pack) fd.append("pack", state.pack);
  const res = await fetch("/api/analyze", { method: "POST", body: fd });
  const data = await res.json();
  if (!res.ok) {
    showError(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
    Plotly.purge("chart");
    $("coverage").textContent = "";
    $("omitted").innerHTML = "";
    $("quartiles").textContent = "";
    renderComparison(null);
    return;
  }
  if (data.date_min && !$("date-from").value) $("date-from").value = data.date_min;
  if (data.date_max && !$("date-to").value) $("date-to").value = data.date_max;
  $("coverage").textContent = `Tokens comptabilisés dans l'analyse : ${formatSig2(data.coverage_pct)}%`;
  const ul = $("omitted");
  ul.innerHTML = "";
  for (const item of data.omitted) {
    const li = document.createElement("li");
    li.textContent = `${item.model} — ${formatSig2(item.tokens)} tokens (sans paramètre)`;
    ul.appendChild(li);
  }
  const q = data.quartiles;
  $("quartiles").textContent =
    `Q1 ${formatSig2(q.q1)} · médiane ${formatSig2(q.median)} · Q3 ${formatSig2(q.q3)} ${data.unit}` +
    ` · coût configuré ${formatSig2(data.total_cost_usd)} $ · ${formatSig2(data.n_draws)} tirages`;
  renderComparison(data.comparison, data.pack);
  drawChart(data);
}

function formatSig2(value) {
  if (!Number.isFinite(value)) return "—";
  if (value === 0) return "0";
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  const exp = Math.floor(Math.log10(abs));
  const scale = 10 ** (exp - 1);
  let rounded = Math.round(abs / scale) * scale;
  if (rounded === 0) return "0";
  const exp2 = Math.floor(Math.log10(rounded));
  const decimals = Math.max(0, 1 - exp2);
  const factor = 10 ** decimals;
  rounded = Math.round(rounded * factor) / factor;
  return sign + rounded.toLocaleString("fr-FR", {
    maximumFractionDigits: decimals,
    minimumFractionDigits: 0,
  });
}

function renderComparison(rows, selectedPack) {
  const panel = $("compare-panel");
  const tbody = document.querySelector("#compare-table tbody");
  tbody.innerHTML = "";
  if (!rows || !rows.length) {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  for (const row of rows) {
    const tr = document.createElement("tr");
    if (row.pack === selectedPack) tr.className = "selected";
    const cells = [
      row.pack,
      formatSig2(row.co2.q1),
      formatSig2(row.co2.median),
      formatSig2(row.co2.q3),
      formatSig2(row.water.q1),
      formatSig2(row.water.median),
      formatSig2(row.water.q3),
    ];
    cells.forEach((text, i) => {
      const td = document.createElement(i === 0 ? "th" : "td");
      td.textContent = text;
      if (i === 0) td.scope = "row";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  }
}

function drawChart(data) {
  const cdf = {
    x: data.cdf.x,
    y: data.cdf.y,
    name: "CDF empirique",
    mode: "lines",
    line: { color: "#7ee0c2", width: 2 },
  };
  const gauss = {
    x: data.gaussian_overlay.x,
    y: data.gaussian_overlay.y,
    name: "Gaussienne (mêmes moments)",
    mode: "lines",
    line: { color: "#9aa3af", width: 1, dash: "dot" },
  };
  const shapes = ["q1", "median", "q3"].map((k, i) => ({
    type: "line",
    x0: data.quartiles[k],
    x1: data.quartiles[k],
    y0: 0,
    y1: 1,
    line: { color: ["#5b8def", "#e8eaed", "#5b8def"][i], width: i === 1 ? 1.5 : 1, dash: i === 1 ? "solid" : "dash" },
  }));
  Plotly.purge("chart");
  Plotly.newPlot(
    "chart",
    [cdf, gauss],
    {
      paper_bgcolor: "#0e1116",
      plot_bgcolor: "#0e1116",
      font: { color: "#e8eaed" },
      margin: { t: 24, r: 16, b: 48, l: 48 },
      xaxis: { title: data.unit, gridcolor: "#2a3140", hoverformat: ".2r", tickformat: ".2r" },
      yaxis: { title: "P(F ≤ x)", range: [0, 1], gridcolor: "#2a3140", hoverformat: ".2r" },
      legend: { orientation: "h" },
      shapes,
      annotations: [
        { x: data.quartiles.q1, y: 1, text: "Q1", showarrow: false, yanchor: "bottom", font: { size: 11 } },
        { x: data.quartiles.median, y: 1, text: "médiane", showarrow: false, yanchor: "bottom", font: { size: 11 } },
        { x: data.quartiles.q3, y: 1, text: "Q3", showarrow: false, yanchor: "bottom", font: { size: 11 } },
      ],
    },
    { displayModeBar: false, responsive: true }
  );
}

$("csv").addEventListener("change", (ev) => {
  state.file = ev.target.files[0] || null;
  $("run").disabled = !state.file;
  $("date-from").value = "";
  $("date-to").value = "";
  if (state.file) analyze();
});

$("run").addEventListener("click", analyze);
$("date-from").addEventListener("change", () => state.file && analyze());
$("date-to").addEventListener("change", () => state.file && analyze());

async function onPackChange(ev) {
  const pack = ev.target.value;
  if (!pack || pack === state.pack) return;
  $("save-status").textContent = "";
  await loadSettings(pack);
  if (state.file) analyze();
}

$("pack").addEventListener("change", onPackChange);
$("pack-params").addEventListener("change", onPackChange);

for (const btn of document.querySelectorAll(".toggle button")) {
  btn.addEventListener("click", () => {
    state.metric = btn.dataset.metric;
    document.querySelectorAll(".toggle button").forEach((b) => b.classList.toggle("active", b === btn));
    if (state.file) analyze();
  });
}

$("add-provider").addEventListener("click", () => {
  state.settings.providers.push({
    id: "nouveau",
    name: "Nouveau",
    mu_L_per_kWh: 1.8,
    sigma_L_per_kWh: 1,
    mu_kg_per_kWh: 0.3,
    sigma_kg_per_kWh: 0.15,
  });
  renderSettingsEditor();
});

$("add-model").addEventListener("click", () => {
  const pid = state.settings.providers[0]?.id || "spacexai";
  state.settings.models.push({
    id: "nouveau-modele",
    provider_id: pid,
    match_prefixes: ["nouveau-modele"],
    input: 1e-6,
    output: 3e-6,
    cache_read: 1e-7,
    cache_write: 1.25e-6,
    mu_kWh_per_usd: 0.12,
    sigma_kWh_per_usd: 0.08,
  });
  renderSettingsEditor();
  renderModelPicks();
});

$("save-settings").addEventListener("click", saveSettings);

loadSettings().catch((err) => showError(String(err)));
