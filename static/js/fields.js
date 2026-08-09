let editingFieldId = null; // null = "add" mode, otherwise the id being edited
let timezonesLoaded = false;

async function ensureTimezoneOptions() {
  if (timezonesLoaded) return;
  const select = document.getElementById("field-timezone-select");
  try {
    const zones = await API.getTimezones();
    select.innerHTML = zones.map(z => `<option value="${z}">${z}</option>`).join("");
    select.value = "America/Chicago";
    timezonesLoaded = true;
  } catch (e) {
    select.innerHTML = `<option value="America/Chicago">America/Chicago</option>`;
  }
}

async function loadFields() {
  await ensureTimezoneOptions();
  const container = document.getElementById("fields-list");
  container.innerHTML = "<p class='hint' style='padding:20px;'>Loading...</p>";
  try {
    const fields = await API.getFields();
    renderFieldsList(container, fields);
  } catch (e) {
    container.innerHTML = `<p class="hint" style="padding:20px;">Failed to load fields: ${e.message}</p>`;
  }
}

function formatLocalTimestamp(isoStringWithOffset) {
  // Server already localized this to the field's timezone and gave us
  // the wall-clock numbers directly — just format, don't re-run
  // through the browser's Date/timezone machinery or it gets converted
  // a second time.
  if (!isoStringWithOffset) return null;
  const [datePart, rest] = isoStringWithOffset.split("T");
  const timePart = rest.slice(0, 5);
  return `${datePart} ${timePart}`;
}

function renderFieldsList(container, fields) {
  if (!fields.length) {
    container.innerHTML = "<p class='hint' style='padding:20px;'>No fields yet.</p>";
    return;
  }
  container.innerHTML = fields.map(f => `
    <div class="list-row">
      <div>
        <div class="li-name">${escapeHtml(f.name)}</div>
        <div class="li-sub mono">
          ${f.loggers.map(l => `${l.serial_number} (${l.port_mode === "exclude" ? "excl " : ""}${l.ports.join(",")})`).join(" · ") || "No loggers"}
          &nbsp;·&nbsp; Threshold ${f.trigger_threshold}
          &nbsp;·&nbsp; ${escapeHtml(f.timezone)}
          ${f.next_check_due_local ? `&nbsp;·&nbsp; Next check: ${formatLocalTimestamp(f.next_check_due_local)}` : ""}
        </div>
      </div>
      <div class="li-actions">
        <button class="icon-btn" onclick="startEditField(${f.id})">Edit</button>
        <button class="icon-btn danger" onclick="removeField(${f.id}, '${escapeHtml(f.name)}')">Remove</button>
      </div>
    </div>
  `).join("");
}

async function removeField(id, name) {
  if (!confirm(`Remove "${name}" and all its loggers? This can't be undone.`)) return;
  try {
    await API.deleteField(id);
    if (editingFieldId === id) cancelEditField();
    loadFields();
    showToast(`Removed ${name}`, "success");
  } catch (e) {
    showToast("Could not remove field: " + e.message, "error");
  }
}

function addLoggerRow(prefill) {
  const wrap = document.getElementById("new-field-loggers");
  const row = document.createElement("div");
  row.className = "logger-card";
  row.innerHTML = `
    <div class="logger-card-top">
      <input type="text" placeholder="Logger serial number (e.g. z6-31580)" class="logger-sn mono" style="max-width:220px;" />
      <button type="button" class="remove-logger" onclick="this.closest('.logger-card').remove()">Remove logger</button>
    </div>
    <div class="logger-card-row">
      <div class="sub-block">
        <label>Port selection mode</label>
        <select class="logger-mode">
          <option value="include">Include only listed ports</option>
          <option value="exclude">Exclude listed ports</option>
        </select>
      </div>
      <div class="sub-block">
        <label>Ports (comma separated)</label>
        <input type="text" placeholder="e.g. 1,3" class="logger-ports mono" />
      </div>
    </div>
  `;
  wrap.appendChild(row);

  if (prefill) {
    row.querySelector(".logger-sn").value = prefill.serial_number;
    row.querySelector(".logger-mode").value = prefill.port_mode;
    row.querySelector(".logger-ports").value = prefill.ports.join(",");
  }
}

function isoLocalToDatetimeLocalValue(isoStringWithOffset) {
  // The server already localized this to the field's own timezone and
  // included the offset (e.g. "2026-08-11T06:00:00-05:00"). The wall-
  // clock digits at the front ARE what the datetime-local input should
  // show — slicing avoids re-interpreting through the browser's own
  // timezone, which would silently shift the displayed time.
  if (!isoStringWithOffset) return "";
  return isoStringWithOffset.slice(0, 16);
}

