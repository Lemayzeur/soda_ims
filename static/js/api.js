const API = {
  async _req(url, opts = {}) {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw new Error(err.error || "Request failed");
    }
    if (res.status === 204) return null;
    return res.json();
  },

  getFields: () => API._req("/api/fields"),
  getField: (id) => API._req(`/api/fields/${id}`),
  createField: (data) => API._req("/api/fields", { method: "POST", body: JSON.stringify(data) }),
  updateField: (id, data) => API._req(`/api/fields/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteField: (id) => API._req(`/api/fields/${id}`, { method: "DELETE" }),

  addLogger: (fieldId, data) => API._req(`/api/fields/${fieldId}/loggers`, { method: "POST", body: JSON.stringify(data) }),
  updateLogger: (id, data) => API._req(`/api/loggers/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteLogger: (id) => API._req(`/api/loggers/${id}`, { method: "DELETE" }),

  getAdmins: () => API._req("/api/admins"),
  addAdminEmail: (email) => API._req("/api/admins", { method: "POST", body: JSON.stringify({ email }) }),
  deleteAdmin: (id) => API._req(`/api/admins/${id}`, { method: "DELETE" }),

  getDashboard: () => API._req("/api/dashboard"),
  getAlerts: () => API._req("/api/alerts"),

  checkNow: () => API._req("/api/check-now", { method: "POST" }),
  checkField: (id) => API._req(`/api/check-now/${id}`, { method: "POST" }),

  getForecast: (fieldId) => API._req(`/api/forecast/${fieldId}`),
  getTimezones: () => API._req("/api/timezones"),
};
