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
      if (typeof body.detail === "string") {
        message = body.detail;
      } else if (Array.isArray(body.detail) && body.detail.length > 0) {
        message = body.detail.map(err => err.msg || JSON.stringify(err)).join(", ");
      }
    } catch (_) {}
    throw new Error(message);
  }

  if (response.status === 204) return null;
  return response.json();
}

const applicationsApi = {
  getAll: () => apiRequest("/applications/"),
  getById: (id) => apiRequest(`/applications/${id}`),
  getActivities: (id) => apiRequest(`/applications/${id}/activities`),
  create: (data) => apiRequest("/applications/", {
    method: "POST",
    body: JSON.stringify(data)
  }),
  update: (id, data) => apiRequest(`/applications/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data)
  }),
  remove: (id) => apiRequest(`/applications/${id}`, { method: "DELETE" }),
  sync: (data) => apiRequest("/applications/sync", {
    method: "POST",
    body: JSON.stringify(data)
  })
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

function parseDateValue(value) {
  if (!value) return null;
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value.trim())) {
    const [year, month, day] = value.trim().split("-").map(Number);
    return new Date(year, month - 1, day);
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatDate(value) {
  const date = parseDateValue(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(date);
}

function formatDateTime(value) {
  const date = parseDateValue(value);
  if (!date) return "—";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false
  }).format(date);
}

function isInterviewStatus(status) {
  return status === "INTERVIEW" || status === "INTERVIEW_CONFIRMED";
}

function formatInterviewDateCell(item) {
  if (!isInterviewStatus(item?.status)) {
    return { text: "—", isMuted: true, isMissing: false };
  }
  const date = parseDateValue(item?.interview_date);
  if (!date) {
    return { text: "Not specified", isMuted: false, isMissing: true };
  }
  return {
    text: new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric"
    }).format(date),
    isMuted: false,
    isMissing: false
  };
}

function formatInterviewTimeCell(item) {
  if (!isInterviewStatus(item?.status)) {
    return { text: "—", isMuted: true, isMissing: false };
  }
  const raw = item?.interview_time;
  if (!raw || typeof raw !== "string" || !raw.trim()) {
    return { text: "Not specified", isMuted: false, isMissing: true };
  }
  const normalized = raw.trim().slice(0, 5);
  return {
    text: normalized,
    isMuted: false,
    isMissing: false
  };
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

function emailCategoryLabel(category) {
  if (!category) return "Not specified";
  const labels = {
    APPLICATION_RECEIVED: "Application received",
    INTERVIEW_INVITATION: "Interview invitation",
    INTERVIEW_CONFIRMED: "Interview confirmed",
    REJECTION: "Rejection",
    OFFER_RECEIVED: "Offer received",
    OTHER: "Other",
    UNKNOWN: "Unknown"
  };
  return labels[category] || category;
}

function statusClass(status) {
  return (status || "unknown").toLowerCase().replaceAll("_", "-");
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  })[char]);
}

function renderHistoryTimeline(item) {
  const activities = Array.isArray(item?.activities)
    ? [...item.activities].sort((a, b) => new Date(a.event_at) - new Date(b.event_at))
    : [];

  const baselineEvents = [];

  const hasCreatedEvent = activities.some(ev => ev.event_type === "CREATED");
  if (!hasCreatedEvent && item?.created_at) {
    const initialCategory = item.email_category ? `${emailCategoryLabel(item.email_category)} · ` : "";
    baselineEvents.push({
      event_type: "RECORDED",
      title: `Application recorded → ${statusLabel(item.status)}`,
      description: `${initialCategory}${item.company} — ${item.position}`,
      event_at: item.last_email_at || item.created_at
    });

    if (isInterviewStatus(item.status) && (item.interview_date || item.interview_time)) {
      const dateStr = item.interview_date ? formatDate(item.interview_date) : "Not specified";
      const timeStr = item.interview_time ? item.interview_time.slice(0, 5) : "Not specified";
      baselineEvents.push({
        event_type: "INTERVIEW_SCHEDULED",
        title: `Interview scheduled → ${dateStr} (${timeStr})`,
        description: `Date: ${dateStr} · Time: ${timeStr}`,
        event_at: item.updated_at || item.last_email_at || item.created_at
      });
    }
  }

  const allEvents = [...baselineEvents, ...activities];

  if (allEvents.length === 0) {
    return `<div class="timeline-empty">No activity events recorded yet for this application.</div>`;
  }

  return `
    <ol class="activity-timeline">
      ${allEvents.map((ev, index) => `
        <li class="timeline-item ${index === allEvents.length - 1 ? "timeline-latest" : ""}">
          <span class="timeline-dot" aria-hidden="true"></span>
          <div class="timeline-body">
            <div class="timeline-header">
              <strong class="timeline-title">${escapeHtml(ev.title)}</strong>
              <time class="timeline-time">${escapeHtml(formatDateTime(ev.event_at))}</time>
            </div>
            ${ev.description ? `<p class="timeline-desc">${escapeHtml(ev.description)}</p>` : ""}
          </div>
        </li>
      `).join("")}
    </ol>
  `;
}

function populateDetailsModal(item, dialogEl) {
  if (!item || !dialogEl) return;

  const setText = (selector, text) => {
    const el = dialogEl.querySelector(selector);
    if (el) el.textContent = text;
  };

  setText("[data-detail-company]", item.company || "—");
  setText("[data-detail-position]", item.position || "—");

  const badgeEl = dialogEl.querySelector("[data-detail-status]");
  if (badgeEl) {
    badgeEl.className = `status-badge ${statusClass(item.status)}`;
    badgeEl.textContent = statusLabel(item.status);
  }

  const summaryEl = dialogEl.querySelector("[data-detail-summary]");
  if (summaryEl) {
    summaryEl.textContent = item.summary?.trim() ? item.summary : "No summary provided for this application.";
    summaryEl.classList.toggle("muted-value", !item.summary?.trim());
  }

  const confidenceText = item.confidence != null
    ? `${Math.round(Number(item.confidence) * 100)}% (${Number(item.confidence).toFixed(2)})`
    : "Not specified";
  setText("[data-detail-confidence]", confidenceText);
  setText("[data-detail-category]", emailCategoryLabel(item.email_category));
  setText("[data-detail-created]", formatDateTime(item.created_at));
  setText("[data-detail-updated]", formatDateTime(item.updated_at));
  setText("[data-detail-last-email]", item.last_email_at ? formatDateTime(item.last_email_at) : "Not specified");
  setText("[data-detail-key]", item.application_key || "—");

  // Interview section
  const interviewDateEl = dialogEl.querySelector("[data-detail-interview-date]");
  const interviewTimeEl = dialogEl.querySelector("[data-detail-interview-time]");
  const interviewNoteEl = dialogEl.querySelector("[data-detail-interview-note]");

  const hasInterview = isInterviewStatus(item.status) || item.interview_date || item.interview_time;
  const formattedDate = item.interview_date
    ? formatDate(item.interview_date)
    : (isInterviewStatus(item.status) ? "Not specified" : "—");
  const formattedTime = item.interview_time
    ? item.interview_time.slice(0, 5)
    : (isInterviewStatus(item.status) ? "Not specified" : "—");

  if (interviewDateEl) {
    interviewDateEl.textContent = formattedDate;
    interviewDateEl.classList.toggle("missing-pill", formattedDate === "Not specified");
  }
  if (interviewTimeEl) {
    interviewTimeEl.textContent = formattedTime;
    interviewTimeEl.classList.toggle("missing-pill", formattedTime === "Not specified");
  }
  if (interviewNoteEl) {
    if (isInterviewStatus(item.status)) {
      if (item.interview_date && item.interview_time) {
        interviewNoteEl.textContent = `Scheduled for ${formattedDate} at ${formattedTime} (24h).`;
      } else {
        interviewNoteEl.textContent = "Status is set to Interview, but full schedule details have not been specified yet.";
      }
    } else if (hasInterview) {
      interviewNoteEl.textContent = `Recorded interview date/time while current status is ${statusLabel(item.status)}.`;
    } else {
      interviewNoteEl.textContent = "No interview scheduled for this application.";
    }
  }

  // Activity timeline
  const timelineContainer = dialogEl.querySelector("[data-detail-timeline]");
  if (timelineContainer) {
    timelineContainer.innerHTML = renderHistoryTimeline(item);
  }
}
