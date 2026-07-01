/* Shared draft persistence for internal tools (localStorage).
   Tools start fresh each visit; if an unfinished draft exists, a resume banner
   is offered. window.MhareDraft is used by the assessment and pricing pages. */
(function () {
  'use strict';

  function ago(ts) {
    var s = Math.max(1, Math.round((Date.now() - ts) / 1000));
    if (s < 60) return s + 's ago';
    var m = Math.round(s / 60);
    if (m < 60) return m + ' min ago';
    var h = Math.round(m / 60);
    if (h < 24) return h + 'h ago';
    return new Date(ts).toLocaleString();
  }

  function Draft(key) { this.key = key; }
  Draft.prototype.save = function (data) {
    try { localStorage.setItem(this.key, JSON.stringify({ t: Date.now(), data: data })); } catch (e) {}
  };
  Draft.prototype.load = function () {
    try { var r = localStorage.getItem(this.key); return r ? JSON.parse(r) : null; } catch (e) { return null; }
  };
  Draft.prototype.clear = function () { try { localStorage.removeItem(this.key); } catch (e) {} };

  /* Show a resume banner in `el`. onResume/onDiscard are callbacks. */
  Draft.prototype.offerResume = function (el, onResume, onDiscard) {
    var saved = this.load();
    if (!el || !saved) return false;
    var self = this;
    el.innerHTML = 'You have an unsaved draft from <strong>' + ago(saved.t) + '</strong>. ' +
      '<button type="button" class="in-btn in-btn--sm" data-resume style="margin-left:8px;">Resume</button> ' +
      '<button type="button" class="in-btn in-btn--sm in-btn--ghost" data-discard>Start new</button>';
    el.hidden = false;
    el.querySelector('[data-resume]').addEventListener('click', function () {
      onResume(saved.data); el.hidden = true;
    });
    el.querySelector('[data-discard]').addEventListener('click', function () {
      self.clear(); if (onDiscard) onDiscard(); el.hidden = true;
    });
    return true;
  };

  window.MhareDraft = function (key) { return new Draft(key); };
})();
