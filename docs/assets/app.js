/* Shared utilities */
const SITE_LABELS = {
  suumo: "SUUMO",
  homes: "LIFULL HOME'S",
  athome: "アットホーム",
};

async function loadProperties() {
  const base = getBaseUrl();
  const resp = await fetch(`${base}/data/properties.json?_=${Date.now()}`);
  if (!resp.ok) return [];
  return resp.json();
}

function getBaseUrl() {
  const path = location.pathname;
  const parts = path.split("/").filter(Boolean);
  const repoName = parts[0] || "";
  return location.origin + (repoName ? `/${repoName}` : "");
}

function formatDate(iso) {
  if (!iso) return "";
  return iso.replace("T", " ").slice(0, 16);
}

function siteBadge(site) {
  return `<span class="site-badge">${SITE_LABELS[site] || site}</span>`;
}

/* ---- Index page ---- */
async function initIndex() {
  const list = document.getElementById("property-list");
  const countEl = document.getElementById("count");
  const filterName = document.getElementById("filter-name");
  const filterSite = document.getElementById("filter-site");
  const filterLayout = document.getElementById("filter-layout");

  let properties = [];
  try {
    properties = await loadProperties();
  } catch {
    list.innerHTML = '<p class="empty-state">データの読み込みに失敗しました。</p>';
    return;
  }

  const render = () => {
    const name = filterName?.value.trim().toLowerCase() || "";
    const site = filterSite?.value || "";
    const layout = filterLayout?.value || "";

    const filtered = properties.filter((p) => {
      if (site && p.site !== site) return false;
      if (layout && !p.layout.includes(layout)) return false;
      if (name && !`${p.name} ${p.address}`.toLowerCase().includes(name)) return false;
      return true;
    });

    countEl && (countEl.textContent = `${filtered.length}件`);

    if (filtered.length === 0) {
      list.innerHTML = '<div class="empty-state">条件に合う物件がありません。</div>';
      return;
    }

    list.innerHTML = filtered.map(cardHtml).join("");
  };

  filterName?.addEventListener("input", render);
  filterSite?.addEventListener("change", render);
  filterLayout?.addEventListener("change", render);
  render();
}

function cardHtml(p) {
  const base = getBaseUrl();
  const detailUrl = `${base}/property.html?id=${encodeURIComponent(p.id)}`;
  return `
<div class="property-card">
  ${siteBadge(p.site)}
  <h2><a class="title-link" href="${detailUrl}">${esc(p.name)}</a></h2>
  <div class="prop-grid">
    <div class="prop-item"><div class="label">住所</div><div class="value">${esc(p.address)}</div></div>
    <div class="prop-item"><div class="label">家賃</div><div class="value rent">${esc(p.rent)}</div></div>
    <div class="prop-item"><div class="label">間取り</div><div class="value">${esc(p.layout)}</div></div>
    <div class="prop-item"><div class="label">面積</div><div class="value">${esc(p.area)}</div></div>
    <div class="prop-item"><div class="label">築年数</div><div class="value">${esc(p.age)}</div></div>
    <div class="prop-item"><div class="label">アクセス</div><div class="value">${esc(p.station_access)}</div></div>
  </div>
  <div class="detected-at">検知: ${esc(p.detected_at || "")}</div>
  <div class="btn-row">
    <a class="btn btn-primary" href="${esc(p.url)}" target="_blank" rel="noopener">元サイトを見る</a>
    <a class="btn btn-success" href="${detailUrl}">詳細・業者検索</a>
  </div>
</div>`;
}

/* ---- Detail page ---- */
async function initDetail() {
  const params = new URLSearchParams(location.search);
  const id = params.get("id");

  if (!id) {
    document.getElementById("content").innerHTML =
      '<p class="empty-state">物件IDが指定されていません。</p>';
    return;
  }

  let properties = [];
  try {
    properties = await loadProperties();
  } catch {
    document.getElementById("content").innerHTML =
      '<p class="empty-state">データの読み込みに失敗しました。</p>';
    return;
  }

  const prop = properties.find((p) => p.id === id);
  if (!prop) {
    document.getElementById("content").innerHTML =
      '<p class="empty-state">物件が見つかりません。</p>';
    return;
  }

  document.title = `${prop.name} — 不動産物件詳細`;
  document.getElementById("content").innerHTML = detailHtml(prop);

  // Store property data for Chrome extension
  try {
    window.postMessage({ type: "REALESTATE_PROPERTY_DATA", property: prop }, "*");
    sessionStorage.setItem("currentProperty", JSON.stringify(prop));
  } catch {}
}

function detailHtml(p) {
  return `
<div class="detail-header">
  ${siteBadge(p.site)}
  <h2 style="font-size:20px;margin:8px 0 16px;">${esc(p.name)}</h2>
  <table class="detail-table">
    <tr><td>住所</td><td>${esc(p.address)}</td></tr>
    <tr><td>家賃</td><td style="color:var(--danger);font-weight:700;font-size:18px;">${esc(p.rent)}</td></tr>
    <tr><td>管理費</td><td>${esc(p.management_fee || "—")}</td></tr>
    <tr><td>間取り</td><td>${esc(p.layout)}</td></tr>
    <tr><td>面積</td><td>${esc(p.area)}</td></tr>
    <tr><td>築年数</td><td>${esc(p.age)}</td></tr>
    <tr><td>階数</td><td>${esc(p.floor || "—")}</td></tr>
    <tr><td>敷金</td><td>${esc(p.deposit || "—")}</td></tr>
    <tr><td>礼金</td><td>${esc(p.key_money || "—")}</td></tr>
    <tr><td>アクセス</td><td>${esc(p.station_access)}</td></tr>
    <tr><td>検知日時</td><td>${esc(p.detected_at || "")}</td></tr>
  </table>
  <div class="btn-row" style="margin-top:16px;">
    <a class="btn btn-primary" href="${esc(p.url)}" target="_blank" rel="noopener">元サイトで確認</a>
    <a class="btn btn-outline" href="index.html">一覧に戻る</a>
  </div>
</div>

<div class="broker-section">
  <h3>業者サイトで検索</h3>
  <p style="font-size:13px;color:var(--muted);margin-bottom:12px;">
    対象サイトにログイン後、ボタンを押してください。Chrome拡張機能が自動入力します。
  </p>
  <div class="btn-row">
    <button class="btn btn-broker" onclick="openBroker('reins', ${JSON.stringify(p.id)})">REINS で検索</button>
    <button class="btn btn-broker" onclick="openBroker('itanzi', ${JSON.stringify(p.id)})">イタンジ で検索</button>
    <button class="btn btn-broker" onclick="openBroker('es_b2b', ${JSON.stringify(p.id)})">いい生活 で検索</button>
    <button class="btn btn-broker" onclick="openBroker('ielove', ${JSON.stringify(p.id)})">いえらぶ で検索</button>
  </div>
</div>`;
}

function openBroker(brokerName, propId) {
  const brokerUrls = {
    reins: "https://system.reins.jp/",
    itanzi: "https://itanzi.jp/",
    es_b2b: "https://www.es-b2b.net/",
    ielove: "https://www.ielove.co.jp/agent/",
  };

  // Notify the extension
  window.postMessage({
    type: "REALESTATE_OPEN_BROKER",
    broker: brokerName,
    propId: propId,
  }, "*");

  const url = brokerUrls[brokerName];
  if (url) {
    window.open(url, "_blank", "noopener");
  }
}

function esc(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
