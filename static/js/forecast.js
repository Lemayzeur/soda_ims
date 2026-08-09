async function loadForecastPage() {
  const select = document.getElementById("forecast-field-select");
  try {
    const fields = await API.getFields();
    if (!fields.length) {
      select.innerHTML = "";
      document.getElementById("forecast-strip").innerHTML = "<p class='hint' style='padding:20px;'>Add a field first on the Manage Fields page.</p>";
      return;
    }
    select.innerHTML = fields.map(f => `<option value="${f.id}">${escapeHtml(f.name)}</option>`).join("");
    select.onchange = () => renderForecast(select.value);
    await renderForecast(select.value);
  } catch (e) {
    document.getElementById("forecast-strip").innerHTML = `<p class="hint" style="padding:20px;">Failed to load fields: ${e.message}</p>`;
  }
}

async function renderForecast(fieldId) {
  const el = document.getElementById("forecast-strip");
  el.innerHTML = "<p class='hint' style='padding:20px;'>Loading...</p>";
  try {
    const data = await API.getForecast(fieldId);
    el.innerHTML = data.days.map(d => `
      <div class="forecast-day">
        <div class="fd-name">${d.day_label}</div>
        <div class="fd-temps">${d.high_f ?? "—"}° <span class="lo">${d.low_f ?? "—"}°</span></div>
        <div class="fd-rain">Rain ${d.rain_probability_pct ?? "—"}%</div>
        <div class="fd-eto">ETo: ${d.eto_mm ?? "—"}</div>
      </div>
    `).join("");
  } catch (e) {
    el.innerHTML = `<p class="hint" style="padding:20px;">Failed to load forecast: ${e.message}</p>`;
  }
}
