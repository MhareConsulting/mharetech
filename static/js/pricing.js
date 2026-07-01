/* myTrack Pricing Toolkit — client-side calculator.
   Mirrors the Excel model (Cost Inputs → Quote Builder) exactly. */
(function () {
  'use strict';

  var SEED = [
    { group: 'Long-haul trucks', qty: 12, source: 'CAN', panic: true, immob: true, rfid: true, temp: false, batt: true, install: 'Standard' },
    { group: 'Delivery vans', qty: 14, source: 'OBD', panic: true, immob: false, rfid: true, temp: false, batt: false, install: 'Basic' },
    { group: 'Reefer trucks', qty: 4, source: 'CAN', panic: true, immob: true, rfid: true, temp: true, batt: true, install: 'Advanced' }
  ];

  var tbody = document.querySelector('#ph-rows tbody');
  var assumptionInputs = document.querySelectorAll('.in-assumptions input[data-key]');

  function zar(n) {
    n = Math.round(n || 0);
    return 'R' + n.toLocaleString('en-ZA');
  }

  function num(el) { var v = parseFloat(el && el.value); return isNaN(v) ? 0 : v; }

  function assumptions() {
    var a = {};
    assumptionInputs.forEach(function (el) { a[el.dataset.key] = num(el); });
    return a;
  }

  function rowTemplate(r) {
    r = r || { group: '', qty: 0, source: 'None', install: 'Basic' };
    function opt(list, sel) {
      return list.map(function (o) { return '<option' + (o === sel ? ' selected' : '') + '>' + o + '</option>'; }).join('');
    }
    function cb(key) { return '<input type="checkbox" data-f="' + key + '"' + (r[key] ? ' checked' : '') + '>'; }
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td><input type="text" data-f="group" value="' + (r.group || '') + '" style="min-width:120px;"></td>' +
      '<td><input type="number" min="0" data-f="qty" value="' + (r.qty || 0) + '" style="width:64px;"></td>' +
      '<td><select data-f="source">' + opt(['CAN', 'OBD', 'Probe', 'None'], r.source) + '</select></td>' +
      '<td style="text-align:center;">' + cb('panic') + '</td>' +
      '<td style="text-align:center;">' + cb('immob') + '</td>' +
      '<td style="text-align:center;">' + cb('rfid') + '</td>' +
      '<td style="text-align:center;">' + cb('temp') + '</td>' +
      '<td style="text-align:center;">' + cb('batt') + '</td>' +
      '<td><select data-f="install">' + opt(['Basic', 'Standard', 'Advanced'], r.install) + '</select></td>' +
      '<td><button type="button" class="in-btn in-btn--ghost in-btn--sm" data-remove>×</button></td>';
    return tr;
  }

  function readRow(tr) {
    var o = {};
    tr.querySelectorAll('[data-f]').forEach(function (el) {
      var k = el.dataset.f;
      if (el.type === 'checkbox') o[k] = el.checked;
      else if (el.type === 'number') o[k] = num(el);
      else o[k] = el.value;
    });
    return o;
  }

  function compute() {
    var a = assumptions();
    var margin = a.margin_pct / 100, hwmk = a.hwmk_pct / 100, insmk = a.insmk_pct / 100;
    var term = Math.max(1, num(document.getElementById('ph-term')));
    var amortise = document.getElementById('ph-billing').value === 'Amortised';

    var runCost = a.m_sim + a.m_host + a.m_lic + a.m_support + a.m_notif + a.m_api + a.m_warranty;
    var srcCost = { CAN: a.can, OBD: a.obd, Probe: a.probe, None: 0 };
    var labour = { Basic: a.lab_basic, Standard: a.lab_standard, Advanced: a.lab_advanced };

    var rows = Array.prototype.map.call(tbody.querySelectorAll('tr'), readRow);
    var totalUnits = rows.reduce(function (s, r) { return s + (r.qty || 0); }, 0);

    var discPct = totalUnits <= 20 ? a.disc_small : (totalUnits <= 100 ? a.disc_med : a.disc_ent);
    var disc = discPct / 100;
    var tier = totalUnits === 0 ? '—' : (totalUnits <= 20 ? 'Small' : (totalUnits <= 100 ? 'Medium' : 'Enterprise'));

    var totalOnce = 0, totalMonthly = 0, breakdown = [];
    rows.forEach(function (r) {
      if (!r.qty) { if (r.group) breakdown.push({ name: r.group, mo: 0, once: 0, qty: 0 }); return; }
      var hw = a.tracker + a.sim + a.cable + (srcCost[r.source] || 0)
        + (r.panic ? a.panic : 0) + (r.immob ? a.immob : 0) + (r.rfid ? a.rfid : 0)
        + (r.temp ? a.temp : 0) + (r.batt ? a.batt : 0);
      var ins = labour[r.install] || 0;
      var hwPrice = hw * (1 + hwmk);
      var insPrice = ins * (1 + insmk);
      var monthlyPre = runCost / (1 - margin) + (amortise ? hwPrice / term : 0);
      var monthlyFinal = monthlyPre * (1 - disc);
      var oncePerUnit = insPrice + (amortise ? 0 : hwPrice);
      totalOnce += r.qty * oncePerUnit;
      totalMonthly += r.qty * monthlyFinal;
      breakdown.push({ name: r.group || '(group)', qty: r.qty, mo: monthlyFinal, once: oncePerUnit });
    });

    var init = a.init;
    var totalOnceOff = totalOnce + (totalUnits > 0 ? init : 0);
    var tcv = totalOnceOff + totalMonthly * term;

    document.getElementById('r-tier').textContent = tier + (totalUnits ? ' · ' + totalUnits + ' units' : '');
    document.getElementById('r-units').textContent = totalUnits;
    document.getElementById('r-hwinstall').textContent = zar(totalOnce);
    document.getElementById('r-init').textContent = totalUnits > 0 ? zar(init) : zar(0);
    document.getElementById('r-disc').textContent = discPct + '%';
    document.getElementById('r-onceoff').textContent = zar(totalOnceOff);
    document.getElementById('r-monthly').textContent = zar(totalMonthly);
    document.getElementById('r-avg').textContent = totalUnits > 0 ? zar(totalMonthly / totalUnits) : zar(0);
    document.getElementById('r-tcv').textContent = zar(tcv);

    document.getElementById('r-breakdown').innerHTML = breakdown.map(function (b) {
      return '<div class="in-kpi"><span class="k">' + b.name + (b.qty ? ' ×' + b.qty : '') +
        '</span><span class="v">' + zar(b.mo) + ' / ' + zar(b.once) + '</span></div>';
    }).join('') || '<p class="in-panel-sub">Add a vehicle group to see pricing.</p>';
  }

  function addRow(data) {
    var tr = rowTemplate(data);
    tbody.appendChild(tr);
    tr.addEventListener('input', compute);
    tr.addEventListener('change', compute);
    tr.querySelector('[data-remove]').addEventListener('click', function () { tr.remove(); compute(); });
  }

  // wire up
  SEED.forEach(addRow);
  document.getElementById('ph-add').addEventListener('click', function () { addRow(); compute(); });
  document.getElementById('ph-billing').addEventListener('change', compute);
  document.getElementById('ph-term').addEventListener('input', compute);
  assumptionInputs.forEach(function (el) { el.addEventListener('input', compute); });
  compute();
})();
