let allApplications = [];

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("add-button").addEventListener("click", () => openDialog());
  document.getElementById("close-dialog").addEventListener("click", closeDialog);
  document.getElementById("cancel-dialog").addEventListener("click", closeDialog);
  document.getElementById("application-form").addEventListener("submit", saveApplication);
  document.getElementById("search-input").addEventListener("input", renderApplications);
  document.getElementById("status-filter").addEventListener("change", renderApplications);
  loadApplications();

  if (window.location.hash === "#new") openDialog();
});

async function loadApplications() {
  const tbody = document.getElementById("applications-table");
  try {
    allApplications = await applicationsApi.getAll();
    document.getElementById("list-count").textContent = allApplications.length;
    renderApplications();
  } catch (error) {
    tbody.innerHTML = `<tr><td colspan="4" class="error-cell">${escapeHtml(error.message)}. Check that FastAPI is running and CORS is configured.</td></tr>`;
    showToast("Could not load applications.", true);
  }
}

function renderApplications() {
  const query = document.getElementById("search-input").value.trim().toLowerCase();
  const status = document.getElementById("status-filter").value;
  const filtered = allApplications.filter(item => {
    const matchesQuery = `${item.company} ${item.position}`.toLowerCase().includes(query);
    return matchesQuery && (!status || item.status === status);
  });
  document.getElementById("list-count").textContent = filtered.length;
  const tbody = document.getElementById("applications-table");
  tbody.innerHTML = filtered.length ? filtered.map(item => `
    <tr>
      <td><div class="company-cell"><span class="company-avatar">${escapeHtml((item.company || "?").slice(0, 1).toUpperCase())}</span><div><strong>${escapeHtml(item.company)}</strong><small>${escapeHtml(item.position)}</small></div></div></td>
      <td><span class="status-badge ${statusClass(item.status)}">${statusLabel(item.status)}</span></td>
      <td class="date-cell">${formatDate(item.last_email_at || item.created_at)}</td>
      <td class="row-actions"><button class="small-action" data-edit="${item.id}">Edit</button><button class="small-action danger-action" data-delete="${item.id}">Delete</button></td>
    </tr>`).join("") : '<tr><td colspan="4" class="empty-cell">No matching applications found.</td></tr>';

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

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}
