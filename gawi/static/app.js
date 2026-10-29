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

// ---------- The ☰ menu on phones ----------
// The button opens and closes the menu. Escape closes it too. On computers
// the menu is a sidebar that is always open, and the button is hidden.

function setUpMenu() {
  const menu = document.querySelector("[data-menu]");
  const button = document.querySelector("[data-menu-button]");
  if (!menu || !button) return;
  const setOpen = (open) => {
    menu.classList.toggle("is-open", open);
    button.setAttribute("aria-expanded", String(open));
    button.setAttribute("aria-label", open ? "Close the menu" : "Menu");
  };
  button.addEventListener("click", () => setOpen(!menu.classList.contains("is-open")));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menu.classList.contains("is-open")) {
      setOpen(false);
      button.focus();
    }
  });
}

// ---------- Closing a message ----------

function setUpFlashClose() {
  document.querySelectorAll("[data-close-flash]").forEach((button) => {
    button.addEventListener("click", () => button.closest(".flash").remove());
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

// ---------- Screen reader messages ----------
// Pages with a <p aria-live="polite" id="live"> read out what just changed.

function announce(text) {
  const live = document.getElementById("live");
  if (live) live.textContent = text;
}

// Play a CSS animation class once (it is removed when the animation ends).
function playOnce(element, className) {
  element.classList.remove(className);
  void element.offsetWidth; // forget the old animation, so it can play again
  element.classList.add(className);
  element.addEventListener("animationend", () => element.classList.remove(className), { once: true });
}

// ---------- Ticking habits on the Today page ----------
// Each <form data-checkin> is sent with fetch(), and the answer (JSON) updates
// the card and the progress ring. Taps on one card wait for each other, so
// fast taps on "+" all count.

function updateCard(card, data) {
  const wasDone = card.classList.contains("is-done");
  const kind = card.dataset.kind;
  card.classList.toggle("is-done", data.done);
  card.classList.toggle("is-rested", data.rested);
  card.classList.toggle("is-slipped", data.slipped);
  card.querySelector("[data-line]").textContent = data.line;
  const nudge = card.querySelector("[data-nudge]");
  nudge.textContent = data.nudge || "";
  nudge.hidden = !data.nudge;
  const streak = card.querySelector("[data-streak]");
  streak.querySelector("[data-streak-count]").textContent = data.streak;
  streak.hidden = data.streak === 0;
  card.querySelector("[data-rest]").setAttribute("aria-pressed", String(data.rested));

  const check = card.querySelector("[data-check]");
  check.style.setProperty("--percent", data.percent);
  const count = card.querySelector("[data-count]");
  if (count) {
    count.textContent = data.value;
    check.setAttribute("aria-label", `Add one: ${card.dataset.name}, ${data.line}`);
  } else {
    check.setAttribute("aria-pressed", String(kind === "avoid" ? data.slipped : data.done));
  }
  const minus = card.querySelector("[data-minus]");
  if (minus) minus.disabled = data.value === 0;
  // A habit to avoid starts "done" (clean), so only real ticks get the pop.
  const justDone = data.done && !wasDone && kind !== "avoid";
  if (justDone) playOnce(card, "just-done");
  return justDone;
}

// A streak just reached a badge: show the celebration card for a while.
function showMilestone(milestone) {
  const box = document.querySelector("[data-milestone]");
  if (!box || !milestone) return;
  box.querySelector("[data-milestone-count]").textContent = milestone.count;
  box.querySelector("[data-milestone-text]").textContent = milestone.message;
  box.hidden = false;
  playOnce(box, "celebrate");
  clearTimeout(box.hideTimer);
  box.hideTimer = setTimeout(() => { box.hidden = true; }, 8000);
}

function setUpMilestoneClose() {
  const box = document.querySelector("[data-milestone]");
  if (!box) return;
  box.querySelector("[data-milestone-close]").addEventListener("click", () => { box.hidden = true; });
}

function updateSummary(summary) {
  const hero = document.querySelector("[data-hero]");
  if (!hero) return;
  const wasPerfect = hero.classList.contains("is-perfect");
  const isPerfect = summary.total > 0 && summary.done === summary.total;
  hero.querySelector("[data-done]").textContent = summary.done;
  hero.querySelector("[data-total]").textContent = summary.total;
  hero.querySelector("[data-message]").textContent = summary.message;
  const ring = hero.querySelector("[data-ring]");
  ring.style.setProperty("--percent", summary.percent);
  ring.setAttribute("aria-label", `${summary.done} of ${summary.total} done today`);
  hero.classList.toggle("is-perfect", isPerfect);
  if (isPerfect && !wasPerfect) playOnce(hero, "celebrate");
}

async function sendCheckin(form, card) {
  // getAttribute, not form.action: the form has a field named "action", which hides that property.
  const response = await fetch(form.getAttribute("action"), {
    method: "POST",
    body: new FormData(form),
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const data = await response.json();
  const justDone = updateCard(card, data);
  updateSummary(data.summary);
  showMilestone(data.milestone);
  const extra = data.milestone ? ` ${data.milestone.message}` : "";
  announce(`${card.dataset.name}: ${justDone ? "done! " : ""}${data.line}. ${data.summary.message}${extra}`);
}

// ---------- Quote of the day ----------
// "Another" shows the next quote from the list in the page (no reload).

function setUpQuotes() {
  const data = document.getElementById("quotes-data");
  const button = document.querySelector("[data-next-quote]");
  if (!data || !button) return;
  const quotes = JSON.parse(data.textContent);
  let index = Number(data.dataset.start) || 0;
  const box = document.querySelector("[data-quote]");
  button.addEventListener("click", () => {
    index = (index + 1) % quotes.length;
    box.querySelector("[data-quote-text]").textContent = quotes[index].quote;
    box.querySelector("[data-quote-author]").textContent = quotes[index].author;
    playOnce(box, "quote-change");
  });
}

// ---------- Install on a phone ----------
// The service worker (/sw.js) makes Gawi installable. Browsers that can
// install it fire "beforeinstallprompt"; then the "Install app" button shows.

function setUpInstall() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Not a problem: the site works the same without it.
    });
  }
  const button = document.querySelector("[data-install]");
  if (!button) return;
  let offer = null;
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault(); // we show our own button instead of the browser's banner
    offer = event;
    button.hidden = false;
  });
  button.addEventListener("click", async () => {
    if (!offer) return;
    offer.prompt();
    await offer.userChoice;
    offer = null;
    button.hidden = true;
  });
  window.addEventListener("appinstalled", () => { button.hidden = true; });
}

