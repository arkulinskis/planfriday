/* core.js: the shared front-end engine (window.UI). Same in every app made from APP_MAKER/template;
   app-specific things live in web/app.js (brand, nav, footer) and web/pages/*.html (the pages).

   Pages:   UI.page(name, {title, nav, icon, auth, order, chrome}, mount)
              auth: null (anyone) | 'guest' (signed-out only) | 'user' | 'admin'
              nav: label for the header / phone tab bar (omit to keep it out of the menus)
              mount(view, ctx) draws into `view`; ctx = {args, me, go, api}. Return a Promise (the page
              is "ready" when it resolves) or {ready, destroy}. URLs are #name/arg1/arg2.
   Server:  UI.api(fn, ...args) -> Promise of the server function's return value. A reply of
              {ok: false, error} rejects with that message (shown as a toast unless you .catch it).
            UI.apiQuiet(fn, ...args) is the same without Anvil's loading spinner.
   Auth:    UI.auth('login'|'signup'|'reset'|'logout', {...}) -> Promise of {ok, me, message}
   Helpers: UI.esc, UI.icon, UI.toast, UI.modal, UI.confirm, UI.busy, UI.formData, UI.fmtDate, UI.ago,
            UI.store, UI.setTheme, UI.feedback, UI.go, UI.refresh
   Tests:   window.UI_READY is true when the current page has finished loading. */
(function () {
  'use strict';
  if (window.UI && window.UI.__v) return;
  var UI = window.UI = { __v: 1, pages: {}, me: null, config: { name: 'App', key: 'app', home: 'home', landing: 'landing' } };
  window.UI_READY = false;

  UI.configure = function (cfg) { Object.keys(cfg).forEach(function (k) { UI.config[k] = cfg[k]; }); };

  /* ------------------------------------------------------------------ small helpers */
  UI.esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  };
  UI.plural = function (n, one, many) { return n + ' ' + (n === 1 ? one : (many || one + 's')); };
  UI.initials = function (name) {
    var p = String(name || '?').trim().split(/\s+/);
    return ((p[0] || '?')[0] + (p.length > 1 ? p[p.length - 1][0] : '')).toUpperCase();
  };
  UI.fmtDate = function (iso, opts) {
    if (!iso) return '';
    var d = iso.length <= 10 ? new Date(iso + 'T12:00:00') : new Date(iso);
    return d.toLocaleDateString(undefined, opts || { day: 'numeric', month: 'short', year: 'numeric' });
  };
  UI.fmtDateTime = function (iso) {
    return iso ? new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
  };
  UI.ago = function (iso) {
    if (!iso) return '';
    var s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (s < 60) return 'just now';
    var steps = [[60, 'minute'], [24, 'hour'], [7, 'day'], [4.35, 'week'], [12, 'month'], [Infinity, 'year']], n = s / 60;
    for (var i = 0; i < steps.length; i++) {
      if (n < steps[i][0]) { n = Math.floor(n); return UI.plural(n, steps[i][1]) + ' ago'; }
      n = n / steps[i][0];
    }
    return '';
  };
  UI.store = {
    get: function (k, dflt) { try { var v = localStorage.getItem(UI.config.key + '.' + k); return v == null ? dflt : JSON.parse(v); } catch (e) { return dflt; } },
    set: function (k, v) { try { localStorage.setItem(UI.config.key + '.' + k, JSON.stringify(v)); } catch (e) {} }
  };
  UI.formData = function (form) {
    var out = {};
    Array.prototype.forEach.call(form.elements, function (el) {
      if (!el.name || el.disabled) return;
      if (el.type === 'checkbox') out[el.name] = el.checked;
      else if (el.type === 'radio') { if (el.checked) out[el.name] = el.value; }
      else out[el.name] = el.value;
    });
    return out;
  };
  /* Disable a button while a Promise runs; returns the Promise. */
  UI.busy = function (btn, promise) {
    if (!btn) return promise;
    btn.disabled = true; btn.classList.add('is-busy');
    var done = function () { btn.disabled = false; btn.classList.remove('is-busy'); };
    promise.then(done, done);
    return promise;
  };

  var ICONS = {
    home: '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/>',
    user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
    users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.5 3-5.5 6.5-5.5s6.5 2 6.5 5.5"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14.7c2.2.6 3.5 2.4 3.5 5.3"/>',
    sliders: '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/>',
    logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    trash: '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M6 6l1 14h10l1-14"/>',
    edit: '<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>',
    check: '<path d="M5 12.5l4.5 4.5L19 7"/>',
    x: '<path d="M6 6l12 12M18 6 6 18"/>',
    chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20.5l1.4-4.9A8 8 0 1 1 21 12z"/>',
    bell: '<path d="M6 8a6 6 0 1 1 12 0c0 7 3 8 3 8H3s3-1 3-8"/><path d="M10 20a2 2 0 0 0 4 0"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    moon: '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    menu: '<path d="M4 7h16M4 12h16M4 17h16"/>',
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
    back: '<path d="M19 12H5M11 18l-6-6 6-6"/>',
    mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8h.01"/>',
    bug: '<rect x="7" y="8" width="10" height="12" rx="5"/><path d="M12 8V5M9 5.5 7.5 4M15 5.5 16.5 4M7 13H3M21 13h-4M7.5 18l-3 2M16.5 18l3 2M7.5 9.5l-3-2M16.5 9.5l3-2"/>',
    bulb: '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    star: '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z"/>',
    heart: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
    search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    chevron: '<path d="m6 9 6 6 6-6"/>',
    external: '<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>',
    lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    inbox: '<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5 5h14l2 8v6H3v-6z"/>',
    grid: '<rect x="4" y="4" width="7" height="7" rx="1.5"/><rect x="13" y="4" width="7" height="7" rx="1.5"/><rect x="4" y="13" width="7" height="7" rx="1.5"/><rect x="13" y="13" width="7" height="7" rx="1.5"/>',
    sparkle: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    database: '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.5"/><path d="M4.5 5.5v13c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5v-13"/><path d="M4.5 12c0 1.4 3.4 2.5 7.5 2.5s7.5-1.1 7.5-2.5"/>',
    refresh: '<path d="M20 11a8 8 0 0 0-14.3-4.9L4 8"/><path d="M4 4v4h4"/><path d="M4 13a8 8 0 0 0 14.3 4.9L20 16"/><path d="M20 20v-4h-4"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    map: '<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2z"/><path d="M9 4v14M15 6v14"/>',
    pin: '<path d="M12 21s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    camera: '<path d="M4 8h3l2-3h6l2 3h3v12H4z"/><circle cx="12" cy="13.5" r="3.5"/>',
    image: '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/><path d="m21 16-5-5-9 9"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.7 3.8 5.7 3.8 9s-1.3 6.3-3.8 9c-2.5-2.7-3.8-5.7-3.8-9S9.5 5.7 12 3z"/>',
    copy: '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
    filter: '<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>',
    more: '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>'
  };
  UI.ICONS = ICONS;
  UI.icon = function (name, cls) {
    return '<svg class="ui-ic ' + (cls || '') + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICONS[name] || ICONS.sparkle) + '</svg>';
  };

  /* ------------------------------------------------------------------ toasts, modals */
  UI.toast = function (msg, kind) {
    var box = document.querySelector('.ui-toasts');
    if (!box) { box = document.createElement('div'); box.className = 'ui ui-toasts'; box.setAttribute('aria-live', 'polite'); document.body.appendChild(box); }
    var t = document.createElement('div');
    t.className = 'ui-toast' + (kind ? ' ' + kind : '');
    t.innerHTML = (kind === 'error' ? UI.icon('info') : kind === 'ok' ? UI.icon('check') : '') + '<span>' + UI.esc(msg) + '</span>';
    box.appendChild(t);
    setTimeout(function () { t.classList.add('out'); setTimeout(function () { t.remove(); }, 300); }, kind === 'error' ? 6500 : 3200);
  };
  UI.modal = function (html, opts) {
    opts = opts || {};
    var prev = document.activeElement;
    var wrap = document.createElement('div');
    wrap.className = 'ui ui-modal-wrap';
    wrap.innerHTML = '<div class="ui-modal' + (opts.wide ? ' wide' : '') + '" role="dialog" aria-modal="true">' +
      '<button class="ui-btn ghost icon ui-modal-x" data-close aria-label="Close">' + UI.icon('x') + '</button>' + html + '</div>';
    document.body.appendChild(wrap);
    document.documentElement.classList.add('ui-modal-open');
    function key(e) { if (e.key === 'Escape') close(); }
    function close() {
      if (!wrap.parentNode) return;
      wrap.remove(); document.removeEventListener('keydown', key);
      if (!document.querySelector('.ui-modal-wrap')) document.documentElement.classList.remove('ui-modal-open');
      if (opts.onclose) opts.onclose();
      if (prev && prev.focus) prev.focus();
    }
    document.addEventListener('keydown', key);
    wrap.addEventListener('mousedown', function (e) { if (e.target === wrap) close(); });
    wrap.addEventListener('click', function (e) { if (e.target.closest('[data-close]')) close(); });
    var first = wrap.querySelector('input, textarea, select');
    setTimeout(function () { (first || wrap.querySelector('.ui-modal')).focus && (first || wrap.querySelector('.ui-modal')).focus(); }, 30);
    return { el: wrap.querySelector('.ui-modal'), close: close };
  };
  UI.confirm = function (o) {
    o = typeof o === 'string' ? { title: o } : (o || {});
    return new Promise(function (resolve) {
      var answered = false;
      var m = UI.modal('<h2>' + UI.esc(o.title || 'Are you sure?') + '</h2>' + (o.text ? '<p class="muted">' + UI.esc(o.text) + '</p>' : '') +
        '<div class="ui-row end" style="margin-top:20px"><button class="ui-btn ghost" data-close>' + UI.esc(o.cancel || 'Cancel') + '</button>' +
        '<button class="ui-btn ' + (o.danger ? 'danger solid' : 'primary') + '" data-ok>' + UI.esc(o.ok || 'OK') + '</button></div>',
      { onclose: function () { if (!answered) resolve(false); } });
      m.el.querySelector('[data-ok]').onclick = function () { answered = true; m.close(); resolve(true); };
    });
  };

  /* ------------------------------------------------------------------ theme */
  UI.theme = function () { return UI.store.get('theme', 'auto'); };
  UI.applyTheme = function (t) {
    if (t === 'light' || t === 'dark') document.documentElement.setAttribute('data-theme', t);
    else document.documentElement.removeAttribute('data-theme');
    var dark = t === 'dark' || (t !== 'light' && window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('ui-dark', !!dark);
  };
  UI.setTheme = function (t) { UI.store.set('theme', t); UI.applyTheme(t); };
  UI.applyTheme(UI.theme());
  if (window.matchMedia) {
    try { matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () { UI.applyTheme(UI.theme()); }); } catch (e) {}
  }

  /* ------------------------------------------------------------------ server bridge */
  var bridge = null;
  function send(kind, payload) {
    if (!bridge) return Promise.reject(new Error('The app is still starting.'));
    var out;
    try { out = bridge(kind, JSON.stringify(payload || {})); } catch (e) { return Promise.reject(e); }
    return Promise.resolve(out).then(function (r) {
      r = typeof r === 'string' ? JSON.parse(r) : (r || {});
      if (r.error) {
        var err = new Error(r.error); err.uiApi = true; err.denied = !!r.denied;
        if (r.detail) console.error(kind, payload && payload.fn, r.detail);
        if (r.reload) setTimeout(function () { location.reload(); }, 2500);
        throw err;
      }
      return r.result;
    });
  }
  function apiCall(quiet, fn, args) {
    return send('call', { fn: fn, args: args, quiet: quiet }).then(function (res) {
      if (res && typeof res === 'object' && res.ok === false) {
        var err = new Error(res.error || 'That didn\'t work.'); err.uiApi = true; err.expected = true; err.result = res;
        throw err;
      }
      return res;
    });
  }
  UI.api = function (fn) { return apiCall(false, fn, Array.prototype.slice.call(arguments, 1)); };
  UI.apiQuiet = function (fn) { return apiCall(true, fn, Array.prototype.slice.call(arguments, 1)); };
  /* Errors nobody caught become a toast, so a failed action is never silent. */
  window.addEventListener('unhandledrejection', function (e) {
    if (e.reason && e.reason.uiApi) { e.preventDefault(); UI.toast(e.reason.message, 'error'); }
  });

  /* Sign in / up / out. On success it navigates: to where the visitor was heading (UI.after) or home
     after signing in, to the landing page after signing out. */
  UI.auth = function (kind, payload) {
    return send(kind, payload || {}).then(function (r) {
      if (r && r.ok === false) { var err = new Error(r.error); err.uiApi = true; err.expected = true; throw err; }
      if (r && 'me' in r && (r.me || kind === 'logout')) {
        UI.me = r.me || null;
        var target = r.me ? (UI.after || '#' + UI.config.home) : '#' + UI.config.landing;
        UI.after = null;
        if (location.hash === target) route(); else location.hash = target;
      }
      return r;
    });
  };
  /* Update the signed-in user's details (e.g. a new name) and redraw the header, without reloading the page. */
  UI.setMe = function (me) {
    UI.me = me || null;
    if (shellRoot) renderChrome(current.name);
  };

  /* ------------------------------------------------------------------ pages and routing */
  UI.page = function (name, opts, mount) {
    if (typeof opts === 'function') { mount = opts; opts = {}; }
    opts.name = name; opts.mount = mount;
    UI.pages[name] = opts;
  };
  UI.allowed = function (p) {
    if (!p) return false;
    if (p.auth === 'user') return !!UI.me;
    if (p.auth === 'admin') return !!(UI.me && UI.me.is_admin);
    if (p.auth === 'guest') return !UI.me;
    return true;
  };
  UI.navPages = function () {
    return Object.keys(UI.pages).map(function (k) { return UI.pages[k]; })
      .filter(function (p) { return p.nav && UI.allowed(p) && (!p.when || p.when()); })
      .sort(function (a, b) { return (a.order || 50) - (b.order || 50); });
  };
  UI.parseHash = function () {
    var h = (location.hash || '').replace(/^#!?\/?/, '');
    var parts = h.split('?')[0].split('/').filter(function (x) { return x !== ''; }).map(decodeURIComponent);
    return { name: parts[0] || '', args: parts.slice(1) };
  };
  UI.hashFor = function (name) {
    var args = Array.prototype.slice.call(arguments, 1).filter(function (a) { return a != null && a !== ''; });
    return '#' + [name].concat(args.map(encodeURIComponent)).join('/');
  };
  UI.go = function (name) {
    var h = UI.hashFor.apply(null, arguments);
    if (location.hash === h) route(); else location.hash = h;
  };
  UI.refresh = function () { route(); };
  UI.after = null;  // where to go after signing in

  var shellRoot = null, view = null, current = { name: null, destroy: null }, routeSeq = 0;

  function defaultPage() { return UI.me ? UI.config.home : UI.config.landing; }

  function route() {
    var r = UI.parseHash(), name = r.name || defaultPage(), p = UI.pages[name];
    if (!p) { name = defaultPage(); p = UI.pages[name]; r.args = []; }
    if (p.auth === 'guest' && UI.me) { p = UI.pages[UI.config.home]; name = UI.config.home; r.args = []; }
    if ((p.auth === 'user' || p.auth === 'admin') && !UI.me) {
      UI.after = location.hash && location.hash !== '#' ? location.hash : null;
      p = UI.pages.auth; name = 'auth'; r.args = [];
    }
    if (p.auth === 'admin' && !(UI.me && UI.me.is_admin)) {
      UI.toast('That page is for admins only.', 'error');
      p = UI.pages[UI.config.home]; name = UI.config.home; r.args = [];
    }
    var seq = ++routeSeq;
    window.UI_READY = false;
    if (current.destroy) { try { current.destroy(); } catch (e) { console.error(e); } }
    current = { name: name, args: r.args, destroy: null };
    if (shellRoot) {
      shellRoot.className = 'ui ui-shell page-' + name + (UI.me ? ' signed-in' : ' signed-out') + (p.chrome === false ? ' no-chrome' : '');
      renderChrome(name);
    }
    // A fresh element for every page, so listeners a page adds to `view` never pile up.
    var fresh = view.cloneNode(false);
    view.parentNode.replaceChild(fresh, view);
    view = fresh;
    window.scrollTo(0, 0);
    document.title = (p.title ? (typeof p.title === 'function' ? p.title(r.args) : p.title) + ' · ' : '') + UI.config.name;
    var ctx = { name: name, args: r.args, me: UI.me, go: UI.go, api: UI.api, page: p };
    var out;
    try { out = p.mount(view, ctx); } catch (e) { console.error(e); out = Promise.reject(e); }
    var ready = out && typeof out.then === 'function' ? out : (out && out.ready) || Promise.resolve();
    if (out && out.destroy) current.destroy = out.destroy;
    Promise.resolve(ready).then(function () { if (seq === routeSeq) window.UI_READY = true; },
      function (e) {
        if (seq !== routeSeq) return;
        console.error(e);
        if (!view.innerHTML) view.innerHTML = '<div class="ui-wrap"><div class="ui-empty">' + UI.icon('info') +
          '<h3>This page didn\'t load</h3><p class="muted">' + UI.esc(e && e.message || 'Something went wrong.') + '</p>' +
          '<button class="ui-btn" onclick="UI.refresh()">Try again</button></div></div>';
        window.UI_READY = true;
      });
  }
  UI.current = function () { return current; };

  /* The shell's parts come from web/app.js: UI.shell = {header(me, active), footer(me), tabbar(me, active)} */
  function renderChrome(active) {
    var S = UI.shell || {};
    var hd = shellRoot.querySelector('[data-ui-header]'), ft = shellRoot.querySelector('[data-ui-footer]'), tb = shellRoot.querySelector('[data-ui-tabbar]');
    if (hd) hd.innerHTML = S.header ? S.header(UI.me, active) : '';
    if (ft) ft.innerHTML = S.footer ? S.footer(UI.me, active) : '';
    if (tb) tb.innerHTML = S.tabbar ? S.tabbar(UI.me, active) : '';
  }
  UI.renderChrome = function () { if (shellRoot) renderChrome(current.name); };

  /* Called by client_code/Main.py (and by the local harness) once the page is up. */
  UI.start = function (node, bridgeFn, bootJson) {
    bridge = bridgeFn;
    var boot = typeof bootJson === 'string' ? JSON.parse(bootJson || '{}') : (bootJson || {});
    UI.me = boot.me || null;
    var host = node && node.matches && node.matches('[data-ui-app]') ? node : (node && node.querySelector('[data-ui-app]')) || node || document.body;
    host.innerHTML = '<div class="ui ui-shell">' +
      '<header class="ui-header" data-ui-header></header>' +
      '<main class="ui-main" data-ui-view></main>' +
      '<footer class="ui-footer" data-ui-footer></footer>' +
      '<nav class="ui-tabbar" data-ui-tabbar aria-label="Main"></nav></div>';
    shellRoot = host.firstChild;
    view = host.querySelector('[data-ui-view]');
    if (UI.shell && UI.shell.wire) UI.shell.wire(shellRoot);
    window.addEventListener('hashchange', route);
    route();
  };

  /* ------------------------------------------------------------------ feedback form (footer + menu) */
  UI.feedback = function (kind) {
    var kinds = [['bug', 'Something\'s broken', 'bug'], ['idea', 'An idea', 'bulb'], ['question', 'A question', 'info'], ['other', 'Something else', 'chat']];
    var m = UI.modal('<h2>Send feedback</h2><p class="muted">Found a bug or have an idea? It goes straight to the people who make ' + UI.esc(UI.config.name) + '.</p>' +
      '<form class="ui-stack" data-fb>' +
      '<div class="ui-choices">' + kinds.map(function (k) {
        return '<label class="ui-choice"><input type="radio" name="kind" value="' + k[0] + '"' + ((kind || 'bug') === k[0] ? ' checked' : '') + '>' +
          '<span>' + UI.icon(k[2]) + UI.esc(k[1]) + '</span></label>';
      }).join('') + '</div>' +
      '<label class="ui-field"><span>What happened, or what would you like?</span><textarea name="message" rows="5" required minlength="5" placeholder="The more detail, the better."></textarea></label>' +
      (UI.me ? '' : '<label class="ui-field"><span>Your email <em>(optional, if you\'d like a reply)</em></span><input type="email" name="email" autocomplete="email"></label>') +
      '<p class="ui-hint">We also send the page you were on, your screen size and browser, to help us fix bugs.</p>' +
      '<div class="ui-row end"><button type="button" class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" type="submit">' + UI.icon('arrow') + 'Send</button></div></form>');
    var form = m.el.querySelector('[data-fb]');
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var v = UI.formData(form);
      var ctx = { page: location.hash || '#', screen: innerWidth + 'x' + innerHeight, browser: navigator.userAgent.slice(0, 280), theme: UI.theme() };
      UI.busy(form.querySelector('[type=submit]'), UI.api('submit_feedback', v.kind, v.message, v.email || null, ctx)).then(function () {
        m.close(); UI.toast('Thank you! Your message was sent.', 'ok');
      });
    });
    return m;
  };

  /* Shared clicks: [data-go="page/arg"], [data-feedback], [data-theme-set] anywhere in the app. */
  document.addEventListener('click', function (e) {
    var el = e.target.closest && e.target.closest('[data-go],[data-feedback],[data-theme-set]');
    if (!el) return;
    if (el.hasAttribute('data-go')) { e.preventDefault(); UI.go.apply(null, el.getAttribute('data-go').split('/')); }
    else if (el.hasAttribute('data-feedback')) { e.preventDefault(); UI.feedback(el.getAttribute('data-feedback') || null); }
    else if (el.hasAttribute('data-theme-set')) { e.preventDefault(); UI.setTheme(el.getAttribute('data-theme-set')); if (UI.shell && UI.shell.onTheme) UI.shell.onTheme(); }
  });
})();


