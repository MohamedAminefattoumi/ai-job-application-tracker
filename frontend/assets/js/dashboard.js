let recentApplications = [];

document.addEventListener("DOMContentLoaded", () => {
  loadDashboard();
  document.getElementById("sync-button")?.addEventListener("click", refreshDashboard);

  const detailsDialog = document.getElementById("details-dialog");
  document.getElementById("close-details-dialog")?.addEventListener("click", closeDetailsDialog);
  document.getElementById("done-details-button")?.addEventListener("click", closeDetailsDialog);
  detailsDialog?.addEventListener("click", event => {
    if (event.target === detailsDialog) closeDetailsDialog();
  });
});

async function loadDashboard() {
  document.getElementById("today-date").textContent = new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(new Date());

  try {
    const applications = await applicationsApi.getAll();
    const items = Array.isArray(applications) ? applications : [];
    recentApplications = items;

    document.getElementById("total-count").textContent = items.length;
    document.getElementById("pending-count").textContent = items.filter(x => x.status === "PENDING").length;
    document.getElementById("interview-count").textContent = items.filter(x => isInterviewStatus(x.status)).length;
    document.getElementById("offer-count").textContent = items.filter(x => x.status === "OFFER_RECEIVED").length;
    document.getElementById("rejected-count").textContent = items.filter(x => x.status === "REJECTED").length;

    const recent = items.slice(0, 6);
    const tbody = document.getElementById("recent-applications");
    tbody.innerHTML = recent.length ? recent.map(item => {
      const interviewDate = formatInterviewDateCell(item);
      const interviewTime = formatInterviewTimeCell(item);
      const lastUpdated = formatDate(item.updated_at || item.last_email_at || item.created_at);

      return `
        <tr>
          <td>
            <div class="company-cell">
              <span class="company-avatar">${escapeHtml((item.company || "?").slice(0, 1).toUpperCase())}</span>
              <div><strong>${escapeHtml(item.company)}</strong></div>
            </div>
          </td>
          <td class="position-cell">${escapeHtml(item.position)}</td>
          <td><span class="status-badge ${statusClass(item.status)}">${escapeHtml(statusLabel(item.status))}</span></td>
          <td class="date-cell ${interviewDate.isMissing ? "missing-cell" : ""} ${interviewDate.isMuted ? "muted-cell" : ""}">${escapeHtml(interviewDate.text)}</td>
          <td class="date-cell ${interviewTime.isMissing ? "missing-cell" : ""} ${interviewTime.isMuted ? "muted-cell" : ""}">${escapeHtml(interviewTime.text)}</td>
          <td class="date-cell">${escapeHtml(lastUpdated)}</td>
          <td class="row-actions">
            <button class="small-action primary-action" data-view="${item.id}">View Details</button>
          </td>
        </tr>`;
    }).join("") : '<tr><td colspan="7" class="empty-cell">No applications yet. Add your first opportunity.</td></tr>';

    tbody.querySelectorAll("[data-view]").forEach(button => {
      button.addEventListener("click", () => openDetailsDialog(Number(button.dataset.view)));
    });
  } catch (error) {
    document.getElementById("recent-applications").innerHTML =
      `<tr><td colspan="7" class="error-cell">${escapeHtml(error.message)}. Check that FastAPI is running and CORS is configured.</td></tr>`;
    showToast("Could not load applications.", true);
  }
}

async function openDetailsDialog(id) {
  const dialog = document.getElementById("details-dialog");
  if (!dialog) return;

  const cached = recentApplications.find(app => app.id === id);
  if (cached) {
    populateDetailsModal(cached, dialog);
  }
  if (!dialog.open) dialog.showModal();

  try {
    const fresh = await applicationsApi.getById(id);
    populateDetailsModal(fresh, dialog);
  } catch (error) {
    if (!cached) {
      closeDetailsDialog();
      showToast(error.message || "Could not load application details.", true);
    }
  }
}

function closeDetailsDialog() {
  const dialog = document.getElementById("details-dialog");
  if (dialog?.open) dialog.close();
}

async function refreshDashboard() {
  const button = document.getElementById("sync-button");
  if (!button) return;
  button.disabled = true;
  button.textContent = "↻ Refreshing…";
  try {
    await loadDashboard();
    showToast("Dashboard refreshed with latest applications.");
  } catch (error) {
    showToast(error.message || "Refresh failed.", true);
  } finally {
    button.disabled = false;
    button.textContent = "↻ Refresh data";
  }
}
