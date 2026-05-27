/**
 * Content script for いい生活 (es-b2b.net).
 *
 * ⚠️ ログイン後に実際のフォームHTMLを確認し、
 *    sites_config.js の es_b2b.fields セレクタを更新してください。
 */

(function () {
  const site = detectCurrentSite();
  if (!site) return;

  chrome.storage.local.get("currentProperty", ({ currentProperty }) => {
    if (!currentProperty) return;
    injectAutofillButton(currentProperty, site.config);
  });

  function injectAutofillButton(prop, config) {
    if (document.getElementById("realestate-autofill-btn")) return;

    const btn = document.createElement("button");
    btn.id = "realestate-autofill-btn";
    btn.textContent = `🏠 自動入力: ${prop.name}`;
    Object.assign(btn.style, {
      position: "fixed",
      bottom: "20px",
      right: "20px",
      zIndex: "99999",
      background: "#7b1fa2",
      color: "#fff",
      border: "none",
      borderRadius: "8px",
      padding: "12px 18px",
      fontSize: "14px",
      fontWeight: "bold",
      cursor: "pointer",
      boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
      fontFamily: "-apple-system, sans-serif",
    });

    btn.addEventListener("click", () => {
      const filled = fillForm(prop, config);
      if (filled > 0) {
        btn.textContent = `✅ ${filled}項目を入力しました`;
        btn.style.background = "#388e3c";
        setTimeout(() => submitIfReady(config), 500);
      } else {
        btn.textContent = "⚠️ フォームが見つかりません";
        btn.style.background = "#e53935";
      }
    });

    document.body.appendChild(btn);
  }

  function fillForm(prop, config) {
    let count = 0;
    const nameEl = queryAny(config.fields.buildingName);
    if (fillInput(nameEl, prop.name)) count++;
    const addrEl = queryAny(config.fields.address);
    if (fillInput(addrEl, prop.address)) count++;
    const areaEl = queryAny(config.fields.area);
    const areaNum = prop.area?.replace(/[^\d.]/g, "") || "";
    if (fillInput(areaEl, areaNum)) count++;
    return count;
  }

  function submitIfReady(config) {
    const submitBtn = queryAny(config.submitButton);
    if (submitBtn) submitBtn.click();
  }
})();