// ---------- The year heatmap ----------
// On a narrow screen the year scrolls sideways; start at the newest days.

function setUpScrollEnd() {
  document.querySelectorAll("[data-scroll-end]").forEach((box) => {
    box.scrollLeft = box.scrollWidth;
  });
}

function setUpCheckins() {
  document.querySelectorAll("form[data-checkin]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const card = form.closest("[data-habit]");
      playOnce(form.querySelector("button"), "pressed");
      card.queue = (card.queue || Promise.resolve())
        .then(() => sendCheckin(form, card))
        .catch(() => announce("That didn't save. Please check your connection and try again."));
    });
  });
}

// ---------- Reordering habits by dragging ----------
// Grab a handle (the six dots) and move it up or down; the other habits make
// room. With the keyboard, focus a handle and press the up or down arrow.
// The new order is saved right away.

function setUpReorder() {
  const list = document.querySelector("[data-reorder]");
  if (!list) return;
  const order = () => [...list.children].map((item) => item.dataset.id).join(",");

  const save = (item) => {
    const position = [...list.children].indexOf(item) + 1;
    announce(`${item.dataset.name} moved to place ${position} of ${list.children.length}.`);
    const body = new FormData();
    body.append("csrf_token", list.dataset.csrf);
    body.append("order", order());
    fetch(list.dataset.url, { method: "POST", body, headers: { Accept: "application/json" } })
      .then((response) => { if (!response.ok) throw new Error(); })
      .catch(() => announce("The new order didn't save. Please reload the page and try again."));
  };

  list.querySelectorAll("[data-handle]").forEach((handle) => {
    const item = handle.closest("li");

    handle.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      // We listen on the whole window: moving the item in the page would
      // cancel a pointer capture on the handle, and the drag would stop.
      const before = order();
      item.classList.add("dragging");
      list.classList.add("is-sorting");

      const move = (moveEvent) => {
        // Put the item before the first other item whose middle is below the pointer.
        const others = [...list.children].filter((other) => other !== item);
        const next = others.find((other) => {
          const box = other.getBoundingClientRect();
          return moveEvent.clientY < box.top + box.height / 2;
        });
        if (next) {
          if (next !== item.nextElementSibling) list.insertBefore(item, next);
        } else if (item !== list.lastElementChild) {
          list.appendChild(item);
        }
      };
      const stop = () => {
        window.removeEventListener("pointermove", move);
        window.removeEventListener("pointerup", stop);
        window.removeEventListener("pointercancel", stop);
        item.classList.remove("dragging");
        list.classList.remove("is-sorting");
        if (order() !== before) save(item);
      };
      window.addEventListener("pointermove", move);
      window.addEventListener("pointerup", stop);
      window.addEventListener("pointercancel", stop);
    });

    handle.addEventListener("keydown", (event) => {
      if (event.key === "ArrowUp" && item.previousElementSibling) {
        list.insertBefore(item, item.previousElementSibling);
      } else if (event.key === "ArrowDown" && item.nextElementSibling) {
        list.insertBefore(item.nextElementSibling, item);
      } else {
        return;
      }
      event.preventDefault();
      handle.focus(); // moving the element can drop the focus
      save(item);
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  setUpThemeToggle();
  setUpMenu();
  setUpConfirms();
  setUpFlashClose();
  setUpShowWhen();
  setUpCheckins();
  setUpMilestoneClose();
  setUpQuotes();
  setUpReorder();
  setUpInstall();
  setUpScrollEnd();
});
