/* pf.js: Plan Friday's drawing engine and browser helpers (wrapped by client_code/pf.py; the data, dates and
   weather words live in Python). The party pictures are inline SVG line art in the three printing inks
   (viewBox 0 0 100 80; classes r/y/n/p/g/k pick the ink, ns = no stroke, thin = a finer line); the weather icons
   are the same style (viewBox 0 0 40 40). Also: copy to the clipboard, download a file, the share sheet, confetti. */
(function () {
  'use strict';
  function esc(s) { return window.UI && UI.esc ? UI.esc(s) : String(s == null ? '' : s); }

  /* ------------------------------------------------------------------ pictures (viewBox 0 0 100 80) */
  var ART = {
    classic: '<path d="M38 20c-3-4 3-6 0-10M50 18c-3-4 3-6 0-10M62 20c-3-4 3-6 0-10"/>' +
      '<path class="p" d="M20 46a30 19 0 0 1 60 0z"/><circle class="y" cx="50" cy="26" r="4"/>' +
      '<path class="r" d="M14 46h72v8a12 12 0 0 1-12 12H26a12 12 0 0 1-12-12z"/><path d="M14 50H7M86 50h7"/><path class="thin" d="M24 56h52" stroke-dasharray="3 4"/>',
    soup: '<path d="M38 22c-4-5 4-8 0-13M50 24c-4-5 4-8 0-13M62 22c-4-5 4-8 0-13"/>' +
      '<path class="r" d="M22 36h56v20a14 14 0 0 1-14 14H36a14 14 0 0 1-14-14z"/><rect class="p" x="17" y="30" width="66" height="8" rx="2"/>' +
      '<path d="M22 44H12v9h10M78 44h10v9H78"/><circle class="p ns" cx="36" cy="56" r="2.6"/><circle class="p ns" cx="50" cy="56" r="2.6"/><circle class="p ns" cx="64" cy="56" r="2.6"/>',
    pancakes: '<ellipse class="p" cx="50" cy="66" rx="42" ry="8"/><rect class="y" x="18" y="53" width="64" height="10" rx="5"/><rect class="y" x="21" y="43" width="58" height="10" rx="5"/>' +
      '<rect class="y" x="19" y="33" width="62" height="10" rx="5"/><path class="r" d="M24 34q26-6 52 0v4q-3 9-6 0-4 10-9 0-5 12-10 0-5 9-9 0-4 8-8 0-3 7-6 0z"/><rect class="p" x="43" y="24" width="14" height="9" rx="1.5"/>',
    dumplings: '<ellipse class="n" cx="50" cy="60" rx="44" ry="13"/>' +
      '<path class="p" d="M14 60q13-26 30 0z"/><path class="thin" d="M22 50l2 4M28 46v5M34 47l-1 5"/>' +
      '<path class="p" d="M40 64q13-26 30 0z"/><path class="thin" d="M48 54l2 4M54 50v5M60 51l-1 5"/>' +
      '<path class="p" d="M58 56q12-22 26 0z"/><path class="thin" d="M65 48l1.5 3.5M71 45v4.5M76 46.5l-1 4"/>' +
      '<path d="M58 6l30 32M66 4l28 32" style="stroke-width:3.2"/>',
    tacos: '<path class="g" d="M16 38q4-13 12-7 6-11 14-3 8-11 15-2 8-10 14 0 8-7 13 7z"/><circle class="r" cx="30" cy="31" r="3.4"/><circle class="r" cx="48" cy="28" r="3.4"/><circle class="r" cx="66" cy="31" r="3.4"/>' +
      '<path class="y" d="M12 38h76a38 32 0 0 1-76 0z"/><circle class="k ns" cx="30" cy="50" r="1.4"/><circle class="k ns" cx="46" cy="58" r="1.4"/><circle class="k ns" cx="62" cy="52" r="1.4"/><circle class="k ns" cx="72" cy="44" r="1.4"/><circle class="k ns" cx="40" cy="45" r="1.4"/>',
    fondue: '<path d="M40 30 26 4M60 30 76 4"/><rect class="p" x="22" y="2" width="8" height="8" transform="rotate(-25 26 6)"/><rect class="p" x="72" y="1" width="8" height="8" transform="rotate(25 76 5)"/>' +
      '<path class="r" d="M22 30h56l-4 22a8 8 0 0 1-8 6H34a8 8 0 0 1-8-6z"/><ellipse class="y" cx="50" cy="30" rx="28" ry="5"/>' +
      '<path d="M32 74l7-15M68 74l-7-15M24 74h52"/><path class="y" d="M50 70c-5-3-3-8 0-11 3 3 5 8 0 11z"/>',
    pizza: '<circle class="y" cx="50" cy="42" r="34"/><circle class="r" cx="50" cy="42" r="27"/>' +
      '<ellipse class="p ns" cx="40" cy="32" rx="6" ry="4"/><ellipse class="p ns" cx="62" cy="38" rx="5" ry="4"/><ellipse class="p ns" cx="46" cy="55" rx="6" ry="4"/>' +
      '<circle class="n" cx="58" cy="26" r="3"/><circle class="n" cx="34" cy="46" r="3"/><circle class="n" cx="64" cy="54" r="3"/>' +
      '<path d="M50 42V8M50 42l30 17M50 42 20 59"/>',
    roast: '<ellipse class="p" cx="50" cy="64" rx="45" ry="11"/><circle class="g" cx="14" cy="62" r="4.5"/><circle class="g" cx="86" cy="62" r="4.5"/><circle class="r" cx="22" cy="68" r="3.5"/>' +
      '<path class="y" d="M66 40c8-7 16-6 18-1s-3 9-10 9"/><circle class="p" cx="86" cy="37" r="3.4"/><circle class="p" cx="83" cy="31" r="3"/>' +
      '<path class="y" d="M22 60c-3-19 12-32 31-32s30 13 26 32z"/><path class="thin" d="M36 42q6-6 14-6"/>',
    salad: '<path class="g" d="M18 42q5-17 16-9 6-15 16-4 9-13 17 0 10-9 15 13z"/><circle class="r" cx="34" cy="36" r="4"/><circle class="r" cx="60" cy="32" r="4"/><circle class="y" cx="48" cy="38" r="3"/>' +
      '<path class="n" d="M12 42h76a38 30 0 0 1-76 0z"/><path class="thin" d="M22 52h56" stroke-dasharray="2 5" style="stroke:var(--c-surface)"/><path d="M72 4l-8 34M80 6l-10 32"/>',
    pie: '<path d="M44 16c-3-4 3-6 0-10M56 16c-3-4 3-6 0-10"/><path class="r" d="M12 44v10c0 8 17 13 38 13s38-5 38-13V44"/><ellipse class="y" cx="50" cy="44" rx="38" ry="12"/>' +
      '<path class="thin" d="M24 38l12 15M38 34l14 19M54 33l14 18M30 50l14-16M46 54l16-20M62 53l12-15"/><circle class="r" cx="50" cy="44" r="3.2"/>',
    wine: '<path class="n" d="M62 10h10v14c7 4 10 9 10 16v34H52V40c0-7 3-12 10-16z"/><rect class="p" x="55" y="44" width="24" height="14"/><path class="thin" d="M60 50h14"/>' +
      '<path class="p" d="M14 22h26c0 15-5 24-13 24s-13-9-13-24z"/><path class="r ns" d="M16 29h22c-1 9-5 14-11 14s-10-5-11-14z"/><path d="M27 46v20M18 68h18"/>' +
      '<path class="thin" d="M44 14l4-5M46 20l6-1M42 9l1-6"/>',
    bbq: '<path d="M40 18c-3-4 3-6 0-10M54 16c-3-4 3-6 0-10"/><rect class="r" x="24" y="27" width="24" height="7" rx="3.5" transform="rotate(-8 36 30)"/><rect class="y" x="50" y="26" width="26" height="7" rx="3.5" transform="rotate(6 63 30)"/>' +
      '<path class="k" d="M16 36h68a34 26 0 0 1-68 0z"/><path d="M16 36h68"/><path d="M32 58l-9 18M68 58l9 18M50 62v14M19 76h10M71 76h10"/>',
    cake: '<path class="y" d="M35 28v-12M50 28v-12M65 28v-12" style="stroke-width:4.5"/><path class="r" d="M35 12c-3-2-2-6 0-8 2 2 3 6 0 8zM50 12c-3-2-2-6 0-8 2 2 3 6 0 8zM65 12c-3-2-2-6 0-8 2 2 3 6 0 8z"/>' +
      '<rect class="p" x="20" y="28" width="60" height="38" rx="3"/><path class="r" d="M20 31h60v8q-4 7-8 0-5 8-10 0-5 8-10 0-5 8-10 0-5 8-10 0-4 7-8 0z"/>' +
      '<path class="thin" d="M24 52h52"/><path d="M10 68h80"/>'
  };

  /* An SVG picture; label = its accessible name, "" = decorative (hidden from screen readers). */
  function art(key, label) {
    var a11y = label ? 'role="img" aria-label="' + esc(label) + '"' : 'aria-hidden="true" focusable="false"';
    return '<svg class="pf-art" viewBox="0 0 100 80" ' + a11y + '>' + (ART[key] || ART.classic) + '</svg>';
  }

  /* ------------------------------------------------------------------ weather icons (viewBox 0 0 40 40) */
  var CLOUD = 'M9 31h22a8 8 0 0 0 0-16 10 10 0 0 0-19 3 6.5 6.5 0 0 0-3 13z', CLOUD_UP = 'M9 24h22a8 8 0 0 0 0-16 10 10 0 0 0-19 3 6.5 6.5 0 0 0-3 13z';
  var WX_ART = {
    sun: '<circle class="y" cx="20" cy="20" r="8"/><path d="M20 4v5M20 31v5M4 20h5M31 20h5M8.7 8.7l3.5 3.5M27.8 27.8l3.5 3.5M8.7 31.3l3.5-3.5M27.8 12.2l3.5-3.5"/>',
    moon: '<path class="y" d="M25 6a14 14 0 1 0 9 22A12 12 0 0 1 25 6z"/><circle class="k ns" cx="31" cy="10" r="1.3"/><circle class="k ns" cx="35" cy="17" r="1"/>',
    partly: '<circle class="y" cx="15" cy="15" r="7"/><path d="M15 3v3M3 15h3M6.5 6.5l2 2M23.5 6.5l-2 2"/><path class="p" d="M12 34h18a7 7 0 0 0 0-14 9 9 0 0 0-17 3 6 6 0 0 0-1 11z"/>',
    cloud: '<path class="p" d="' + CLOUD + '"/>',
    fog: '<path class="p" d="M9 25h22a8 8 0 0 0 0-16 10 10 0 0 0-19 3 6.5 6.5 0 0 0-3 13z"/><path d="M5 30h30M9 35h22"/>',
    drizzle: '<path class="p" d="' + CLOUD_UP + '"/><circle class="n" cx="13" cy="31" r="1.8"/><circle class="n" cx="21" cy="34" r="1.8"/><circle class="n" cx="29" cy="31" r="1.8"/>',
    rain: '<path class="p" d="' + CLOUD_UP + '"/><path d="M14 28l-2 7M21 28l-2 7M28 28l-2 7" style="stroke:var(--c-navy);stroke-width:3"/>',
    snow: '<path class="p" d="' + CLOUD_UP + '"/><path d="M13 29v7M9.5 32.5h7M27 29v7M23.5 32.5h7"/>',
    storm: '<path class="n" d="' + CLOUD_UP + '"/><path class="y" d="M22 22l-6 9h5l-3 7 9-11h-5l3-5z"/>'
  };
  function wx(kind, label) {
    return '<svg class="pf-art pf-wxi" viewBox="0 0 40 40" ' + (label ? 'role="img" aria-label="' + esc(label) + '"' : 'aria-hidden="true" focusable="false"') + '>' +
      (WX_ART[kind] || WX_ART.cloud) + '</svg>';
  }

  /* ------------------------------------------------------------------ browser helpers */
  /* Copy text; the Promise says whether it worked (Python shows the toast). */
  function copy(text) {
    function fallback() {
      var t = document.createElement('textarea'); t.value = text; t.style.position = 'fixed'; t.style.opacity = '0';
      document.body.appendChild(t); t.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      t.remove();
      return ok;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () { return true; }, function () { return fallback(); });
    }
    return Promise.resolve(fallback());
  }
  function download(name, text, type) {
    var blob = new Blob([text], { type: type || 'text/plain' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name;
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  function canShare() { return !!navigator.share; }
  function share(title, text, url) { if (navigator.share) navigator.share({ title: title, text: text, url: url }).catch(function () {}); }
  function confetti() {
    if (window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var box = document.createElement('div'); box.className = 'pf-confetti'; box.setAttribute('aria-hidden', 'true');
    var colours = ['var(--c-brand)', 'var(--c-accent)', 'var(--c-navy)', 'var(--c-good)', 'var(--c-surface)'];
    var html = '';
    for (var i = 0; i < 90; i++) {
      html += '<i style="left:' + (Math.random() * 100) + '%;background:' + colours[i % colours.length] + ';--dx:' + (Math.random() * 160 - 80) + 'px;--rot:' +
        (Math.random() * 900 - 450) + 'deg;animation-duration:' + (1.6 + Math.random() * 1.6) + 's;animation-delay:' + (Math.random() * .4) + 's;' +
        (i % 3 ? '' : 'border-radius:50%;width:10px;height:10px;') + 'border:1px solid #1f1a14"></i>';
    }
    box.innerHTML = html;
    document.body.appendChild(box);
    setTimeout(function () { box.remove(); }, 3800);
  }
  /* Is the keyboard in a text field inside el? (the party page's quiet refresh waits until it isn't) */
  function typingIn(el) {
    var a = document.activeElement;
    return !!(a && /INPUT|TEXTAREA|SELECT/.test(a.tagName) && el && el.contains(a));
  }
  function dialogOpen() { return !!document.querySelector('.anvil-modal.in, .modal.in, .anvil-modal[style*="display: block"]'); }
  /* Test a JavaScript regular expression (case-insensitive); Python's re in the browser lacks some features. */
  function test(pattern, text) { try { return new RegExp(pattern, 'i').test(String(text || '')); } catch (e) { return false; } }

  window.PF = { ART: ART, art: art, wx: wx, copy: copy, download: download, canShare: canShare, share: share, confetti: confetti,
    typingIn: typingIn, dialogOpen: dialogOpen, test: test };
})();