/* app.js: this app's identity and frame: name, header, footer, phone tab bar.
   Pages live in web/pages/*.html. The engine (window.UI) is web/core.js. */
(function () {
  'use strict';
  UI.configure({
    name: 'Plan Friday',
    key: 'planfriday',          // prefix for this app's browser storage
    tagline: 'The weekend catalogue. Order by Friday, feast by Saturday.',   // footer line
    home: 'home',                // first page after signing in
    landing: 'landing'           // first page for visitors who aren't signed in
  });

  var esc = UI.esc;

  function brand() {
    return '<a class="ui-brand" href="#" data-go="' + (UI.me ? UI.config.home : UI.config.landing) + '" aria-label="' + esc(UI.config.name) + ' home">' +
      '<img src="_/theme/icon.svg" alt="" width="32" height="32"><span>' + esc(UI.config.name) + '</span></a>';
  }

  function themeSwitch() {
    var t = UI.theme();
    return '<div class="ui-seg" role="group" aria-label="Appearance">' + [['auto', 'Auto'], ['light', 'Light'], ['dark', 'Dark']].map(function (o) {
      return '<button type="button" data-theme-set="' + o[0] + '" class="' + (t === o[0] ? 'on' : '') + '">' + o[1] + '</button>';
    }).join('') + '</div>';
  }

  function userMenu(me) {
    return '<div class="ui-menu" data-menu hidden>' +
      '<div class="ui-menu-head"><strong>' + esc(me.name) + '</strong><span class="muted small">' + esc(me.email) + '</span></div>' +
      '<a href="#profile" data-go="profile">' + UI.icon('user') + 'Your profile</a>' +
      (me.is_admin ? '<a href="#admin" data-go="admin">' + UI.icon('shield') + 'Admin</a>' : '') +
      '<div class="ui-menu-block"><span class="small muted">Appearance</span>' + themeSwitch() + '</div>' +
      '<button type="button" data-feedback>' + UI.icon('chat') + 'Send feedback</button>' +
      '<button type="button" data-lk-open="overview">' + UI.icon('lock') + 'Privacy &amp; Terms</button>' +
      '<button type="button" data-signout>' + UI.icon('logout') + 'Sign out</button></div>';
  }

  UI.shell = {
    header: function (me, active) {
      var nav = UI.navPages();
      var t = new Date();
      var strip = '<div class="pf-strip" aria-hidden="true"><div class="pf-strip-in"><span><b>The Weekend Catalogue</b> · Friday Edition</span>' +
        '<span>Order by Friday · Feast by Saturday</span><span>' + esc(t.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })) + '</span></div></div>';
      return strip + '<div class="ui-header-in">' + brand() +
        (me ? '<nav class="ui-nav" aria-label="Main">' + nav.map(function (p) {
          return '<a href="#' + p.name + '" class="' + (p.name === active ? 'on' : '') + '">' + UI.icon(p.icon) + '<span>' + esc(p.nav) + '</span></a>';
        }).join('') + '</nav>' : '') +
        '<div class="ui-header-right">' +
        (me ? '<button type="button" class="ui-avatar-btn" data-menu-toggle aria-label="Your account" aria-haspopup="true">' + esc(UI.initials(me.name)) + '</button>' + userMenu(me)
          : (active === 'auth' ? '' : '<a class="ui-btn ghost pf-hide-sm" href="#catalogue" data-go="catalogue">Catalogue</a><a class="ui-btn ghost" href="#auth" data-go="auth">Sign in</a>' +
            '<a class="ui-btn primary" href="#auth/signup" data-go="auth/signup">Host a party</a>')) +
        '</div></div>';
    },
    footer: function (me) {
      return '<div class="ui-footer-in"><div class="ui-footer-brand">' + brand() + '<p class="muted small">' + esc(UI.config.tagline) + '</p></div>' +
        '<div class="ui-footer-links">' +
        '<a href="#landing" data-go="landing">About</a>' +
        '<a href="#catalogue" data-go="catalogue">The catalogue</a>' +
        '<button type="button" data-feedback>Send feedback</button>' +
        '<button type="button" data-lk-open="overview">Privacy &amp; Terms</button>' +
        '</div><p class="pf-foot-fine">Satisfaction guaranteed or your weekend back. Prices good through Sunday. Dishes not included; ' +
        'guests bring those. Ask at any kitchen table.</p>' +
        '<p class="ui-footer-legal small muted">© ' + new Date().getFullYear() + ' ' + esc(UI.config.name) + ' &amp; Co.</p></div>';
    },
    tabbar: function (me, active) {
      var nav = UI.navPages();
      if (!me || nav.length < 2) return '';
      return nav.slice(0, 4).map(function (p) {
        return '<a href="#' + p.name + '" class="' + (p.name === active ? 'on' : '') + '">' + UI.icon(p.icon) + '<span>' + esc(p.nav) + '</span></a>';
      }).join('') + '<a href="#profile" class="' + (active === 'profile' ? 'on' : '') + '">' + UI.icon('user') + '<span>You</span></a>';
    },
    wire: function (root) {
      root.addEventListener('click', function (e) {
        var t = e.target.closest('[data-menu-toggle]');
        var menu = root.querySelector('[data-menu]');
        if (t && menu) { menu.hidden = !menu.hidden; t.setAttribute('aria-expanded', String(!menu.hidden)); return; }
        if (e.target.closest('[data-signout]')) { UI.auth('logout').then(function () { UI.toast('Signed out. See you soon!'); }); }
        if (menu && !menu.hidden && !e.target.closest('[data-menu] .ui-seg')) menu.hidden = true;
      });
      document.addEventListener('keydown', function (e) {
        var menu = root.querySelector('[data-menu]');
        if (e.key === 'Escape' && menu) menu.hidden = true;
      });
    },
    onTheme: function () {  // redraw the menu's Auto/Light/Dark buttons and keep the menu open
      var menu = document.querySelector('[data-menu]'), open = menu && !menu.hidden;
      UI.renderChrome();
      if (open) document.querySelector('[data-menu]').hidden = false;
    }
  };
})();


