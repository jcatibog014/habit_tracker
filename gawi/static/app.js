// Gawi. The pages work without JavaScript; this file only adds extras.
"use strict";

// ---------- Light / dark theme ----------
// With no saved choice, the page follows the system setting (CSS does that).
// Pressing the button saves the opposite of what is showing now.

function currentTheme() {
  const saved = document.documentElement.dataset.theme;
  if (saved === "light" || saved === "dark") return saved;
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function updateThemeButton(button) {
  const next = currentTheme() === "dark" ? "light" : "dark";
  button.setAttribute("aria-label", `Switch to ${next} theme`);
}

function setUpThemeToggle() {
  const button = document.getElementById("theme-toggle");
  if (!button) return;
  updateThemeButton(button);
  button.addEventListener("click", () => {
    const next = currentTheme() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch (e) {
      // Private windows can block storage; the theme still changes for this page.
    }
    updateThemeButton(button);
    document.dispatchEvent(new Event("themechange"));
  });
}

// ---------- "Are you sure?" before deleting ----------
// A form with data-confirm="Question?" asks first. Without JavaScript it just sends.

function setUpConfirms() {
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
}

// ---------- Show only the fields that matter ----------
// <div data-show-when="kind=count"> shows only while the radio "kind" is "count".
// Without JavaScript every field shows, and the server ignores the unused ones.

function setUpShowWhen() {
  const parts = document.querySelectorAll("[data-show-when]");
  if (!parts.length) return;
  const update = () => {
    parts.forEach((part) => {
      const [name, value] = part.dataset.showWhen.split("=");
      const checked = document.querySelector(`input[name="${name}"]:checked`);
      part.hidden = !checked || checked.value !== value;
    });
  };
  document.addEventListener("change", update);
  update();
}

document.addEventListener("DOMContentLoaded", () => {
  setUpThemeToggle();
  setUpConfirms();
  setUpShowWhen();
});
