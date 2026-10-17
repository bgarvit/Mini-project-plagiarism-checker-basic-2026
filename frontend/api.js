const API_BASE = window.location.origin;

function getToken() {
  return localStorage.getItem("plagifyToken");
}
function setToken(token) {
  if (token) localStorage.setItem("plagifyToken", token);
  else localStorage.removeItem("plagifyToken");
}
function clearToken() {
  localStorage.removeItem("plagifyToken");
  localStorage.removeItem("plagifyLoggedIn");
  localStorage.removeItem("plagifyUser");
  localStorage.removeItem("plagifyUserProfile");
}
function saveSession(data) {
  setToken(data.access_token);
  localStorage.setItem("plagifyLoggedIn", "true");
  localStorage.setItem("plagifyUser", data.email || "");
  const profile = {
    email: data.email || "",
    name: data.name || "",
    picture: data.picture || "",
    auth_provider: data.auth_provider || "local",
  };
  localStorage.setItem("plagifyUserProfile", JSON.stringify(profile));
  return profile;
}
function getStoredProfile() {
  try {
    return JSON.parse(localStorage.getItem("plagifyUserProfile") || "null");
  } catch {
    return null;
  }
}

async function apiRequest(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  let data = null;
  const ct = response.headers.get("content-type") || "";
  if (ct.includes("application/json")) data = await response.json();
  else data = await response.text();
  if (!response.ok) {
    const detail = data && data.detail ? data.detail : "Request failed";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

window.plagifyApi = {
  getToken,
  setToken,
  clearToken,
  saveSession,
  getStoredProfile,
  login(email, password) {
    return apiRequest("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },
  register({ email, password, name, picture }) {
    return apiRequest("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        name,
        picture: picture || null,
      }),
    });
  },
  googleLogin(payload) {
    return apiRequest("/api/auth/google", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  authConfig() {
    return apiRequest("/api/auth/config");
  },
  me() {
    return apiRequest("/api/auth/me");
  },
  updateProfile(payload) {
    return apiRequest("/api/auth/me", { method: "PATCH", body: JSON.stringify(payload) });
  },
  requestPasswordOtp() {
    return apiRequest("/api/auth/password/request-otp", {
      method: "POST",
      body: "{}",
    });
  },
  changePasswordWithOtp({ otp, new_password, confirm_password }) {
    return apiRequest("/api/auth/password/change", {
      method: "POST",
      body: JSON.stringify({ otp, new_password, confirm_password }),
    });
  },
  analyzeAI({ text, file }) {
    const fd = new FormData();
    if (file) fd.append("file", file);
    if (text) fd.append("text", text);
    return apiRequest("/api/ai-detection/analyze", { method: "POST", body: fd });
  },
  plagiarismStatus() {
    return apiRequest("/api/plagiarism/status");
  },
  getOriginal() {
    return apiRequest("/api/plagiarism/original");
  },
  registerOriginal(file) {
    const fd = new FormData();
    fd.append("file", file);
    return apiRequest("/api/plagiarism/original", { method: "POST", body: fd });
  },
  deleteOriginal() {
    return apiRequest("/api/plagiarism/original", { method: "DELETE" });
  },
  compareToOriginal(file) {
    const fd = new FormData();
    fd.append("file", file);
    return apiRequest("/api/plagiarism/compare", { method: "POST", body: fd });
  },
};