/* ===== _shared.html ===== */
(function () {
  'use strict';
  var esc = UI.esc;

  // Extra line icons for UI.icon (same 24px stroke style as core.js).
  var I = UI.ICONS;
  I.scissors = '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12"/>';
  I.utensils = '<path d="M7 3v8a2 2 0 0 0 2 2v8M5 3v5M9 3v5M17 3c-2 1-3 4-3 7h3v11"/>';
  I.share = '<circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4"/>';
  I.print = '<path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="1"/><path d="M6 14h12v7H6z"/>';
  I.dice = '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.2"/><circle cx="16" cy="16" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="16" cy="8" r="1.2"/><circle cx="8" cy="16" r="1.2"/>';
  I.ticket = '<path d="M3 7h18v3a2 2 0 0 0 0 4v3H3v-3a2 2 0 0 0 0-4z"/><path d="M14 7v10"/>';
  I.link = '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>';
  I.download = '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>';
  I.pot = '<path d="M4 10h16v6a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4z"/><path d="M2 10h20M9 6c0-1 1-1.5 1-2.5M14 6c0-1 1-1.5 1-2.5"/>';
  I.party = '<path d="M4 20 9 7l8 8z"/><path d="M13 4v2M18 6l-1.5 1.5M20 11h-2M15 2.5l.5 1.5"/>';
  I.phone = '<rect x="7" y="2.5" width="10" height="19" rx="2"/><path d="M11 18.5h2"/>';

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
  var COVER_NAMES = { classic: 'Casserole', soup: 'Soup pot', pancakes: 'Pancakes', dumplings: 'Dumplings', tacos: 'Tacos', fondue: 'Fondue',
    pizza: 'Pizza', roast: 'Roast', salad: 'Salad bowl', pie: 'Pie', wine: 'Wine', bbq: 'Grill', cake: 'Cake' };

  function art(key, label) {
    return '<svg class="pf-art" viewBox="0 0 100 80" role="img" aria-label="' + esc(label || COVER_NAMES[key] || 'A dish') + '">' + (ART[key] || ART.classic) + '</svg>';
  }

  /* ------------------------------------------------------------------ the catalogue of party ideas */
  // slots: [day (0 Fri, 1 Sat, 2 Sun), part]; menu: [section, how many wanted]
  var IDEAS = [
    { key: 'soupnight', no: '12F 4108', name: 'Soup Night Supper', cover: 'soup', tags: ['cosy'], serves: '6–12', effort: 1, style: 'potluck',
      blurb: 'Everyone brings a pot. The host does bread and bowls. The coziest potluck there is, and it reheats beautifully.',
      slots: [[0, 'dinner'], [1, 'dinner'], [2, 'lunch']], menu: [['Soup', 3], ['Bread', 2], ['Salad', 1], ['Dessert', 2], ['Drinks', 2]] },
    { key: 'pancakes', no: '31P 2275', name: 'Sunday Pancake Brunch', cover: 'pancakes', tags: ['brunch'], serves: '4–10', effort: 2, style: 'hostcooks',
      blurb: 'You flip, they bring the toppings. Maple, berries, whipped butter, and a very large pot of coffee.',
      slots: [[1, 'brunch'], [2, 'brunch']], menu: [['Toppings', 3], ['Fruit', 1], ['Coffee & juice', 2]] },
    { key: 'dumplings', no: '57K 9031', name: 'Dumpling Folding Party', cover: 'dumplings', tags: ['handson'], serves: '4–8', effort: 3, style: 'potluck',
      blurb: 'Dough on the table, fillings in bowls, everyone folds. Ugly dumplings taste exactly the same.',
      slots: [[0, 'late'], [1, 'afternoon'], [1, 'dinner']], menu: [['Fillings', 2], ['Dipping sauces', 2], ['Sides', 1], ['Drinks', 2], ['Dessert', 1]] },
    { key: 'tacos', no: '22T 6610', name: 'Taco Saturday', cover: 'tacos', tags: ['crowd'], serves: '6–16', effort: 1, style: 'potluck',
      blurb: 'Tortillas from the host, a salsa from everyone else. Build-your-own means nobody is fussy.',
      slots: [[0, 'dinner'], [1, 'dinner']], menu: [['Fillings', 2], ['Salsas', 3], ['Toppings', 2], ['Sides', 1], ['Drinks', 2], ['Dessert', 1]] },
    { key: 'fondue', no: '40F 1955', name: 'Fondue & Fiasco', cover: 'fondue', tags: ['cosy'], serves: '4–6', effort: 2, style: 'hostcooks',
      blurb: 'One pot of melted cheese, a dozen forks, and the old rule: drop your bread, you do the dishes.',
      slots: [[0, 'dinner'], [1, 'dinner']], menu: [['Dippers', 3], ['Salad', 1], ['Wine', 2], ['Dessert', 1]] },
    { key: 'pizza', no: '18R 3030', name: 'Pizza Dough Workshop', cover: 'pizza', tags: ['handson', 'crowd'], serves: '6–12', effort: 2, style: 'potluck',
      blurb: 'The host makes the dough the night before. Guests bring toppings. The oven never rests.',
      slots: [[1, 'afternoon'], [1, 'dinner'], [2, 'lunch']], menu: [['Toppings', 4], ['Salad', 1], ['Drinks', 2], ['Dessert', 1]] },
    { key: 'roast', no: '09W 7744', name: 'The Sunday Roast', cover: 'roast', tags: ['cosy'], serves: '6–10', effort: 3, style: 'hostcooks',
      blurb: 'A proper roast from the host. Guests cover the sides, the gravy and the pudding. Seconds compulsory.',
      slots: [[2, 'lunch'], [2, 'dinner']], menu: [['Sides', 3], ['Gravy & sauces', 1], ['Dessert', 1], ['Wine', 2]] },
    { key: 'garden', no: '64P 1212', name: 'Garden Potluck Picnic', cover: 'salad', tags: ['outdoor', 'crowd'], serves: '8–20', effort: 1, style: 'potluck',
      blurb: 'Blankets, big salads and something cold to drink. Rain plan: everyone squeezes into the kitchen.',
      slots: [[1, 'lunch'], [1, 'afternoon'], [2, 'lunch'], [2, 'afternoon']], menu: [['Salads', 2], ['Mains', 2], ['Sides', 2], ['Dessert', 2], ['Drinks', 2], ['Supplies', 1]] },
    { key: 'pie', no: '33R 3141', name: 'The Pie Social', cover: 'pie', tags: ['crowd'], serves: '8–20', effort: 2, style: 'potluck',
      blurb: 'Savoury, sweet, store-bought and proud. Everyone brings a pie, everyone goes home with a slice of six.',
      slots: [[1, 'afternoon'], [2, 'afternoon']], menu: [['Savoury pies', 2], ['Sweet pies', 3], ['Ice cream', 1], ['Drinks', 1]] },
    { key: 'grill', no: '71K 4040', name: 'Backyard Grill-Out', cover: 'bbq', tags: ['outdoor', 'crowd'], serves: '8–20', effort: 2, style: 'potluck',
      blurb: 'Light the grill at five. Bring something to throw on it, and something to drink while it cooks.',
      slots: [[0, 'dinner'], [1, 'afternoon'], [1, 'dinner']], menu: [['For the grill', 3], ['Sides', 3], ['Buns & bread', 1], ['Drinks', 3], ['Dessert', 1], ['Ice', 1]] },
    { key: 'cheese', no: '45T 0808', name: 'Cheese & Wine Evening', cover: 'wine', tags: ['cosy'], serves: '4–12', effort: 1, style: 'byob',
      blurb: 'No cooking at all. Everyone brings a cheese and a bottle, and you argue about which is best.',
      slots: [[0, 'dinner'], [0, 'late'], [1, 'late']], menu: [['Cheese', 3], ['Crackers & bread', 2], ['Wine', 4], ['Fruit & pickles', 1]] },
    { key: 'birthday', no: '26W 0101', name: 'Birthday Dinner', cover: 'cake', tags: ['crowd'], serves: '6–14', effort: 2, style: 'potluck',
      blurb: 'A potluck with a purpose. One cake, many candles, and a menu that comes together by itself.',
      slots: [[0, 'dinner'], [1, 'dinner']], menu: [['Starters', 1], ['Mains', 2], ['Sides', 2], ['Cake', 1], ['Drinks', 2]] },
    { key: 'classic', no: '01F 0001', name: 'The Classic Potluck', cover: 'classic', tags: ['crowd'], serves: 'Any', effort: 1, style: 'potluck',
      blurb: 'The original. A little of everything: starter, soup, salad, main, sides, dessert and drinks.',
      slots: [[0, 'dinner'], [1, 'dinner'], [2, 'lunch']], menu: [['Starters', 1], ['Soup', 1], ['Salad', 1], ['Mains', 2], ['Sides', 2], ['Dessert', 2], ['Drinks', 2]] }
  ];
  var TAGS = { cosy: 'Cosy', brunch: 'Brunch', handson: 'Hands-on', crowd: 'Big crowd', outdoor: 'Outdoors' };
  var STYLES = { potluck: ['Potluck', 'Everyone brings a dish'], hostcooks: ['Host cooks', 'The host cooks; guests bring extras'],
    byob: ['Bring your own', 'No cooking: everyone brings their own'] };

  /* ------------------------------------------------------------------ weekend dates and slots */
  var PARTS = { brunch: { label: 'Brunch', time: '10:30' }, lunch: { label: 'Lunch', time: '12:30' }, afternoon: { label: 'Afternoon', time: '15:00' },
    dinner: { label: 'Dinner', time: '19:00' }, late: { label: 'Late supper', time: '21:30' } };
  var DAY_PARTS = [['dinner', 'late'], ['brunch', 'lunch', 'afternoon', 'dinner', 'late'], ['brunch', 'lunch', 'afternoon', 'dinner']];
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function iso(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function parse(s) { var p = String(s).split('-'); return new Date(+p[0], +p[1] - 1, +p[2], 12); }
  function addDays(d, n) { var x = new Date(d.getTime()); x.setDate(x.getDate() + n); return x; }
  function today() { var d = new Date(); d.setHours(12, 0, 0, 0); return d; }
  /* The Friday of this weekend (Fri/Sat/Sun) or the coming one, plus `weeks`. */
  function friday(weeks, from) {
    var t = from || today(), wd = t.getDay();  // Sun 0 ... Sat 6
    var off = wd === 5 ? 0 : wd === 6 ? -1 : wd === 0 ? -2 : 5 - wd;
    return addDays(t, off + 7 * (weeks || 0));
  }
  function slot(key) { var a = String(key).split('|'); return { key: key, date: a[0], part: a[1], d: parse(a[0]) }; }
  function slotKey(fri, day, part) { return iso(addDays(fri, day)) + '|' + part; }
  function partLabel(p) { return (PARTS[p] || { label: p }).label; }
  function day(d, len) { return d.toLocaleDateString(undefined, { weekday: len || 'long' }); }
  function shortDate(d) { return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }); }
  function slotLabel(key) { var s = slot(key); return day(s.d, 'short') + ' · ' + partLabel(s.part); }
  function isPast(key) { return slot(key).date < iso(today()); }
  function timeLabel(t) {
    if (!t) return '';
    var d = new Date(2000, 0, 1, +t.slice(0, 2), +t.slice(3, 5));
    return d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  }
  function whenText(p) {
    if (!p.chosen) return '';
    var s = slot(p.chosen);
    return day(s.d) + ' ' + partLabel(s.part).toLowerCase() + ', ' + shortDate(s.d) + ' · ' + timeLabel(p.chosen_time || (PARTS[s.part] || {}).time);
  }
  function weekendRange(fri) { return shortDate(fri) + ' – ' + shortDate(addDays(fri, 2)); }
  function allPast(p) { var keys = p.chosen ? [p.chosen] : (p.slots || []); return keys.length > 0 && keys.every(isPast); }
  function countdown() {
    var wd = today().getDay();
    if (wd === 5) return { big: 'It\'s Friday!', small: 'Perfect timing: plan the weekend right now.', burst: 'Today!', hot: true };
    if (wd === 6) return { big: 'It\'s Saturday', small: 'Tonight still counts. So does tomorrow.', burst: 'Tonight?', hot: true };
    if (wd === 0) return { big: 'It\'s Sunday', small: 'One more feast, or line up next weekend.', burst: 'Lunch?', hot: true };
    var n = 5 - wd;
    return { big: n === 1 ? 'Friday is tomorrow' : n + ' days to Friday', small: 'Get a head start: send the link now, decide on Friday.', burst: n === 1 ? '1 day' : n + ' days', hot: false };
  }

  /* ------------------------------------------------------------------ diets, tags, dish ideas */
  var DIETS = [['veg', 'Vegetarian'], ['vegan', 'Vegan'], ['gf', 'Gluten-free'], ['df', 'Dairy-free'], ['nutfree', 'Nut allergy'], ['halal', 'Halal']];
  var DISH_TAGS = [['veg', 'Veg'], ['vegan', 'Vegan'], ['gf', 'GF'], ['df', 'Dairy-free'], ['nuts', 'Has nuts'], ['spicy', 'Spicy']];
  var SUGGEST = [
    [/soup/i, ['Roasted squash soup', 'French onion soup', 'Minestrone', 'Spicy black bean soup', 'Leek & potato soup', 'Miso soup with tofu']],
    [/bread|bun|cracker/i, ['Garlic bread', 'Focaccia with rosemary', 'Cornbread', 'Seeded sourdough', 'Cheese scones']],
    [/salad/i, ['Greek salad', 'Crunchy slaw', 'Beetroot & feta salad', 'Potato salad', 'Tabbouleh']],
    [/dessert|pie|cake|sweet|pudding/i, ['Lemon tart', 'Brownies', 'Tiramisu', 'Apple pie', 'Chocolate mousse', 'Pavlova', 'Rice pudding']],
    [/drink|wine|juice|coffee/i, ['A bottle of red', 'Sparkling lemonade', 'Craft beer, a six-pack', 'Hot mulled wine', 'Iced tea', 'Fancy soda']],
    [/main|grill|filling/i, ['Lasagne', 'Chilli con carne', 'Mushroom stroganoff', 'Roast vegetables', 'Pulled pork', 'Halloumi skewers']],
    [/side/i, ['Roast potatoes', 'Mac & cheese', 'Green beans with almonds', 'Honey carrots', 'Corn on the cob']],
    [/starter|snack|dipper/i, ['Hummus & crudités', 'Devilled eggs', 'Cheese straws', 'Olives & pickles', 'Bread cubes & apples']],
    [/topping|salsa|sauce|gravy/i, ['Pico de gallo', 'Guacamole', 'Chilli oil', 'Maple syrup', 'Garlic yoghurt sauce', 'Proper gravy']],
    [/cheese/i, ['A runny brie', 'Aged cheddar', 'Blue cheese', 'Goat cheese log']],
    [/fruit|pickle/i, ['Grapes & figs', 'Fruit salad', 'Quince paste', 'Cornichons']],
    [/suppl|ice/i, ['Paper plates & napkins', 'A bag of ice', 'Folding chairs', 'Extra glasses', 'A speaker and a playlist']]
  ];
  function suggest(category) {
    for (var i = 0; i < SUGGEST.length; i++) if (SUGGEST[i][0].test(category)) return SUGGEST[i][1];
    return ['Something homemade', 'A family recipe', 'Your famous dish', 'Something from the bakery'];
  }
  function dietLabel(k) { for (var i = 0; i < DIETS.length; i++) if (DIETS[i][0] === k) return DIETS[i][1]; return k; }
  function tagLabel(k) { for (var i = 0; i < DISH_TAGS.length; i++) if (DISH_TAGS[i][0] === k) return DISH_TAGS[i][1]; return k; }

  /* ------------------------------------------------------------------ sharing, calendar, confetti */
  function partyUrl(token) { return location.origin + location.pathname + '#p/' + encodeURIComponent(token); }
  function inviteText(p) {
    return 'You\'re invited to ' + p.title + '! Tell ' + (p.host_name || 'the host').split(' ')[0] + ' which day suits you and what you\'ll bring: ' + partyUrl(p.token);
  }
  function copy(text) {
    var done = function () { UI.toast('Link copied. Paste it anywhere!', 'ok'); };
    if (navigator.clipboard && navigator.clipboard.writeText) return navigator.clipboard.writeText(text).then(done, function () { fallback(); });
    fallback();
    function fallback() {
      var t = document.createElement('textarea'); t.value = text; t.style.position = 'fixed'; t.style.opacity = '0';
      document.body.appendChild(t); t.select();
      try { document.execCommand('copy'); done(); } catch (e) { UI.toast('Select the link and copy it by hand.', 'error'); }
      t.remove();
    }
  }
  function times(p) {
    var s = slot(p.chosen), t = p.chosen_time || (PARTS[s.part] || {}).time || '19:00';
    var start = new Date(s.d.getFullYear(), s.d.getMonth(), s.d.getDate(), +t.slice(0, 2), +t.slice(3, 5));
    var end = new Date(start.getTime() + 3 * 3600 * 1000);
    var f = function (d) { return d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + 'T' + pad(d.getHours()) + pad(d.getMinutes()) + '00'; };
    return { start: f(start), end: f(end) };
  }
  function icsEsc(s) { return String(s || '').replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/([,;])/g, '\\$1'); }
  function downloadIcs(p) {
    var t = times(p), now = new Date();
    var stamp = now.getUTCFullYear() + pad(now.getUTCMonth() + 1) + pad(now.getUTCDate()) + 'T' + pad(now.getUTCHours()) + pad(now.getUTCMinutes()) + '00Z';
    var lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Plan Friday//EN', 'BEGIN:VEVENT', 'UID:' + p.token + '@planfriday', 'DTSTAMP:' + stamp,
      'DTSTART:' + t.start, 'DTEND:' + t.end, 'SUMMARY:' + icsEsc(p.title), 'LOCATION:' + icsEsc(p.location),
      'DESCRIPTION:' + icsEsc('Hosted by ' + p.host_name + '. The menu and guest list: ' + partyUrl(p.token)), 'END:VEVENT', 'END:VCALENDAR'];
    var blob = new Blob([lines.join('\r\n') + '\r\n'], { type: 'text/calendar' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = (p.title || 'party').replace(/[^\w]+/g, '-').toLowerCase() + '.ics';
    document.body.appendChild(a); a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  function googleCal(p) {
    var t = times(p);
    return 'https://calendar.google.com/calendar/render?action=TEMPLATE&text=' + encodeURIComponent(p.title) + '&dates=' + t.start + '/' + t.end +
      '&location=' + encodeURIComponent(p.location || '') + '&details=' + encodeURIComponent('Hosted by ' + p.host_name + '. ' + partyUrl(p.token));
  }
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

  /* ------------------------------------------------------------------ weather check (forecasts come from the server: Weather.py) */
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
  function wxKind(code, hour) {
    var night = hour != null && (hour < 7 || hour >= 19);
    if (code === 0 || code === 1) return [night ? 'moon' : 'sun', code === 0 ? (night ? 'Clear night' : 'Sunny') : 'Mostly clear'];
    if (code === 2) return ['partly', 'Partly cloudy'];
    if (code === 3) return ['cloud', 'Overcast'];
    if (code === 45 || code === 48) return ['fog', 'Foggy'];
    if (code >= 51 && code <= 57) return ['drizzle', 'Drizzle'];
    if ((code >= 61 && code <= 67) || (code >= 80 && code <= 82)) return ['rain', code >= 80 ? 'Showers' : 'Rain'];
    if ((code >= 71 && code <= 77) || code === 85 || code === 86) return ['snow', 'Snow'];
    if (code >= 95) return ['storm', 'Thunderstorms'];
    return ['cloud', 'Cloudy'];
  }
  function wxIcon(w) {
    var k = wxKind(w.code, w.hour);
    return '<svg class="pf-art pf-wxi" viewBox="0 0 40 40" role="img" aria-label="' + esc(k[1]) + '">' + WX_ART[k[0]] + '</svg>';
  }
  function units() { return UI.store.get('units', 'C'); }
  function temp(c) {
    if (c == null) return '';
    return units() === 'F' ? Math.round(c * 9 / 5 + 32) + '°F' : Math.round(c) + '°C';
  }
  function wind(kmh) { return units() === 'F' ? Math.round(kmh / 1.609) + ' mph' : Math.round(kmh) + ' km/h'; }
  function advice(w, outdoors) {
    var k = wxKind(w.code, w.hour)[0], t = w.temp, rain = w.rain || 0;
    if (k === 'storm') return outdoors ? 'Thunder on the way: move it indoors.' : 'Stormy outside, cosy inside.';
    if (k === 'snow') return outdoors ? 'Snow! Hot drinks and a quick retreat indoors.' : 'Snow boots by the door.';
    if (k === 'rain' || rain >= 60) return outdoors ? 'Rain plan needed: everyone into the kitchen!' : 'Umbrellas by the door.';
    if (rain >= 30) return outdoors ? 'Might sprinkle. Have a plan B.' : 'Bring a brolly, just in case.';
    if (outdoors && w.wind >= 35) return 'Windy: weigh down the napkins.';
    if (t < 5) return outdoors ? 'Too cold for the patio. Soup, anyone?' : 'Proper soup weather.';
    if (t < 12) return outdoors ? 'Sweater weather: bring a layer.' : 'Crisp out, cosy in.';
    if (t >= 30) return 'A scorcher! Bring ice. Lots of ice.';
    if (t >= 18 && (k === 'sun' || k === 'partly' || k === 'moon')) return outdoors ? 'Perfect patio weather.' : 'Lovely for the walk over.';
    return outdoors ? 'Looks fine for outside.' : 'Nothing to worry about.';
  }
  function wxChip(w) {
    if (!w) return '';
    var k = wxKind(w.code, w.hour);
    return '<span class="pf-wx' + ((w.rain || 0) >= 50 ? ' wet' : (w.rain || 0) <= 10 ? ' dry' : '') + '" title="' + esc(k[1] + ', ' + temp(w.temp) + ', ' + (w.rain || 0) + '% chance of rain') + '">' +
      wxIcon(w) + esc(temp(w.temp)) + ' · ' + (w.rain || 0) + '%</span>';
  }

  /* ------------------------------------------------------------------ parties seen on this device (guests have no account) */
  function remember(p) {
    var list = UI.store.get('visited', []).filter(function (x) { return x.token !== p.token; });
    list.unshift({ token: p.token, title: p.title, cover: p.cover, host: p.host_name, at: Date.now() });
    UI.store.set('visited', list.slice(0, 12));
  }
  function forget(token) { UI.store.set('visited', UI.store.get('visited', []).filter(function (x) { return x.token !== token; })); }

  /* ------------------------------------------------------------------ a party card (home page) */
  function partyCard(s) {
    var status;
    if (s.chosen) status = '<span class="pf-stamp good">It\'s on · ' + esc(slotLabel(s.chosen)) + '</span>';
    else if (s.best) status = '<span class="pf-label">Leading: ' + esc(slotLabel(s.best)) + '</span>';
    else status = '<span class="pf-label">Waiting for answers</span>';
    var past = allPast(s);
    return '<a class="pf-pcard' + (past ? ' past' : '') + '" href="#p/' + esc(s.token) + '" data-go="p/' + esc(s.token) + '">' +
      '<div class="pf-cover ' + (s.chosen ? 'red' : '') + '">' + art(s.cover) + '</div>' +
      '<div class="in"><div class="pf-no">' + esc(s.catalog_no || '') + (s.is_host ? ' · You host' : ' · ' + esc(s.host_name)) + (past ? ' · Past' : '') + '</div>' +
      '<h3>' + esc(s.title) + '</h3><div>' + status + '</div>' +
      '<div class="pf-leader small"><span class="a">' + UI.plural(s.heads, 'seat') + ' taken</span><span class="dots"></span><span class="b">' + s.maybe + ' maybe</span></div>' +
      '<div class="pf-leader small"><span class="a">Menu</span><span class="dots"></span><span class="b">' + s.filled + ' of ' + s.wanted_total + ' filled</span></div>' +
      (s.wx ? '<div class="pf-leader small"><span class="a">Weather</span><span class="dots"></span><span class="b">' + wxChip(s.wx) + '</span></div>' : '') +
      (s.status === 'closed' ? '<span class="ui-badge">RSVPs closed</span>' : '') + '</div></a>';
  }

  window.PF = {
    art: art, ART: ART, COVER_NAMES: COVER_NAMES, IDEAS: IDEAS, TAGS: TAGS, STYLES: STYLES,
    idea: function (key) { for (var i = 0; i < IDEAS.length; i++) if (IDEAS[i].key === key) return IDEAS[i]; return null; },
    PARTS: PARTS, DAY_PARTS: DAY_PARTS, iso: iso, parse: parse, addDays: addDays, today: today, friday: friday,
    slot: slot, slotKey: slotKey, partLabel: partLabel, day: day, shortDate: shortDate, slotLabel: slotLabel, isPast: isPast,
    timeLabel: timeLabel, whenText: whenText, weekendRange: weekendRange, allPast: allPast, countdown: countdown,
    DIETS: DIETS, DISH_TAGS: DISH_TAGS, suggest: suggest, dietLabel: dietLabel, tagLabel: tagLabel,
    partyUrl: partyUrl, inviteText: inviteText, copy: copy, downloadIcs: downloadIcs, googleCal: googleCal, confetti: confetti,
    remember: remember, forget: forget, partyCard: partyCard,
    wxKind: wxKind, wxIcon: wxIcon, wxChip: wxChip, temp: temp, wind: wind, units: units, advice: advice,
    effort: function (n) { return '★★★'.slice(0, n) + '☆☆☆'.slice(0, 3 - n); }
  };
})();

