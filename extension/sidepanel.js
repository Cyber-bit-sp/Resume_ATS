const APP_ORIGIN = "http://localhost:5173";
const appFrame = document.getElementById("app");
const statusNode = document.getElementById("status");
let resendTimer = null;

function clearResendTimer() {
  if (!resendTimer) return;
  window.clearInterval(resendTimer);
  resendTimer = null;
}

function postCapture(capture) {
  if (!capture || !appFrame.contentWindow) return;
  appFrame.contentWindow.postMessage(
    {
      source: "ats-resume-extension",
      type: "JOB_DESCRIPTION_CAPTURED",
      payload: capture,
    },
    APP_ORIGIN
  );
}

function showStatus(message) {
  statusNode.style.display = "block";
  statusNode.textContent = message;
}

async function latestCapture() {
  const result = await chrome.storage.local.get("latestJobCapture");
  return result.latestJobCapture || null;
}

window.addEventListener("message", async (event) => {
  if (event.data?.source !== "ats-resume-app") return;

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
    appFrame.contentWindow?.postMessage(
      {
        source: "ats-resume-extension",
        type: "AUTH_TOKEN_VALUE",
        payload: {
          token: result.authToken || "",
        },
      },
      APP_ORIGIN
    );
  }
});

async function sendCaptureToApp() {
  const capture = await latestCapture();
  if (!capture || !appFrame.contentWindow) return;

  postCapture(capture);
  clearResendTimer();
  resendTimer = window.setInterval(() => {
    postCapture(capture);
  }, 1200);

  showStatus("Captured job description detected. Waiting for the app to receive it...");
}

appFrame.addEventListener("load", sendCaptureToApp);

window.addEventListener("message", (event) => {
  if (event.origin !== APP_ORIGIN) return;
  if (event.data?.source !== "ats-resume-app") return;
  if (event.data?.type !== "JOB_DESCRIPTION_CAPTURED_ACK") return;

  clearResendTimer();
  showStatus("Captured job description inserted.");
  window.setTimeout(() => {
    statusNode.style.display = "none";
  }, 1200);
});

chrome.storage.onChanged.addListener((changes, areaName) => {
  if (areaName === "local" && changes.latestJobCapture) {
    sendCaptureToApp();
  }
});
