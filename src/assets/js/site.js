/* Maya Tuya — site.js
   1. Mobile menu + submenu toggles
   2. Form submission (Web3Forms) with an inline confirmation
   No dependencies. */
(function () {
  'use strict';

  // ── 1. Navigation ──────────────────────────────────────────────
  var toggle = document.querySelector('.mt-nav-toggle');
  var nav = document.getElementById('mt-nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
  }
  document.querySelectorAll('.mt-nav .has-sub > a').forEach(function (a) {
    a.addEventListener('click', function (e) {
      // On small screens a tap on a parent opens the submenu instead of navigating
      if (window.matchMedia('(max-width: 860px)').matches) {
        var li = a.parentElement;
        if (!li.classList.contains('open')) { e.preventDefault(); li.classList.add('open'); }
      }
    });
  });

  // ── 2. Forms ───────────────────────────────────────────────────
  function esc(s) { return s.replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function linkify(s) {
    return esc(s).replace(/([\w.+-]+@[\w-]+\.[\w.]+)/g, '<a href="mailto:$1">$1</a>');
  }

  document.querySelectorAll('form.mt-form').forEach(function (form) {
    var status = form.querySelector('.mt-form-status');
    var btn = form.querySelector('button[type="submit"]');
    var date = form.querySelector('input[type="date"]');
    if (date) { date.min = new Date().toISOString().slice(0, 10); }

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (!form.checkValidity()) { form.reportValidity(); return; }
      var label = btn.textContent;
      btn.disabled = true; btn.textContent = '…'; status.textContent = '';

      var data = {};
      new FormData(form).forEach(function (v, k) { data[k] = v; });

      fetch(form.action, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(data)
      })
        .then(function (r) { return r.json(); })
        .then(function (res) {
          if (!res.success) { throw new Error(res.message || 'failed'); }
          var go = form.getAttribute('data-redirect');
          if (go) { window.location.assign(go); return; }
          var msg = (form.getAttribute('data-success') || '').replace('[Name]', data.first_name || '');
          var box = document.createElement('div');
          box.className = 'mt-form-success'; box.setAttribute('role', 'status');
          box.innerHTML = linkify(msg);
          form.replaceWith(box);
          box.scrollIntoView({ block: 'center', behavior: 'smooth' });
        })
        .catch(function () {
          btn.disabled = false; btn.textContent = label;
          status.innerHTML = esc(form.getAttribute('data-error') || 'Something went wrong.') +
            ' <a href="mailto:' + esc(form.getAttribute('data-mail') || '') + '">' + esc(form.getAttribute('data-mail') || '') + '</a>';
        });
    });
  });
})();