/* ===== admin.html ===== */
(function () {
  var esc = UI.esc;
  var TABS = [['overview', 'Overview', 'grid'], ['feedback', 'Feedback', 'inbox'], ['users', 'Users', 'users'], ['parties', 'Parties', 'party'], ['demo', 'Demo data', 'database']];

  UI.page('admin', { title: 'Admin', auth: 'admin' }, function (view, ctx) {
    var tab = TABS.some(function (t) { return t[0] === ctx.args[0]; }) ? ctx.args[0] : 'overview';
    var fbFilter = 'new';
    view.innerHTML = '<div class="ui-wrap"><div class="ui-page-head"><div><h1>Admin</h1><p class="muted">Only admins see this page.</p></div></div>' +
      '<nav class="ui-tabs">' + TABS.map(function (t) {
        return '<a href="#admin/' + t[0] + '" class="' + (t[0] === tab ? 'on' : '') + '">' + UI.icon(t[2]) + t[1] + '</a>';
      }).join('') + '</nav><div data-body><div class="ui-skel"></div></div></div>';
    var body = view.querySelector('[data-body]');

    function overview() {
      return UI.api('admin_overview').then(function (d) {
        var stat = function (n, label, go) { return '<a class="ui-card ui-stat" href="#admin/' + go + '" style="text-decoration:none;color:inherit"><b>' + n + '</b><span>' + label + '</span></a>'; };
        body.innerHTML = '<div class="ad-stats">' + stat(d.users, 'people signed up', 'users') + stat(d.admins, UI.plural(d.admins, 'admin').replace(/^\d+ /, ''), 'users') +
          stat(d.feedback_new, 'new feedback', 'feedback') + stat(d.parties, 'parties', 'parties') + stat(d.guests, 'names on guest lists', 'parties') + '</div>' +
          '<p class="muted small" style="margin-top:18px">Demo data is <b>' + esc(d.demo.state) + '</b> (' + d.demo.counts.users + ' demo people). Manage it in the Demo data tab.</p>';
      });
    }

    function feedback() {
      return UI.api('list_feedback', null).then(function (d) {
        var items = d.items.filter(function (i) { return fbFilter === 'all' || i.status === fbFilter; });
        body.innerHTML = '<div class="ui-row" style="margin-bottom:16px"><div class="ui-seg">' + [['new', 'New'], ['read', 'Read'], ['done', 'Done'], ['all', 'All']].map(function (f) {
          var n = f[0] === 'all' ? d.items.length : d.counts[f[0]];
          return '<button data-filter="' + f[0] + '" class="' + (fbFilter === f[0] ? 'on' : '') + '">' + f[1] + ' (' + n + ')</button>';
        }).join('') + '</div></div>' +
          (items.length ? '<div class="ad-fb">' + items.map(function (i) {
            var c = i.context || {};
            return '<div class="ui-item" data-id="' + esc(i.id) + '"><div class="meta"><span class="ui-badge ' + (i.kind === 'bug' ? 'bad' : i.kind === 'idea' ? 'brand' : '') + '">' + esc(i.kind_label) + '</span>' +
              '<b>' + esc(i.name) + '</b>' + (i.email ? '<a href="mailto:' + esc(i.email) + '">' + esc(i.email) + '</a>' : '') + '<span>' + esc(UI.fmtDateTime(i.created)) + '</span></div>' +
              '<p class="msg">' + esc(i.message) + '</p>' +
              '<div class="ctx">' + esc([c.page, c.screen, c.theme, c.browser].filter(Boolean).join(' · ')) + '</div>' +
              '<textarea data-note placeholder="Private note (only admins see it)">' + esc(i.note) + '</textarea>' +
              '<div class="ui-row" style="margin-top:10px">' + ['new', 'read', 'done'].map(function (s) {
                return '<button class="ui-btn sm' + (i.status === s ? ' primary' : '') + '" data-status="' + s + '">' + s[0].toUpperCase() + s.slice(1) + '</button>';
              }).join('') + '<span class="ui-spacer"></span><button class="ui-btn sm danger" data-del-fb>' + UI.icon('trash') + 'Delete</button></div></div>';
          }).join('') + '</div>'
            : '<div class="ui-empty">' + UI.icon('inbox') + '<h3>No ' + (fbFilter === 'all' ? '' : fbFilter + ' ') + 'messages</h3><p>Messages from the "Send feedback" form show up here.</p></div>');
      });
    }

    function users(query) {
      return UI.api('list_users', query || null).then(function (d) {
        body.innerHTML = '<form class="ui-row" data-search style="margin-bottom:14px"><input type="search" name="q" placeholder="Search by name or email" value="' + esc(query || '') + '" style="max-width:360px">' +
          '<button class="ui-btn" type="submit">' + UI.icon('search') + 'Search</button><span class="muted small">' + UI.plural(d.total, 'person', 'people') + '</span></form>' +
          '<table class="ad-users"><thead><tr><th>Name</th><th>Email</th><th>Joined</th><th>Admin</th><th>Active</th></tr></thead><tbody>' +
          d.users.map(function (u) {
            return '<tr data-id="' + esc(u.id) + '"><td><b>' + esc(u.name) + '</b></td><td class="email">' + esc(u.email) + '</td><td class="joined muted">' + esc(UI.fmtDate(u.joined)) + '</td>' +
              '<td><label class="ui-check"><input type="checkbox" data-admin' + (u.is_admin ? ' checked' : '') + '> Admin</label></td>' +
              '<td><label class="ui-check"><input type="checkbox" data-enabled' + (u.enabled ? ' checked' : '') + '> Active</label></td></tr>';
          }).join('') + '</tbody></table>';
      });
    }

    function demo() {
      return UI.api('admin_overview').then(function (d) {
        var c = d.demo.counts;
        body.innerHTML = '<div class="ui-card ui-narrow" style="margin:0"><h3>Demo data</h3>' +
          '<p class="muted">Three sample parties (fictional hosts and guests), so the app never looks empty. They move to the coming weekend by themselves, and visitors cannot change them. Demo rows are flagged, so removing them never touches real data. Once removed, it stays removed until you load it again.</p>' +
          '<p>Status: <b>' + esc(d.demo.state) + '</b> · ' + Object.keys(c).map(function (k) { return c[k] + ' ' + esc(k); }).join(', ') + '</p>' +
          '<div class="ui-row"><button class="ui-btn primary" data-demo="load">' + UI.icon('refresh') + (d.demo.state === 'loaded' ? 'Reload demo data' : 'Load demo data') + '</button>' +
          '<button class="ui-btn danger" data-demo="remove">' + UI.icon('trash') + 'Remove demo data</button></div></div>';
      });
    }

    function parties(query) {
      return UI.api('admin_parties', query || null).then(function (d) {
        body.innerHTML = '<form class="ui-row" data-psearch style="margin-bottom:14px"><input type="search" name="q" placeholder="Search by party, host or email" value="' + esc(query || '') + '" style="max-width:360px">' +
          '<button class="ui-btn" type="submit">' + UI.icon('search') + 'Search</button><span class="muted small">' + UI.plural(d.total, 'party', 'parties') + '</span></form>' +
          (d.parties.length ? '<div class="ui-list">' + d.parties.map(function (p) {
            return '<div class="ui-item" data-pid="' + esc(p.id) + '"><div class="grow"><h3><a href="#p/' + esc(p.token) + '" data-go="p/' + esc(p.token) + '">' + esc(p.title) + '</a>' +
              (p.demo ? ' <span class="ui-badge">Sample</span>' : '') + (p.status === 'closed' ? ' <span class="ui-badge">Closed</span>' : '') + '</h3>' +
              '<p class="small muted">' + esc(p.host) + (p.host_email ? ' · ' + esc(p.host_email) : '') + ' · ' + esc(UI.fmtDate(p.created)) + '</p>' +
              '<p class="small">' + UI.plural(p.guests, 'guest') + ' · ' + UI.plural(p.dishes, 'dish', 'dishes') + ' · ' + UI.plural(p.comments, 'note') + '</p></div>' +
              '<button class="ui-btn sm danger" data-del-party>' + UI.icon('trash') + 'Delete</button></div>';
          }).join('') + '</div>' : '<div class="ui-empty">' + UI.icon('party') + '<h3>No parties</h3><p>Parties people host show up here.</p></div>');
      });
    }

    var DRAW = { overview: overview, feedback: feedback, users: users, parties: parties, demo: demo };

    view.addEventListener('click', function (e) {
      var f = e.target.closest('[data-filter]');
      if (f) { fbFilter = f.getAttribute('data-filter'); feedback(); return; }
      var st = e.target.closest('[data-status]');
      if (st) {
        var card = st.closest('[data-id]');
        UI.api('set_feedback_status', card.getAttribute('data-id'), st.getAttribute('data-status'), card.querySelector('[data-note]').value).then(function () { UI.toast('Saved', 'ok'); feedback(); });
        return;
      }
      var del = e.target.closest('[data-del-fb]');
      if (del) {
        UI.confirm({ title: 'Delete this message?', ok: 'Delete', danger: true }).then(function (yes) {
          if (yes) UI.api('delete_feedback', del.closest('[data-id]').getAttribute('data-id')).then(feedback);
        });
        return;
      }
      var dp = e.target.closest('[data-del-party]');
      if (dp) {
        UI.confirm({ title: 'Delete this party?', text: 'Its guest list, menu and notes go too, and the link stops working.', ok: 'Delete', danger: true }).then(function (yes) {
          if (yes) UI.api('admin_delete_party', dp.closest('[data-pid]').getAttribute('data-pid')).then(function () { UI.toast('Deleted', 'ok'); parties(); });
        });
        return;
      }
      var dm = e.target.closest('[data-demo]');
      if (dm) {
        var load = dm.getAttribute('data-demo') === 'load';
        UI.confirm({ title: load ? 'Load the demo data?' : 'Remove the demo data?', text: load ? 'Demo people and content are added (any old demo rows are replaced).' : 'Every demo row is deleted. Real data stays.', ok: load ? 'Load' : 'Remove', danger: !load })
          .then(function (yes) { if (yes) UI.busy(dm, UI.api(load ? 'demo_load' : 'demo_remove')).then(function () { UI.toast('Done', 'ok'); demo(); }); });
      }
    });
    view.addEventListener('change', function (e) {
      var row = e.target.closest('tr[data-id]');
      if (!row) return;
      var id = row.getAttribute('data-id'), box = e.target;
      var fn = box.hasAttribute('data-admin') ? 'set_admin' : box.hasAttribute('data-enabled') ? 'set_enabled' : null;
      if (fn) UI.api(fn, id, box.checked).then(function () { UI.toast('Saved', 'ok'); }, function (err) { box.checked = !box.checked; UI.toast(err.message, 'error'); });
    });
    view.addEventListener('submit', function (e) {
      if (e.target.matches('[data-search]')) { e.preventDefault(); users(UI.formData(e.target).q); }
      if (e.target.matches('[data-psearch]')) { e.preventDefault(); parties(UI.formData(e.target).q); }
    });
    return DRAW[tab]();
  });
})();

/* ===== auth.html ===== */
(function () {
  var esc = UI.esc;
  function pw(name, auto) {
    return '<div class="au-pw"><input type="password" name="' + name + '" autocomplete="' + auto + '" required minlength="8">' +
      '<button type="button" data-show>Show</button></div>';
  }
  UI.page('auth', { title: 'Sign in', auth: 'guest' }, function (view, ctx) {
    var mode = ['signup', 'reset'].indexOf(ctx.args[0]) >= 0 ? ctx.args[0] : 'login';
    function draw(msg, isErr) {
      var heading = { login: 'Welcome back', signup: 'Create your account', reset: 'Reset your password' }[mode];
      var sub = { login: 'Sign in to continue to ' + esc(UI.config.name) + '.', signup: 'It\'s free and takes a few seconds.',
        reset: 'We\'ll email you a link to choose a new password.' }[mode];
      view.innerHTML = '<div class="au-wrap"><div class="ui-card au-card">' +
        '<h1>' + heading + '</h1><p class="muted">' + sub + '</p>' +
        (mode !== 'reset' ? '<div class="ui-seg" role="tablist"><button type="button" data-mode="login" class="' + (mode === 'login' ? 'on' : '') + '">Sign in</button>' +
          '<button type="button" data-mode="signup" class="' + (mode === 'signup' ? 'on' : '') + '">Create account</button></div>' : '<div style="height:14px"></div>') +
        '<form class="ui-stack" data-form="' + mode + '" novalidate>' +
        (mode === 'signup' ? '<label class="ui-field"><span>Your name</span><input type="text" name="name" autocomplete="name" required maxlength="60"></label>' : '') +
        '<label class="ui-field"><span>Email</span><input type="email" name="email" autocomplete="email" required></label>' +
        (mode === 'login' ? '<label class="ui-field"><span>Password</span>' + pw('password', 'current-password') + '</label>' : '') +
        (mode === 'signup' ? '<label class="ui-field"><span>Password <em>(at least 8 characters)</em></span>' + pw('password', 'new-password') + '</label>' +
          (window.LegalKit ? '<div>' + LegalKit.consentField() + '</div>' : '') : '') +
        '<div data-msg role="alert"' + (msg ? ' class="' + (isErr ? 'ui-error' : 'ui-note') + '">' + esc(msg) : ' hidden>') + '</div>' +
        '<button class="ui-btn primary block" type="submit">' + { login: 'Sign in', signup: 'Create account', reset: 'Send the link' }[mode] + '</button></form>' +
        '<div class="au-links">' + (mode === 'login' ? '<a data-mode="reset">Forgot your password?</a>' : '<a data-mode="login">' + UI.icon('back') + ' Back to sign in</a>') +
        '<a href="#landing" data-go="landing">About ' + esc(UI.config.name) + '</a></div></div></div>';
      var first = view.querySelector('input');
      if (first && !msg) first.focus();
    }
    view.addEventListener('click', function (e) {
      var m = e.target.closest('[data-mode]');
      if (m) { e.preventDefault(); mode = m.getAttribute('data-mode'); history.replaceState(null, '', '#auth' + (mode === 'login' ? '' : '/' + mode)); draw(); return; }
      var s = e.target.closest('[data-show]');
      if (s) { var i = s.parentNode.querySelector('input'); i.type = i.type === 'password' ? 'text' : 'password'; s.textContent = i.type === 'password' ? 'Show' : 'Hide'; }
    });
    view.addEventListener('submit', function (e) {
      e.preventDefault();
      var form = e.target, v = UI.formData(form);
      var problem = !/^\S+@\S+\.\S+$/.test(v.email || '') ? 'Please enter a valid email address.'
        : mode !== 'reset' && (v.password || '').length < (mode === 'signup' ? 8 : 1) ? (mode === 'signup' ? 'Please choose a password of at least 8 characters.' : 'Please enter your password.')
        : mode === 'signup' && (v.name || '').trim().length < 2 ? 'Please tell us your name.' : null;
      if (problem) { say(problem, true); return; }
      if (mode === 'signup' && window.LegalKit && !LegalKit.consentChecked(form)) return;  // the kit shows its own message
      UI.busy(form.querySelector('[type=submit]'), UI.auth(mode, v)).then(function (r) {
        if (mode === 'reset' || (r && !r.me)) { mode = 'login'; draw(r && r.message, false); restore({ email: v.email }); }
        else UI.toast(mode === 'signup' ? 'Welcome to ' + UI.config.name + '!' : 'Welcome back!', 'ok');
      }, function (err) { say(err.message, true); });
    });
    function say(msg, isErr) {
      var box = view.querySelector('[data-msg]');
      box.className = isErr ? 'ui-error' : 'ui-note'; box.textContent = msg; box.hidden = false;
    }
    function restore(v) {
      ['name', 'email'].forEach(function (k) { var i = view.querySelector('[name=' + k + ']'); if (i && v[k]) i.value = v[k]; });
    }
    draw();
  });
})();

/* ===== catalogue.html ===== */
(function () {
  var esc = UI.esc;
  function item(i, n) {
    var menu = i.menu.map(function (m) { return m[0] + (m[1] > 1 ? ' ×' + m[1] : ''); }).join(' · ');
    var best = PF.day(PF.addDays(PF.friday(0), i.slots[0][0]), 'long') + ' ' + PF.partLabel(i.slots[0][1]).toLowerCase();
    return '<article class="pf-idea ct-item" data-tags="' + i.tags.join(' ') + '"><div class="pf-cover ' + (n % 3 === 1 ? 'red' : n % 3 === 2 ? 'navy' : '') + '">' +
      '<span class="ui-badge ct-tagline" style="background:var(--c-surface)">' + esc(PF.TAGS[i.tags[0]]) + '</span>' + PF.art(i.cover, i.name) + '</div>' +
      '<div class="in"><div class="pf-no">No. ' + esc(i.no) + '</div><h3>' + esc(i.name) + '</h3><p>' + esc(i.blurb) + '</p>' +
      '<div class="spec"><div class="pf-leader"><span class="a">Serves</span><span class="dots"></span><span class="b">' + esc(i.serves) + '</span></div>' +
      '<div class="pf-leader"><span class="a">Effort</span><span class="dots"></span><span class="b" aria-label="' + i.effort + ' of 3">' + PF.effort(i.effort) + '</span></div>' +
      '<div class="pf-leader"><span class="a">Style</span><span class="dots"></span><span class="b">' + esc(PF.STYLES[i.style][0]) + '</span></div>' +
      '<div class="pf-leader"><span class="a">Best on</span><span class="dots"></span><span class="b">' + esc(best) + '</span></div></div>' +
      '<div class="menu"><b>Menu:</b> ' + esc(menu) + '</div>' +
      '<div class="foot"><span class="price">Free!</span><a class="ui-btn primary sm" href="#new/' + i.key + '" data-go="new/' + i.key + '">Order this party</a></div></div></article>';
  }
  UI.page('catalogue', { title: 'The catalogue', nav: 'Catalogue', icon: 'grid', order: 20 }, function (view, ctx) {
    var tag = PF.TAGS[ctx.args[0]] ? ctx.args[0] : 'all';
    var tags = [['all', 'Everything']].concat(Object.keys(PF.TAGS).map(function (k) { return [k, PF.TAGS[k]]; }));
    view.innerHTML = '<div class="ui-wrap"><header class="ct-mast"><div class="pf-label">Plan Friday &amp; Co. present</div>' +
      '<h1>The Weekend Catalogue</h1><div class="pf-script">' + PF.IDEAS.length + ' parties, ready to order by Friday</div>' +
      '<div class="pf-burst red"><span><b>All</b>free</span></div></header>' +
      '<nav class="ct-filters" aria-label="Kinds of party"><div class="ui-seg">' + tags.map(function (t) {
        return '<button type="button" data-tag="' + t[0] + '" class="' + (t[0] === tag ? 'on' : '') + '">' + esc(t[1]) + '</button>';
      }).join('') + '</div></nav>' +
      '<div class="ct-grid">' + PF.IDEAS.map(item).join('') + '</div>' +
      '<p class="muted small" style="text-align:center;margin-top:28px">Don\'t see your party? <a href="#new" data-go="new">Start from a blank order form</a>.</p></div>';
    function filter() {
      view.querySelectorAll('.ct-item').forEach(function (el) { el.hidden = tag !== 'all' && el.getAttribute('data-tags').split(' ').indexOf(tag) < 0; });
      view.querySelectorAll('[data-tag]').forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-tag') === tag); });
    }
    view.addEventListener('click', function (e) {
      var b = e.target.closest('[data-tag]');
      if (!b) return;
      tag = b.getAttribute('data-tag');
      history.replaceState(null, '', '#catalogue' + (tag === 'all' ? '' : '/' + tag));
      filter();
    });
    filter();
  });
})();

/* ===== home.html ===== */
(function () {
  var esc = UI.esc;
  function pickHtml(i) {
    return '<a class="hm-pick" href="#new/' + i.key + '" data-go="new/' + i.key + '"><div class="pf-cover">' + PF.art(i.cover) + '</div>' +
      '<div><b>' + esc(i.name) + '</b><span>No. ' + esc(i.no) + ' · serves ' + esc(i.serves) + '</span></div></a>';
  }
  UI.page('home', { title: 'Your weekend', nav: 'Weekend', icon: 'calendar', auth: 'user', order: 10 }, function (view, ctx) {
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:200px"></div></div>';
    var cd = PF.countdown(), fri = PF.friday(0);
    // Three catalogue picks that change every day.
    var seed = new Date().getDate(), ideas = PF.IDEAS.slice();
    var picks = [ideas[seed % ideas.length], ideas[(seed + 4) % ideas.length], ideas[(seed + 9) % ideas.length]];
    function draw(d) {
      var first = ctx.me.name.split(' ')[0];
      var all = d.hosting.concat(d.invited);
      var upcoming = function (s) { return !PF.allPast(s); };
      var device = UI.store.get('visited', []).filter(function (v) { return !all.some(function (s) { return s.token === v.token; }) && v.token.indexOf('sample') !== 0; });
      view.innerHTML = '<div class="ui-wrap">' +
        '<div class="hm-top"><section class="hm-count"><div><div class="pf-label">Hello, ' + esc(first) + ' · Today\'s edition</div><h1>' + esc(cd.big) + '</h1>' +
          '<p>' + esc(cd.small) + '</p><span class="wk">' + (cd.hot ? 'This weekend' : 'The weekend') + ': ' + esc(PF.weekendRange(fri)) + '</span></div>' +
          '<div class="pf-burst"><span><b>' + esc(cd.burst) + '</b></span></div></section>' +
        '<section class="pf-coupon hm-coupon"><span class="pf-scissors">' + UI.icon('scissors') + '</span><div class="pf-label">Coupon · good any day</div>' +
          '<h2>Host a party this weekend</h2><p>Two minutes to fill in. One link to send. Your friends do the rest.</p>' +
          '<div class="ui-row"><a class="ui-btn primary" href="#new" data-go="new">' + UI.icon('plus') + 'Start a party</a>' +
          '<a class="ui-btn" href="#catalogue" data-go="catalogue">Browse ideas</a></div></section></div>' +
        '<div class="hm-block"><div class="pf-sec"><h2>You\'re hosting</h2><span class="pf-label">' + UI.plural(d.hosting.filter(upcoming).length, 'party', 'parties') + ' coming up</span></div>' +
          (d.hosting.length ? '<div class="pf-pcards">' + d.hosting.map(PF.partyCard).join('') + '</div>'
            : '<div class="ui-empty">' + UI.icon('pot') + '<h3>Nothing on the stove yet</h3><p>Start a party, or order one straight from the catalogue.</p>' +
              (d.sample ? '<p><a href="#p/' + esc(d.sample) + '" data-go="p/' + esc(d.sample) + '">Peek at a sample party first</a></p>' : '') + '</div>') + '</div>' +
        (d.invited.length ? '<div class="hm-block"><div class="pf-sec"><h2>You\'re invited</h2><span class="pf-label">From your friends</span></div>' +
          '<div class="pf-pcards">' + d.invited.map(PF.partyCard).join('') + '</div></div>' : '') +
        (device.length ? '<div class="hm-block"><div class="pf-sec"><h2>Opened on this device</h2><span class="pf-label">Links you followed</span></div><div class="hm-device">' +
          device.map(function (v) { return '<a class="ui-btn sm" href="#p/' + esc(v.token) + '" data-go="p/' + esc(v.token) + '">' + UI.icon('ticket') + esc(v.title) + '</a>'; }).join('') + '</div></div>' : '') +
        '<div class="hm-block"><div class="pf-sec"><h2>Today\'s picks from the catalogue</h2><a class="pf-label" href="#catalogue" data-go="catalogue">See all ' + PF.IDEAS.length + ' →</a></div>' +
          '<div class="hm-picks">' + picks.map(pickHtml).join('') + '</div></div>' +
        '</div>';
    }
    return UI.api('get_home').then(draw);
  });
})();

