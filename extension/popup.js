const BROKER_URLS = {
  reins: "https://system.reins.jp/",
  itanzi: "https://itanzi.jp/",
  es_b2b: "https://www.es-b2b.net/",
  ielove: "https://www.ielove.co.jp/agent/",
};

async function init() {
  const data = await chrome.storage.local.get("currentProperty");
  const prop = data.currentProperty;

  if (!prop) {
    document.getElementById("no-property").style.display = "block";
    document.getElementById("property-section").style.display = "none";
    document.getElementById("broker-section").style.display = "none";
    document.getElementById("status").textContent = "物件データがありません";
    return;
  }

  document.getElementById("no-property").style.display = "none";
  document.getElementById("property-section").style.display = "block";
  document.getElementById("broker-section").style.display = "block";

  document.getElementById("prop-name").textContent = prop.name || "—";
  document.getElementById("prop-meta").textContent =
    [prop.address, prop.rent, prop.layout, prop.area].filter(Boolean).join(" / ");

  // Enable broker buttons
  for (const [key] of Object.entries(SITES_CONFIG)) {
    const btn = document.getElementById(`btn-${key}`);
    if (btn) {
      btn.disabled = false;
      btn.addEventListener("click", () => openBroker(key, prop));
    }
  }

  // Check if current tab is a broker site to enable autofill
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const currentSite = detectSiteFromUrl(tab?.url || "");
  const autofillBtn = document.getElementById("btn-autofill");

  if (currentSite) {
    autofillBtn.textContent = `${currentSite.config.name} のフォームを自動入力`;
    autofillBtn.addEventListener("click", () => {
      chrome.tabs.sendMessage(tab.id, {
        type: "TRIGGER_AUTOFILL",
        property: prop,
      });
      window.close();
    });
    document.getElementById("status").textContent = `${currentSite.config.name} を検出しました`;
  } else {
    autofillBtn.style.display = "none";
    document.getElementById("status").textContent = "業者サイトでボタンを押すと自動入力します";
  }
}

function openBroker(brokerKey, prop) {
  chrome.runtime.sendMessage({
    type: "OPEN_BROKER_TAB",
    broker: brokerKey,
    property: prop,
  });
  window.close();
}

function detectSiteFromUrl(url) {
  for (const [key, config] of Object.entries(SITES_CONFIG)) {
    if (config.urlPattern.test(url)) {
      return { key, config };
    }
  }
  return null;
}

init();
