const APP_ORIGIN = "http://localhost:5173";
const APP_URL = "http://localhost:5173/job";

let dockRoot = null;
let dockFrame = null;
let resendTimer = null;
let pendingCapture = null;
const AUTO_OPEN_KEY = "atsResumeDockAutoOpened";

function selectedText() {
  const selection = window.getSelection();
  return selection ? selection.toString().trim() : "";
}

function isJobCaptureShortcut(event) {
  const isSpace = event.code === "Space" || event.key === " ";
  return event.ctrlKey && !event.shiftKey && isSpace;
}

function isTypingTarget(target) {
  if (!target) return false;
  if (target.isContentEditable) return true;
  const tagName = (target.tagName || "").toLowerCase();
  return tagName === "input" || tagName === "textarea";
}

function looksLikeJobPage() {
  if (window.location.origin === APP_ORIGIN) return false;

  const haystack = `${window.location.href} ${document.title}`.toLowerCase();
  const urlHints = [
    "job",
    "jobs",
    "careers",
    "position",
    "opening",
    "greenhouse",
    "lever.co",
    "workdayjobs",
    "smartrecruiters",
    "ashbyhq",
  ];

  return urlHints.some((hint) => haystack.includes(hint));
}

function tryAutoOpenDock() {
  if (!looksLikeJobPage()) return;

  const pageKey = `${window.location.origin}${window.location.pathname}`;
  const openedKey = sessionStorage.getItem(AUTO_OPEN_KEY);
  if (openedKey === pageKey) return;

  openDock();
  setDockStatus("Panel ready. Select job text and press Ctrl+Space.");
  sessionStorage.setItem(AUTO_OPEN_KEY, pageKey);
}

function clearResendTimer() {
  if (!resendTimer) return;
  window.clearInterval(resendTimer);
  resendTimer = null;
}

function createDockIfNeeded() {
  if (dockRoot) return;

  const style = document.createElement("style");
  style.textContent = `
    #ats-resume-dock {
      position: fixed;
      top: 12px;
      right: 12px;
      bottom: 12px;
      width: min(420px, 92vw);
      z-index: 2147483646;
      background: #f8fafc;
      border: 1px solid #d4d9e1;
      border-radius: 14px;
      box-shadow: 0 14px 40px rgba(16, 24, 40, 0.25);
      overflow: hidden;
      display: none;
      flex-direction: column;
    }

    #ats-resume-dock.ats-open {
      display: flex;
    }

    #ats-resume-dock-header {
      height: 46px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 12px;
      border-bottom: 1px solid #d4d9e1;
      background: #ffffff;
      font: 600 13px/1.2 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: #0f172a;
    }

    #ats-resume-dock-title {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    #ats-resume-dock-status {
      font-weight: 500;
      color: #475467;
      margin-left: 8px;
    }

    #ats-resume-dock-close {
      border: 0;
      background: transparent;
      color: #475467;
      font-size: 20px;
      line-height: 1;
      cursor: pointer;
      padding: 2px 4px;
    }

    #ats-resume-dock-frame {
      width: 100%;
      flex: 1;
      border: 0;
      background: #ffffff;
    }

    #ats-resume-dock-tab {
      position: fixed;
      right: 12px;
      top: 45%;
      transform: translateY(-50%);
      z-index: 2147483645;
      border: 1px solid #c8d0dd;
      border-radius: 10px;
      background: #ffffff;
      color: #0f172a;
      box-shadow: 0 10px 26px rgba(16, 24, 40, 0.18);
      padding: 10px 12px;
      cursor: pointer;
      font: 600 12px/1.1 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    #ats-resume-dock.ats-open + #ats-resume-dock-tab {
      display: none;
    }
  `;

  dockRoot = document.createElement("section");
  dockRoot.id = "ats-resume-dock";
  dockRoot.innerHTML = `
    <div id="ats-resume-dock-header">
      <div id="ats-resume-dock-title">
        <span>ATS Resume</span>
        <span id="ats-resume-dock-status">Ready</span>
      </div>
      <button id="ats-resume-dock-close" type="button" aria-label="Close">×</button>
    </div>
    <iframe id="ats-resume-dock-frame" src="${APP_URL}" title="ATS Resume Generator"></iframe>
  `;

  const dockTab = document.createElement("button");
  dockTab.id = "ats-resume-dock-tab";
  dockTab.type = "button";
  dockTab.textContent = "ATS Resume";

  document.documentElement.append(style, dockRoot, dockTab);

  dockFrame = dockRoot.querySelector("#ats-resume-dock-frame");
  dockRoot.querySelector("#ats-resume-dock-close")?.addEventListener("click", () => {
    dockRoot.classList.remove("ats-open");
    clearResendTimer();
  });

  dockTab.addEventListener("click", () => {
    if (selectedText()) {
      captureSelection();
      return;
    }

    dockRoot.classList.add("ats-open");
    sendPendingCapture();
  });

  dockFrame?.addEventListener("load", () => {
    sendPendingCapture();
  });
}

