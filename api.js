const BASE = import.meta.env.VITE_API_URL || "/api";

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("Cannot reach the HumanTwin backend. Make sure it is running on port 8000.");
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  health: () => request("/health"),
  getProfile: () => request("/profile"),
  updateProfile: (payload) => request("/profile", { method: "PUT", body: JSON.stringify(payload) }),
  getGoals: () => request("/goals"),
  createGoal: (payload) => request("/goals", { method: "POST", body: JSON.stringify(payload) }),
  getTasks: () => request("/tasks"),
  createTask: (payload) => request("/tasks", { method: "POST", body: JSON.stringify(payload) }),
  updateTask: (id, payload) => request(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  deleteTask: (id) => request(`/tasks/${id}`, { method: "DELETE" }),
  getTwin: () => request("/twin"),
  getContext: () => request("/twin/context"),
  getPatterns: () => request("/patterns"),
  resetTwin: () => request("/twin/reset", { method: "POST" }),
  whatIf: (payload) => request("/what-if", { method: "POST", body: JSON.stringify(payload) }),
  feedback: (payload) => request("/feedback", { method: "POST", body: JSON.stringify(payload) }),
  getPermissions: () => request("/permissions"),
  updatePermission: (payload) => request("/permissions", { method: "PUT", body: JSON.stringify(payload) }),
  deleteCategoryData: (category) => request(`/permissions/${category}/data`, { method: "DELETE" }),
  loadDemo: () => request("/demo/load", { method: "POST" }),
  chat: (message) => request("/chat", { method: "POST", body: JSON.stringify({ message }) }),
};