/* ===== landing.html ===== */
(function () {
  var COPY = {
    eyebrow: 'The Weekend Catalogue · Friday Edition',
    title: 'Plan it on Friday. <em>Feast</em> on the <span class="pf-script">weekend.</span>',
    lead: 'Plan Friday is the quickest way to throw a last-minute dinner party. Make a party page, send one link, and your friends say which day suits them and what they\'re bringing: the soup, the salad, the dessert. No group-chat chaos, and no accounts for guests.',
    cta: 'Host a party, it\'s free',
    proof: ['Guests need no account', 'Ready in two minutes', 'Made for phones'],
    stepsTitle: 'How it works',
    stepsLead: 'From "we should have people over" to a full table, before the weekend starts.',
    steps: [['Order from the catalogue', 'Pick a party idea (Soup Night, Taco Saturday, Pancake Brunch...) or start blank. Tick the weekend slots that could work.', 'Two minutes'],
            ['Send one link', 'Text it, WhatsApp it, email it. Friends open it, put their name down, tick the days they\'re free and pick a dish.', 'Friday afternoon'],
            ['Lock in the day', 'The best day rises to the top. Lock it in, everyone adds it to their calendar, and the menu fills itself.', 'Friday night']],
    hosts: ['A party page with your picture, your note, your address', 'Slots across Friday, Saturday and Sunday (this weekend or next)',
            'A menu by section (soup, mains, dessert, drinks...) with how many of each you want', 'Lock in the best day, close RSVPs, set a seat limit',
            'A weather check for every slot, a printable order sheet, and "run it again" for next week'],
    guests: ['Open the link. No app, no account, no password', 'Put your name down and RSVP, with a +1 or two',
             'Tick ✓ free, ~ maybe or ✕ can\'t for each day', 'Say what you\'re bringing, or let the dice suggest something',
             'Note your diet, leave a note for the host, add the day to your calendar'],
    features: [['calendar', 'Best day wins', 'Everyone ticks the slots that suit them. The one most people can make gets a "best bet" sticker.'],
               ['utensils', 'A menu that adds up', 'Sections with how many you need. Everyone sees what\'s covered and what\'s still wanted.'],
               ['heart', 'Diets, sorted', 'Guests note allergies and diets. Dishes carry tags, and a nut allergy next to walnuts gets flagged.'],
               ['mail', 'Letters to the host', 'A guestbook on every party, for questions, jokes, parking and "running 10 minutes late".'],
               ['print', 'The order sheet', 'Who brings what, on one printable page with tick boxes. Stick it on the fridge.'],
               ['sun', 'Weather check', 'A forecast for every slot, with advice: "perfect patio weather" or "rain plan needed". Outdoor parties get the driest day flagged.']],
    faq: [['Do my guests need an account?', 'No. They open your link, type their name, and they\'re on the list. Their browser remembers them. Only the host needs an account (free), so every party has an owner.'],
          ['Can it really be last minute?', 'That\'s the whole idea. Make the party on Friday morning, send the link at lunch, lock in Saturday dinner by the evening. Your friends see changes right away.'],
          ['Where does the weather come from?', 'From Open-Meteo, a free weather service. Our server asks it for the forecast in the town the host typed, so your browser never contacts it, and the forecast is refreshed every hour.'],
          ['What if nobody is free?', 'Edit the party and add more slots, or tick next weekend too. Answers people already gave are kept.'],
          ['Who can see my party?', 'Anyone with the link. It\'s long and random, so nobody finds it by chance. Guests see first names, RSVPs, dishes and notes, never emails. You can close RSVPs, remove someone, or delete the party at any time.'],
          ['Is it free?', 'Yes. No ads, no fees, nothing to install. It works in any browser, and you can add it to your phone\'s home screen.']],
    bandTitle: { 5: 'It\'s Friday. Perfect timing.', 6: 'There\'s still time.', 0: 'Next weekend, then?' }[new Date().getDay()] || 'It\'s nearly Friday.',
    bandLead: 'Start the party page now and you\'ll have a plan by tonight.'
  };

  function heroArt() {
    var sat = PF.addDays(PF.friday(0), 1);
    return '<div class="lp-art" aria-hidden="true"><div class="lp-cover"><div class="mast"><b>The Weekend Catalogue</b><span class="pf-no">No. 1</span></div>' +
      '<div class="scene"><div>' + PF.art('wine') + '</div><div>' + PF.art('soup') + '</div><div>' + PF.art('pie') + '</div></div>' +
      '<div class="lines"><span>Soups · Pies · Wines</span><span>Friday Edition</span></div>' +
      '<div class="pf-burst red"><span><b>Free!</b>this week</span></div></div>' +
      '<div class="lp-slip"><div class="pf-label">Order slip · Soup Night</div>' +
      '<div class="rowx"><b>' + UI.esc(PF.day(sat, 'short')) + ' · Dinner</b><span class="ok">✓ 5 free</span></div>' +
      '<div class="rowx"><span>Tomato soup</span><span class="muted small">Maya</span></div>' +
      '<div class="rowx"><span>Apple crumble</span><span class="muted small">Lou</span></div></div></div>';
  }

  UI.page('landing', { title: 'Plan a weekend dinner party' }, function (view, ctx) {
    var me = ctx.me, C = COPY, esc = UI.esc;
    var primary = me ? '<a class="ui-btn primary lg" href="#home" data-go="home">Open your weekend ' + UI.icon('arrow') + '</a><a class="ui-btn lg" href="#new" data-go="new">Host a party</a>'
      : '<a class="ui-btn primary lg" href="#auth/signup" data-go="auth/signup">' + esc(C.cta) + ' ' + UI.icon('arrow') + '</a>' +
        '<a class="ui-btn lg" href="#p/sample" data-go="p/sample">See a sample party</a>';
    var device = UI.store.get('visited', []).filter(function (v) { return v.token.indexOf('sample') !== 0; });
    view.innerHTML =
      '<section class="lp-hero"><div class="ui-wrap"><div>' +
        '<div class="eyebrow">' + esc(C.eyebrow) + '</div><h1>' + C.title + '</h1><p class="lp-lead">' + esc(C.lead) + '</p>' +
        '<div class="lp-cta">' + primary + '</div>' +
        '<div class="lp-proof">' + C.proof.map(function (p) { return '<span>' + UI.icon('check') + esc(p) + '</span>'; }).join('') + '</div>' +
      '</div>' + heroArt() + '</div></section>' +
      (device.length && !me ? '<section class="lp-section" style="padding-top:0"><div class="ui-wrap"><div class="pf-coupon"><span class="pf-scissors">' + UI.icon('scissors') + '</span>' +
        '<div class="pf-label" style="text-align:center;margin-bottom:10px">Back for your party? Opened on this device</div><div class="lp-device">' +
        device.map(function (v) { return '<a class="ui-btn" href="#p/' + esc(v.token) + '" data-go="p/' + esc(v.token) + '">' + UI.icon('ticket') + esc(v.title) + '</a>'; }).join('') + '</div></div></div></section>' : '') +
      '<section class="lp-section" id="how"><div class="ui-wrap"><div class="lp-head"><div class="eyebrow">Page 2</div><h2>' + esc(C.stepsTitle) + '</h2><p>' + esc(C.stepsLead) + '</p></div>' +
        '<div class="lp-steps">' + C.steps.map(function (s) { return '<div class="ui-card lp-step"><span class="pf-label">' + esc(s[2]) + '</span><h3>' + esc(s[0]) + '</h3><p class="muted" style="margin:0">' + esc(s[1]) + '</p></div>'; }).join('') + '</div></div></section>' +
      '<section class="lp-section"><div class="ui-wrap"><div class="lp-two">' +
        '<div class="ui-card lp-aud"><div class="pf-label">For the host</div><h3>You make the page</h3><ul>' + C.hosts.map(function (h) { return '<li>' + UI.icon('check') + '<span>' + esc(h) + '</span></li>'; }).join('') + '</ul>' +
          (me ? '<a class="ui-btn primary" href="#new" data-go="new">Host a party</a>' : '<a class="ui-btn primary" href="#auth/signup" data-go="auth/signup">Create a free host account</a>') + '</div>' +
        '<div class="pf-coupon lp-aud"><span class="pf-scissors">' + UI.icon('scissors') + '</span><div class="pf-label">For the guests</div><h3>Got a link from a friend?</h3><ul>' +
          C.guests.map(function (h) { return '<li>' + UI.icon('check') + '<span>' + esc(h) + '</span></li>'; }).join('') + '</ul>' +
          '<a class="ui-btn" href="#p/sample" data-go="p/sample">See what guests see</a></div>' +
      '</div></div></section>' +
      '<section class="lp-section"><div class="ui-wrap"><div class="lp-head"><div class="eyebrow">Page 3 · Features</div><h2>Everything for a full table</h2></div>' +
        '<div class="lp-feats">' + C.features.map(function (f, i) { return '<div class="lp-feat"><span class="no">No. ' + (i + 1) + 'F</span><h3>' + UI.icon(f[0]) + esc(f[1]) + '</h3><p>' + esc(f[2]) + '</p></div>'; }).join('') + '</div>' +
        '<p style="text-align:center;margin-top:22px"><a class="ui-btn" href="#catalogue" data-go="catalogue">' + UI.icon('grid') + 'Browse ' + PF.IDEAS.length + ' party ideas</a></p></div></section>' +
      '<section class="lp-section"><div class="ui-wrap"><div class="lp-head"><div class="eyebrow">Page 4</div><h2>Questions &amp; answers</h2></div><div class="lp-faq">' +
        C.faq.map(function (q) { return '<details><summary>' + esc(q[0]) + '</summary><p>' + esc(q[1]) + '</p></details>'; }).join('') + '</div></div></section>' +
      '<section class="lp-section"><div class="ui-wrap"><div class="lp-band"><div><h2>' + esc(C.bandTitle) + '</h2><p>' + esc(C.bandLead) + '</p></div>' +
        (me ? '<a class="ui-btn lg" href="#new" data-go="new">Host a party</a>' : '<a class="ui-btn lg" href="#auth/signup" data-go="auth/signup">' + esc(C.cta) + '</a>') +
      '</div></div></section>';
  });
})();

