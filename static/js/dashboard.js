async function loadDashboard() {
  const tableEl = document.getElementById("dashboard-fields-table");
  const summaryEl = document.getElementById("dashboard-summary");
  tableEl.innerHTML = "<p class='hint' style='padding:20px;'>Loading...</p>";

  try {
    const data = await API.getDashboard();
    renderSummary(summaryEl, data.summary);
    renderFieldsTable(tableEl, data.fields);
  } catch (e) {
    tableEl.innerHTML = `<p class="hint" style="padding:20px;">Failed to load dashboard: ${e.message}</p>`;
  }

  try {
    const alerts = await API.getAlerts();
    renderRecentAlerts(alerts.slice(0, 5));
  } catch (e) {
    /* non-fatal for the dashboard */
  }
}

function renderSummary(el, summary) {
  el.innerHTML = `
    <div class="summary-card"><div class="num">${summary.total_fields}</div><div class="label">Fields monitored</div></div>
    <div class="summary-card warn"><div class="num">${summary.needs_water}</div><div class="label">Need irrigation</div></div>
    <div class="summary-card ok"><div class="num">${summary.ok}</div><div class="label">No action needed</div></div>
    <div class="summary-card info"><div class="num">${summary.issues}</div><div class="label">Sensor issues</div></div>
  `;
}

function statusFor(latest) {
  if (!latest) return { label: "No checks yet", cls: "nodata" };
  if (latest.decision === "IRRIGATED") return { label: "Needs water", cls: "needs" };
  if (latest.decision === "OK") return { label: "OK", cls: "ok" };
  if (latest.decision === "PARTIAL") return { label: "Partial data", cls: "partial" };
  return { label: "No data", cls: "nodata" };
}

function renderFieldsTable(container, rows) {
  if (!rows.length) {
    container.innerHTML = `<p class="hint" style="padding:20px;">No fields yet — add one on the Manage Fields page.</p>`;
    return;
  }

  const rowsHtml = rows.map(({ field, latest }) => {
    const status = statusFor(latest);
    const loggerLine = field.loggers
      .map(l => `${l.serial_number} (${l.port_mode === "exclude" ? "excl " : ""}${l.ports.join(",")})`)
      .join(" · ") || "No loggers configured";

    let readingsHtml = "<span class='hint'>No reading yet — try Check now</span>";
    if (latest) {
      readingsHtml = `
        <div>Average: ${latest.average_vwc ?? "—"} <span class="range">(min ${latest.min_vwc ?? "—"} – max ${latest.max_vwc ?? "—"})</span></div>
        <div class="timestamp">${formatLocalTimestamp(latest.timestamp_local) ?? "—"}</div>
      `;
    }

    let actionHtml = "<span class='dash'>—</span>";
    if (latest && latest.decision === "IRRIGATED") {
      actionHtml = `<div class="amt">≈ ${latest.liters_needed} L</div><div class="dur">Run for ${latest.runtime_hours}h ${latest.runtime_minutes}m</div>`;
    } else if (latest && latest.decision === "OK") {
      actionHtml = `<span class='dash'>No irrigation needed</span>`;
    } else if (latest && latest.decision === "PARTIAL") {
      actionHtml = `<span class='dash'>Check sensors</span>`;
    }

    const nextDue = field.next_check_due_local
      ? `<div class="timestamp">Next due: ${formatLocalTimestamp(field.next_check_due_local)} (${escapeHtml(field.timezone)})</div>`
      : "";

    const hasDetail = latest && latest.ports && latest.ports.length > 0;

    return `
      <div class="field-row">
        <div>
          <div class="field-name">${escapeHtml(field.name)}</div>
          <div class="field-logger mono">${escapeHtml(loggerLine)}</div>
          ${nextDue}
        </div>
        <div class="readings">${readingsHtml}</div>
        <div><span class="status-pill ${status.cls}"><span class="dot"></span>${status.label}</span></div>
        <div class="action-block">${actionHtml}</div>
        <div class="row-actions">
          <button class="btn ghost small" onclick="checkFieldNow(${field.id}, this)">Check now</button>
          ${hasDetail ? `<button class="btn ghost small detail-toggle" id="toggle-${field.id}" onclick="toggleFieldDetail(${field.id})">▸ Sensors</button>` : ""}
        </div>
      </div>
      ${hasDetail ? `<div class="field-detail hidden" id="detail-${field.id}">${renderPortDetail(field, latest)}</div>` : ""}
    `;
  }).join("");

  container.innerHTML = `
    <div class="field-row header">
      <div>Field</div><div>Latest readings</div><div>Status</div><div>Recommended action</div><div></div>
    </div>
    ${rowsHtml}
  `;
}

