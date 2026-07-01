/* Mhare pricing toolkit — assessment-driven, dual-mode (hardware / software).
   The needs assessment (stored in this browser) is mandatory and pre-fills the
   calculator; softer answers trigger editable weightings. Config is embedded. */
(function () {
  'use strict';

  var CFG = JSON.parse(document.getElementById('pricing-config').textContent);
  var URLS = document.getElementById('ph-urls').dataset;
  var left = document.getElementById('ph-left');
  var draft = window.MhareDraft('mhare:draft:pricing:' + CFG.slug);

  function zar(n) { return 'R' + Math.round(n || 0).toLocaleString('en-ZA'); }
  function num(el) { var v = parseFloat(el && el.value); return isNaN(v) ? 0 : v; }
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }

  // ── assessment bridge ────────────────────────────────────────────────────
  function readAssessment() {
    try {
      var r = localStorage.getItem('mhare:assessment:' + CFG.slug + ':result');
      if (!r) return null;
      var o = JSON.parse(r);
      return o && o.data ? toLookup(o.data) : null;
    } catch (e) { return null; }
  }
  function toLookup(list) {
    var m = {};
    list.forEach(function (f) {
      if (f.t === 'checkbox' || f.t === 'radio') { if (f.c) (m[f.n] = m[f.n] || []).push(f.v); }
      else if (f.v != null && f.v !== '') m[f.n] = f.v;
    });
    return m;
  }
  function val(a, n) { return Array.isArray(a[n]) ? a[n].join(', ') : (a[n] || ''); }
  function arr(a, n) { return Array.isArray(a[n]) ? a[n] : (a[n] ? [a[n]] : []); }
  function yes(s) { return /^yes/i.test(s || ''); }
  function numOf(s) { var m = /(\d+(\.\d+)?)/.exec(s || ''); return m ? parseFloat(m[1]) : 0; }
  function mustCount(a) { return Object.keys(a).filter(function (k) { return /^feat_/.test(k) && val(a, k) === 'must'; }).length; }

  var ANS = readAssessment();

  // Which weightings fire for these answers.
  var TRIG = {
    roaming: function (a) { return yes(val(a, 'roaming')); },
    mobile_install: function (a) { return arr(a, 'install_location').some(function (x) { return /mobile|multiple/i.test(x); }); },
    sla_support: function (a) { return arr(a, 'training').some(function (x) { return /on-site/i.test(x); }) || !!val(a, 'sla'); },
    premium_features: function (a) { return mustCount(a) >= 4; },
    api_setup: function (a) { return yes(val(a, 'api_needed')); },
    whitelabel: function (a) { return yes(val(a, 'whitelabel')); },
    popia: function (a) { return /needs/i.test(val(a, 'popia')); },
    geocoding: function (a) { return yes(val(a, 'geocoding_need')); },
    constraints: function (a) { return arr(a, 'constraints').length >= 3; }
  };
  var TRIGGERED = ANS ? (CFG.weights || []).filter(function (w) { return TRIG[w.key] && TRIG[w.key](ANS); }) : [];

  // Pre-fill the calculator from the assessment.
  function derivePrefill() {
    if (!ANS) return null;
    var term = numOf(val(ANS, 'contract_term')) || 36;
    if (CFG.mode === 'software') {
      return {
        vehicles: numOf(val(ANS, 'vehicles_delivery')),
        integration: yes(val(ANS, 'api_needed')) || /erp|wms|kasistock/i.test(val(ANS, 'order_source')),
        term: term
      };
    }
    var rows = [];
    for (var i = 0; i < 12; i++) {
      var g = ANS['hw_' + i + '_group'], s = ANS['hw_' + i + '_source'], q = ANS['hw_' + i + '_qty'], ac = ANS['hw_' + i + '_accessories'];
      if (g || s || q) rows.push(hwFromAssess(g, s, q, ac));
    }
    if (!rows.length) {  // fall back to the fleet table
      for (var j = 0; j < 12; j++) {
        var t = ANS['fleet_' + j + '_type'], fq = ANS['fleet_' + j + '_qty'];
        if (t || fq) {
          var can = ANS['fleet_' + j + '_can'], obd = ANS['fleet_' + j + '_obd'];
          var src = can === 'Y' ? 'CAN' : (obd === 'Y' ? 'OBD' : 'None');
          rows.push({ group: t || 'Group', qty: numOf(fq), source: src, panic: false, immob: false, rfid: false, temp: false, batt: false, install: can === 'Y' ? 'Standard' : 'Basic' });
        }
      }
    }
    return { rows: rows, term: term, billing: /upfront/i.test(val(ANS, 'hw_billing')) ? 'Upfront' : 'Amortised' };
  }
  function hwFromAssess(g, s, q, ac) {
    ac = (ac || '').toLowerCase();
    var source = ['CAN', 'OBD', 'Probe'].indexOf(s) >= 0 ? s : 'None';
    return {
      group: g || 'Group', qty: numOf(q), source: source,
      panic: /panic/.test(ac), immob: /immob|cut/.test(ac), rfid: /rfid|ibutton|button/.test(ac),
      temp: /temp|reefer|cold/.test(ac), batt: /batt|battery/.test(ac),
      install: s === 'Probe' ? 'Advanced' : (s === 'CAN' ? 'Standard' : 'Basic')
    };
  }
  var PREFILL = derivePrefill();

  // ── assumptions + adjustments ────────────────────────────────────────────
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
  function adjustmentsHtml() {
    if (!TRIGGERED.length) return '';
    var items = TRIGGERED.map(function (w) {
      var pct = /pct/.test(w.type);
      return '<div class="in-field"><label>' + esc(w.label) + '</label>' +
        '<input type="number" step="' + (pct ? '1' : 'any') + '" data-weight="' + w.key + '" data-wtype="' + w.type + '" value="' + w.value + '"></div>';
    }).join('');
    return '<div class="in-panel" style="margin-top:0;"><h2>Adjustments from the assessment</h2>' +
      '<p class="in-panel-sub">Uplifts triggered by the client’s answers. Edit if needed.</p>' +
      '<div class="in-assumptions-body" style="padding:0;">' + items + '</div></div>';
  }
  function readAdj() {
    var adj = { addMonthlyUnit: 0, pctInstall: 0, addOnce: 0, pctMonthly: 0 };
    document.querySelectorAll('[data-weight]').forEach(function (el) {
      var v = num(el), t = el.dataset.wtype;
      if (t === 'add_monthly_unit') adj.addMonthlyUnit += v;
      else if (t === 'pct_install') adj.pctInstall += v / 100;
      else if (t === 'pct_monthly') adj.pctMonthly += v / 100;
      else if (t === 'add_once') adj.addOnce += v;
    });
    return adj;
  }

  // ── HARDWARE mode UI ─────────────────────────────────────────────────────
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
  function buildHardware(pf) {
    var rows = pf && pf.rows && pf.rows.length ? pf.rows : [{ group: '', qty: 0, source: 'None', install: 'Basic' }];
    left.innerHTML = adjustmentsHtml() +
      '<div class="in-panel"' + (TRIGGERED.length ? '' : ' style="margin-top:0;"') + '><h2>Deal</h2><div class="in-fieldgrid">' +
      '<div class="in-field"><label>Hardware billing</label><select id="ph-billing"><option value="Amortised">Amortised into monthly</option><option value="Upfront">Upfront (once-off)</option></select></div>' +
      '<div class="in-field"><label>Contract term (months)</label><input type="number" id="ph-term" min="1" value="' + ((pf && pf.term) || 36) + '"></div>' +
      '</div></div>' +
      '<div class="in-panel"><h2>Fleet</h2><p class="in-panel-sub">Pre-filled from the assessment — adjust if needed.</p>' +
      '<div class="in-table-wrap"><table class="in-table" id="ph-rows"><thead><tr>' +
      '<th>Group</th><th>Qty</th><th>Source</th><th>Panic</th><th>Immob</th><th>RFID</th><th>Temp</th><th>Batt</th><th>Install</th><th></th>' +
      '</tr></thead><tbody></tbody></table></div>' +
      '<div class="in-table-actions"><button type="button" class="in-btn in-btn--ghost in-btn--sm" id="ph-add">+ Add group</button></div></div>' +
      assumptionsHtml();
    rows.forEach(hwAddRow);
    if (pf && pf.billing) $('ph-billing').value = pf.billing;
    $('ph-add').addEventListener('click', function () { hwAddRow(); onChange(); });
  }

  function computeHardware(a, adj) {
    var margin = a.margin_pct / 100, hwmk = a.hwmk_pct / 100, insmk = a.insmk_pct / 100;
    var term = Math.max(1, num($('ph-term')));
    var amortise = $('ph-billing').value === 'Amortised';
    var run = a.m_sim + a.m_host + a.m_lic + a.m_support + a.m_notif + a.m_api + a.m_warranty + adj.addMonthlyUnit;
    var src = { CAN: a.can, OBD: a.obd, Probe: a.probe, None: 0 };
    var lab = { Basic: a.lab_basic, Standard: a.lab_standard, Advanced: a.lab_advanced };
    var rows = Array.prototype.map.call($('ph-rows').tBodies[0].querySelectorAll('tr'), hwReadRow);
    var units = rows.reduce(function (s, r) { return s + (r.qty || 0); }, 0);
    var discPct = units <= 20 ? a.disc_small : (units <= 100 ? a.disc_med : a.disc_ent);
    var disc = discPct / 100, up = 1 + adj.pctMonthly;
    var lines = [], subtotal = 0, monthly = 0, sumPre = 0;
    rows.forEach(function (r) {
      if (!r.qty) return;
      var hw = a.tracker + a.sim + a.cable + (src[r.source] || 0) +
        (r.panic ? a.panic : 0) + (r.immob ? a.immob : 0) + (r.rfid ? a.rfid : 0) + (r.temp ? a.temp : 0) + (r.batt ? a.batt : 0);
      var hwP = hw * (1 + hwmk), insP = (lab[r.install] || 0) * (1 + insmk) * (1 + adj.pctInstall);
      var moPreUnit = (run / (1 - margin) + (amortise ? hwP / term : 0)) * up;
      var moUnit = moPreUnit * (1 - disc);
      var onceUnit = insP + (amortise ? 0 : hwP);
      subtotal += r.qty * onceUnit; monthly += r.qty * moUnit; sumPre += r.qty * moPreUnit;
      lines.push({ desc: r.group || 'Vehicle group', qty: r.qty, once_unit: onceUnit, monthly_unit: moUnit });
    });
    var fee = units > 0 ? a.init + adj.addOnce : 0;
    var listPerUnit = units > 0 ? sumPre / units : run / (1 - margin) * up;
    return finalize(units, discPct, term, amortise ? 'Amortised' : 'Upfront', lines, subtotal, fee, monthly,
      listPerUnit, { small: a.disc_small, med: a.disc_med, ent: a.disc_ent });
  }

  // ── SOFTWARE mode UI ─────────────────────────────────────────────────────
  function buildSoftware(pf) {
    pf = pf || {};
    left.innerHTML = adjustmentsHtml() +
      '<div class="in-panel"' + (TRIGGERED.length ? '' : ' style="margin-top:0;"') + '><h2>Deal</h2>' +
      '<p class="in-panel-sub">Pre-filled from the assessment — adjust if needed.</p><div class="in-fieldgrid">' +
      '<div class="in-field"><label>Number of vehicles</label><input type="number" id="ph-vehicles" min="0" value="' + (pf.vehicles || 0) + '"></div>' +
      '<div class="in-field"><label>Contract term (months)</label><input type="number" id="ph-term" min="1" value="' + (pf.term || 36) + '"></div>' +
      '<div class="in-field in-field--full"><label class="in-pill" style="width:max-content;"><input type="checkbox" id="ph-integration"' + (pf.integration ? ' checked' : '') + '> Include integration (once-off)</label></div>' +
      '</div></div>' + assumptionsHtml();
  }
  function computeSoftware(a, adj) {
    var margin = a.margin_pct / 100;
    var term = Math.max(1, num($('ph-term')));
    var vehicles = Math.max(0, num($('ph-vehicles')));
    var integration = $('ph-integration').checked;
    var run = a.m_platform + a.m_host + a.m_api + a.m_support + a.m_notif + adj.addMonthlyUnit;
    var discPct = vehicles <= 20 ? a.disc_small : (vehicles <= 100 ? a.disc_med : a.disc_ent);
    var up = 1 + adj.pctMonthly;
    var listPerUnit = run / (1 - margin) * up;
    var moUnit = listPerUnit * (1 - discPct / 100);
    var monthly = vehicles * moUnit;
    var subtotal = integration ? a.integration : 0;
    var fee = vehicles > 0 ? (a.setup + a.dataload + a.training + adj.addOnce) : 0;
    var lines = vehicles > 0 ? [{ desc: CFG.name + ' subscription', qty: vehicles, once_unit: 0, monthly_unit: moUnit }] : [];
    return finalize(vehicles, discPct, term, integration ? 'With integration' : 'Software only', lines, subtotal, fee, monthly,
      listPerUnit, { small: a.disc_small, med: a.disc_med, ent: a.disc_ent });
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
    var s = CFG.mode === 'software' ? computeSoftware(assumptions(), readAdj()) : computeHardware(assumptions(), readAdj());
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

  // ── Client pricing: usage slider + tier cards ────────────────────────────
  function bandDisc(bands, u) { return u <= 20 ? bands.small : (u <= 100 ? bands.med : bands.ent); }
  function tierName(u) { return u <= 20 ? 'Small' : (u <= 100 ? 'Medium' : 'Enterprise'); }
  function renderExperiment(s) { renderSlider(s); renderTiers(s); }

  function renderSlider(s) {
    var sl = CFG.slider, unit = sl.unit, one = unit.replace(/s$/, '');
    var start = Math.min(sl.max, Math.max(sl.min, s.units || sl.min));
    $('ph-slider').innerHTML =
      '<div class="in-slider-top"><span class="lab">' + esc(sl.label) + '</span><span class="val" id="xp-count"></span></div>' +
      '<input type="range" class="in-range" id="xp-range" min="' + sl.min + '" max="' + sl.max + '" step="' + sl.step + '" value="' + start + '">' +
      '<div class="in-range-scale"><span>' + sl.min + '</span><span>' + sl.max + '+</span></div>' +
      '<div class="in-subtile">' +
        '<div class="in-subtile-head"><span class="in-subtile-name">' + esc(CFG.name) + ' subscription</span><span class="in-tier-tag" id="st-tier"></span></div>' +
        '<div class="in-subtile-price"><span class="amt" id="st-monthly"></span><span class="per">/month</span></div>' +
        '<div class="in-subtile-meta" id="st-meta"></div>' +
      '</div>';
    var range = $('xp-range');
    function upd() {
      var u = parseInt(range.value, 10) || 0;
      var perUnit = s.listPerUnit * (1 - bandDisc(s.discBands, u) / 100);
      $('xp-count').textContent = u + ' ' + unit;
      $('st-tier').textContent = tierName(u) + ' tier';
      $('st-monthly').textContent = zar(u * perUnit);
      $('st-meta').textContent = zar(perUnit) + ' per ' + one + '/month · ' + u + ' ' + unit;
    }
    range.addEventListener('input', upd);
    upd();
  }

  function renderTiers(s) {
    var html = CFG.plans.map(function (p) {
      var perUnit = s.listPerUnit * (1 - p.discount / 100);
      var monthly = s.units * perUnit;
      var feats = p.features.map(function (f) { return '<li>' + esc(f) + '</li>'; }).join('');
      var one = (CFG.slider.unit || 'unit').replace(/s$/, '');
      var priceBlock = s.units > 0
        ? '<div class="in-plan-price"><span class="amt">' + zar(perUnit) + '</span><span class="per"> /' + esc(one) + '/mo</span></div>' +
          '<div class="in-plan-meta">' + zar(monthly) + '/mo for ' + s.units + ' · ' + p.term + '-month term</div>'
        : '<div class="in-plan-price"><span class="amt">' + zar(perUnit) + '</span><span class="per"> /unit/mo</span></div>' +
          '<div class="in-plan-meta">' + p.term + '-month term</div>';
      return '<div class="in-plan' + (p.recommended ? ' in-plan--featured' : '') + '">' +
        (p.recommended ? '<span class="in-plan-badge">Recommended</span>' : '') +
        '<div class="in-plan-name">' + esc(p.name) + '</div>' +
        '<div class="in-plan-blurb">' + esc(p.blurb) + '</div>' + priceBlock +
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
    var w = {};
    document.querySelectorAll('[data-weight]').forEach(function (el) { w[el.dataset.weight] = el.value; });
    var st = { assumptions: a, weights: w, term: num($('ph-term')), q_for: $('q-for').value, q_by: $('q-by').value };
    if (CFG.mode === 'software') { st.vehicles = num($('ph-vehicles')); st.integration = $('ph-integration').checked; }
    else { st.billing = $('ph-billing').value; st.rows = Array.prototype.map.call($('ph-rows').tBodies[0].querySelectorAll('tr'), hwReadRow); }
    return st;
  }
  var saveTimer = null;
  function scheduleSave() { clearTimeout(saveTimer); saveTimer = setTimeout(function () { draft.save(serialize()); }, 400); }

  function restore(st) {
    if (CFG.mode === 'software') buildSoftware({ vehicles: st.vehicles, integration: st.integration, term: st.term });
    else buildHardware({ rows: st.rows, term: st.term, billing: st.billing });
    if (st.term) $('ph-term').value = st.term;
    if (st.assumptions) Object.keys(st.assumptions).forEach(function (k) {
      var el = document.querySelector('.in-assumptions input[data-key="' + k + '"]'); if (el) el.value = st.assumptions[k];
    });
    if (st.weights) Object.keys(st.weights).forEach(function (k) {
      var el = document.querySelector('[data-weight="' + k + '"]'); if (el) el.value = st.weights[k];
    });
    $('q-for').value = st.q_for || ''; $('q-by').value = st.q_by || '';
    wireInputs(); compute();
  }
  function buildFresh() { CFG.mode === 'software' ? buildSoftware(PREFILL) : buildHardware(PREFILL); wireInputs(); compute(); }
  function wireInputs() {
    left.querySelectorAll('input, select').forEach(function (el) {
      el.addEventListener('input', onChange); el.addEventListener('change', onChange);
    });
  }

  // ── quote PDF ────────────────────────────────────────────────────────────
  function cookie(name) { var m = document.cookie.match('(?:^|; )' + name + '=([^;]*)'); return m ? decodeURIComponent(m[1]) : ''; }
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
    fetch(URLS.quote, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cookie('csrftoken') }, body: JSON.stringify(payload) })
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
  function showGate() {
    ['.in-xp', '.in-pricing-layout'].forEach(function (sel) { var e = document.querySelector(sel); if (e) e.style.display = 'none'; });
    var g = $('ph-gate');
    g.hidden = false;
    g.innerHTML = '<h2>Complete the needs assessment first</h2>' +
      '<p class="in-panel-sub">Pricing is generated from the client’s ' + esc(CFG.name) + ' needs assessment. ' +
      'Fill it in (in this browser) and the toolkit will pre-fill and weight the pricing automatically.</p>' +
      '<div class="in-toolbar"><a class="in-btn" href="' + URLS.assess + '">Start the ' + esc(CFG.name) + ' assessment</a></div>';
  }

  if (!ANS) { showGate(); return; }
  $('q-pdf').addEventListener('click', generatePdf);
  $('q-for').addEventListener('input', onChange); $('q-by').addEventListener('input', onChange);
  buildFresh();
  draft.offerResume($('ph-resume'), restore, buildFresh);
})();
