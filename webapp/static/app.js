const API = "";

// ---------- nav ----------
document.querySelectorAll(".nav-item").forEach(el => {
  el.addEventListener("click", () => showView(el.dataset.view));
});

function showView(name) {
  document.querySelectorAll(".nav-item").forEach(el =>
    el.classList.toggle("active", el.dataset.view === name));
  document.querySelectorAll(".view").forEach(el =>
    el.classList.toggle("active", el.id === `view-${name}`));
  if (name === "history") loadHistory();
  if (name === "settings") loadSettings();
  if (name === "feed" || name === "run") loadFeedsAndTrends();
}

// ---------- helpers ----------
async function api(path, opts) {
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return res.json();
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// ---------- Dashboard ----------
async function loadStatus() {
  const s = await api("/api/status");
  const grid = document.getElementById("status-grid");
  const badge = v => `<span class="badge ${v}">${v}</span>`;
  grid.innerHTML = `
    <div class="card"><div class="stat-label">Claude</div><div class="stat-value">${badge(s.claude)}</div></div>
    <div class="card"><div class="stat-label">Image gen (Pollinations)</div><div class="stat-value">${badge(s.image_gen)}</div></div>
    <div class="card"><div class="stat-label">Pinterest</div><div class="stat-value">${badge(s.pinterest)}</div></div>
  `;
  const mini = document.getElementById("status-mini");
  mini.innerHTML = `
    <div class="row"><span>claude</span>${badge(s.claude)}</div>
    <div class="row"><span>images</span>${badge(s.image_gen)}</div>
    <div class="row"><span>pinterest</span>${badge(s.pinterest)}</div>
  `;
  return s;
}

// ---------- Trends ----------
let trendsCache = [];

function trendCardHtml(t, i) {
  return `
  <div class="trend-card" data-idx="${i}">
    <div class="trend-card-head">
      <strong>${escapeHtml(t.category) || "(нова категорія)"}</strong>
      <button class="small remove-trend" data-idx="${i}">Видалити</button>
    </div>
    <label>Category</label>
    <input type="text" class="t-category" value="${escapeHtml(t.category)}">
    <div class="row2">
      <div>
        <label>Keywords (через кому)</label>
        <input type="text" class="t-keywords" value="${escapeHtml((t.keywords||[]).join(', '))}">
      </div>
      <div>
        <label>Audience</label>
        <input type="text" class="t-audience" value="${escapeHtml(t.audience)}">
      </div>
    </div>
    <label>Aesthetic</label>
    <input type="text" class="t-aesthetic" value="${escapeHtml(t.aesthetic)}">
    <div class="row2">
      <div>
        <label>Surfaces (через кому)</label>
        <input type="text" class="t-surfaces" value="${escapeHtml((t.surfaces||[]).join(', '))}">
      </div>
      <div>
        <label>Lighting</label>
        <input type="text" class="t-lighting" value="${escapeHtml(t.lighting)}">
      </div>
    </div>
    <label>Background elements (через кому)</label>
    <input type="text" class="t-background" value="${escapeHtml((t.background_elements||[]).join(', '))}">
  </div>`;
}

function renderTrends() {
  const list = document.getElementById("trends-list");
  list.innerHTML = trendsCache.length
    ? trendsCache.map(trendCardHtml).join("")
    : '<div class="empty">Немає трендів. Додай перший.</div>';
  list.querySelectorAll(".remove-trend").forEach(btn => {
    btn.addEventListener("click", () => {
      trendsCache.splice(Number(btn.dataset.idx), 1);
      renderTrends();
    });
  });
}

function collectTrendsFromDom() {
  const cards = document.querySelectorAll(".trend-card");
  return Array.from(cards).map(card => ({
    category: card.querySelector(".t-category").value.trim(),
    keywords: card.querySelector(".t-keywords").value.split(",").map(s => s.trim()).filter(Boolean),
    aesthetic: card.querySelector(".t-aesthetic").value.trim(),
    surfaces: card.querySelector(".t-surfaces").value.split(",").map(s => s.trim()).filter(Boolean),
    lighting: card.querySelector(".t-lighting").value.trim(),
    background_elements: card.querySelector(".t-background").value.split(",").map(s => s.trim()).filter(Boolean),
    audience: card.querySelector(".t-audience").value.trim(),
  }));
}

async function loadTrends() {
  const data = await api("/api/trends");
  trendsCache = data.trends;
  renderTrends();
}

document.getElementById("add-trend").addEventListener("click", () => {
  trendsCache.push({
    category: "", keywords: [], aesthetic: "", surfaces: [],
    lighting: "", background_elements: [], audience: "",
  });
  renderTrends();
});

document.getElementById("save-trends").addEventListener("click", async () => {
  const status = document.getElementById("trends-save-status");
  try {
    trendsCache = collectTrendsFromDom();
    const res = await api("/api/trends", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trends: trendsCache }),
    });
    status.textContent = `Збережено ${res.count} трендів о ${new Date().toLocaleTimeString()}`;
    await populateTrendSelectors();
  } catch (e) {
    status.textContent = "Помилка: " + e.message;
  }
});