/* ===== party.html ===== */
(function () {
  var esc = UI.esc;
  var ANS = [['yes', '✓', 'Free'], ['maybe', '~', 'Maybe'], ['no', '✕', 'Can\'t']];

  UI.page('p', { title: 'Party' }, function (view, ctx) {
    var token = ctx.args[0] || '', key = 'g.' + token;
    var secret = UI.store.get(key, null), V = null, timer = null, last = '';

    function call(fn) {
      var args = [fn, token, secret].concat(Array.prototype.slice.call(arguments, 1));
      return UI.api.apply(null, args).then(took);
    }
    function host(fn) {  // host tools work on the party id and need the account
      return UI.api.apply(null, [fn, V.party.id].concat(Array.prototype.slice.call(arguments, 1))).then(took);
    }
    function took(r) {
      if (r && r.secret) { secret = r.secret; UI.store.set(key, secret); }
      if (r && r.view) { V = r.view; last = JSON.stringify(V); draw(); }
      return r;
    }
    function load(quiet) {
      return (quiet ? UI.apiQuiet : UI.api)('party_view', token, secret).then(function (r) {
        if (r.missing) { PF.forget(token); return missing(); }
        var s = JSON.stringify(r.view);
        if (s === last) return;
        V = r.view; last = s;
        PF.remember(V.party);
        document.title = V.party.title + ' · ' + UI.config.name;
        draw();
      });
    }

    /* ---------------------------------------------------------------- drawing */
    function missing() {
      view.innerHTML = '<div class="ui-wrap"><div class="ui-empty pt-missing">' + UI.icon('ticket') + '<h3>We couldn\'t find that party</h3>' +
        '<p>The link may be incomplete, or the host has deleted the party. Ask them to send it again.</p>' +
        '<div class="ui-row" style="justify-content:center"><a class="ui-btn primary" href="#new" data-go="new">Host your own</a><a class="ui-btn" href="#catalogue" data-go="catalogue">Browse the catalogue</a></div></div></div>';
    }
    function guestName(id) { for (var i = 0; i < V.guests.length; i++) if (V.guests[i].id === id) return V.guests[i].name; return '?'; }
    function chip(id, kind) {
      var mine = V.me && V.me.id === id;
      return '<span class="pf-chip ' + kind + (mine ? ' me' : '') + '" title="' + esc(guestName(id)) + (kind === 'maybe' ? ' (maybe)' : '') + '">' + esc(UI.initials(guestName(id))) + '</span>';
    }

    function draw() {
      var p = V.party, st = V.stats, me = V.me;
      var scrollY = window.scrollY;
      var past = PF.allPast(p);
      view.innerHTML = '<div class="ui-wrap">' +
        (p.demo ? '<div class="pt-sample"><b>' + UI.icon('info') + ' Sample page · a party for you to look around</b>' +
          (ctx.me ? '<button class="ui-btn sm" data-copy-sample>' + UI.icon('copy') + 'Copy it as my party</button>' : '<a class="ui-btn sm" href="#auth/signup" data-go="auth/signup">Host your own, free</a>') + '</div>' : '') +
        hero(p, st, past) +
        (V.is_host ? shareBox(p, true) : '') +
        slip(p, me) +
        '<div class="pt-grid"><div>' + when(p, st, me, past) + menu(p, st, me) + book(me) + '</div>' +
        '<aside class="pt-side">' + guestList(p, st) + table(st) + (V.is_host || p.demo ? '' : shareBox(p, false)) + '</aside></div></div>';
      window.scrollTo(0, scrollY);
    }

    function hero(p, st, past) {
      var whenBox;
      if (p.chosen) {
        whenBox = '<div class="pt-when on"><div class="pf-burst red sm"><span><b>It\'s</b>on!</span></div><div class="grow"><div class="pf-label">The day is set</div>' +
          '<div class="big">' + esc(PF.whenText(p)) + '</div></div>' +
          '<div class="ui-row"><button class="ui-btn sm" data-ics>' + UI.icon('download') + 'Add to calendar</button>' +
          '<a class="ui-btn sm" target="_blank" rel="noopener" href="' + esc(PF.googleCal(p)) + '">' + UI.icon('calendar') + 'Google</a></div></div>';
      } else {
        whenBox = '<div class="pt-when"><div class="grow"><div class="pf-label">Day to be decided · ' + UI.plural(p.slots.length, 'option') + '</div>' +
          '<div class="big">' + (st.best ? 'Leading: ' + esc(PF.slotLabel(st.best)) + ', ' + esc(PF.shortDate(PF.slot(st.best).d)) : 'Waiting for answers') + '</div></div>' +
          (V.is_host && st.best && !p.demo ? '<button class="ui-btn primary sm" data-lock="' + esc(st.best) + '">' + UI.icon('lock') + 'Lock it in</button>' : '') + '</div>';
      }
      return '<section class="pt-hero"><div class="pt-hero-cover"><div class="pf-cover ' + (p.chosen ? 'red' : '') + '">' + PF.art(p.cover) + '</div>' +
        (p.status === 'closed' ? '<span class="pf-stamp">RSVPs closed</span>' : past ? '<span class="pf-stamp navy">Been &amp; gone</span>' : '') + '</div>' +
        '<div><div class="pf-no">Catalogue ' + esc(p.catalog_no || '') + ' · ' + esc(PF.STYLES[p.style] ? PF.STYLES[p.style][0] : 'Potluck') + '</div>' +
        '<h1>' + esc(p.title) + '</h1>' +
        '<div class="pt-meta"><span>' + UI.icon('user') + 'Hosted by ' + esc(p.host_name) + '</span>' +
          (p.location ? '<span>' + UI.icon('pin') + esc(p.location) + '</span>' : '') +
          '<span>' + UI.icon('users') + UI.plural(st.heads, 'seat') + ' taken' + (p.cap ? ' of ' + p.cap : '') + '</span>' +
          (p.outdoors ? '<span>' + UI.icon('sun') + 'Outdoors</span>' : '') + '</div>' +
        (p.blurb ? '<p class="pt-blurb">' + esc(p.blurb) + '</p>' : '') + whenBox + wxBox(p, st) +
        (V.is_host && past && !p.demo ? '<div class="ui-note" style="margin-top:12px">This weekend has been and gone. <a href="#" data-dup>Run it again next weekend →</a></div>' : '') +
        '</div></section>';
    }

    /* The weather check: for the locked-in day, else the leading one, else the first slot with a forecast. */
    function wxBox(p, st) {
      var w = V.weather;
      if (!w) return V.is_host && !p.demo ? '<p class="pt-wxnote muted">' + UI.icon('sun') + ' Add a town in <a href="#edit/' + esc(p.id) + '" data-go="edit/' + esc(p.id) + '">Edit</a> to get a weather check for each day.</p>' : '';
      var key = p.chosen || st.best, f = key && w.slots[key];
      if (!f) { key = p.slots.filter(function (k) { return w.slots[k] && !PF.isPast(k); })[0]; f = key && w.slots[key]; }
      var town = (w.place || '').split(',')[0];
      var credit = '<p class="pt-credit">Forecast by <a href="https://open-meteo.com/" target="_blank" rel="noopener">Open-Meteo.com</a>' +
        (w.updated ? ' · updated ' + esc(UI.ago(w.updated)) : '') + (w.ok ? '' : ' · the weather service is slow to answer, so this may be a little old') + '</p>';
      if (!f) return '<div class="pt-wx"><div class="grow"><div class="pf-label">Weather check · ' + esc(town) + '</div>' +
        '<div>' + (p.slots.every(PF.isPast) ? 'This weekend has been and gone.' : 'The forecast opens about two weeks ahead. Check back closer to the day.') + '</div></div></div>' + credit;
      var kind = PF.wxKind(f.code, f.hour), u = PF.units();
      return '<div class="pt-wx"><div class="ic">' + PF.wxIcon(f) + '</div><div class="grow"><div class="pf-label">Weather check · ' + esc(PF.slotLabel(key)) + ' · ' + esc(town) + '</div>' +
        '<div class="big">' + esc(kind[1]) + ', ' + esc(PF.temp(f.temp)) + '</div>' +
        '<div class="small">' + (f.rain || 0) + '% chance of rain · wind ' + esc(PF.wind(f.wind)) + (f.tmax != null ? ' · high ' + esc(PF.temp(f.tmax)) + ', low ' + esc(PF.temp(f.tmin)) : '') + '</div>' +
        '<div class="pf-script advice">' + esc(PF.advice(f, w.outdoors)) + '</div></div>' +
        '<div class="ui-seg" role="group" aria-label="Units"><button type="button" data-units="C" class="' + (u === 'C' ? 'on' : '') + '">°C</button>' +
        '<button type="button" data-units="F" class="' + (u === 'F' ? 'on' : '') + '">°F</button></div></div>' + credit;
    }

    function shareBox(p, isHost) {
      var url = PF.partyUrl(p.token), text = PF.inviteText(p);
      var ways = '<div class="ways">' + (navigator.share ? '<button class="ui-btn sm" data-share>' + UI.icon('share') + 'Share</button>' : '') +
        '<a class="ui-btn sm" href="sms:?&body=' + encodeURIComponent(text) + '">' + UI.icon('phone') + 'Text</a>' +
        '<a class="ui-btn sm" target="_blank" rel="noopener" href="https://wa.me/?text=' + encodeURIComponent(text) + '">' + UI.icon('chat') + 'WhatsApp</a>' +
        '<a class="ui-btn sm" href="mailto:?subject=' + encodeURIComponent('Invitation: ' + p.title) + '&body=' + encodeURIComponent(text) + '">' + UI.icon('mail') + 'Email</a></div>';
      if (!isHost) {
        return '<div class="ui-card"><h3>Pass it on</h3><p class="small muted">Anyone with this link can join the guest list.</p>' +
          '<div class="pt-share"><div class="link"><button class="ui-btn sm block" data-copy>' + UI.icon('link') + 'Copy the link</button></div>' + ways.replace('class="ways"', 'class="ways" style="margin-top:8px"') + '</div>' +
          '<a class="ui-btn ghost sm" href="#sheet/' + esc(p.token) + '" data-go="sheet/' + esc(p.token) + '">' + UI.icon('print') + 'Printable order sheet</a></div>';
      }
      return '<section class="pf-coupon pt-share"><span class="pf-scissors">' + UI.icon('scissors') + '</span>' +
        '<div class="ui-row between" style="margin-bottom:10px"><div><div class="pf-label">For the host only</div><h2 style="margin:2px 0 0;font-size:1.4rem">Send this link to your guests</h2></div>' +
        (p.demo ? '' : '<span class="ui-badge ' + (p.status === 'closed' ? 'bad' : 'good') + '">' + (p.status === 'closed' ? 'RSVPs closed' : 'Taking RSVPs') + '</span>') + '</div>' +
        '<div class="link"><input type="text" readonly value="' + esc(url) + '" aria-label="Party link" data-linkbox><button class="ui-btn primary" data-copy>' + UI.icon('copy') + 'Copy link</button></div>' + ways +
        '<div class="pt-host">' +
          (p.demo ? '' : '<a class="ui-btn sm" href="#edit/' + esc(p.id) + '" data-go="edit/' + esc(p.id) + '">' + UI.icon('edit') + 'Edit</a>') +
          (p.demo ? '' : p.chosen ? '<button class="ui-btn sm" data-unlock>' + UI.icon('refresh') + 'Change the day</button>' : '<button class="ui-btn sm" data-lock="">' + UI.icon('lock') + 'Lock in the day</button>') +
          (p.demo ? '' : '<button class="ui-btn sm" data-status="' + (p.status === 'closed' ? 'open' : 'closed') + '">' + UI.icon(p.status === 'closed' ? 'check' : 'x') + (p.status === 'closed' ? 'Reopen RSVPs' : 'Close RSVPs') + '</button>') +
          '<a class="ui-btn sm" href="#sheet/' + esc(p.token) + '" data-go="sheet/' + esc(p.token) + '">' + UI.icon('print') + 'Order sheet</a>' +
          '<button class="ui-btn sm" data-dup>' + UI.icon('copy') + 'Run it again</button>' +
          (p.demo ? '' : '<button class="ui-btn sm danger" data-delete>' + UI.icon('trash') + 'Delete</button>') +
        '</div></section>';
    }

    function slip(p, me) {
      if (!me) {
        var blocked = p.demo ? 'This is a sample party, so the guest list is just for show.' : p.status === 'closed' ? 'The host has closed RSVPs for this party.' : '';
        var name = V.suggest_name || UI.store.get('name', '');
        return '<section class="pf-coupon pt-slip" id="slip"><span class="pf-scissors">' + UI.icon('scissors') + '</span>' +
          '<div class="pf-label">Your order slip · no account needed</div><h2>Are you coming?</h2>' +
          '<p class="muted" style="margin:0">Put your name down, then tick the days you\'re free and pick something to bring.</p>' +
          (blocked ? '<p class="ui-note" style="margin:14px 0 0">' + esc(blocked) + '</p>' :
          '<form class="pt-join" data-join><label class="ui-field"><span>Your name</span><input type="text" name="name" maxlength="40" required autocomplete="given-name" placeholder="As your friends know you" value="' + esc(name) + '"></label>' +
          '<div class="btns"><button class="ui-btn primary" name="rsvp" value="yes" type="submit">' + UI.icon('check') + 'Count me in</button>' +
          '<button class="ui-btn" name="rsvp" value="maybe" type="submit">Maybe</button><button class="ui-btn" name="rsvp" value="no" type="submit">Can\'t make it</button></div></form>') +
          (!ctx.me && !p.demo ? '<p class="small muted" style="margin:12px 0 0">This browser remembers you. On another device? <a href="#auth" data-go="auth">Sign in</a> and it follows you.</p>' : '') +
          '</section>';
      }
      var closed = p.status === 'closed' && !V.is_host;
      return '<section class="ui-card pt-slip" id="slip"><div class="ui-row between"><div><div class="pf-label">Your order slip</div>' +
        '<h2>' + (me.rsvp === 'yes' ? 'You\'re coming, ' : me.rsvp === 'maybe' ? 'Maybe coming, ' : 'Not this time, ') + esc(me.name) + (me.rsvp === 'no' ? '' : '!') + '</h2></div>' +
        '<button class="ui-btn ghost sm" data-rename>' + UI.icon('edit') + 'Change name</button></div>' +
        '<div class="pt-mine"><div><span class="pf-label">RSVP</span><div class="ui-seg pt-rsvp">' + [['yes', 'Coming'], ['maybe', 'Maybe'], ['no', 'Can\'t']].map(function (o) {
          return '<button type="button" data-rsvp="' + o[0] + '" class="' + (me.rsvp === o[0] ? 'on' : '') + '"' + (closed ? ' disabled' : '') + '>' + o[1] + '</button>';
        }).join('') + '</div></div>' +
        '<div><span class="pf-label">Bringing extra people</span><div class="pt-step"><button type="button" data-plus="-1" aria-label="Fewer"' + (closed ? ' disabled' : '') + '>−</button><output>+' + me.plus + '</output>' +
          '<button type="button" data-plus="1" aria-label="More"' + (closed ? ' disabled' : '') + '>+</button></div></div>' +
        '<div><span class="pf-label">Your diet <span class="pf-script" style="font-size:1rem;color:var(--c-muted)">(the host will thank you)</span></span><div class="pt-diets">' + PF.DIETS.map(function (d) {
          return '<button type="button" class="pt-tog' + (me.diet.indexOf(d[0]) >= 0 ? ' on' : '') + '" data-diet="' + d[0] + '">' + esc(d[1]) + '</button>';
        }).join('') + '</div></div></div>' +
        (closed ? '<p class="small muted" style="margin:12px 0 0">RSVPs are closed, but you can still change your dish and write in the guestbook.</p>' : '') +
        (me.is_host ? '' : '<p class="small" style="margin:14px 0 0"><a href="#" data-forget>Take me off the guest list</a></p>') + '</section>';
    }

    function when(p, st, me, past) {
      var mineOk = me && me.rsvp !== 'no' && !p.chosen && !(p.status === 'closed' && !V.is_host);
      var W = V.weather ? V.weather.slots : {}, driest = null;
      if (V.weather && V.weather.outdoors) p.slots.forEach(function (k) { if (W[k] && !PF.isPast(k) && (driest === null || W[k].rain < W[driest].rain)) driest = k; });
      if (driest && p.slots.filter(function (k) { return W[k]; }).length < 2) driest = null;
      var rows = p.slots.map(function (k) {
        var s = PF.slot(k), t = st.slots[k] || { yes: [], maybe: [], no: [] }, isPast = PF.isPast(k);
        var chosen = p.chosen === k, best = !p.chosen && st.best === k;
        var mine = me && me.avail[k];
        return '<div class="pt-slot' + (chosen ? ' chosen' : '') + (best ? ' best' : '') + (p.chosen && !chosen ? ' dim' : '') + (isPast && !chosen ? ' past' : '') + '">' +
          (best ? '<span class="pf-burst sm"><span><b>Best</b>bet</span></span>' : '') +
          '<div class="day"><b>' + esc(PF.day(s.d, 'short')) + '</b><span>' + esc(PF.shortDate(s.d)) + '</span></div>' +
          '<div class="who"><div class="t">' + esc(PF.partLabel(s.part)) + ' <small>· ' + esc(chosen && p.chosen_time ? PF.timeLabel(p.chosen_time) : PF.timeLabel(PF.PARTS[s.part].time)) +
            ' · ' + t.yes.length + ' free' + (t.maybe.length ? ', ' + t.maybe.length + ' maybe' : '') + (isPast ? ' · past' : '') + '</small></div>' +
            (W[k] || driest === k ? '<div class="wxrow">' + PF.wxChip(W[k]) + (driest === k ? '<span class="ui-badge warn">' + UI.icon('sun') + 'Driest</span>' : '') + '</div>' : '') +
            (t.yes.length || t.maybe.length ? '<div class="pf-chips">' + t.yes.map(function (id) { return chip(id, ''); }).join('') + t.maybe.map(function (id) { return chip(id, 'maybe'); }).join('') + '</div>' : '') + '</div>' +
          '<div class="mine">' + (mineOk && !isPast ? ANS.map(function (a) {
            return '<button type="button" class="pt-ans' + (mine === a[0] ? ' on' : '') + '" data-ans="' + a[0] + '" data-slot="' + esc(k) + '" title="' + a[2] + '" aria-label="' + a[2] + ' for ' + esc(PF.slotLabel(k)) + '" aria-pressed="' + (mine === a[0]) + '">' + a[1] + '</button>';
          }).join('') : chosen ? '<span class="pf-stamp good">It\'s on</span>' : '') +
          (V.is_host && !p.chosen && !p.demo ? '<button class="ui-btn sm lock" data-lock="' + esc(k) + '" title="Lock in this day">' + UI.icon('lock') + '<span class="pf-hide-xs">Lock</span></button>' : '') + '</div></div>';
      }).join('');
      var hint = p.chosen ? 'The host locked in the day. See you there!' : !me ? 'Put your name down above to answer.' : me.rsvp === 'no' ? 'You said you can\'t come. Change your RSVP to answer.'
        : 'Tap ✓ free, ~ maybe or ✕ can\'t for each one.';
      return '<section class="pt-sec"><div class="pf-sec"><h2>When are you free?</h2><span class="pf-label">' + esc(hint) + '</span></div><div class="pt-slots">' + rows + '</div></section>';
    }

    function menu(p, st, me) {
      var still = Object.keys(st.menu).filter(function (c) { return st.menu[c].have < st.menu[c].wanted; })
        .map(function (c) { return (st.menu[c].wanted - st.menu[c].have) + ' × ' + c.toLowerCase(); });
      var pct = st.wanted_total ? Math.round(100 * st.filled / st.wanted_total) : 0;
      var open = !p.demo;
      var cats = p.categories.filter(function (c) { return st.menu[c] && (st.menu[c].wanted || st.menu[c].have || c !== 'Something else'); });
      if (cats.indexOf('Something else') < 0) cats.push('Something else');
      return '<section class="pt-sec"><div class="pf-sec"><h2>The menu</h2><span class="pf-label">' + UI.plural(st.dishes, 'dish', 'dishes') + ' promised</span></div>' +
        (st.wanted_total ? '<div class="pt-meterrow"><b class="pf-label" style="color:var(--c-ink)">' + st.filled + ' of ' + st.wanted_total + ' filled</b>' +
          '<span class="small muted">' + (still.length ? 'Still wanted: ' + esc(still.slice(0, 4).join(', ')) + (still.length > 4 ? '…' : '') : 'Every section is covered. Bravo!') + '</span>' +
          '<div class="pf-meter" role="progressbar" aria-valuenow="' + pct + '" aria-valuemin="0" aria-valuemax="100"><i style="width:' + pct + '%"></i></div></div>' : '') +
        cats.map(function (c) {
          var m = st.menu[c] || { wanted: 0, have: 0 }, dishes = V.dishes.filter(function (d) { return d.category === c; });
          var boxes = '';
          for (var i = 0; i < Math.max(m.wanted, m.have); i++) boxes += '<i class="' + (i < m.have ? (i < m.wanted ? 'on' : 'over') : '') + '"></i>';
          return '<div class="pt-cat"><header><h3>' + esc(c) + '</h3><div class="need">' +
            (m.wanted ? '<span class="pf-label">' + (m.have >= m.wanted ? 'Covered' : (m.wanted - m.have) + ' wanted') + '</span>' : '') + (boxes ? '<span class="pf-boxes" aria-hidden="true">' + boxes + '</span>' : '') + '</div></header>' +
            (dishes.length ? '<ul class="pt-dishes">' + dishes.map(function (d) {
              return '<li><div class="pf-leader"><span class="a">' + esc(d.name) + '</span><span class="dots"></span><span class="b">' + esc(d.by) + (d.serves ? ' · serves ' + d.serves : '') + '</span></div>' +
                (d.can_remove && open ? '<button class="ui-btn ghost icon sm x" data-deldish="' + esc(d.id) + '" aria-label="Take ' + esc(d.name) + ' off the menu">' + UI.icon('x') + '</button>' : '') +
                (d.tags.length ? '<div class="tags">' + d.tags.map(function (t) { return '<span class="ui-badge' + (t === 'nuts' ? ' bad' : t === 'spicy' ? ' warn' : ' good') + '">' + esc(PF.tagLabel(t)) + '</span>'; }).join('') + '</div>' : '') +
                (d.note ? '<div class="note">' + esc(d.note) + '</div>' : '') + '</li>';
            }).join('') + '</ul>' : '<p class="empty">' + (m.wanted ? 'Nobody yet. Could it be you?' : 'Anything else you\'d like to bring.') + '</p>') +
            (open ? '<div class="add"><button class="ui-btn sm" data-bring="' + esc(c) + '">' + UI.icon('plus') + 'I\'ll bring ' + (c === 'Something else' ? 'something' : 'one') + '</button></div>' : '') + '</div>';
        }).join('') + '</section>';
    }

    function book(me) {
      return '<section class="pt-sec pt-book"><div class="pf-sec"><h2>Letters to the host</h2><span class="pf-label">' + UI.plural(V.comments.length, 'note') + '</span></div>' +
        (me && !V.party.demo ? '<form data-comment><label class="ui-field"><span>Write a note <em>(everyone with the link can read it)</em></span>' +
          '<textarea name="body" maxlength="600" placeholder="Can I bring my dog? Running 15 minutes late? Allergic to cilantro?"></textarea></label>' +
          '<div class="ui-row end"><button class="ui-btn primary" type="submit">' + UI.icon('mail') + 'Post it</button></div></form>' :
          (!me && !V.party.demo ? '<p class="muted">Put your name on the guest list to write a note.</p>' : '')) +
        (V.comments.length ? V.comments.slice().reverse().map(function (c) {
          return '<article class="pt-note' + (c.by_host ? ' host' : '') + '"><div class="by">' + esc(c.by) + (c.by_host ? ' <span class="ui-badge brand">Host</span>' : '') +
            '<time datetime="' + esc(c.created) + '">' + esc(UI.ago(c.created)) + '</time></div><p>' + esc(c.body) + '</p>' +
            (c.can_remove && !V.party.demo ? '<button class="ui-btn ghost icon sm x" data-delnote="' + esc(c.id) + '" aria-label="Delete this note">' + UI.icon('x') + '</button>' : '') + '</article>';
        }).join('') : '<div class="ui-empty" style="padding:26px">' + UI.icon('mail') + '<p style="margin:0">No notes yet. Questions, jokes and allergy warnings welcome.</p></div>') + '</section>';
    }

    function guestList(p, st) {
      var groups = [['yes', 'Coming'], ['maybe', 'Maybe'], ['no', 'Can\'t make it']];
      var seats = p.cap ? '<div class="pf-leader small" style="margin-bottom:6px"><span class="a">Seats</span><span class="dots"></span><span class="b">' + st.heads + ' of ' + p.cap + '</span></div>' +
        '<div class="pf-meter" style="margin-bottom:12px"><i style="width:' + Math.min(100, Math.round(100 * st.heads / p.cap)) + '%"></i></div>' : '';
      return '<div class="ui-card"><h3>The guest list</h3>' + seats + groups.map(function (g) {
        var list = V.guests.filter(function (x) { return x.rsvp === g[0]; });
        if (!list.length) return '';
        return '<div class="pf-label pt-glabel">' + g[1] + ' · ' + (g[0] === 'yes' ? st.heads : list.length) + '</div><ul class="pt-guests">' + list.map(function (x) {
          return '<li><span class="pf-chip ' + (g[0] === 'yes' ? '' : 'maybe') + (x.mine ? ' me' : '') + '">' + esc(UI.initials(x.name)) + '</span><span class="nm">' + esc(x.name) +
            (x.plus ? ' <b>+' + x.plus + '</b>' : '') + (x.mine ? ' <span class="muted small">(you)</span>' : '') + '</span>' +
            '<span class="ic">' + (x.is_host ? '<span class="ui-badge brand">Host</span>' : '') + (x.diet.length ? '<span class="ui-badge" title="' + esc(x.diet.map(PF.dietLabel).join(', ')) + '">' + esc(x.diet.map(PF.dietLabel).join(', ').slice(0, 14)) + (x.diet.join(', ').length > 14 ? '…' : '') + '</span>' : '') +
            (V.is_host && !x.is_host && !p.demo ? '<button class="ui-btn ghost icon sm" data-kick="' + esc(x.id) + '" aria-label="Remove ' + esc(x.name) + '" style="width:30px;min-height:30px">' + UI.icon('x') + '</button>' : '') + '</span></li>';
        }).join('') + '</ul>';
      }).join('') + (V.guests.length ? '' : '<p class="muted">Nobody yet. Be the first!</p>') + '</div>';
    }

    function table(st) {
      var keys = Object.keys(st.diets);
      var warn = [];
      var nuts = V.dishes.filter(function (d) { return d.tags.indexOf('nuts') >= 0; });
      if (st.diets.nutfree && nuts.length) warn.push(UI.plural(st.diets.nutfree, 'guest has', 'guests have') + ' a nut allergy, and ' + nuts.map(function (d) { return d.name; }).join(', ') + ' ' + (nuts.length === 1 ? 'has' : 'have') + ' nuts.');
      var veg = (st.diets.veg || 0) + (st.diets.vegan || 0), vegDishes = V.dishes.filter(function (d) { return d.tags.indexOf('veg') >= 0 || d.tags.indexOf('vegan') >= 0; }).length;
      if (veg && V.dishes.length >= 3 && vegDishes < 2) warn.push('Only ' + UI.plural(vegDishes, 'dish is', 'dishes are') + ' tagged vegetarian for ' + UI.plural(veg, 'veggie guest') + '.');
      if (st.diets.vegan && !V.dishes.some(function (d) { return d.tags.indexOf('vegan') >= 0; }) && V.dishes.length) warn.push('Nothing on the menu is tagged vegan yet.');
      if (st.diets.gf && V.dishes.length >= 3 && !V.dishes.some(function (d) { return d.tags.indexOf('gf') >= 0; })) warn.push('Nothing is tagged gluten-free yet.');
      return '<div class="ui-card"><h3>At the table</h3>' + (keys.length ? keys.map(function (k) {
        return '<div class="pf-leader small"><span class="a">' + esc(PF.dietLabel(k)) + '</span><span class="dots"></span><span class="b">' + st.diets[k] + '</span></div>';
      }).join('') : '<p class="muted small" style="margin:0">No dietary notes yet.</p>') +
        warn.map(function (w) { return '<div class="pt-warn">' + UI.icon('info') + ' ' + esc(w) + '</div>'; }).join('') + '</div>';
    }

    /* ---------------------------------------------------------------- modals */
    function bring(cat) {
      if (!V.me) { needName(); return; }
      var ideas = PF.suggest(cat), n = Math.floor(Math.random() * ideas.length);
      var m = UI.modal('<div class="pf-label">' + esc(V.party.title) + ' · the menu</div><h2>What are you bringing?</h2><form class="ui-stack" data-dish>' +
        '<label class="ui-field"><span>Section</span><select name="category">' + V.party.categories.map(function (c) {
          return '<option' + (c === cat ? ' selected' : '') + '>' + esc(c) + '</option>';
        }).join('') + '</select></label>' +
        '<label class="ui-field"><span>The dish</span><div class="ui-row" style="flex-wrap:nowrap"><input type="text" name="name" maxlength="80" required placeholder="' + esc(ideas[n]) + '" style="flex:1">' +
          '<button type="button" class="ui-btn icon" data-idea title="Need an idea?" aria-label="Suggest a dish">' + UI.icon('dice') + '</button></div></label>' +
        '<div class="ui-row top" style="flex-wrap:nowrap;gap:12px"><label class="ui-field" style="width:120px"><span>Serves</span><input type="number" name="serves" min="1" max="50" placeholder="6"></label>' +
          '<label class="ui-field" style="flex:1"><span>Note <em>(optional)</em></span><input type="text" name="note" maxlength="140" placeholder="Needs the oven for 10 min"></label></div>' +
        '<div class="ui-field"><span>Good to know</span><div class="pt-diets">' + PF.DISH_TAGS.map(function (t) {
          return '<button type="button" class="pt-tog" data-tag="' + t[0] + '" aria-pressed="false">' + esc(t[1]) + '</button>';
        }).join('') + '</div></div>' +
        '<div class="ui-row end"><button type="button" class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" type="submit">' + UI.icon('check') + 'Put it on the menu</button></div></form>');
      var f = m.el.querySelector('form');
      m.el.addEventListener('click', function (e) {
        var t = e.target.closest('[data-tag]');
        if (t) { t.classList.toggle('on'); t.setAttribute('aria-pressed', t.classList.contains('on')); return; }
        if (e.target.closest('[data-idea]')) {
          var list = PF.suggest(f.elements['category'].value); n = (n + 1) % list.length; f.elements['name'].value = list[n]; f.elements['name'].focus();
        }
      });
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        var v = UI.formData(f);
        if ((v.name || '').trim().length < 2) { f.elements['name'].focus(); UI.toast('Give your dish a name.', 'error'); return; }
        v.tags = Array.prototype.map.call(m.el.querySelectorAll('[data-tag].on'), function (b) { return b.getAttribute('data-tag'); });
        UI.busy(f.querySelector('[type=submit]'), call('dish_add', v)).then(function () { m.close(); UI.toast('On the menu. Thank you!', 'ok'); });
      });
    }
    function lock(key) {
      var p = V.party, st = V.stats;
      var pick = key || st.best || p.slots[0];
      var m = UI.modal('<div class="pf-label">' + esc(p.title) + '</div><h2>Lock in the day</h2><p class="muted">Everyone sees it right away, with a button to add it to their calendar.</p>' +
        '<form class="ui-stack" data-lockf><div class="ui-stack" style="gap:6px">' + p.slots.map(function (k) {
          var t = st.slots[k] || { yes: [], maybe: [] };
          return '<label class="ui-choice"><input type="radio" name="slot" value="' + esc(k) + '"' + (k === pick ? ' checked' : '') + '><span style="justify-content:space-between">' +
            '<b>' + esc(PF.slotLabel(k) + ', ' + PF.shortDate(PF.slot(k).d)) + '</b><small class="muted">' + t.yes.length + ' free · ' + t.maybe.length + ' maybe' + (k === st.best ? ' · best' : '') + '</small></span></label>';
        }).join('') + '</div><label class="ui-field" style="max-width:200px"><span>Starts at</span><input type="time" name="time" value="' + esc(PF.PARTS[PF.slot(pick).part].time) + '"></label>' +
        '<div class="ui-row end"><button type="button" class="ui-btn ghost" data-close>Not yet</button><button class="ui-btn primary" type="submit">' + UI.icon('lock') + 'Lock it in</button></div></form>');
      var f = m.el.querySelector('form');
      f.addEventListener('change', function (e) { if (e.target.name === 'slot') f.elements['time'].value = PF.PARTS[PF.slot(e.target.value).part].time; });
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        var v = UI.formData(f);
        UI.busy(f.querySelector('[type=submit]'), host('lock_slot', v.slot, v.time || null)).then(function () { m.close(); PF.confetti(); UI.toast('It\'s on! Your guests can see the day now.', 'ok'); });
      });
    }
    function needName() {
      var s = view.querySelector('#slip');
      if (s) s.scrollIntoView({ behavior: 'smooth', block: 'center' });
      var i = view.querySelector('[data-join] [name=name]');
      if (i) setTimeout(function () { i.focus(); }, 300);
      UI.toast('Put your name down first, then you\'re in.');
    }
    function rename() {
      var m = UI.modal('<h2>Change your name</h2><form class="ui-stack"><label class="ui-field"><span>Your name on this party</span><input type="text" name="name" maxlength="40" required value="' + esc(V.me.name) + '"></label>' +
        '<div class="ui-row end"><button type="button" class="ui-btn ghost" data-close>Cancel</button><button class="ui-btn primary" type="submit">Save</button></div></form>');
      var f = m.el.querySelector('form');
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        UI.busy(f.querySelector('[type=submit]'), call('guest_save', { name: f.elements['name'].value })).then(function () { UI.store.set('name', f.elements['name'].value.trim()); m.close(); UI.toast('Saved', 'ok'); });
      });
    }

    /* ---------------------------------------------------------------- clicks */
    var submitter = null;
    view.addEventListener('click', function (e) {
      var t = e.target.closest('button, a');
      if (!t) return;
      if (t.type === 'submit' && t.name === 'rsvp') { submitter = t.value; return; }
      var a = t.getAttribute.bind(t);
      if (t.hasAttribute('data-ans')) {
        var ch = {}; ch[a('data-slot')] = t.classList.contains('on') ? '' : a('data-ans');
        call('guest_save', { avail: ch }); return;
      }
      if (t.hasAttribute('data-rsvp')) { if (!t.classList.contains('on')) call('guest_save', { rsvp: a('data-rsvp') }).then(function () { UI.toast('RSVP saved', 'ok'); }); return; }
      if (t.hasAttribute('data-plus')) { call('guest_save', { plus: Math.max(0, Math.min(6, V.me.plus + +a('data-plus'))) }); return; }
      if (t.hasAttribute('data-diet')) {
        var d = V.me.diet.slice(), k = a('data-diet'), i = d.indexOf(k);
        if (i >= 0) d.splice(i, 1); else d.push(k);
        call('guest_save', { diet: d }); return;
      }
      if (t.hasAttribute('data-bring')) { bring(a('data-bring')); return; }
      if (t.hasAttribute('data-deldish')) {
        UI.confirm({ title: 'Take it off the menu?', ok: 'Remove', danger: true }).then(function (y) { if (y) call('dish_remove', a('data-deldish')); }); return;
      }
      if (t.hasAttribute('data-delnote')) {
        UI.confirm({ title: 'Delete this note?', ok: 'Delete', danger: true }).then(function (y) { if (y) call('comment_remove', a('data-delnote')); }); return;
      }
      if (t.hasAttribute('data-rename')) { rename(); return; }
      if (t.hasAttribute('data-forget')) {
        e.preventDefault();
        UI.confirm({ title: 'Take yourself off the list?', text: 'Your RSVP, your days, your dishes and your notes are deleted.', ok: 'Take me off', danger: true }).then(function (y) {
          if (y) call('guest_forget').then(function () { UI.store.set(key, null); secret = null; UI.toast('You\'re off the list. Maybe next time!'); });
        });
        return;
      }
      if (t.hasAttribute('data-copy')) { PF.copy(PF.partyUrl(V.party.token)); var box = view.querySelector('[data-linkbox]'); if (box) box.select(); return; }
      if (t.hasAttribute('data-share')) { navigator.share({ title: V.party.title, text: PF.inviteText(V.party).replace(PF.partyUrl(V.party.token), '').trim(), url: PF.partyUrl(V.party.token) }).catch(function () {}); return; }
      if (t.hasAttribute('data-ics')) { PF.downloadIcs(V.party); return; }
      if (t.hasAttribute('data-units')) { UI.store.set('units', a('data-units')); draw(); return; }
      if (t.hasAttribute('data-lock')) { lock(a('data-lock')); return; }
      if (t.hasAttribute('data-unlock')) {
        UI.confirm({ title: 'Change the day?', text: 'The day is unlocked and guests can answer again.', ok: 'Unlock' }).then(function (y) { if (y) host('lock_slot', null, null); }); return;
      }
      if (t.hasAttribute('data-status')) {
        var to = a('data-status');
        host('set_party_status', to).then(function () { UI.toast(to === 'closed' ? 'RSVPs closed. The guest list is final.' : 'RSVPs are open again.', 'ok'); }); return;
      }
      if (t.hasAttribute('data-kick')) {
        UI.confirm({ title: 'Remove this guest?', text: 'Their RSVP, dishes and notes are deleted. They can join again with the link.', ok: 'Remove', danger: true }).then(function (y) { if (y) host('host_remove_guest', a('data-kick')); }); return;
      }
      if (t.hasAttribute('data-dup') || t.hasAttribute('data-copy-sample')) {
        e.preventDefault();
        UI.api('duplicate_party', V.party.id).then(function (r) { UI.toast('A fresh copy is ready. Check the days and send it!', 'ok'); UI.go('edit', r.id); }); return;
      }
      if (t.hasAttribute('data-delete')) {
        UI.confirm({ title: 'Delete this party?', text: 'The guest list, menu and notes are deleted, and the link stops working. This can\'t be undone.', ok: 'Delete the party', danger: true }).then(function (y) {
          if (y) UI.api('remove_party', V.party.id).then(function () { PF.forget(token); UI.toast('Party deleted.'); UI.go('home'); });
        });
      }
    });
    view.addEventListener('submit', function (e) {
      e.preventDefault();
      var f = e.target;
      if (f.matches('[data-join]')) {
        var name = f.elements['name'].value.trim();
        if (!name) { f.elements['name'].focus(); UI.toast('Please tell the host your name.', 'error'); return; }
        var rsvp = submitter || 'yes'; submitter = null;
        UI.store.set('name', name);
        UI.busy(f.querySelector('[value=' + rsvp + ']'), call('guest_join', name, rsvp, 0)).then(function () {
          if (rsvp === 'yes') PF.confetti();
          UI.toast(rsvp === 'no' ? 'Thanks for letting them know.' : 'You\'re on the list! Now tick the days you\'re free.', 'ok');
        });
      } else if (f.matches('[data-comment]')) {
        var body = f.elements['body'].value.trim();
        if (!body) return;
        UI.busy(f.querySelector('[type=submit]'), call('comment_add', body)).then(function () { UI.toast('Posted', 'ok'); });
      }
    });

    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:320px"></div></div>';
    var ready = load(false).then(function () {
      if (V && V.is_host && UI.store.get('justMade') === token) {
        UI.store.set('justMade', null);
        PF.confetti();
        var box = view.querySelector('[data-linkbox]');
        if (box) { box.scrollIntoView({ block: 'center' }); box.select(); }
      }
    });
    timer = setInterval(function () {
      if (document.hidden || document.querySelector('.ui-modal-wrap')) return;
      var a = document.activeElement;
      if (a && /INPUT|TEXTAREA|SELECT/.test(a.tagName) && view.contains(a)) return;
      load(true).catch(function () {});
    }, 30000);
    return { ready: ready, destroy: function () { clearInterval(timer); } };
  });
})();

