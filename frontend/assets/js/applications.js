let allApplications = [];
let currentDetailsItem = null;

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("add-button").addEventListener("click", () => openDialog());
  document.getElementById("close-dialog").addEventListener("click", closeDialog);
  document.getElementById("cancel-dialog").addEventListener("click", closeDialog);
  document.getElementById("application-form").addEventListener("submit", saveApplication);
  document.getElementById("search-input").addEventListener("input", renderApplications);
  document.getElementById("status-filter").addEventListener("change", renderApplications);

  const detailsDialog = document.getElementById("details-dialog");
  document.getElementById("close-details-dialog")?.addEventListener("click", closeDetailsDialog);
  document.getElementById("done-details-button")?.addEventListener("click", closeDetailsDialog);
  document.getElementById("edit-from-details-button")?.addEventListener("click", () => {
    const itemToEdit = currentDetailsItem;
    closeDetailsDialog();
    if (itemToEdit) openDialog(itemToEdit);
  });
  detailsDialog?.addEventListener("click", event => {
    if (event.target === detailsDialog) closeDetailsDialog();
  });

  const formDialog = document.getElementById("application-dialog");
  formDialog?.addEventListener("click", event => {
    if (event.target === formDialog) closeDialog();
  });

  loadApplications();

  if (window.location.hash === "#new") openDialog();
});

async function loadApplications() {
  const tbody = document.getElementById("applications-table");
  try {
    allApplications = await applicationsApi.getAll();
    document.getElementById("list-count").textContent = allApplications.length;
    renderApplications();

    const params = new URLSearchParams(window.location.search);
    const viewId = Number(params.get("view"));
    if (viewId) {
      openDetailsDialog(viewId);
      window.history.replaceState({}, "", window.location.pathname);
    }
  } catch (error) {
    tbody.innerHTML = `<tr><td colspan="7" class="error-cell">${escapeHtml(error.message)}. Check that FastAPI is running and CORS is configured.</td></tr>`;
    showToast("Could not load applications.", true);
  }
}

function renderApplications() {
  const query = document.getElementById("search-input").value.trim().toLowerCase();
  const status = document.getElementById("status-filter").value;
  const filtered = allApplications.filter(item => {
    const matchesQuery = `${item.company} ${item.position} ${item.summary || ""}`.toLowerCase().includes(query);
    return matchesQuery && (!status || item.status === status);
  });
  document.getElementById("list-count").textContent = filtered.length;
  const tbody = document.getElementById("applications-table");

  tbody.innerHTML = filtered.length ? filtered.map(item => {
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
          <button class="small-action" data-edit="${item.id}">Edit</button>
          <button class="small-action danger-action" data-delete="${item.id}">Delete</button>
        </td>
      </tr>`;
  }).join("") : '<tr><td colspan="7" class="empty-cell">No matching applications found.</td></tr>';

  tbody.querySelectorAll("[data-view]").forEach(button => {
    button.addEventListener("click", () => openDetailsDialog(Number(button.dataset.view)));
  });
  tbody.querySelectorAll("[data-edit]").forEach(button => {
    button.addEventListener("click", () => {
      const item = allApplications.find(app => app.id === Number(button.dataset.edit));
      if (item) openDialog(item);
    });
  });
  tbody.querySelectorAll("[data-delete]").forEach(button => {
    button.addEventListener("click", () => deleteApplication(Number(button.dataset.delete)));
  });
}

async function openDetailsDialog(id) {
  const dialog = document.getElementById("details-dialog");
  if (!dialog) return;

  const cached = allApplications.find(app => app.id === id);
  if (cached) {
    currentDetailsItem = cached;
    populateDetailsModal(cached, dialog);
  }
  if (!dialog.open) dialog.showModal();

  try {
    const fresh = await applicationsApi.getById(id);
    currentDetailsItem = fresh;
    const index = allApplications.findIndex(app => app.id === id);
    if (index !== -1) allApplications[index] = fresh;
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

function openDialog(item = null) {
  const form = document.getElementById("application-form");
  form.reset();
  document.getElementById("application-id").value = item?.id ?? "";
  document.getElementById("dialog-title").textContent = item ? "Edit application" : "Add application";
  document.getElementById("company").value = item?.company ?? "";
  document.getElementById("position").value = item?.position ?? "";
  document.getElementById("summary").value = item?.summary ?? "";
  document.getElementById("status").value = item?.status ?? "PENDING";
  document.getElementById("email-category").value = item?.email_category ?? "";
  document.getElementById("interview-date").value = item?.interview_date ?? "";
  document.getElementById("interview-time").value = item?.interview_time?.slice(0, 5) ?? "";
  document.getElementById("confidence").value = item?.confidence ?? "";
  document.getElementById("application-dialog").showModal();
}

function closeDialog() {
  document.getElementById("application-dialog").close();
}

async function saveApplication(event) {
  event.preventDefault();
  const id = document.getElementById("application-id").value;
  const saveButton = document.getElementById("save-button");
  const data = {
    company: document.getElementById("company").value.trim(),
    position: document.getElementById("position").value.trim(),
    summary: document.getElementById("summary").value.trim() || null,
    status: document.getElementById("status").value,
    email_category: document.getElementById("email-category").value || null,
    interview_date: document.getElementById("interview-date").value || null,
    interview_time: document.getElementById("interview-time").value || null,
    confidence: document.getElementById("confidence").value === "" ? null : Number(document.getElementById("confidence").value)
  };

  if (saveButton) saveButton.disabled = true;
  try {
    if (id) {
      await applicationsApi.update(id, data);
      showToast("Application updated.");
    } else {
      data.application_key = createApplicationKey(data.company, data.position);
      await applicationsApi.create(data);
      showToast("Application added.");
    }
    closeDialog();
    await loadApplications();
  } catch (error) {
    showToast(error.message, true);
  } finally {
    if (saveButton) saveButton.disabled = false;
  }
}

async function deleteApplication(id) {
  const item = allApplications.find(app => app.id === id);
  if (!item || !window.confirm(`Delete the application for ${item.company} — ${item.position}? This cannot be undone.`)) return;
  try {
    await applicationsApi.remove(id);
    showToast("Application deleted.");
    await loadApplications();
  } catch (error) {
    showToast(error.message, true);
  }
}

function createApplicationKey(company, position) {
  return `${company}_${position}`.toLowerCase()
    .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "").slice(0, 255);
}