// ---------- Feed + Run shared selectors ----------
async function populateFeedSelectors() {
  const data = await api("/api/feed/list");
  const opts = data.feeds.map(f => `<option value="${escapeHtml(f)}">${escapeHtml(f)}</option>`).join("");
  document.getElementById("feed-select").innerHTML = opts;
  document.getElementById("run-feed-select").innerHTML = opts;
}

async function populateTrendSelectors() {
  const data = await api("/api/trends");
  const opts = data.trends.map(t =>
    `<option value="${escapeHtml(t.category)}">${escapeHtml(t.category)}</option>`).join("");
  document.getElementById("feed-trend-select").innerHTML = opts;
  document.getElementById("run-trend-select").innerHTML = opts;
}

async function loadFeedsAndTrends() {
  await Promise.all([populateFeedSelectors(), populateTrendSelectors()]);
}

// ---------- Feed preview ----------
document.getElementById("upload-feed").addEventListener("click", async () => {
  const fileInput = document.getElementById("feed-file");
  const status = document.getElementById("upload-status");
  if (!fileInput.files.length) { status.textContent = "Обери файл спочатку."; return; }
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  try {
    const res = await fetch("/api/feed/upload", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    status.textContent = `Завантажено: ${data.row_count} рядків, колонки: ${data.columns.join(", ")}`;
    await populateFeedSelectors();
  } catch (e) {
    status.textContent = "Помилка: " + e.message;
  }
});

document.getElementById("preview-feed").addEventListener("click", async () => {
  const feed_path = document.getElementById("feed-select").value;
  const trend = document.getElementById("feed-trend-select").value;
  const limit = Number(document.getElementById("feed-limit").value);
  const box = document.getElementById("feed-results");
  box.innerHTML = "завантаження...";
  try {
    const data = await api("/api/feed/preview", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feed_path, trend, limit }),
    });
    if (!data.products.length) {
      box.innerHTML = '<div class="empty">Нічого не пройшло фільтри (ціна/sold/комісія в config.py) або все вже опубліковано.</div>';
      return;
    }
    box.innerHTML = `<table><thead><tr>
        <th>Product</th><th>Price</th><th>Sold</th><th>Comm %</th><th>Category</th>
      </tr></thead><tbody>${data.products.map(p => `
        <tr><td>${escapeHtml(p.title)}</td><td>$${Number(p.price).toFixed(2)}</td>
        <td>${Number(p.sold_count).toLocaleString()}</td><td>${p.commission_pct}%</td>
        <td>${escapeHtml(p.category)}</td></tr>`).join("")}
      </tbody></table>`;
  } catch (e) {
    box.innerHTML = `<div class="empty">Помилка: ${escapeHtml(e.message)}</div>`;
  }
});

// ---------- Run ----------
const TAG_CLASS = { SYSTEM: "SYSTEM", SCOUT: "SCOUT", FEED: "FEED", CLAUDE: "CLAUDE",
                   IMAGE: "IMAGE", UPLOAD: "UPLOAD", DB: "DB", WARN: "WARN", ERROR: "ERROR" };

function appendLog(tag, message, ts) {
  const log = document.getElementById("log");
  if (log.querySelector(".empty")) log.innerHTML = "";
  const div = document.createElement("div");
  div.className = "line";
  const cls = TAG_CLASS[tag] || "SYSTEM";
  div.innerHTML = `<span class="ts">${escapeHtml(ts)}</span><span class="tag tag-${cls}">[${escapeHtml(tag)}]</span>${escapeHtml(message)}`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

document.getElementById("start-run").addEventListener("click", async () => {
  const feed_path = document.getElementById("run-feed-select").value;
  const trendSelect = document.getElementById("run-trend-select");
  const trends = Array.from(trendSelect.selectedOptions).map(o => o.value);
  const limit = Number(document.getElementById("run-limit").value);
  const post = document.getElementById("run-post").checked;
  const btn = document.getElementById("start-run");
  const titlebar = document.getElementById("run-titlebar");
  const summaryCard = document.getElementById("run-summary-card");

  document.getElementById("log").innerHTML = "";
  summaryCard.style.display = "none";
  btn.disabled = true;
  titlebar.textContent = "pin_pipeline — запускається...";

  try {
    const { run_id } = await api("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feed_path, trends, limit, post }),
    });
    titlebar.textContent = `pin_pipeline — run ${run_id}`;
    const es = new EventSource(`/api/run/${run_id}/stream`);
    es.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      if (data.type === "log") {
        appendLog(data.tag, data.message, data.ts);
      } else if (data.type === "done") {
        renderSummary(data.summary);
        titlebar.textContent = `pin_pipeline — готово (${data.summary.length} продуктів)`;
        es.close();
        btn.disabled = false;
      } else if (data.type === "error") {
        appendLog("WARN", "ERROR: " + data.message, new Date().toLocaleTimeString());
        titlebar.textContent = "pin_pipeline — помилка";
        es.close();
        btn.disabled = false;
      }
    };
    es.onerror = () => {
      es.close();
      btn.disabled = false;
    };
  } catch (e) {
    appendLog("WARN", "Не вдалось стартувати: " + e.message, new Date().toLocaleTimeString());
    btn.disabled = false;
  }
});

