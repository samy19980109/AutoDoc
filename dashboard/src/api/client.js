const API_BASE = "/api";

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const headers = { ...options.headers };

  const isFormData = options.body instanceof FormData;
  if (!isFormData) {
    headers["Content-Type"] = "application/json";
  }

  const apiKey = localStorage.getItem("api_key");
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  const authToken = localStorage.getItem("auth_token");
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(url, { ...options, headers });

  if (response.status === 204) {
    return null;
  }

  const text = await response.text();
  let payload = null;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { detail: text };
    }
  }

  if (!response.ok) {
    const detail = payload?.detail || response.statusText || "Request failed";
    throw new Error(detail);
  }

  return payload;
}

export const api = {
  // Auth
  login: (username, password) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),

  // Repositories
  listRepos: (skip = 0, limit = 50) => request(`/repos?skip=${skip}&limit=${limit}`),
  getRepo: (id) => request(`/repos/${id}`),
  createRepo: (data) => request("/repos", { method: "POST", body: JSON.stringify(data) }),
  updateRepo: (id, data) => request(`/repos/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteRepo: (id) => request(`/repos/${id}`, { method: "DELETE" }),
  triggerRepo: (id, triggerType = "manual") =>
    request(`/repos/${id}/trigger?trigger_type=${encodeURIComponent(triggerType)}`, { method: "POST" }),

  // Jobs
  listJobs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/jobs${query ? `?${query}` : ""}`);
  },
  getJob: (id) => request(`/jobs/${id}`),
  getJobLogs: (id) => request(`/jobs/${id}/logs`),

  // Mappings
  listMappings: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/mappings${query ? `?${query}` : ""}`);
  },
  getMapping: (id) => request(`/mappings/${id}`),
  deleteMapping: (id) => request(`/mappings/${id}`, { method: "DELETE" }),
};