/* ===== plan.html ===== */
(function () {
  var esc = UI.esc;
  var PRESETS = ['Starters', 'Soup', 'Salad', 'Mains', 'Sides', 'Bread', 'Dessert', 'Drinks', 'Cheese', 'Snacks', 'Supplies'];
  var WEEK = 7 * 24 * 3600 * 1000;

  function fromIdea(i) {
    var st = { title: i.key === 'classic' ? '' : i.name, blurb: '', location: '', style: i.style, cover: i.cover, cap: '', idea: i.key,
      wx_place: UI.store.get('town', ''), outdoors: i.tags.indexOf('outdoor') >= 0,
      menu: i.menu.map(function (m) { return { name: m[0], wanted: m[1] }; }), slots: {} };
    var week = 0;
    var keys = function (w) { return i.slots.map(function (s) { return PF.slotKey(PF.friday(w), s[0], s[1]); }).filter(function (k) { return !PF.isPast(k); }); };
    var k = keys(0);
    if (!k.length) { week = 1; k = keys(1); }
    k.forEach(function (x) { st.slots[x] = true; });
    st.week = week;
    return st;
  }

  function mount(view, ctx, editing) {
    var st, weeks = [0, 1], answers = 0, partyId = editing ? ctx.args[0] : null;

    function draw() {
      var ideaBar = editing ? '' : '<div class="pf-label" style="margin-bottom:6px">Start from the catalogue</div><div class="pl-ideas" role="group" aria-label="Party ideas">' +
        PF.IDEAS.map(function (i) {
          return '<button type="button" data-idea="' + i.key + '" class="' + (st.idea === i.key ? 'on' : '') + '"><span class="pf-cover" style="padding:2px">' + PF.art(i.cover) + '</span>' + esc(i.name) + '</button>';
        }).join('') + '</div>';
      view.innerHTML = '<div class="ui-wrap" style="max-width:940px">' +
        '<div class="pl-head"><div><div class="pf-no">' + (editing ? esc(st.catalog_no || '') + ' · Changes to your order' : 'Order blank · Form PF-1') + '</div>' +
          '<h1>' + (editing ? 'Edit your party' : 'Host a party') + '</h1><p>' + (editing ? 'Guests see the changes as soon as you save.' : 'Fill it in, send the link, and the weekend plans itself.') + '</p></div>' +
          (editing ? '<a class="ui-btn" href="#p/' + esc(st.token) + '" data-go="p/' + esc(st.token) + '">' + UI.icon('back') + 'Back to the party</a>' : '<div class="pf-burst"><span><b>Free</b>no stamp needed</span></div>') + '</div>' +
        ideaBar +
        '<form class="pl-form" data-plan novalidate>' +
        box(1, 'Name your party', 'What should the invitation say?',
          '<label class="ui-field pl-title"><span>Party name</span><input type="text" name="title" maxlength="80" required placeholder="Soup Night Supper" value="' + esc(st.title) + '"></label>' +
          '<div class="ui-field"><span>Pick a picture</span><div class="pl-covers">' + Object.keys(PF.ART).map(function (k) {
            return '<label><input type="radio" name="cover" value="' + k + '"' + (st.cover === k ? ' checked' : '') + '><div class="pf-cover">' + PF.art(k) + '</div><span>' + esc(PF.COVER_NAMES[k]) + '</span></label>';
          }).join('') + '</div></div>') +
        box(2, 'When could it be?', 'Tick every slot that works for you. Your guests say which suit them, then you lock one in.',
          '<div class="ui-row between"><div class="ui-seg" data-weeks>' + weeks.map(function (w) {
            return '<button type="button" data-week="' + w + '" class="' + (st.week === w ? 'on' : '') + '">' + (w === 0 ? 'This weekend' : w === 1 ? 'Next weekend' : 'Weekend of') + ' · ' + esc(PF.weekendRange(PF.friday(w))) + '</button>';
          }).join('') + '</div><span class="pf-label" data-count></span></div>' +
          '<div class="pl-days" data-days></div><div class="pl-picked" data-picked></div>' +
          (answers ? '<p class="ui-note small" style="margin:0">' + UI.plural(answers, 'guest has', 'guests have').replace(' has', ' has') + ' answered already. Unticking a slot drops their answers for it.</p>' : '')) +
        box(3, 'The menu', 'What should people bring? Set how many of each you\'d like.',
          '<div class="pl-menu" data-menu></div>' +
          '<div class="ui-row"><input type="text" data-newcat maxlength="30" placeholder="Add a section, e.g. Pickles" style="flex:1;min-width:180px"><button type="button" class="ui-btn sm" data-addcat>' + UI.icon('plus') + 'Add</button></div>' +
          '<div class="pl-presets" data-presets></div>' +
          '<p class="ui-hint" style="margin:0">Guests can always add things under "Something else".</p>') +
        box(4, 'The particulars', 'Where, how, and how many.',
          '<div class="pl-styles">' + Object.keys(PF.STYLES).map(function (k) {
            return '<label class="ui-choice"><input type="radio" name="style" value="' + k + '"' + (st.style === k ? ' checked' : '') + '><span><b>' + esc(PF.STYLES[k][0]) + '</b><small>' + esc(PF.STYLES[k][1]) + '</small></span></label>';
          }).join('') + '</div>' +
          '<div class="pl-two"><label class="ui-field"><span>Where <em>(optional)</em></span><input type="text" name="location" maxlength="120" placeholder="My place, 3rd floor" value="' + esc(st.location) + '"></label>' +
          '<label class="ui-field"><span>Seats at the table <em>(optional)</em></span><input type="number" name="cap" min="2" max="100" placeholder="No limit" value="' + esc(st.cap || '') + '"></label></div>' +
          '<div class="pl-two"><div class="ui-field"><span>Town for the weather check <em>(optional)</em></span>' +
            '<div class="ui-row" style="flex-wrap:nowrap"><input type="text" name="wx_place" maxlength="80" placeholder="Montréal" value="' + esc(st.wx_place || '') + '" style="flex:1">' +
            '<button type="button" class="ui-btn sm" data-wxcheck>' + UI.icon('sun') + 'Check</button></div><p class="ui-hint" data-wxres>Just the town name. We show the forecast for each slot.</p></div>' +
            '<label class="ui-check" style="align-self:center"><input type="checkbox" name="outdoors"' + (st.outdoors ? ' checked' : '') + '><span><b>It\'s outdoors</b> (garden, rooftop, park). ' +
            'The weather check flags the driest day and plans for rain.</span></label></div>' +
          '<label class="ui-field"><span>A note for your guests <em>(optional)</em></span><textarea name="blurb" maxlength="1000" rows="3" placeholder="Come hungry. Bring a sweater, the garden gets cold.">' + esc(st.blurb) + '</textarea></label>') +
        '<div data-msg hidden></div>' +
        '<div class="pl-submit"><p>' + (editing ? 'Everyone with the link sees your changes.' : 'Next: you get one link to send to everyone.') + '</p>' +
          '<button class="ui-btn primary lg" type="submit">' + (editing ? UI.icon('check') + 'Save changes' : 'Send my order ' + UI.icon('arrow')) + '</button></div>' +
        '</form></div>';
      days(); menu();
    }
    function box(n, title, hint, body) {
      return '<section class="pl-box"><h2><span class="n">' + n + '</span>' + esc(title) + ' <small>' + esc(hint) + '</small></h2><div class="pl-body">' + body + '</div></section>';
    }
    function days() {
      var fri = PF.friday(st.week), names = ['Friday', 'Saturday', 'Sunday'];
      view.querySelector('[data-days]').innerHTML = PF.DAY_PARTS.map(function (parts, d) {
        var date = PF.addDays(fri, d);
        return '<div class="pl-day"><h3>' + names[d] + ' <small>' + esc(PF.shortDate(date)) + '</small></h3><div class="opts">' + parts.map(function (p) {
          var key = PF.slotKey(fri, d, p), past = PF.isPast(key), on = !!st.slots[key];
          return '<label class="pl-opt' + (past && !on ? ' off' : '') + '"><input type="checkbox" data-slot="' + key + '"' + (on ? ' checked' : '') + (past && !on ? ' disabled' : '') + '>' +
            '<b>' + esc(PF.partLabel(p)) + '</b><span>' + esc(PF.timeLabel(PF.PARTS[p].time)) + '</span></label>';
        }).join('') + '</div></div>';
      }).join('');
      picked();
    }
    function picked() {
      var keys = Object.keys(st.slots).filter(function (k) { return st.slots[k]; }).sort();
      view.querySelector('[data-count]').textContent = keys.length ? UI.plural(keys.length, 'slot') + ' ticked' : 'Nothing ticked yet';
      var fri = PF.iso(PF.friday(st.week)), last = PF.iso(PF.addDays(PF.friday(st.week), 2));
      var other = keys.filter(function (k) { var d = k.split('|')[0]; return d < fri || d > last; });
      view.querySelector('[data-picked]').innerHTML = other.length ? '<span class="pf-label">Also ticked:</span>' + other.map(function (k) {
        return '<button type="button" class="ui-btn sm" data-unslot="' + esc(k) + '">' + esc(PF.slotLabel(k) + ', ' + PF.shortDate(PF.slot(k).d)) + ' ' + UI.icon('x') + '</button>';
      }).join('') : '';
    }
    function menu() {
      view.querySelector('[data-menu]').innerHTML = st.menu.length ? st.menu.map(function (m, i) {
        return '<div class="pl-mrow" data-row="' + i + '"><input type="text" data-catname maxlength="30" value="' + esc(m.name) + '" aria-label="Menu section">' +
          '<div class="pl-step" aria-label="How many"><button type="button" data-step="-1" aria-label="Fewer">−</button><output>' + m.wanted + '</output><button type="button" data-step="1" aria-label="More">+</button></div>' +
          '<button type="button" class="ui-btn ghost icon" data-delcat aria-label="Remove ' + esc(m.name) + '">' + UI.icon('trash') + '</button></div>';
      }).join('') : '<p class="muted" style="margin:0">No sections yet. Add some below, or leave it open and guests bring "something else".</p>';
      var have = st.menu.map(function (m) { return m.name.toLowerCase(); });
      view.querySelector('[data-presets]').innerHTML = PRESETS.filter(function (p) { return have.indexOf(p.toLowerCase()) < 0; }).map(function (p) {
        return '<button type="button" class="ui-btn sm" data-preset="' + esc(p) + '">+ ' + esc(p) + '</button>';
      }).join('');
    }
    function addCat(name) {
      name = (name || '').trim().slice(0, 30);
      if (!name) return;
      if (st.menu.some(function (m) { return m.name.toLowerCase() === name.toLowerCase(); })) { UI.toast('That section is already on the menu.'); return; }
      if (st.menu.length >= 14) { UI.toast('That\'s plenty of sections (14 at most).', 'error'); return; }
      st.menu.push({ name: name, wanted: 1 }); menu();
    }

    view.addEventListener('click', function (e) {
      var t;
      if ((t = e.target.closest('[data-idea]'))) { st = fromIdea(PF.idea(t.getAttribute('data-idea'))); history.replaceState(null, '', '#new/' + st.idea); draw(); return; }
      if ((t = e.target.closest('[data-week]'))) { st.week = +t.getAttribute('data-week'); view.querySelectorAll('[data-week]').forEach(function (b) { b.classList.toggle('on', b === t); }); days(); return; }
      if ((t = e.target.closest('[data-unslot]'))) { delete st.slots[t.getAttribute('data-unslot')]; days(); return; }
      if ((t = e.target.closest('[data-step]'))) {
        var i = +t.closest('[data-row]').getAttribute('data-row');
        st.menu[i].wanted = Math.max(0, Math.min(20, st.menu[i].wanted + +t.getAttribute('data-step')));
        t.parentNode.querySelector('output').textContent = st.menu[i].wanted; return;
      }
      if ((t = e.target.closest('[data-delcat]'))) { st.menu.splice(+t.closest('[data-row]').getAttribute('data-row'), 1); menu(); return; }
      if ((t = e.target.closest('[data-preset]'))) { addCat(t.getAttribute('data-preset')); return; }
      if ((t = e.target.closest('[data-wxcheck]'))) {
        var res = view.querySelector('[data-wxres]'), q = (st.wx_place || '').trim();
        if (!q) { res.textContent = 'Type a town first.'; return; }
        UI.busy(t, UI.api('weather_lookup', q)).then(function (r) { res.innerHTML = UI.icon('check') + ' Found: <b>' + esc(r.place) + '</b>'; },
          function (err) { res.innerHTML = '<span style="color:var(--c-bad)">' + esc(err.message) + '</span>'; });
        return;
      }
      if (e.target.closest('[data-addcat]')) { var inp = view.querySelector('[data-newcat]'); addCat(inp.value); inp.value = ''; inp.focus(); }
    });
    view.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && e.target.matches('[data-newcat]')) { e.preventDefault(); addCat(e.target.value); e.target.value = ''; }
    });
    view.addEventListener('change', function (e) {
      var t = e.target;
      if (t.matches('[data-slot]')) { if (t.checked) st.slots[t.getAttribute('data-slot')] = true; else delete st.slots[t.getAttribute('data-slot')]; picked(); }
      if (t.name === 'cover') st.cover = t.value;
      if (t.name === 'style') st.style = t.value;
      if (t.name === 'outdoors') st.outdoors = t.checked;
    });
    view.addEventListener('input', function (e) {
      var t = e.target;
      if (t.matches('[data-catname]')) st.menu[+t.closest('[data-row]').getAttribute('data-row')].name = t.value;
      else if (['title', 'location', 'cap', 'blurb', 'wx_place'].indexOf(t.name) >= 0) st[t.name] = t.value;
    });
    view.addEventListener('submit', function (e) {
      e.preventDefault();
      var f = e.target, msg = view.querySelector('[data-msg]');
      var slots = Object.keys(st.slots).filter(function (k) { return st.slots[k]; });
      var problem = st.title.trim().length < 2 ? 'Give your party a name (section 1).' : !slots.length ? 'Tick at least one day and time (section 2).' : null;
      if (problem) { msg.className = 'ui-error'; msg.textContent = problem; msg.hidden = false; msg.scrollIntoView({ block: 'center', behavior: 'smooth' }); return; }
      msg.hidden = true;
      var wanted = {}, cats = [];
      st.menu.forEach(function (m) { if (m.name.trim()) { cats.push(m.name.trim()); wanted[m.name.trim()] = m.wanted; } });
      var data = { title: st.title, blurb: st.blurb, location: st.location, style: st.style, cover: st.cover, cap: st.cap ? +st.cap : null,
        slots: slots, categories: cats, wanted: wanted, wx_place: (st.wx_place || '').trim(), outdoors: !!st.outdoors };
      var call = editing ? UI.api('update_party', partyId, data) : UI.api('create_party', data);
      UI.busy(f.querySelector('[type=submit]'), call).then(function (r) {
        if (!editing) { UI.store.set('justMade', r.token); }
        if (data.wx_place) UI.store.set('town', data.wx_place);
        if (r.note) setTimeout(function () { UI.toast(r.note); }, 600);
        UI.toast(editing ? 'Saved. Your guests see the changes.' : 'Your party is in print! Now send the link.', 'ok');
        UI.go('p', r.token);
      }, function (err) { msg.className = 'ui-error'; msg.textContent = err.message; msg.hidden = false; });
    });

    if (editing) {
      view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:300px"></div></div>';
      return UI.api('get_party_form', partyId).then(function (r) {
        var p = r.party;
        answers = p.answers || 0;
        st = { title: p.title, blurb: p.blurb, location: p.location, style: p.style, cover: p.cover, cap: p.cap || '', token: p.token, catalog_no: p.catalog_no,
          wx_place: p.wx_place || '', outdoors: !!p.outdoors,
          menu: p.categories.map(function (c) { return { name: c, wanted: p.wanted[c] == null ? 1 : p.wanted[c] }; }), slots: {} };
        p.slots.forEach(function (k) { st.slots[k] = true; });
        var w = p.slots.length ? Math.round((PF.friday(0, PF.slot(p.slots[0]).d) - PF.friday(0)) / WEEK) : 0;
        st.week = w;
        if (weeks.indexOf(w) < 0) weeks = [w].concat(weeks);
        draw();
      });
    }
    st = fromIdea(PF.idea(ctx.args[0]) || PF.idea('classic'));
    if (!PF.idea(ctx.args[0])) st.idea = null;
    draw();
  }

  UI.page('new', { title: 'Host a party', nav: 'Host', icon: 'plus', auth: 'user', order: 30 }, function (view, ctx) { return mount(view, ctx, false); });
  UI.page('edit', { title: 'Edit your party', auth: 'user' }, function (view, ctx) { return mount(view, ctx, true); });
})();

