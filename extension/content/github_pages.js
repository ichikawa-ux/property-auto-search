/**
 * Content script for GitHub Pages property detail pages.
 * Listens for property data from the page and stores it in chrome.storage.local.
 */

window.addEventListener("message", (event) => {
  if (event.origin !== location.origin) return;

  if (event.data?.type === "REALESTATE_PROPERTY_DATA") {
    const property = event.data.property;
    chrome.storage.local.set({ currentProperty: property });
    console.log("[不動産拡張] 物件データを保存しました:", property?.name);
  }

  if (event.data?.type === "REALESTATE_OPEN_BROKER") {
    chrome.runtime.sendMessage({
      type: "OPEN_BROKER_TAB",
      broker: event.data.broker,
    });
  }
});
