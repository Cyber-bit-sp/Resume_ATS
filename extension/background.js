const BACKEND_ORIGIN = "http://localhost:8000";

async function saveCapture(payload) {
  await chrome.storage.local.set({
    latestJobCapture: {
      ...payload,
      capturedAt: new Date().toISOString(),
    },
  });
}

async function requestDockOpen(tab) {
  if (!tab?.id) return;
  await chrome.tabs.sendMessage(tab.id, { type: "ATS_OPEN_INLINE_DOCK" });
}

async function requestCaptureFromTab(tab) {
  if (!tab?.id) return;
  await chrome.tabs.sendMessage(tab.id, { type: "ATS_CAPTURE_SELECTION" });
}

chrome.runtime.onInstalled.addListener(() => {
  // Intentionally no side panel behavior; UI is injected inline in the page.
});

chrome.action.onClicked.addListener((tab) => {
  requestDockOpen(tab);
});

chrome.commands.onCommand.addListener(async (command) => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (command === "capture-selected-job") {
    await requestCaptureFromTab(tab);
    return;
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "GOOGLE_AUTH") {
    handleGoogleAuth()
      .then((result) => sendResponse({ ok: true, ...result }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true;
  }

  if (message?.type !== "ATS_JOB_SELECTION_CAPTURED") return false;

  saveCapture({
    description_text: message.description_text,
    job_url: sender.tab?.url || "",
    page_title: sender.tab?.title || "",
  })
    .then(() => requestDockOpen(sender.tab))
    .then(() => sendResponse({ ok: true }))
    .catch((error) => sendResponse({ ok: false, error: error.message }));

  return true;
});

function getGoogleToken() {
  return new Promise((resolve, reject) => {
    chrome.identity.getAuthToken({ interactive: true }, (token) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(token);
      }
    });
  });
}

async function handleGoogleAuth() {
  const googleToken = await getGoogleToken();

  const response = await fetch(`${BACKEND_ORIGIN}/api/auth/google/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ access_token: googleToken }),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "Google authentication failed.");
  }

  await chrome.storage.local.set({ authToken: data.token });
  return { token: data.token, user: data.user };
}