function renderSummary(rows) {
  const card = document.getElementById("run-summary-card");
  const tbody = card.querySelector("tbody");
  tbody.innerHTML = rows.map(r => `
    <tr><td>${escapeHtml(r.product)}</td><td>$${Number(r.price).toFixed(2)}</td>
    <td>${r.images}</td><td>${r.pins}</td><td>${escapeHtml(r.board)}</td>
    <td>${escapeHtml(r.status)}</td></tr>`).join("");
  card.style.display = "block";
}

// ---------- History ----------
async function loadHistory() {
  const data = await api("/api/history");
  const pinsBody = document.querySelector("#pins-table tbody");
  pinsBody.innerHTML = data.pins.length
    ? data.pins.map(p => `
        <tr><td>${p.id}</td><td>${escapeHtml(p.product_id)}</td><td>${escapeHtml(p.title)}</td>
        <td>${escapeHtml(p.board_name || p.board_id)}</td><td>${escapeHtml((p.created_at||"").slice(0,19))}</td>
        <td>${p.dry_run ? "dry-run" : "posted"}</td></tr>`).join("")
    : `<tr><td colspan="6" class="empty">Ще немає жодного піна.</td></tr>`;

  const postedBody = document.querySelector("#posted-table tbody");
  postedBody.innerHTML = data.posted_products.length
    ? data.posted_products.map(p => `
        <tr><td>${escapeHtml(p.product_id)}</td><td>${escapeHtml(p.title)}</td>
        <td>${escapeHtml((p.posted_at||"").slice(0,19))}</td></tr>`).join("")
    : `<tr><td colspan="3" class="empty">Ще немає опублікованих продуктів.</td></tr>`;
}
document.getElementById("refresh-history").addEventListener("click", loadHistory);

// ---------- Settings ----------
async function loadSettings() {
  const s = await api("/api/settings");
  const badge = (label, isSet) =>
    `<div class="card"><div class="stat-label">${label}</div><div class="stat-value">
       <span class="badge ${isSet ? "set" : "unset"}">${isSet ? "set" : "not set"}</span></div></div>`;
  document.getElementById("settings-badges").innerHTML =
    badge("Anthropic", s.ANTHROPIC_API_KEY) +
    badge("Pinterest token", s.PINTEREST_ACCESS_TOKEN) +
    badge("Pinterest app", s.PINTEREST_APP_ID && s.PINTEREST_APP_SECRET);
  document.getElementById("redirect-uri-hint").textContent =
    `Redirect URI, зареєстрований у Pinterest Developer App має збігатися з: ${s.redirect_uri}`;
}

document.getElementById("save-settings").addEventListener("click", async () => {
  const status = document.getElementById("settings-save-status");
  const payload = {};
  const map = {
    "set-anthropic": "ANTHROPIC_API_KEY",
    "set-pin-app-id": "PINTEREST_APP_ID",
    "set-pin-app-secret": "PINTEREST_APP_SECRET",
    "set-pin-token": "PINTEREST_ACCESS_TOKEN",
  };
  for (const [id, key] of Object.entries(map)) {
    const v = document.getElementById(id).value.trim();
    if (v) payload[key] = v;
  }
  try {
    const res = await api("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    status.textContent = res.note + (res.updated.length ? ` (${res.updated.join(", ")})` : "");
    Object.keys(map).forEach(id => document.getElementById(id).value = "");
    await loadSettings();
  } catch (e) {
    status.textContent = "Помилка: " + e.message;
  }
});

document.getElementById("pinterest-auth-btn").addEventListener("click", async () => {
  const box = document.getElementById("pinterest-auth-result");
  try {
    const data = await api("/api/pinterest/auth-url");
    box.innerHTML = `Відкрий і авторизуйся: <a href="${data.auth_url}" target="_blank">${data.auth_url}</a>`;
  } catch (e) {
    box.textContent = "Помилка: " + e.message;
  }
});

// ---------- init ----------
(async function init() {
  await loadStatus();
  await loadTrends();
  await loadFeedsAndTrends();
})();
