const API_BASE = "/api";

async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const headers = { "Content-Type": "application/json", ...options.headers };
  const apiKey = localStorage.getItem("api_key");
  if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }

  const response = await fetch(url, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || "Request failed");
  }
  return response.json();
}

export const api = {
  // Repositories
  listRepos: (skip = 0, limit = 50) => request(`/repos?skip=${skip}&limit=${limit}`),
  getRepo: (id) => request(`/repos/${id}`),
  createRepo: (data) => request("/repos", { method: "POST", body: JSON.stringify(data) }),
  updateRepo: (id, data) => request(`/repos/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteRepo: (id) => request(`/repos/${id}`, { method: "DELETE" }),
  triggerRepo: (id) => request(`/repos/${id}/trigger`, { method: "POST" }),

  // Jobs
  listJobs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/jobs?${query}`);
  },
  getJob: (id) => request(`/jobs/${id}`),
  getJobLogs: (id) => request(`/jobs/${id}/logs`),

  // Mappings
  listMappings: (repoId) => request(`/mappings?repo_id=${repoId}`),
  deleteMapping: (id) => request(`/mappings/${id}`, { method: "DELETE" }),
};
