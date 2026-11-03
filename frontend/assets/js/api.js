// Change this URL if your FastAPI server uses another host or port.
const API_BASE_URL = "http://localhost:8000";

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch (_) {}
    throw new Error(message);
  }

  if (response.status === 204) return null;
  return response.json();
}

const applicationsApi = {
  getAll: () => apiRequest("/applications/"),
  getById: (id) => apiRequest(`/applications/${id}`),
  create: (data) => apiRequest("/applications/", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  update: (id, data) => apiRequest(`/applications/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data)
  }),
  remove: (id) => apiRequest(`/applications/${id}`, { method: "DELETE" }),
  sync: () => apiRequest("/applications/sync", { method: "POST" })
};

function showToast(message, isError = false) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.toggle("toast-error", isError);
  toast.classList.add("visible");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => toast.classList.remove("visible"), 3200);
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

function statusLabel(status) {
  const labels = {
    PENDING: "Pending",
    INTERVIEW: "Interview",
    INTERVIEW_CONFIRMED: "Interview confirmed",
    REJECTED: "Rejected",
    OFFER_RECEIVED: "Offer received",
    UNKNOWN: "Unknown"
  };
  return labels[status] || status || "Unknown";
}

function statusClass(status) {
  return (status || "unknown").toLowerCase().replaceAll("_", "-");
}
