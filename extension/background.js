// Background service worker — handles tab creation and message routing

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "OPEN_BROKER_TAB") {
    handleOpenBrokerTab(msg).then(sendResponse);
    return true; // async response
  }
  if (msg.type === "GET_CURRENT_PROPERTY") {
    chrome.storage.local.get("currentProperty", (data) => {
      sendResponse(data.currentProperty || null);
    });
    return true;
  }
  if (msg.type === "SET_PROPERTY") {
    chrome.storage.local.set({ currentProperty: msg.property }, () => {
      sendResponse({ ok: true });
    });
    return true;
  }
});

async function handleOpenBrokerTab(msg) {
  const brokerUrls = {
    reins: "https://system.reins.jp/",
    itanzi: "https://itanzi.jp/",
    es_b2b: "https://www.es-b2b.net/",
    ielove: "https://www.ielove.co.jp/agent/",
  };

  if (msg.property) {
    await chrome.storage.local.set({ currentProperty: msg.property });
  }

  const url = brokerUrls[msg.broker];
  if (url) {
    chrome.tabs.create({ url });
  }
  return { ok: true };
}
