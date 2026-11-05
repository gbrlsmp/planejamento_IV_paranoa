"use strict";

const reportTabs = document.querySelector("[data-report-tabs]");
const links = Array.from(reportTabs.querySelectorAll("a"));
const panels = links.map(link => document.getElementById(link.hash.slice(1)));

function showSubtab() {
  const target = document.getElementById(location.hash.slice(1));
  const activePanel = panels.find(panel => panel.contains(target)) ?? panels[0];
  const wasHidden = activePanel.hidden;

  panels.forEach((panel, index) => {
    const active = panel === activePanel;
    panel.hidden = !active;
    if (active) links[index].setAttribute("aria-current", "location");
    else links[index].removeAttribute("aria-current");
  });

  return { target, wasHidden };
}

reportTabs.addEventListener("click", event => {
  const link = event.target.closest("a");
  if (!link || event.defaultPrevented || event.button !== 0 ||
      event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;

  event.preventDefault();
  if (location.hash !== link.hash) history.pushState(null, "", link.hash);
  showSubtab();
});

window.addEventListener("hashchange", () => {
  const { target, wasHidden } = showSubtab();
  // A native jump cannot scroll to a section while it is hidden.
  if (wasHidden && target) target.scrollIntoView();
});

showSubtab();
