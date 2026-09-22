// Applies the persisted theme immediately (called inline in <head> to avoid
// a flash of the wrong theme), and wires up the toggle button if present.
(function () {
  const saved = localStorage.getItem("cs-theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
})();

// Reads the *current* theme's CSS custom properties so Chart.js configs
// (which bake colors into the canvas at draw time, not via CSS) stay legible
// in both dark and light mode. Call this fresh right before building each chart.
function chartColors() {
  const style = getComputedStyle(document.documentElement);
  const v = (name, fallback) => (style.getPropertyValue(name) || fallback).trim();
  return {
    text: v("--text", "#E2E8F0"),
    textMuted: v("--text-muted", "#94A3B8"),
    grid: v("--border-soft", "#24314A"),
    primary: v("--primary", "#2563EB"),
    secondary: v("--secondary", "#3B82F6"),
    accent: v("--accent", "#06B6D4"),
    success: v("--success", "#22C55E"),
    warning: v("--warning", "#F59E0B"),
    danger: v("--danger", "#EF4444"),
  };
}

function initThemeToggle() {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  const icon = document.getElementById("theme-icon");

  function reflectIcon() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    if (icon) icon.className = current === "dark" ? "bi bi-moon-stars" : "bi bi-sun";
  }
  reflectIcon();

  btn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    localStorage.setItem("cs-theme", next);
    // Reload so every Chart.js instance on the page rebuilds with chartColors()
    // reading the new theme's variables — canvas colors don't update live otherwise.
    location.reload();
  });
}

document.addEventListener("DOMContentLoaded", initThemeToggle);