function renderPortDetail(field, latest) {
  const loggerBlocks = latest.ports.map(loggerEntry => {
    const portsHtml = loggerEntry.ports.map(p => {
      if (p.error || p.value === null) {
        return `<div class="detail-port-row err">Port ${p.port_number}: sensor error, no reading</div>`;
      }
      const below = p.value < field.trigger_threshold;
      return `<div class="detail-port-row ${below ? "low" : ""}">Port ${p.port_number}: ${p.value} m³/m³${below ? " ⚠ below threshold" : ""}</div>`;
    }).join("");

    const battery = loggerEntry.battery_percent != null ? ` · Battery ${loggerEntry.battery_percent}%` : "";

    return `
      <div class="detail-logger">
        <div class="detail-logger-head mono">${escapeHtml(loggerEntry.serial_number)}${battery}</div>
        ${portsHtml}
      </div>
    `;
  }).join("");

  return `<div class="field-detail-inner">${loggerBlocks}</div>`;
}

function toggleFieldDetail(fieldId) {
  const detail = document.getElementById(`detail-${fieldId}`);
  const btn = document.getElementById(`toggle-${fieldId}`);
  const isHidden = detail.classList.contains("hidden");
  detail.classList.toggle("hidden");
  btn.textContent = isHidden ? "▾ Sensors" : "▸ Sensors";
}

function renderRecentAlerts(alerts) {
  const el = document.getElementById("dashboard-alerts");
  if (!alerts.length) {
    el.innerHTML = "<p class='hint' style='padding:16px 22px;'>No alerts yet.</p>";
    return;
  }
  el.innerHTML = alerts.map(a => `
    <div class="activity-item">
      <div class="activity-time">${formatLocalTimestamp(a.created_at_local) ?? new Date(a.created_at).toLocaleString()}</div>
      <div class="activity-text">
        <b>${a.alert_type === "IRRIGATION" ? "Irrigation alert" : "Sensor warning"}</b>
        for ${escapeHtml(a.field_name)} — ${escapeHtml(a.message)}
        <span class="to">${a.sent_to.length ? "sent to " + a.sent_to.join(", ") : "(not sent — no admins or credentials configured)"}</span>
      </div>
    </div>
  `).join("");
}

function decisionSummary(result) {
  if (result.decision === "IRRIGATED") {
    return `needs ~${result.liters_needed} L, run ${result.runtime_hours}h ${result.runtime_minutes}m`;
  }
  if (result.decision === "OK") return "no irrigation needed";
  if (result.decision === "PARTIAL") return `${result.num_ports_error} sensor(s) not reporting`;
  return "no data received";
}

async function checkNowAll(btn) {
  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span>Checking all fields...`;

  try {
    const response = await API.checkNow();
    const results = response.results || [];
    const irrigated = results.filter(r => r.decision === "IRRIGATED").length;
    showToast(
      `✓ Checked ${response.checked} field${response.checked === 1 ? "" : "s"} — ${irrigated} need${irrigated === 1 ? "s" : ""} water`,
      "success"
    );
    await loadDashboard();
  } catch (e) {
    showToast(`✕ Check failed: ${e.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.innerHTML = original;
  }
}

async function checkFieldNow(fieldId, btn) {
  const original = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span>Checking...`;

  try {
    const result = await API.checkField(fieldId);
    showToast(`✓ ${result.field_name}: ${decisionSummary(result)}`, result.decision === "IRRIGATED" ? "info" : "success");
    await loadDashboard();
  } catch (e) {
    showToast(`✕ Check failed for this field: ${e.message}`, "error");
    btn.disabled = false;
    btn.innerHTML = original;
  }
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
