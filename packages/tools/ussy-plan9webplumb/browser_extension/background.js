/**
 * Plan9-WebPlumb Background Service Worker
 *
 * Handles context menu creation, extension icon clicks,
 * and communication with the content scripts.
 */

const PLUMB_WS_URL = "ws://localhost:31151";

/**
 * Send a message directly to the plumber via WebSocket.
 */
async function plumbDirect(message) {
  try {
    const ws = new WebSocket(PLUMB_WS_URL);
    return new Promise((resolve, reject) => {
      ws.addEventListener("open", () => {
        ws.send(JSON.stringify(message));
      });
      ws.addEventListener("message", (event) => {
        const response = JSON.parse(event.data);
        ws.close();
        resolve(response);
      });
      ws.addEventListener("error", (event) => {
        reject(new Error("Connection error - is the plumber running?"));
      });
    });
  } catch (err) {
    console.error("[Plan9-WebPlumb] Failed to connect:", err);
    throw err;
  }
}

// Create context menus on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "plumb-selection",
    title: "Plumb selection",
    contexts: ["selection"],
  });

  chrome.contextMenus.create({
    id: "plumb-link",
    title: "Plumb link",
    contexts: ["link"],
  });

  chrome.contextMenus.create({
    id: "plumb-page",
    title: "Plumb page URL",
    contexts: ["page"],
  });

  console.log("[Plan9-WebPlumb] Context menus created");
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const tabId = tab ? tab.id : -1;
  const tabTitle = tab ? tab.title : "";
  const tabUrl = tab ? tab.url : "";

  if (info.menuItemId === "plumb-selection") {
    // Send selected text through content script
    if (tab && tab.id) {
      chrome.tabs.sendMessage(tab.id, { action: "plumb_selection" });
    }
  } else if (info.menuItemId === "plumb-link") {
    // Send the clicked link URL
    await plumbDirect({
      data: info.linkUrl || "",
      url: info.linkUrl || "",
      title: tabTitle,
      src: "browser",
      msg_type: "url",
      tab_id: tabId,
    });
  } else if (info.menuItemId === "plumb-page") {
    // Send the page URL
    await plumbDirect({
      data: tabUrl,
      url: tabUrl,
      title: tabTitle,
      src: "browser",
      msg_type: "url",
      tab_id: tabId,
    });
  }
});

// Handle extension icon click
chrome.action.onClicked.addListener(async (tab) => {
  if (tab && tab.id) {
    chrome.tabs.sendMessage(tab.id, { action: "plumb_selection" });
  }
});

console.log("[Plan9-WebPlumb] Background service worker loaded");
