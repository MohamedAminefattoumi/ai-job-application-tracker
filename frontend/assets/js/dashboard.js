document.addEventListener("DOMContentLoaded", () => {
  loadDashboard();
  document.getElementById("sync-button")?.addEventListener("click", syncApplications);
});

async function loadDashboard() {
  document.getElementById("today-date").textContent = new Intl.DateTimeFormat("en-GB", {
    weekday: "short", day: "numeric", month: "short", year: "numeric"
  }).format(new Date());

  try {
    const applications = await applicationsApi.getAll();
    const items = Array.isArray(applications) ? applications : [];
    document.getElementById("total-count").textContent = items.length;
    document.getElementById("pending-count").textContent = items.filter(x => x.status === "PENDING").length;
    document.getElementById("interview-count").textContent = items.filter(x => x.status === "INTERVIEW").length;
    document.getElementById("offer-count").textContent = items.filter(x => x.status === "OFFER_RECEIVED").length;
    document.getElementById("rejected-count").textContent = items.filter(x => x.status === "REJECTED").length;

    const recent = items.slice(0, 5);
    const tbody = document.getElementById("recent-applications");
    tbody.innerHTML = recent.length ? recent.map(item => `
      <tr>
        <td><div class="company-cell"><span class="company-avatar">${escapeHtml((item.company || "?").slice(0, 1).toUpperCase())}</span><div><strong>${escapeHtml(item.company)}</strong><small>${escapeHtml(item.position)}</small></div></div></td>
        <td><span class="status-badge ${statusClass(item.status)}">${statusLabel(item.status)}</span></td>
        <td class="date-cell">${formatDate(item.last_email_at || item.created_at)}</td>
      </tr>`).join("") : '<tr><td colspan="3" class="empty-cell">No applications yet. Add your first opportunity.</td></tr>';
  } catch (error) {
    document.getElementById("recent-applications").innerHTML =
      `<tr><td colspan="3" class="error-cell">${escapeHtml(error.message)}. Check that FastAPI is running and CORS is configured.</td></tr>`;
    showToast("Could not load applications.", true);
  }
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}

async function syncApplications() {
  const button = document.getElementById("sync-button");
  if (!button) return;
  button.disabled = true; button.textContent = "↻ Syncing…";
  try {
    await applicationsApi.sync();
    showToast("Inbox synchronization completed.");
    await loadDashboard();
  } catch (error) {
    showToast(error.message || "Synchronization failed.", true);
  } finally {
    button.disabled = false; button.textContent = "↻ Sync inbox";
  }
}
