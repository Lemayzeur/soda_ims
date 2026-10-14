async function loadAlertsPage() {
  await loadAdmins();
  await loadAlertHistory();
}

async function loadAdmins() {
  const el = document.getElementById("admin-list");
  el.innerHTML = "<p class='hint'>Loading...</p>";
  try {
    const admins = await API.getAdmins();
    el.innerHTML = admins.length
      ? admins.map(a => `<span class="email-chip">${escapeHtml(a.email)} <button onclick="removeAdmin(${a.id})">✕</button></span>`).join("")
      : "<p class='hint'>No admins yet — add one below.</p>";
  } catch (e) {
    el.innerHTML = `<p class="hint">Failed to load admins: ${e.message}</p>`;
  }
}

async function addAdmin(event) {
  event.preventDefault();
  const input = document.getElementById("new-admin-email");
  try {
    await API.addAdminEmail(input.value.trim());
    input.value = "";
    loadAdmins();
  } catch (e) {
    alert(e.message);
  }
}

async function removeAdmin(id) {
  try {
    await API.deleteAdmin(id);
    loadAdmins();
  } catch (e) {
    alert("Could not remove admin: " + e.message);
  }
}

async function loadAlertHistory() {
  const el = document.getElementById("alerts-history");
  el.innerHTML = "<p class='hint' style='padding:16px 22px;'>Loading...</p>";
  try {
    const alerts = await API.getAlerts();
    el.innerHTML = alerts.length
      ? alerts.map(a => `
          <div class="activity-item">
            <div class="activity-time">${formatLocalTimestamp(a.created_at_local) ?? new Date(a.created_at).toLocaleString()}</div>
            <div class="activity-text">
              <b>${a.alert_type === "IRRIGATION" ? "Irrigation alert" : "Sensor warning"}</b>
              — ${escapeHtml(a.field_name)}: ${escapeHtml(a.message)}
              <span class="to">${a.sent_to.length ? "→ " + a.sent_to.join(", ") : ""}</span>
            </div>
          </div>
        `).join("")
      : "<p class='hint' style='padding:16px 22px;'>No alerts yet.</p>";
  } catch (e) {
    el.innerHTML = `<p class="hint">Failed to load alert history: ${e.message}</p>`;
  }
}