/* ===== profile.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('profile', { title: 'Your profile', auth: 'user' }, function (view, ctx) {
    var me = ctx.me;
    view.innerHTML = '<div class="ui-wrap ui-narrow"><div class="pf-head"><span class="ui-avatar">' + esc(UI.initials(me.name)) + '</span>' +
      '<div><h1>' + esc(me.name) + '</h1><div class="muted">' + esc(me.email) + (me.joined ? ' · member since ' + esc(UI.fmtDate(me.joined, { month: 'long', year: 'numeric' })) : '') + '</div></div></div>' +
      '<div class="pf-grid"><form class="ui-card ui-stack" data-name><h3>Your name</h3><label class="ui-field"><span>Shown to other people</span>' +
      '<input type="text" name="name" value="' + esc(me.name) + '" maxlength="60" required></label><button class="ui-btn primary" type="submit">Save</button></form>' +
      '<div class="ui-card ui-stack"><h3>Appearance</h3><p class="muted small">Follow your device, or pick one.</p><div data-theme-box></div>' +
      '<h3 style="margin-top:22px">Password</h3><p class="muted small">We\'ll email you a link to choose a new one.</p>' +
      '<button class="ui-btn" data-reset>' + UI.icon('mail') + 'Email me a reset link</button></div></div>' +
      '<div class="ui-card" style="margin-top:16px"><div class="pf-links">' +
      (me.is_admin ? '<a href="#admin" data-go="admin">' + UI.icon('shield') + 'Admin</a>' : '') +
      '<button data-feedback>' + UI.icon('chat') + 'Send feedback</button>' +
      '<button data-lk-open="overview">' + UI.icon('lock') + 'Privacy &amp; Terms, and your data</button>' +
      '<button data-signout-here>' + UI.icon('logout') + 'Sign out</button></div></div></div>';
    function themeBox() {
      var t = UI.theme();
      view.querySelector('[data-theme-box]').innerHTML = '<div class="ui-seg">' + [['auto', 'Auto'], ['light', 'Light'], ['dark', 'Dark']].map(function (o) {
        return '<button type="button" data-theme-pick="' + o[0] + '" class="' + (t === o[0] ? 'on' : '') + '">' + o[1] + '</button>';
      }).join('') + '</div>';
    }
    themeBox();
    view.addEventListener('click', function (e) {
      var t = e.target.closest('[data-theme-pick]');
      if (t) { UI.setTheme(t.getAttribute('data-theme-pick')); themeBox(); UI.renderChrome(); return; }
      if (e.target.closest('[data-reset]')) {
        UI.busy(e.target.closest('[data-reset]'), UI.auth('reset', { email: me.email })).then(function (r) { UI.toast(r.message, 'ok'); });
      }
      if (e.target.closest('[data-signout-here]')) UI.auth('logout');
    });
    view.querySelector('[data-name]').addEventListener('submit', function (e) {
      e.preventDefault();
      var v = UI.formData(e.target);
      UI.busy(e.target.querySelector('[type=submit]'), UI.api('update_profile', v.name)).then(function (r) {
        UI.setMe(r.me); ctx.me = r.me; UI.toast('Saved', 'ok');
        view.querySelector('.pf-head h1').textContent = r.me.name;
      });
    });
  });
})();

/* ===== sheet.html ===== */
(function () {
  var esc = UI.esc;
  UI.page('sheet', { title: 'Order sheet' }, function (view, ctx) {
    var token = ctx.args[0] || '';
    view.innerHTML = '<div class="ui-wrap"><div class="ui-skel" style="height:300px"></div></div>';
    return UI.api('party_view', token, UI.store.get('g.' + token, null)).then(function (r) {
      if (r.missing) { view.innerHTML = '<div class="ui-wrap"><div class="ui-empty"><h3>We couldn\'t find that party</h3></div></div>'; return; }
      var V = r.view, p = V.party, st = V.stats;
      var coming = V.guests.filter(function (g) { return g.rsvp === 'yes'; }), maybe = V.guests.filter(function (g) { return g.rsvp === 'maybe'; });
      var cats = p.categories.filter(function (c) { return (st.menu[c] || {}).wanted || V.dishes.some(function (d) { return d.category === c; }); });
      view.innerHTML = '<div class="ui-wrap sh-wrap"><div class="sh-tools no-print"><a class="ui-btn" href="#p/' + esc(token) + '" data-go="p/' + esc(token) + '">' + UI.icon('back') + 'Back to the party</a>' +
        '<button class="ui-btn primary" data-print>' + UI.icon('print') + 'Print it</button></div>' +
        '<article class="sh-page"><div class="sh-top"><div><div class="pf-no">Order sheet · ' + esc(p.catalog_no || '') + '</div><h1>' + esc(p.title) + '</h1>' +
          '<div class="pf-label">' + (p.chosen ? esc(PF.whenText(p)) : 'Day to be decided' + (st.best ? ' · leading: ' + esc(PF.slotLabel(st.best)) : '')) + '</div></div>' +
          '<div class="pf-cover">' + PF.art(p.cover) + '</div></div>' +
        '<div class="sh-facts">' +
          '<div class="pf-leader"><span class="a">Host</span><span class="dots"></span><span class="b">' + esc(p.host_name) + '</span></div>' +
          '<div class="pf-leader"><span class="a">Where</span><span class="dots"></span><span class="b">' + esc(p.location || 'Ask the host') + '</span></div>' +
          '<div class="pf-leader"><span class="a">Seats taken</span><span class="dots"></span><span class="b">' + st.heads + (p.cap ? ' of ' + p.cap : '') + '</span></div>' +
          '<div class="pf-leader"><span class="a">Maybe</span><span class="dots"></span><span class="b">' + maybe.length + '</span></div>' +
          (V.weather && V.weather.slots[p.chosen || st.best] ? '<div class="pf-leader"><span class="a">Weather</span><span class="dots"></span><span class="b">' +
            PF.wxChip(V.weather.slots[p.chosen || st.best]) + ' ' + esc(PF.advice(V.weather.slots[p.chosen || st.best], V.weather.outdoors)) + '</span></div>' : '') +
          Object.keys(st.diets).map(function (k) { return '<div class="pf-leader"><span class="a">' + esc(PF.dietLabel(k)) + '</span><span class="dots"></span><span class="b">' + st.diets[k] + '</span></div>'; }).join('') +
        '</div>' +
        cats.map(function (c) {
          var ds = V.dishes.filter(function (d) { return d.category === c; }), m = st.menu[c] || { wanted: 0, have: 0 }, gaps = '';
          for (var i = ds.length; i < m.wanted; i++) gaps += '<tr class="want"><td class="box"><i></i></td><td>Still wanted</td><td class="who">—</td></tr>';
          return '<table class="sh-table"><caption>' + esc(c) + '</caption><tbody>' + ds.map(function (d) {
            return '<tr><td class="box"><i></i></td><td><b>' + esc(d.name) + '</b>' + (d.tags.length ? ' <span class="small muted">(' + esc(d.tags.map(PF.tagLabel).join(', ')) + ')</span>' : '') +
              (d.note ? '<div class="small muted">' + esc(d.note) + '</div>' : '') + '</td><td class="who">' + esc(d.by) + (d.serves ? ' · serves ' + d.serves : '') + '</td></tr>';
          }).join('') + gaps + '</tbody></table>';
        }).join('') +
        '<table class="sh-table"><caption>Coming (' + st.heads + ')</caption></table><ul class="sh-guests">' + coming.map(function (g) {
          return '<li>☐ ' + esc(g.name) + (g.plus ? ' +' + g.plus : '') + (g.diet.length ? ' <span class="small muted">· ' + esc(g.diet.map(PF.dietLabel).join(', ')) + '</span>' : '') + '</li>';
        }).join('') + maybe.map(function (g) { return '<li class="muted">☐ ' + esc(g.name) + ' (maybe)</li>'; }).join('') + '</ul>' +
        '<p class="sh-foot">Printed from Plan Friday · ' + esc(PF.partyUrl(token).replace(/^https?:\/\//, '')) + '</p></article></div>';
      view.querySelector('[data-print]').addEventListener('click', function () { window.print(); });
    });
  });
})();