function setDockStatus(message) {
  if (!dockRoot) return;
  const status = dockRoot.querySelector("#ats-resume-dock-status");
  if (status) status.textContent = message;
}

function openDock() {
  createDockIfNeeded();
  dockRoot.classList.add("ats-open");
}

function postCapture(capture) {
  if (!capture || !dockFrame?.contentWindow) return;
  dockFrame.contentWindow.postMessage(
    {
      source: "ats-resume-extension",
      type: "JOB_DESCRIPTION_CAPTURED",
      payload: capture,
    },
    APP_ORIGIN
  );
}

function sendPendingCapture() {
  if (!pendingCapture) return;
  postCapture(pendingCapture);
  clearResendTimer();
  resendTimer = window.setInterval(() => {
    postCapture(pendingCapture);
  }, 1200);
  setDockStatus("Sending capture...");
}

async function loadAndSendLatestCapture() {
  const result = await chrome.storage.local.get("latestJobCapture");
  pendingCapture = result.latestJobCapture || null;
  if (pendingCapture) {
    sendPendingCapture();
  }
}

async function captureSelection() {
  const descriptionText = selectedText();
  if (!descriptionText) return;

  const response = await chrome.runtime.sendMessage({
    type: "ATS_JOB_SELECTION_CAPTURED",
    description_text: descriptionText,
  });

  if (response?.ok) {
    openDock();
    await loadAndSendLatestCapture();
  }
}

document.addEventListener(
  "keydown",
  (event) => {
    if (!isJobCaptureShortcut(event)) return;

    const hasSelection = !!selectedText();
    if (isTypingTarget(event.target) && !hasSelection) return;

    event.preventDefault();

    openDock();
    if (hasSelection) {
      captureSelection();
      return;
    }

    setDockStatus("Panel opened. Select text and press Ctrl+Space.");
  },
  true
);

chrome.runtime.onMessage.addListener((message) => {
  if (message?.type === "ATS_CAPTURE_SELECTION") {
    captureSelection();
    return;
  }

  if (message?.type === "ATS_OPEN_INLINE_DOCK") {
    openDock();
    loadAndSendLatestCapture();
    return;
  }
});

window.addEventListener("message", async (event) => {
  if (event.data?.source !== "ats-resume-app") return;

  if (event.data?.type === "REQUEST_GOOGLE_AUTH") {
    chrome.runtime.sendMessage({ type: "GOOGLE_AUTH" }, (response) => {
      event.source?.postMessage(
        {
          source: "ats-resume-extension",
          type: "GOOGLE_AUTH_RESULT",
          payload: response || { ok: false, error: "No response from extension." },
        },
        "*"
      );
    });
    return;
  }

  if (event.data?.type === "AUTH_TOKEN_SAVE") {
    const token = event.data?.payload?.token || "";
    if (token) {
      await chrome.storage.local.set({ authToken: token });
    }
    return;
  }

  if (event.data?.type === "AUTH_TOKEN_CLEAR") {
    await chrome.storage.local.remove("authToken");
    return;
  }

  if (event.data?.type === "REQUEST_AUTH_TOKEN") {
    const result = await chrome.storage.local.get("authToken");
    event.source?.postMessage(
      {
        source: "ats-resume-extension",
        type: "AUTH_TOKEN_VALUE",
        payload: {
          token: result.authToken || "",
        },
      },
      "*"
    );
  }
});

window.addEventListener("message", (event) => {
  if (event.origin !== APP_ORIGIN) return;
  if (event.data?.source !== "ats-resume-app") return;
  if (event.data?.type !== "JOB_DESCRIPTION_CAPTURED_ACK") return;

  clearResendTimer();
  setDockStatus("Captured and inserted");
});

window.addEventListener("message", (event) => {
  if (event.origin !== APP_ORIGIN) return;
  if (event.data?.source !== "ats-resume-app") return;
});

createDockIfNeeded();
if (document.readyState === "complete" || document.readyState === "interactive") {
  window.setTimeout(tryAutoOpenDock, 700);
} else {
  window.addEventListener("DOMContentLoaded", () => window.setTimeout(tryAutoOpenDock, 700), { once: true });
}
