/* Mhare pricing toolkit — dual-mode (hardware / software) calculator,
   draft persistence and branded PDF quote. Config is embedded per product. */
(function () {
  'use strict';

  var CFG = JSON.parse(document.getElementById('pricing-config').textContent);
  var QUOTE_URL = document.getElementById('ph-urls').dataset.quote;
  var left = document.getElementById('ph-left');
  var draft = window.MhareDraft('mhare:draft:pricing:' + CFG.slug);

  function zar(n) { return 'R' + Math.round(n || 0).toLocaleString('en-ZA'); }
  function num(el) { var v = parseFloat(el && el.value); return isNaN(v) ? 0 : v; }
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // ── build assumptions accordion (shared) ─────────────────────────────────
  function assumptionsHtml() {
    var groups = CFG.assumptions.map(function (g) {
      var items = g.items.map(function (it) {
        return '<div class="in-field"><label>' + esc(it.label) + '</label>' +
          '<input type="number" step="' + (it.pct ? '1' : 'any') + '" data-key="' + it.key + '" value="' + it.value + '"></div>';
      }).join('');
      return '<div class="in-subhead" style="padding:12px 14px 0;">' + esc(g.title) + '</div>' +
        '<div class="in-assumptions-body">' + items + '</div>';
    }).join('');
    return '<details class="in-assumptions"><summary>Cost assumptions &amp; margins (editable — placeholders)</summary><div>' + groups + '</div></details>';
  }

  // ── HARDWARE mode UI ─────────────────────────────────────────────────────
  var HW_SEED = CFG.seed;
  function hwRow(r) {
    r = r || { group: '', qty: 0, source: 'None', install: 'Basic' };
    function opt(list, sel) { return list.map(function (o) { return '<option' + (o === sel ? ' selected' : '') + '>' + o + '</option>'; }).join(''); }
    function cb(k) { return '<input type="checkbox" data-f="' + k + '"' + (r[k] ? ' checked' : '') + '>'; }
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td><input type="text" data-f="group" value="' + esc(r.group) + '" style="min-width:120px;"></td>' +
      '<td><input type="number" min="0" data-f="qty" value="' + (r.qty || 0) + '" style="width:64px;"></td>' +
      '<td><select data-f="source">' + opt(['CAN', 'OBD', 'Probe', 'None'], r.source) + '</select></td>' +
      '<td style="text-align:center;">' + cb('panic') + '</td><td style="text-align:center;">' + cb('immob') + '</td>' +
      '<td style="text-align:center;">' + cb('rfid') + '</td><td style="text-align:center;">' + cb('temp') + '</td>' +
      '<td style="text-align:center;">' + cb('batt') + '</td>' +
      '<td><select data-f="install">' + opt(['Basic', 'Standard', 'Advanced'], r.install) + '</select></td>' +
      '<td><button type="button" class="in-btn in-btn--ghost in-btn--sm" data-remove>×</button></td>';
    return tr;
  }
  function hwReadRow(tr) {
    var o = {};
    tr.querySelectorAll('[data-f]').forEach(function (el) {
      var k = el.dataset.f;
      o[k] = el.type === 'checkbox' ? el.checked : (el.type === 'number' ? num(el) : el.value);
    });
    return o;
  }
  function hwAddRow(data) {
    var tr = hwRow(data);
    $('ph-rows').tBodies[0].appendChild(tr);
    tr.addEventListener('input', onChange); tr.addEventListener('change', onChange);
    tr.querySelector('[data-remove]').addEventListener('click', function () { tr.remove(); onChange(); });
  }
  function buildHardware(rows) {
    left.innerHTML =
      '<div class="in-panel" style="margin-top:0;"><h2>Deal</h2><div class="in-fieldgrid">' +
      '<div class="in-field"><label>Hardware billing</label><select id="ph-billing"><option value="Amortised">Amortised into monthly</option><option value="Upfront">Upfront (once-off)</option></select></div>' +
      '<div class="in-field"><label>Contract term (months)</label><input type="number" id="ph-term" min="1" value="36"></div>' +
      '</div></div>' +
      '<div class="in-panel"><h2>Fleet</h2><p class="in-panel-sub">One row per vehicle group. Accessories tick per unit.</p>' +
      '<div class="in-table-wrap"><table class="in-table" id="ph-rows"><thead><tr>' +
      '<th>Group</th><th>Qty</th><th>Source</th><th>Panic</th><th>Immob</th><th>RFID</th><th>Temp</th><th>Batt</th><th>Install</th><th></th>' +
      '</tr></thead><tbody></tbody></table></div>' +
      '<div class="in-table-actions"><button type="button" class="in-btn in-btn--ghost in-btn--sm" id="ph-add">+ Add group</button></div></div>' +
      assumptionsHtml();
    (rows || HW_SEED).forEach(hwAddRow);
    $('ph-add').addEventListener('click', function () { hwAddRow(); onChange(); });
  }

  function computeHardware(a) {
    var margin = a.margin_pct / 100, hwmk = a.hwmk_pct / 100, insmk = a.insmk_pct / 100;
    var term = Math.max(1, num($('ph-term')));
    var amortise = $('ph-billing').value === 'Amortised';
    var run = a.m_sim + a.m_host + a.m_lic + a.m_support + a.m_notif + a.m_api + a.m_warranty;
    var src = { CAN: a.can, OBD: a.obd, Probe: a.probe, None: 0 };
    var lab = { Basic: a.lab_basic, Standard: a.lab_standard, Advanced: a.lab_advanced };
    var rows = Array.prototype.map.call($('ph-rows').tBodies[0].querySelectorAll('tr'), hwReadRow);
    var units = rows.reduce(function (s, r) { return s + (r.qty || 0); }, 0);
    var discPct = units <= 20 ? a.disc_small : (units <= 100 ? a.disc_med : a.disc_ent);
    var disc = discPct / 100;
    var lines = [], subtotal = 0, monthly = 0, sumPre = 0;
    rows.forEach(function (r) {
      if (!r.qty) return;
      var hw = a.tracker + a.sim + a.cable + (src[r.source] || 0) +
        (r.panic ? a.panic : 0) + (r.immob ? a.immob : 0) + (r.rfid ? a.rfid : 0) + (r.temp ? a.temp : 0) + (r.batt ? a.batt : 0);
      var hwP = hw * (1 + hwmk), insP = (lab[r.install] || 0) * (1 + insmk);
      var moPreUnit = run / (1 - margin) + (amortise ? hwP / term : 0);
      var moUnit = moPreUnit * (1 - disc);
      var onceUnit = insP + (amortise ? 0 : hwP);
      subtotal += r.qty * onceUnit; monthly += r.qty * moUnit; sumPre += r.qty * moPreUnit;
      lines.push({ desc: r.group || 'Vehicle group', qty: r.qty, once_unit: onceUnit, monthly_unit: moUnit });
    });
    var fee = units > 0 ? a.init : 0;
    var listPerUnit = units > 0 ? sumPre / units : run / (1 - margin);
    return finalize(units, discPct, term, amortise ? 'Amortised' : 'Upfront', lines, subtotal, fee, monthly,
      listPerUnit, { small: a.disc_small, med: a.disc_med, ent: a.disc_ent });
  }

  // ── SOFTWARE mode UI ─────────────────────────────────────────────────────
  function buildSoftware(seed) {
    seed = seed || CFG.seed;
    left.innerHTML =
      '<div class="in-panel" style="margin-top:0;"><h2>Deal</h2><div class="in-fieldgrid">' +
      '<div class="in-field"><label>Number of vehicles</label><input type="number" id="ph-vehicles" min="0" value="' + (seed.vehicles || 0) + '"></div>' +
      '<div class="in-field"><label>Contract term (months)</label><input type="number" id="ph-term" min="1" value="36"></div>' +
      '<div class="in-field in-field--full"><label class="in-pill" style="width:max-content;"><input type="checkbox" id="ph-integration"' + (seed.integration ? ' checked' : '') + '> Include integration (once-off)</label></div>' +
      '</div></div>' + assumptionsHtml();
  }
  function computeSoftware(a) {
    var margin = a.margin_pct / 100;
    var term = Math.max(1, num($('ph-term')));
    var vehicles = Math.max(0, num($('ph-vehicles')));
    var integration = $('ph-integration').checked;
    var run = a.m_platform + a.m_host + a.m_api + a.m_support + a.m_notif;
    var discPct = vehicles <= 20 ? a.disc_small : (vehicles <= 100 ? a.disc_med : a.disc_ent);
    var moUnit = (run / (1 - margin)) * (1 - discPct / 100);
    var monthly = vehicles * moUnit;
    var subtotal = integration ? a.integration : 0;
    var fee = vehicles > 0 ? (a.setup + a.dataload + a.training) : 0;
    var lines = vehicles > 0 ? [{ desc: CFG.name + ' subscription', qty: vehicles, once_unit: 0, monthly_unit: moUnit }] : [];
    return finalize(vehicles, discPct, term, integration ? 'With integration' : 'Software only', lines, subtotal, fee, monthly,
      run / (1 - margin), { small: a.disc_small, med: a.disc_med, ent: a.disc_ent });
  }

  // ── shared finalize + render ─────────────────────────────────────────────
  function finalize(units, discPct, term, billing, lines, subtotal, fee, monthly, listPerUnit, discBands) {
    var once = subtotal + fee;
    return {
      units: units, discPct: discPct, term: term, billing: billing, lines: lines,
      subtotal_once: subtotal, fee_once: fee, once_off: once, monthly: monthly,
      avg_unit: units > 0 ? monthly / units : 0, tcv: once + monthly * term,
      tier: units === 0 ? '—' : (units <= 20 ? 'Small' : (units <= 100 ? 'Medium' : 'Enterprise')),
      listPerUnit: listPerUnit || 0, discBands: discBands || { small: 0, med: 0, ent: 0 }
    };
  }
  function assumptions() {
    var a = {};
    document.querySelectorAll('.in-assumptions input[data-key]').forEach(function (el) { a[el.dataset.key] = num(el); });
    return a;
  }
  var lastState = null;
  function compute() {
    var a = assumptions();
    var s = CFG.mode === 'software' ? computeSoftware(a) : computeHardware(a);
    lastState = s;
    $('r-tier').textContent = s.tier + (s.units ? ' · ' + s.units + ' units' : '');
    $('r-units').textContent = s.units;
    $('r-sub-label').textContent = CFG.result_labels.subtotal;
    $('r-fee-label').textContent = CFG.result_labels.fee;
    $('r-sub').textContent = zar(s.subtotal_once);
    $('r-fee').textContent = zar(s.fee_once);
    $('r-disc').textContent = s.discPct + '%';
    $('r-onceoff').textContent = zar(s.once_off);
    $('r-monthly').textContent = zar(s.monthly);
    $('r-avg').textContent = zar(s.avg_unit);
    $('r-tcv').textContent = zar(s.tcv);
    $('r-breakdown').innerHTML = s.lines.map(function (b) {
      return '<div class="in-kpi"><span class="k">' + esc(b.desc) + ' ×' + b.qty + '</span><span class="v">' + zar(b.monthly_unit) + '/mo · ' + zar(b.once_unit) + '</span></div>';
    }).join('') || '<p class="in-panel-sub">Add units to see pricing.</p>';
    renderExperiment(s);
    scheduleSave();
  }
  function onChange() { compute(); }

  // ── Client pricing experiment: usage slider + tier cards ─────────────────
  function bandDisc(bands, u) { return u <= 20 ? bands.small : (u <= 100 ? bands.med : bands.ent); }
  function tierName(u) { return u <= 20 ? 'Small' : (u <= 100 ? 'Medium' : 'Enterprise'); }

  function renderExperiment(s) {
    renderSlider(s);
    renderTiers(s);
  }

  function renderSlider(s) {
    var sl = CFG.slider, unit = sl.unit;
    var start = Math.min(sl.max, Math.max(sl.min, s.units || sl.min));
    $('ph-slider').innerHTML =
      '<div class="in-slider-top"><span class="lab">' + esc(sl.label) + '</span><span class="val" id="xp-count"></span></div>' +
      '<input type="range" class="in-range" id="xp-range" min="' + sl.min + '" max="' + sl.max + '" step="' + sl.step + '" value="' + start + '">' +
      '<div class="in-range-scale"><span>' + sl.min + '</span><span>' + sl.max + '+</span></div>' +
      '<div class="in-slider-out"><span class="big" id="xp-monthly"></span><span class="sub" id="xp-sub"></span></div>';
    var range = $('xp-range');
    function upd() {
      var u = parseInt(range.value, 10) || 0;
      var perUnit = s.listPerUnit * (1 - bandDisc(s.discBands, u) / 100);
      $('xp-count').textContent = u + ' ' + unit;
      $('xp-monthly').textContent = zar(u * perUnit) + '/mo';
      $('xp-sub').textContent = zar(perUnit) + ' per ' + unit.replace(/s$/, '') + '/mo · ' + tierName(u) + ' tier';
    }
    range.addEventListener('input', upd);
    upd();
  }

  function renderTiers(s) {
    var html = CFG.plans.map(function (p) {
      var perUnit = s.listPerUnit * (1 - p.discount / 100);
      var monthly = s.units * perUnit;
      var feats = p.features.map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('');
      var priceBlock = s.units > 0
        ? '<div class="in-plan-price"><span class="amt">' + zar(perUnit) + '</span><span class="per"> /' + esc((CFG.slider.unit || 'unit').replace(/s$/, '')) + '/mo</span></div>' +
          '<div class="in-plan-meta">' + zar(monthly) + '/mo for ' + s.units + ' · ' + p.term + '-month term</div>'
        : '<div class="in-plan-price"><span class="amt">' + zar(perUnit) + '</span><span class="per"> /unit/mo</span></div>' +
          '<div class="in-plan-meta">' + p.term + '-month term</div>';
      return '<div class="in-plan' + (p.recommended ? ' in-plan--featured' : '') + '">' +
        (p.recommended ? '<span class="in-plan-badge">Recommended</span>' : '') +
        '<div class="in-plan-name">' + esc(p.name) + '</div>' +
        '<div class="in-plan-blurb">' + esc(p.blurb) + '</div>' +
        priceBlock +
        '<ul class="in-plan-feats">' + feats + '</ul>' +
        '<button type="button" class="in-btn' + (p.recommended ? '' : ' in-btn--ghost') + '" data-plan-term="' + p.term + '">' + esc(p.cta) + '</button>' +
        '</div>';
    }).join('');
    $('ph-tiers').innerHTML = html;
    $('ph-tiers').querySelectorAll('[data-plan-term]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var t = $('ph-term'); if (t) { t.value = btn.dataset.planTerm; onChange(); }
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    });
  }

  // ── draft ────────────────────────────────────────────────────────────────
  function serialize() {
    var a = {};
    document.querySelectorAll('.in-assumptions input[data-key]').forEach(function (el) { a[el.dataset.key] = el.value; });
    var st = { assumptions: a, term: num($('ph-term')), q_for: $('q-for').value, q_by: $('q-by').value };
    if (CFG.mode === 'software') {
      st.vehicles = num($('ph-vehicles')); st.integration = $('ph-integration').checked;
    } else {
      st.billing = $('ph-billing').value;
      st.rows = Array.prototype.map.call($('ph-rows').tBodies[0].querySelectorAll('tr'), hwReadRow);
    }
    return st;
  }
  var saveTimer = null;
  function scheduleSave() { clearTimeout(saveTimer); saveTimer = setTimeout(function () { draft.save(serialize()); }, 400); }

  function restore(st) {
    if (CFG.mode === 'software') { buildSoftware({ vehicles: st.vehicles, integration: st.integration }); }
    else { buildHardware(st.rows && st.rows.length ? st.rows : HW_SEED); if (st.billing) $('ph-billing').value = st.billing; }
    if (st.term) $('ph-term').value = st.term;
    if (st.assumptions) Object.keys(st.assumptions).forEach(function (k) {
      var el = document.querySelector('.in-assumptions input[data-key="' + k + '"]'); if (el) el.value = st.assumptions[k];
    });
    $('q-for').value = st.q_for || ''; $('q-by').value = st.q_by || '';
    wireInputs(); compute();
  }
  function buildFresh() { CFG.mode === 'software' ? buildSoftware() : buildHardware(); wireInputs(); compute(); }

  function wireInputs() {
    left.querySelectorAll('input, select').forEach(function (el) {
      el.addEventListener('input', onChange); el.addEventListener('change', onChange);
    });
  }

  // ── quote PDF ────────────────────────────────────────────────────────────
  function cookie(name) {
    var m = document.cookie.match('(?:^|; )' + name + '=([^;]*)'); return m ? decodeURIComponent(m[1]) : '';
  }
  function quoteRef() {
    var d = new Date(), p = function (n) { return ('0' + n).slice(-2); };
    return 'MQ-' + d.getFullYear() + p(d.getMonth() + 1) + p(d.getDate()) + '-' + Math.floor(100 + Math.random() * 900);
  }
  function generatePdf() {
    if (!lastState) return;
    var s = lastState, btn = $('q-pdf');
    var payload = {
      product: CFG.slug, product_name: CFG.name, currency: 'R',
      quote_ref: quoteRef(), date: new Date().toLocaleDateString('en-ZA'),
      prepared_for: $('q-for').value, prepared_by: $('q-by').value,
      meta: { term: s.term, tier: s.tier, discount_pct: s.discPct, billing: s.billing },
      labels: CFG.result_labels, lines: s.lines,
      totals: { units: s.units, subtotal_once: s.subtotal_once, fee_once: s.fee_once, once_off: s.once_off, monthly: s.monthly, avg_unit: s.avg_unit, tcv: s.tcv }
    };
    btn.disabled = true; btn.textContent = 'Generating…';
    fetch(QUOTE_URL, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cookie('csrftoken') }, body: JSON.stringify(payload) })
      .then(function (r) { if (!r.ok) throw new Error('http ' + r.status); return r.blob(); })
      .then(function (blob) {
        var url = URL.createObjectURL(blob), a = document.createElement('a');
        a.href = url; a.download = 'Mhare_Quote_' + payload.quote_ref + '.pdf';
        document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      })
      .catch(function () { alert('Could not generate the quote PDF. Please try again.'); })
      .finally(function () { btn.disabled = false; btn.textContent = 'Generate quote PDF'; });
  }

  // ── init ─────────────────────────────────────────────────────────────────
  $('q-pdf').addEventListener('click', generatePdf);
  $('q-for').addEventListener('input', onChange); $('q-by').addEventListener('input', onChange);
  buildFresh();
  draft.offerResume($('ph-resume'), restore, buildFresh);
})();
