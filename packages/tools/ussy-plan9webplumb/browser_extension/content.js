/**
 * Plan9-WebPlumb Content Script
 *
 * Listens for messages from the background script and captures
 * selected text, URL, and DOM context from the active page.
 */

(function () {
  "use strict";

  const PLUMB_WS_URL = "ws://localhost:31151";

  /**
   * Get the current selection context from the page.
   */
  function getSelectionContext() {
    const selection = window.getSelection();
    const selectedText = selection ? selection.toString().trim() : "";
    return {
      data: selectedText,
      url: window.location.href,
      title: document.title,
      src: "browser",
      msg_type: selectedText ? "text" : "url",
      tab_id: -1,
    };
  }

  /**
   * Send a plumb message to the local plumber server.
   */
  async function plumbMessage(message) {
    try {
      const ws = new WebSocket(PLUMB_WS_URL);

      ws.addEventListener("open", () => {
        ws.send(JSON.stringify(message));
      });

      ws.addEventListener("message", (event) => {
        const response = JSON.parse(event.data);
        if (response.type === "dispatch_result") {
          console.log(
            "[Plan9-WebPlumb] Dispatched:",
            response.handlers_fired,
            "handlers fired"
          );
        } else if (response.type === "error") {
          console.error("[Plan9-WebPlumb] Error:", response.error);
        }
        ws.close();
      });

      ws.addEventListener("error", (event) => {
        console.error("[Plan9-WebPlumb] Connection error - is the plumber running?");
      });
    } catch (err) {
      console.error("[Plan9-WebPlumb] Failed to send:", err);
    }
  }

  // Listen for messages from the background script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "plumb_selection") {
      const context = getSelectionContext();
      plumbMessage(context);
      sendResponse({ status: "sent", data: context });
    } else if (request.action === "plumb_url") {
      plumbMessage({
        data: window.location.href,
        url: window.location.href,
        title: document.title,
        src: "browser",
        msg_type: "url",
        tab_id: -1,
      });
      sendResponse({ status: "sent" });
    } else if (request.action === "plumb_clipboard") {
      // Clipboard content is handled by the background script
      sendResponse({ status: "ok" });
    }
    return true; // Keep message channel open for async response
  });

  console.log("[Plan9-WebPlumb] Content script loaded");
})();