async function startEditField(id) {
  try {
    await ensureTimezoneOptions();
    const field = await API.getField(id);
    editingFieldId = id;

    const form = document.getElementById("field-form");
    form.name.value = field.name;
    form.trigger_threshold.value = field.trigger_threshold;
    form.target_vwc.value = field.target_vwc;
    form.check_frequency_days.value = field.check_frequency_days;
    form.soil_volume_m3.value = field.soil_volume_m3;
    form.system_flow_lps.value = field.system_flow_lps;
    form.timezone.value = field.timezone;
    form.start_date.value = isoLocalToDatetimeLocalValue(field.start_date_local);
    form.latitude.value = field.latitude ?? "";
    form.longitude.value = field.longitude ?? "";

    document.getElementById("new-field-loggers").innerHTML = "";
    field.loggers.forEach(l => addLoggerRow(l));

    document.getElementById("field-form-title").textContent = `Edit ${field.name}`;
    document.getElementById("field-form-submit-btn").textContent = "Save changes";
    document.getElementById("cancel-edit-btn").style.display = "";
    document.getElementById("edit-mode-hint").style.display = "";

    form.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    showToast("Could not load field for editing: " + e.message, "error");
  }
}

function cancelEditField() {
  editingFieldId = null;
  const form = document.getElementById("field-form");
  form.reset();
  form.timezone.value = "America/Chicago";
  document.getElementById("new-field-loggers").innerHTML = "";
  document.getElementById("field-form-title").textContent = "Add a field";
  document.getElementById("field-form-submit-btn").textContent = "Save field";
  document.getElementById("cancel-edit-btn").style.display = "none";
  document.getElementById("edit-mode-hint").style.display = "none";
}

function collectLoggersFromForm() {
  return [...document.querySelectorAll("#new-field-loggers .logger-card")].map(card => ({
    serial_number: card.querySelector(".logger-sn").value.trim(),
    port_mode: card.querySelector(".logger-mode").value,
    ports: card.querySelector(".logger-ports").value
      .split(",").map(s => s.trim()).filter(Boolean).map(Number),
  })).filter(l => l.serial_number);
}

function collectFieldPayloadFromForm(form) {
  return {
    name: form.name.value.trim(),
    trigger_threshold: parseFloat(form.trigger_threshold.value),
    target_vwc: parseFloat(form.target_vwc.value),
    soil_volume_m3: parseFloat(form.soil_volume_m3.value),
    system_flow_lps: parseFloat(form.system_flow_lps.value),
    check_frequency_days: parseInt(form.check_frequency_days.value, 10),
    timezone: form.timezone.value,
    // Sent as the raw "YYYY-MM-DDTHH:MM" wall-clock string, on purpose —
    // the backend interprets it using `timezone` above via pytz. Do NOT
    // convert this through `new Date(...).toISOString()` here, that
    // would silently reinterpret it in the browser's own timezone
    // instead of the field's.
    start_date: form.start_date.value || null,
    latitude: form.latitude.value ? parseFloat(form.latitude.value) : null,
    longitude: form.longitude.value ? parseFloat(form.longitude.value) : null,
  };
}

async function submitFieldForm(event) {
  event.preventDefault();
  const form = event.target;
  const submitBtn = document.getElementById("field-form-submit-btn");
  const payload = collectFieldPayloadFromForm(form);
  const loggers = collectLoggersFromForm();

  submitBtn.disabled = true;
  const originalText = submitBtn.textContent;
  submitBtn.innerHTML = `<span class="spinner"></span>Saving...`;

  try {
    if (editingFieldId === null) {
      // --- Create mode ---
      const field = await API.createField(payload);
      for (const l of loggers) {
        await API.addLogger(field.id, l);
      }
      showToast(`✓ Added ${field.name}`, "success");
    } else {
      // --- Edit mode: pull current loggers, replace wholesale with
      // what's in the form now. Simpler and more predictable than
      // trying to diff individual logger edits. ---
      const current = await API.getField(editingFieldId);
      const updated = await API.updateField(editingFieldId, payload);

      for (const l of current.loggers) {
        await API.deleteLogger(l.id);
      }
      for (const l of loggers) {
        await API.addLogger(editingFieldId, l);
      }

      showToast(`✓ Updated ${updated.name}`, "success");
    }

    cancelEditField();
    loadFields();
  } catch (e) {
    showToast("Could not save field: " + e.message, "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = originalText;
  }
}
