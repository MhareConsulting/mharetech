/* The plans page: pick a tier per product, add single functions or build your own, and see the selection build up.
   Nothing is stored or sent from here; "Request this plan" opens a mail, filled in, in the person's own mail app. */
(function () {
  "use strict";
  document.documentElement.classList.add("js");

  var panels = Array.prototype.slice.call(document.querySelectorAll(".pl-panel"));
  var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-product-tab]"));
  var bar = document.getElementById("pl-bar");
  var chips = bar.querySelector(".pl-chips");
  var request = bar.querySelector("[data-request]");
  var clearBtn = bar.querySelector("[data-clear]");
  var words = function (s) { return s ? s.split(" ").filter(Boolean) : []; };

  // ── state: per product, the tier picked (or null) and the single functions added on top
  var state = {};
  panels.forEach(function (p) { state[p.dataset.product] = { tier: null, extra: {} }; });

  function fnEl(panel, key) { return panel.querySelector('[data-fn="' + key + '"]'); }
  function tierKeys(panel, st) {
    var card = st.tier && panel.querySelector('[data-tier="' + st.tier + '"]');
    return card ? words(card.dataset.keys) : [];
  }
  function chosen(panel, st) {                        // everything switched on: the tier's functions and the extras
    var set = {};
    tierKeys(panel, st).forEach(function (k) { set[k] = true; });
    Object.keys(st.extra).forEach(function (k) { set[k] = true; });
    return set;
  }
  function met(panel, key, set) {
    var el = fnEl(panel, key);
    if (!el) { return true; }
    var need = words(el.dataset.requires), any = words(el.dataset.requiresAny);
    return need.every(function (k) { return set[k]; }) && (!any.length || any.some(function (k) { return set[k]; }));
  }
  function add(panel, st, key) {                      // add a function and whatever it needs
    var set = chosen(panel, st);
    if (set[key]) { return; }
    st.extra[key] = true;
    var el = fnEl(panel, key);
    if (!el) { return; }
    words(el.dataset.requires).forEach(function (k) { add(panel, st, k); });
    var any = words(el.dataset.requiresAny);
    if (any.length && !any.some(function (k) { return chosen(panel, st)[k]; })) { add(panel, st, any[0]); }
  }
  function settle(panel, st) {                        // drop extras that lost something they need
    var changed = true;
    while (changed) {
      changed = false;
      Object.keys(st.extra).forEach(function (k) {
        if (!met(panel, k, chosen(panel, st))) { delete st.extra[k]; changed = true; }
      });
    }
  }

  // ── drawing
  function draw(panel) {
    var st = state[panel.dataset.product], set = chosen(panel, st), locked = {};
    tierKeys(panel, st).forEach(function (k) { locked[k] = true; });
    var tierName = "";
    panel.querySelectorAll("[data-tier]").forEach(function (card) {
      var on = card.dataset.tier === st.tier;
      card.classList.toggle("is-picked", on);
      var b = card.querySelector("[data-pick]");
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.textContent = on ? card.dataset.name + " selected" : "Select " + card.dataset.name;
      if (on) { tierName = card.dataset.name; }
    });
    var custom = panel.querySelector("[data-custom]"), extras = Object.keys(st.extra).length;
    var customOn = !st.tier && extras > 0;
    custom.classList.toggle("is-picked", customOn);
    custom.querySelector("[data-build]").setAttribute("aria-pressed", customOn ? "true" : "false");
    panel.querySelectorAll("[data-fn]").forEach(function (li) {
      var key = li.dataset.fn, box = li.querySelector("input"), note = li.querySelector(".pl-note");
      if ("free" in li.dataset) {                     // comes free with another function
        var free = words(li.dataset.freeWith).some(function (k) { return set[k]; });
        box.checked = free; box.disabled = true;
        note.textContent = free ? "Included free with what you picked" : "Comes free with " + words(li.dataset.freeWith).map(function (k) { var e = fnEl(panel, k); return e ? e.dataset.label : k; }).join(", ");
        li.classList.remove("is-locked");
        return;
      }
      box.checked = !!set[key];
      box.disabled = !!locked[key];
      li.classList.toggle("is-locked", !!locked[key]);
      note.textContent = locked[key] ? "Included in " + tierName : "";
    });
  }

  function label(panel, key) { var e = fnEl(panel, key); return e ? e.dataset.label : key; }

  function summarise() {
    var lines = [], items = [];
    panels.forEach(function (panel) {
      var st = state[panel.dataset.product], name = panel.dataset.label;
      var extras = Object.keys(st.extra);
      if (!st.tier && !extras.length) { return; }
      var tier = st.tier && panel.querySelector('[data-tier="' + st.tier + '"]').dataset.name;
      var text = tier ? tier + (extras.length ? " + " + extras.length + " added" : "") : "Custom, " + extras.length + " function" + (extras.length === 1 ? "" : "s");
      items.push({ name: name, text: text });
      var detail = tier ? ["Tier: " + tier] : [];
      extras.forEach(function (k) { detail.push((tier ? "Added: " : "Function: ") + label(panel, k)); });
      lines.push(name + "\n  " + detail.join("\n  "));
    });
    chips.innerHTML = "";
    items.forEach(function (it) {
      var li = document.createElement("li"), b = document.createElement("b");
      b.textContent = it.name; li.appendChild(b); li.appendChild(document.createTextNode(": " + it.text)); chips.appendChild(li);
    });
    bar.classList.toggle("has-items", items.length > 0);
    clearBtn.hidden = items.length === 0;
    if (request) {
      var to = bar.dataset.email, org = bar.dataset.org;
      if (items.length && to) {
        var body = "Hello,\n\nI would like to talk about this plan" + (org ? " for " + org : "") + ":\n\n" + lines.join("\n\n") + "\n";
        request.href = "mailto:" + to + "?subject=" + encodeURIComponent("Plan request") + "&body=" + encodeURIComponent(body);
        request.setAttribute("aria-disabled", "false");
      } else { request.href = "#"; request.setAttribute("aria-disabled", "true"); }
    }
  }
  function refresh(panel) { draw(panel); summarise(); }

  // ── events
  panels.forEach(function (panel) {
    var key = panel.dataset.product, st = state[key];
    panel.querySelectorAll("[data-pick]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var tier = btn.closest("[data-tier]").dataset.tier;
        st.tier = st.tier === tier ? null : tier;
        tierKeys(panel, st).forEach(function (k) { delete st.extra[k]; });
        settle(panel, st);
        refresh(panel);
      });
    });
    panel.querySelector("[data-build]").addEventListener("click", function () {
      st.tier = null;
      refresh(panel);
      panel.querySelector(".pl-build").scrollIntoView({ behavior: "smooth", block: "center" });
    });
    panel.querySelectorAll("[data-fn] input").forEach(function (box) {
      box.addEventListener("change", function () {
        var fn = box.closest("[data-fn]").dataset.fn;
        if (box.checked) { add(panel, st, fn); } else { delete st.extra[fn]; settle(panel, st); }
        refresh(panel);
      });
    });
    draw(panel);
  });
  clearBtn.addEventListener("click", function () {
    panels.forEach(function (p) { state[p.dataset.product] = { tier: null, extra: {} }; });
    panels.forEach(draw); summarise();
  });
  if (request) { request.addEventListener("click", function (e) { if (request.getAttribute("aria-disabled") === "true") { e.preventDefault(); } }); }

  // ── product switch, kept in the address so a product can be linked to
  function show(key) {
    if (!panels.some(function (p) { return p.dataset.product === key; })) { key = panels[0].dataset.product; }
    panels.forEach(function (p) { p.hidden = p.dataset.product !== key; });
    tabs.forEach(function (t) { t.setAttribute("aria-selected", t.dataset.productTab === key ? "true" : "false"); });
  }
  tabs.forEach(function (t) {
    t.addEventListener("click", function () { show(t.dataset.productTab); history.replaceState(null, "", "#" + t.dataset.productTab); });
  });
  window.addEventListener("hashchange", function () { show(location.hash.replace("#", "")); });
  show(location.hash.replace("#", ""));
  summarise();
})();
