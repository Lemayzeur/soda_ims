function showToast(message, type = "info", durationMs = 4500) {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), durationMs);
}

document.addEventListener("DOMContentLoaded", () => {
  const buttons = document.querySelectorAll(".nav-btn");

  function showPage(name) {
    document.querySelectorAll(".page").forEach(p => p.classList.remove("active"));
    document.getElementById("page-" + name).classList.add("active");
    buttons.forEach(b => b.classList.toggle("active", b.dataset.page === name));

    if (name === "dashboard") loadDashboard();
    if (name === "fields") loadFields();
    if (name === "alerts") loadAlertsPage();
    if (name === "forecast") loadForecastPage();
  }

  buttons.forEach(b => b.addEventListener("click", () => showPage(b.dataset.page)));

  loadDashboard(); // initial page on load
});
