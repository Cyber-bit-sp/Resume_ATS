import { createContext, useContext, useEffect, useMemo, useState } from "react";

import api from "../api/client";

const AuthContext = createContext(null);

const isInExtension = window.parent !== window;

function requestAuthTokenFromParent() {
  return new Promise((resolve) => {
    const timeoutId = window.setTimeout(() => {
      window.removeEventListener("message", handleMessage);
      resolve("");
    }, 1000);

    function handleMessage(event) {
      if (event.data?.source !== "ats-resume-extension") return;
      if (event.data?.type !== "AUTH_TOKEN_VALUE") return;

      window.clearTimeout(timeoutId);
      window.removeEventListener("message", handleMessage);
      resolve(event.data?.payload?.token || "");
    }

    window.addEventListener("message", handleMessage);
    window.parent.postMessage(
      {
        source: "ats-resume-app",
        type: "REQUEST_AUTH_TOKEN",
      },
      "*"
    );
  });
}

function requestGoogleAuthFromExtension() {
  return new Promise((resolve) => {
    // Allow up to 30 s for the interactive Google sign-in popup
    const timeoutId = window.setTimeout(() => {
      window.removeEventListener("message", handleMessage);
      resolve(null);
    }, 30000);

    function handleMessage(event) {
      if (event.data?.source !== "ats-resume-extension") return;
      if (event.data?.type !== "GOOGLE_AUTH_RESULT") return;

      window.clearTimeout(timeoutId);
      window.removeEventListener("message", handleMessage);
      resolve(event.data?.payload || null);
    }

    window.addEventListener("message", handleMessage);
    window.parent.postMessage(
      {
        source: "ats-resume-app",
        type: "REQUEST_GOOGLE_AUTH",
      },
      "*"
    );
  });
}

function syncAuthTokenToParent(token) {
  if (!token) return;
  window.parent.postMessage(
    {
      source: "ats-resume-app",
      type: "AUTH_TOKEN_SAVE",
      payload: { token },
    },
    "*"
  );
}

function clearAuthTokenInParent() {
  if (window.parent === window) return;
  window.parent.postMessage(
    {
      source: "ats-resume-app",
      type: "AUTH_TOKEN_CLEAR",
    },
    "*"
  );
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      let token = localStorage.getItem("authToken");
      if (!token) {
        token = await requestAuthTokenFromParent();
        if (token) {
          localStorage.setItem("authToken", token);
        }
      }

      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const response = await api.get("/auth/me/");
        setUser(response.data);
      } catch {
        localStorage.removeItem("authToken");
        clearAuthTokenInParent();
      } finally {
        setLoading(false);
      }
    }
    loadUser();
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      isInExtension,
      async login(payload) {
        const response = await api.post("/auth/login/", payload);
        localStorage.setItem("authToken", response.data.token);
        syncAuthTokenToParent(response.data.token);
        setUser(response.data.user);
      },
      async googleLogin() {
        const result = await requestGoogleAuthFromExtension();
        if (!result?.ok) {
          throw new Error(result?.error || "Google sign-in failed or timed out.");
        }
        localStorage.setItem("authToken", result.token);
        // Token was already saved to chrome.storage.local by background.js
        setUser(result.user);
      },
      async logout() {
        try {
          await api.post("/auth/logout/");
        } finally {
          localStorage.removeItem("authToken");
          clearAuthTokenInParent();
          setUser(null);
        }
      },
    }),
    [user, loading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
