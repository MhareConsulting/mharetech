/* Needs-assessment page: dynamic table rows + draft autosave/restore. */
(function () {
  'use strict';
  var form = document.getElementById('in-assessment');
  if (!form) return;

  // ── add-row for schema tables (clone last row, reindex names) ────────────
  function wireAddRows() {
    form.querySelectorAll('[data-add-row]').forEach(function (btn) {
      btn.addEventListener('click', function () { addRow(btn); });
    });
  }
  function addRow(btn) {
    var table = document.getElementById(btn.dataset.addRow);
    var body = table.tBodies[0];
    var rows = body.querySelectorAll('tr');
    if (rows.length >= 12) { btn.disabled = true; return null; }
    var idx = rows.length;
    var clone = rows[rows.length - 1].cloneNode(true);
    clone.querySelectorAll('input, select').forEach(function (el) {
      var name = el.getAttribute('name') || '';
      el.setAttribute('name', name.replace(/_\d+_/, '_' + idx + '_'));
      if (el.tagName === 'SELECT') el.selectedIndex = 0; else el.value = '';
    });
    body.appendChild(clone);
    return clone;
  }

  // ── serialize / restore ──────────────────────────────────────────────────
  function serialize() {
    var out = [];
    form.querySelectorAll('input, select, textarea').forEach(function (el) {
      if (!el.name || el.name === 'csrfmiddlewaretoken' || el.name === 'contact_hp') return;
      if (el.type === 'checkbox' || el.type === 'radio') out.push({ n: el.name, v: el.value, c: el.checked, t: el.type });
      else out.push({ n: el.name, v: el.value });
    });
    return out;
  }
  function ensureRows(saved) {
    var maxIdx = {};
    saved.forEach(function (f) {
      var m = /^([a-z]+)_(\d+)_/.exec(f.n);
      if (m) maxIdx[m[1]] = Math.max(maxIdx[m[1]] || 0, +m[2]);
    });
    Object.keys(maxIdx).forEach(function (prefix) {
      var btn = form.querySelector('[data-add-row][data-prefix="' + prefix + '"]');
      var table = btn && document.getElementById(btn.dataset.addRow);
      if (!table) return;
      while (table.tBodies[0].querySelectorAll('tr').length <= maxIdx[prefix]) {
        if (!addRow(btn)) break;
      }
    });
  }
  function restore(saved) {
    ensureRows(saved);
    saved.forEach(function (f) {
      var els = form.querySelectorAll('[name="' + (window.CSS && CSS.escape ? CSS.escape(f.n) : f.n) + '"]');
      els.forEach(function (el) {
        if (f.t === 'checkbox' || f.t === 'radio') { if (el.value === f.v) el.checked = f.c; }
        else el.value = f.v;
      });
    });
  }

  // ── draft wiring ─────────────────────────────────────────────────────────
  var draft = window.MhareDraft(form.dataset.draftkey);
  var saveTimer = null;
  function scheduleSave() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(function () { draft.save(serialize()); }, 400);
  }
  wireAddRows();
  form.addEventListener('input', scheduleSave);
  form.addEventListener('change', scheduleSave);

  draft.offerResume(document.getElementById('in-resume'), restore);

  document.getElementById('in-clear').addEventListener('click', function () {
    if (confirm('Clear this draft and reset the form?')) { draft.clear(); form.reset(); }
  });

  form.addEventListener('submit', function () {
    draft.clear();  // submitted → no longer a draft
    var b = document.getElementById('in-submit');
    b.disabled = true; b.textContent = 'Submitting…';
  });
})();
