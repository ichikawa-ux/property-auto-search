/**
 * 各業者サイトのフォームセレクタ設定。
 * サイトのHTMLが変更された場合はここを更新してください。
 */
const SITES_CONFIG = {
  reins: {
    name: "REINS",
    urlPattern: /reins\.or\.jp/,
    // ログイン後の物件検索フォームページURL（ログイン後に確認してセットしてください）
    searchPagePattern: /search|bukken|chintai/i,
    fields: {
      buildingName: [
        "#bukken_name",
        "input[name='bukken_name']",
        "input[name='tatemono_name']",
        // サイト更新時はここにセレクタを追加
      ],
      address: [
        "#address",
        "input[name='address']",
        "input[name='shozaichi']",
      ],
      area: [
        "#menseki",
        "input[name='menseki']",
        "input[name='senyumenseki']",
      ],
      buildYear: [
        "#chikunen",
        "input[name='chikunen']",
        "select[name='chikunen']",
      ],
    },
    submitButton: [
      "input[type='submit']",
      "button[type='submit']",
      ".search-btn",
      "#search_btn",
    ],
  },

  itanzi: {
    name: "イタンジ",
    urlPattern: /itanzi\.jp/,
    searchPagePattern: /search|bukken/i,
    fields: {
      buildingName: [
        "input[placeholder*='建物名']",
        "input[name*='building']",
        "input[name*='tatemono']",
        "#building_name",
      ],
      address: [
        "input[placeholder*='住所']",
        "input[name*='address']",
        "#address",
      ],
      area: [
        "input[placeholder*='面積']",
        "input[name*='area']",
        "input[name*='menseki']",
      ],
    },
    submitButton: [
      "button[type='submit']",
      ".btn-search",
      "input[type='submit']",
    ],
  },

  es_b2b: {
    name: "いい生活",
    urlPattern: /es-b2b\.net/,
    searchPagePattern: /search|bukken|chintai/i,
    fields: {
      buildingName: [
        "input[name*='building']",
        "input[name*='tatemono']",
        "input[placeholder*='建物']",
        "#building_name",
      ],
      address: [
        "input[name*='address']",
        "input[placeholder*='住所']",
        "#address",
      ],
      area: [
        "input[name*='area']",
        "input[name*='menseki']",
        "input[placeholder*='面積']",
      ],
    },
    submitButton: [
      "button[type='submit']",
      "input[type='submit']",
      ".search-btn",
    ],
  },

  ielove: {
    name: "いえらぶ",
    urlPattern: /ielove\.co\.jp/,
    searchPagePattern: /search|agent|bukken/i,
    fields: {
      buildingName: [
        "input[name*='building']",
        "input[name*='tatemono']",
        "input[placeholder*='建物名']",
        "#building_name",
      ],
      address: [
        "input[name*='address']",
        "input[placeholder*='住所']",
        "#address",
      ],
      area: [
        "input[name*='area']",
        "input[name*='menseki']",
        "input[placeholder*='面積']",
      ],
    },
    submitButton: [
      "button[type='submit']",
      "input[type='submit']",
      ".btn-search",
    ],
  },
};

/**
 * Detect which broker site is currently open.
 */
function detectCurrentSite() {
  for (const [key, config] of Object.entries(SITES_CONFIG)) {
    if (config.urlPattern.test(location.hostname)) {
      return { key, config };
    }
  }
  return null;
}

/**
 * Try multiple selectors until one matches.
 */
function queryAny(selectors) {
  for (const sel of selectors) {
    try {
      const el = document.querySelector(sel);
      if (el) return el;
    } catch {}
  }
  return null;
}

/**
 * Fill a single input element, triggering React/Vue change events.
 */
function fillInput(el, value) {
  if (!el || value === undefined || value === null) return false;
  const nativeSetter =
    Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value") ||
    Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value");
  if (nativeSetter && nativeSetter.set) {
    nativeSetter.set.call(el, value);
  } else {
    el.value = value;
  }
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  return true;
}
