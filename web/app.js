/* Icon Hub — 本地图标库前端逻辑（无依赖） */
(function () {
  'use strict';

  var DATA = window.ICON_HUB;
  if (!DATA) {
    document.body.innerHTML =
      '<p style="padding:40px;font-family:sans-serif">找不到数据文件：web/data/catalog.js\n先运行 scripts/export_web.py</p>';
    return;
  }

  var STR = {
    en: {
      tagline: function (s) { return s.icons + ' icons · ' + s.categories + ' categories · ' + s.sources + ' source'; },
      categories: 'Categories', all: 'All icons',
      size: 'Size', stroke: 'Stroke', color: 'Color',
      copySvg: 'Copy SVG', copyJsx: 'Copy JSX', copyName: 'Copy name', download: 'Download .svg',
      source: 'Source', tags: 'Tags', aliases: 'Aliases', meta: 'Meta',
      searchPh: 'Search by name, alias, tag… (press /)',
      results: function (n, total, q) { return n + ' / ' + total + ' icons' + (q ? ' · "' + q + '"' : ''); },
      showing: function (n) { return 'showing first ' + n; },
      emptyTitle: 'No icons match', emptyHint: 'Try another keyword or clear the category filter.',
      copied: 'Copied to clipboard', copyFail: 'Copy failed — select manually',
      pending: 'translation pending', deprecated: 'deprecated',
      allIcons: 'All icons', sourceList: 'Source', metaText: function (b) { return b + ' bytes'; },
      customizer: 'Customizer', strokeWidth: 'Stroke width', nonScaling: 'Non-scaling stroke',
      reset: 'Reset', resetDone: 'Restored to default'
    },
    zh: {
      tagline: function (s) { return s.icons + ' 个图标 · ' + s.categories + ' 个分类 · ' + s.sources + ' 个源'; },
      categories: '分类', all: '全部图标',
      size: '尺寸', stroke: '线宽', color: '颜色',
      copySvg: '复制 SVG', copyJsx: '复制 JSX', copyName: '复制名称', download: '下载 .svg',
      source: '来源', tags: '标签', aliases: '别名', meta: '信息',
      searchPh: '按名称 / 别名 / 标签搜索…（按 / 聚焦）',
      results: function (n, total, q) { return n + ' / ' + total + ' 个图标' + (q ? ' · "' + q + '"' : ''); },
      showing: function (n) { return '仅显示前 ' + n + ' 个'; },
      emptyTitle: '没有匹配的图标', emptyHint: '换个关键词，或清除左侧分类筛选。',
      copied: '已复制到剪贴板', copyFail: '复制失败，请手动选择',
      pending: '待译', deprecated: '已废弃',
      allIcons: '全部图标', sourceList: '图标源', metaText: function (b) { return b + ' 字节'; },
      customizer: '自定义', strokeWidth: '描边宽度', nonScaling: '非缩放描边',
      reset: '重置', resetDone: '已恢复默认值'
    }
  };

  var CZ_DEFAULT = { color: '#18181b', stroke: 2, size: 28, nonScaling: false };

  var state = {
    lang: (DATA.defaultLanguage === 'zh' ? 'zh' : 'en'),
    q: '',
    cat: '__all__',
    active: null,
    color: '#18181b',
    cz: {
      color: CZ_DEFAULT.color,
      stroke: CZ_DEFAULT.stroke,
      size: CZ_DEFAULT.size,
      nonScaling: CZ_DEFAULT.nonScaling
    }
  };

  /* ---------- 索引 ---------- */
  /** 图标的唯一标识 = 源 + 名。两源会有同名图标（user / settings / arrow-left…） */
  function idOf(ic) { return ic.source + ':' + ic.name; }

  var byName = new Map();
  DATA.icons.forEach(function (ic) { byName.set(idOf(ic), ic); });
  function idOfCat(c) { return c.source + ':' + c.key; }

  var byCat = new Map();
  DATA.categories.forEach(function (c) { byCat.set(idOfCat(c), c); });
  var byTag = new Map();
  DATA.tags.forEach(function (t) { byTag.set(t.key, t); });

  /* ---------- 元素 ---------- */
  var $ = function (id) { return document.getElementById(id); };
  var grid = $('grid'), catList = $('catList'), empty = $('empty');
  var drawer = $('drawer'), scrim = $('scrim'), toastEl = $('toast');
  var searchInput = $('search');

  function t(key) { return STR[state.lang][key]; }

  /** 双语字段取值：目标语言为空时回退英文 */
  function localize(field) {
    if (!field) return '';
    return field[state.lang] || field.en || '';
  }
  function isPending(field) {
    return state.lang === 'zh' && !!field && !!field.en && !field.zh;
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ---------- 顶部 / 文案 ---------- */
  function renderChrome() {
    $('brandStats').textContent = t('tagline')(DATA.stats);
    searchInput.placeholder = t('searchPh');
    document.documentElement.lang = state.lang === 'zh' ? 'zh-CN' : 'en';
    Array.prototype.forEach.call(document.querySelectorAll('[data-i18n]'), function (el) {
      var k = el.getAttribute('data-i18n');
      if (STR[state.lang][k]) el.textContent = STR[state.lang][k];
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-i18n-title]'), function (el) {
      var k = el.getAttribute('data-i18n-title');
      if (STR[state.lang][k]) el.title = STR[state.lang][k];
    });
    Array.prototype.forEach.call(document.querySelectorAll('#langSwitch button'), function (b) {
      b.classList.toggle('on', b.getAttribute('data-lang') === state.lang);
    });
    Array.prototype.forEach.call(document.querySelectorAll('[data-copy]'), function (b) {
      var k = 'copy' + b.getAttribute('data-copy').replace(/^./, function (c) { return c.toUpperCase(); });
      if (b.getAttribute('data-copy') === 'file') k = 'download';
      if (STR[state.lang][k]) b.textContent = STR[state.lang][k];
    });
  }

  /* ---------- 左栏分类 ---------- */
  /** 分类的唯一标识 = 源 + key。两源可能有同名分类（animals/arrows/design…），只比 key 会跨源误命中 */
  function catKey(c) { return c.source + ':' + c.key; }

  function renderCategories() {
    var html = catRow('__all__', t('all'), DATA.stats.icons);
    var multi = DATA.sources.length > 1;
    DATA.sources.forEach(function (src) {
      var cats = DATA.categories
        .filter(function (c) { return c.source === src.key; })
        .sort(function (a, b) { return a.order - b.order; });
      if (!cats.length) return;
      if (multi) {
        html += '<div class="cat-sep">' + esc(localize(src.name)) +
                '<span class="cat-num">' + cats.length + '</span></div>';
      }
      cats.forEach(function (c) { html += catRow(catKey(c), localize(c.title), c.count); });
    });
    catList.innerHTML = html;
    $('sideCount').textContent = DATA.categories.length;
  }

  function catRow(key, label, count) {
    return '<button class="cat' + (state.cat === key ? ' on' : '') + '" data-cat="' + esc(key) + '">' +
      '<span class="cat-name">' + esc(label) + '</span>' +
      '<span class="cat-num">' + count + '</span></button>';
  }

  /* ---------- 网格 ---------- */
  var zhTagList = null, zhCatList = null;
  var zhCache = new Map();

  function ensureZhIndex() {
    if (zhTagList) return;
    zhTagList = [];
    DATA.tags.forEach(function (t) { if (t.label && t.label.zh) zhTagList.push({ key: t.key, zh: t.label.zh }); });
    zhCatList = [];
    DATA.categories.forEach(function (c) { if (c.title && c.title.zh) zhCatList.push({ key: c.key, zh: c.title.zh }); });
  }

  /** 中文关键词 → 命中的中文标签/分类 key 集合（让中文界面也能用中文搜） */
  function zhHits(word) {
    if (zhCache.has(word)) return zhCache.get(word);
    ensureZhIndex();
    var tags = new Set(), cats = new Set(), i;
    for (i = 0; i < zhTagList.length; i++) {
      if (zhTagList[i].zh.indexOf(word) !== -1) tags.add(zhTagList[i].key);
    }
    for (i = 0; i < zhCatList.length; i++) {
      if (zhCatList[i].zh.indexOf(word) !== -1) cats.add(zhCatList[i].key);
    }
    var r = { tags: tags, cats: cats };
    zhCache.set(word, r);
    return r;
  }

  function filtered() {
    var q = state.q.trim().toLowerCase();
    var words = q ? q.split(/\s+/) : [];
    var plans = words.map(function (w) { return { w: w, zh: zhHits(w) }; });

    // 分类筛选用「源:key」复合键
    var catSrc = null, catKeyName = null;
    if (state.cat !== '__all__') {
      var sep = state.cat.indexOf(':');
      catSrc = state.cat.slice(0, sep);
      catKeyName = state.cat.slice(sep + 1);
    }

    return DATA.icons.filter(function (ic) {
      if (catSrc && (ic.source !== catSrc || ic.categories.indexOf(catKeyName) === -1)) return false;
      if (!plans.length) return true;
      var hay = (ic.name + ' ' + ic.aliases.join(' ') + ' ' + ic.tags.join(' ') + ' ' + ic.categories.join(' ')).toLowerCase();
      return plans.every(function (p) {
        if (hay.indexOf(p.w) !== -1) return true;
        if (p.zh.tags.size && ic.tags.some(function (t) { return p.zh.tags.has(t); })) return true;
        if (p.zh.cats.size && ic.categories.some(function (c) { return p.zh.cats.has(c); })) return true;
        return false;
      });
    });
  }

  var RENDER_LIMIT = 800;   // 首屏最多渲染多少个；超出靠搜索/分类缩小范围

  function renderGrid() {
    var list = filtered();
    var shown = list.length > RENDER_LIMIT ? list.slice(0, RENDER_LIMIT) : list;
    var q = state.q.trim();
    $('resultInfo').textContent = t('results')(list.length, DATA.stats.icons, q) +
      (shown.length < list.length ? ' · ' + t('showing')(shown.length) : '');

    if (!list.length) {
      grid.innerHTML = '';
      empty.hidden = false;
      empty.innerHTML = '<h3 style="margin:0 0 6px;font-size:15px">' + esc(t('emptyTitle')) + '</h3>' +
        '<div>' + esc(t('emptyHint')) + '</div>';
      return;
    }
    empty.hidden = true;

    var multi = DATA.sources.length > 1;
    var tip = function (ic) {
      var parts = [ic.source + ' · ' + ic.name];
      if (ic.tags.length) parts.push('tags: ' + ic.tags.join(', '));
      if (ic.aliases.length) parts.push('aliases: ' + ic.aliases.join(', '));
      return parts.join('  |  ');
    };

    var html = '';
    for (var i = 0; i < shown.length; i++) {
      var ic = shown[i];
      html += '<button class="cell' + (state.active === idOf(ic) ? ' on' : '') +
        '" data-name="' + esc(idOf(ic)) + '" title="' + esc(tip(ic)) + '">' +
        '<span class="cell-icon">' + ic.svg + '</span>' +
        '<span class="cell-name">' + esc(ic.name) + '</span>' +
        (multi ? '<span class="cell-src">' + esc(ic.source) + '</span>' : '') +
        '</button>';
    }
    grid.innerHTML = html;
  }

  /* ---------- 详情抽屉 ---------- */
  function iconMarkup(ic, size, stroke, color) {
    return ic.svg
      .replace(/width="[\d.]+"/, 'width="' + size + '"')
      .replace(/height="[\d.]+"/, 'height="' + size + '"')
      .replace(/stroke-width="[\d.]+"/, 'stroke-width="' + stroke + '"')
      .replace(/stroke="currentColor"/g, 'stroke="' + color + '"');
  }

  function toJsx(svg, size, stroke) {
    return svg
      .replace(/\sclass="[^"]*"/g, '')
      .replace(/stroke-width=/g, 'strokeWidth=')
      .replace(/stroke-linecap=/g, 'strokeLinecap=')
      .replace(/stroke-linejoin=/g, 'strokeLinejoin=')
      .replace(/\swidth="[\d.]+"/, ' width={' + size + '}')
      .replace(/\sheight="[\d.]+"/, ' height={' + size + '}')
      .replace(/strokeWidth="[\d.]+"/g, 'strokeWidth={' + stroke + '}')
      .replace(/<svg/, '\n<svg')
      .replace(/><path/, '>\n  <path')
      .replace(/></g, '>\n  <');
  }

  function chip(label, kind, key, pending) {
    return '<button class="chip' + (pending ? ' pending' : '') + '" data-' + kind + '="' + esc(key) + '">' +
      esc(label) + (pending ? ' · ' + esc(t('pending')) : '') + '</button>';
  }

  function renderDetail() {
    var ic = byName.get(state.active);
    if (!ic) { closeDetail(); return; }
    $('dName').textContent = ic.name;
    $('dPreview').innerHTML = iconMarkup(ic, +$('dSize').value, +$('dStroke').value / 10, state.color);

    var src = DATA.sources.filter(function (s) { return s.key === ic.source; })[0];
    $('dSource').innerHTML = src
      ? chip(localize(src.name), 'src', src.key, isPending(src.name))
      : '';

    $('dCats').innerHTML = ic.categories.map(function (k) {
      var c = byCat.get(ic.source + ':' + k);
      return c ? chip(localize(c.title), 'cat', idOfCat(c), isPending(c.title)) : '';
    }).join('') || '<span class="muted">—</span>';

    $('dTags').innerHTML = ic.tags.slice().sort().map(function (k) {
      var tg = byTag.get(k);
      var label = tg ? localize(tg.label) : k;
      return chip(label, 'tag', k, tg ? isPending(tg.label) : false);
    }).join('') || '<span class="muted">—</span>';

    if (ic.aliases.length) {
      $('dAliasRow').hidden = false;
      $('dAliases').innerHTML = ic.aliases.map(function (a) { return chip(a, 'alias', a); }).join('');
    } else {
      $('dAliasRow').hidden = true;
    }

    var pcat = ic.primaryCategory ? byCat.get(ic.source + ':' + ic.primaryCategory) : null;
    $('dMeta').innerHTML =
      esc(ic.source) + ' · ' + t('metaText')(ic.bytes) +
      (ic.deprecated ? ' · <strong>' + esc(t('deprecated')) + '</strong>' : '') +
      (pcat ? ' · ' + esc(localize(pcat.title)) : '');
  }

  function openDetail(name) {
    state.active = name;
    closeCz();
    drawer.hidden = false;
    scrim.hidden = false;
    renderDetail();
    var on = grid.querySelector('.cell.on');
    if (on) on.classList.add('on');
  }

  function closeDetail() {
    state.active = null;
    drawer.hidden = true;
    scrim.hidden = true;
    Array.prototype.forEach.call(grid.querySelectorAll('.cell.on'), function (el) { el.classList.remove('on'); });
  }

  /* ---------- Customizer（控制整个网格的显示外观） ---------- */
  function normalizeHex(v) {
    v = String(v).trim().replace(/^#/, '');
    if (/^[0-9a-f]{3}$/i.test(v)) v = v[0] + v[0] + v[1] + v[1] + v[2] + v[2];
    return /^[0-9a-f]{6}$/i.test(v) ? '#' + v.toLowerCase() : null;
  }

  function paintRange(el) {
    var min = +el.min, max = +el.max, v = +el.value;
    var p = max > min ? ((v - min) / (max - min)) * 100 : 0;
    el.style.background = 'linear-gradient(90deg, var(--accent) ' + p + '%, #ececf0 ' + p + '%)';
  }

  /** 把 cz 状态写进 CSS 变量；不回写 hex 输入框（避免打断正在输入的手感） */
  function applyCustomizer() {
    var root = document.documentElement.style;
    root.setProperty('--icon-size', state.cz.size + 'px');
    root.setProperty('--icon-stroke', state.cz.stroke);
    root.setProperty('--icon-color', state.cz.color);
    grid.classList.toggle('non-scaling', state.cz.nonScaling);

    $('czSize').value = state.cz.size;
    $('czSizeOut').textContent = state.cz.size + 'px';
    $('czStroke').value = Math.round(state.cz.stroke * 10);
    $('czStrokeOut').textContent = state.cz.stroke + 'px';
    $('czColor').value = state.cz.color;
    $('czNonScaling').setAttribute('aria-checked', String(state.cz.nonScaling));
    paintRange($('czSize'));
    paintRange($('czStroke'));
  }

  /** 完整同步：CSS 变量 + 全部控件（含 hex 文本框） */
  function syncCzControls() {
    applyCustomizer();
    $('czHex').value = state.cz.color;
  }

  function openCz() {
    $('cz').hidden = false;
    $('czToggle').classList.add('on');
    $('czToggle').setAttribute('aria-expanded', 'true');
  }

  function closeCz() {
    $('cz').hidden = true;
    $('czToggle').classList.remove('on');
    $('czToggle').setAttribute('aria-expanded', 'false');
  }

  function saveCz() {
    try { localStorage.setItem('iconhub.customizer', JSON.stringify(state.cz)); } catch (e) {}
  }

  function loadCz() {
    try {
      var raw = localStorage.getItem('iconhub.customizer');
      if (!raw) return;
      var o = JSON.parse(raw) || {};
      if (typeof o.size === 'number' && isFinite(o.size)) {
        state.cz.size = Math.min(96, Math.max(16, Math.round(o.size)));
      }
      if (typeof o.stroke === 'number' && isFinite(o.stroke)) {
        state.cz.stroke = Math.min(4, Math.max(0.5, Math.round(o.stroke * 10) / 10));
      }
      var c = normalizeHex(o.color);
      if (c) state.cz.color = c;
      state.cz.nonScaling = !!o.nonScaling;
    } catch (e) {}
  }

  /* ---------- 交互 ---------- */
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { toastEl.hidden = true; }, 1500);
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { toast(t('copied')); },
        function () { fallback(); });
    } else { fallback(); }
    function fallback() {
      var ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      document.body.removeChild(ta);
      toast(ok ? t('copied') : t('copyFail'));
    }
  }

  function downloadSvg(name, text) {
    var blob = new Blob([text], { type: 'image/svg+xml' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name + '.svg';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  function bind() {
    searchInput.addEventListener('input', function () {
      state.q = this.value;
      $('clearSearch').hidden = !this.value;
      renderGrid();
    });
    $('clearSearch').addEventListener('click', function () {
      searchInput.value = '';
      state.q = '';
      $('clearSearch').hidden = true;
      renderGrid();
      searchInput.focus();
    });

    $('langSwitch').addEventListener('click', function (e) {
      var b = e.target.closest('button[data-lang]');
      if (!b) return;
      state.lang = b.getAttribute('data-lang');
      renderChrome();
      renderCategories();
      renderGrid();
      if (state.active) renderDetail();
    });

    catList.addEventListener('click', function (e) {
      var b = e.target.closest('.cat');
      if (!b) return;
      state.cat = b.getAttribute('data-cat');
      renderCategories();
      renderGrid();
      if (window.matchMedia('(max-width: 860px)').matches) $('sidebar').classList.remove('open');
    });

    grid.addEventListener('click', function (e) {
      var b = e.target.closest('.cell');
      if (!b) return;
      var name = b.getAttribute('data-name');
      if (state.active === name) { closeDetail(); return; }
      Array.prototype.forEach.call(grid.querySelectorAll('.cell.on'), function (el) { el.classList.remove('on'); });
      b.classList.add('on');
      openDetail(name);
    });

    $('dClose').addEventListener('click', closeDetail);
    scrim.addEventListener('click', closeDetail);

    $('dSize').addEventListener('input', function () {
      $('dSizeOut').textContent = this.value;
      renderDetail();
    });
    $('dStroke').addEventListener('input', function () {
      $('dStrokeOut').textContent = (this.value / 10).toFixed(1);
      renderDetail();
    });
    $('dColor').addEventListener('input', function () {
      state.color = this.value;
      $('dColorOut').textContent = this.value;
      renderDetail();
    });

    drawer.addEventListener('click', function (e) {
      var el = e.target.closest('[data-copy]');
      if (el) {
        var ic = byName.get(state.active);
        if (!ic) return;
        var size = +$('dSize').value, stroke = +$('dStroke').value / 10;
        var mode = el.getAttribute('data-copy');
        if (mode === 'svg') copyText(iconMarkup(ic, size, stroke, state.color));
        else if (mode === 'jsx') copyText(toJsx(iconMarkup(ic, size, stroke, state.color), size, stroke));
        else if (mode === 'name') copyText(ic.name);
        else if (mode === 'file') downloadSvg(ic.name, iconMarkup(ic, size, stroke, state.color));
        return;
      }
      var target = e.target.closest('[data-cat],[data-tag],[data-alias]');
      if (!target) return;
      if (target.hasAttribute('data-cat')) {
        state.cat = target.getAttribute('data-cat');
        renderCategories();
        renderGrid();
      } else {
        var v = target.getAttribute('data-tag') || target.getAttribute('data-alias');
        state.cat = '__all__';
        state.q = v;
        searchInput.value = v;
        $('clearSearch').hidden = false;
        renderCategories();
        renderGrid();
      }
    });

    /* --- Customizer --- */
    $('czToggle').addEventListener('click', function () {
      if ($('cz').hidden) { closeDetail(); openCz(); } else { closeCz(); }
    });

    $('czReset').addEventListener('click', function () {
      state.cz = {
        color: CZ_DEFAULT.color,
        stroke: CZ_DEFAULT.stroke,
        size: CZ_DEFAULT.size,
        nonScaling: CZ_DEFAULT.nonScaling
      };
      syncCzControls();
      saveCz();
      toast(t('resetDone'));
    });

    $('czSize').addEventListener('input', function () {
      state.cz.size = +this.value;
      applyCustomizer();
      saveCz();
    });

    $('czStroke').addEventListener('input', function () {
      state.cz.stroke = +this.value / 10;
      applyCustomizer();
      saveCz();
    });

    $('czColor').addEventListener('input', function () {
      state.cz.color = this.value;
      syncCzControls();
      saveCz();
    });

    $('czHex').addEventListener('input', function () {
      var c = normalizeHex(this.value);
      if (!c) return;
      state.cz.color = c;
      applyCustomizer();
      saveCz();
    });
    $('czHex').addEventListener('blur', function () {
      this.value = state.cz.color;
    });

    $('czNonScaling').addEventListener('click', function () {
      state.cz.nonScaling = !state.cz.nonScaling;
      applyCustomizer();
      saveCz();
    });

    // 点击面板外部关闭（捕获阶段，先于其它点击处理）
    document.addEventListener('click', function (e) {
      if ($('cz').hidden) return;
      var t = e.target;
      if (t && t.closest && (t.closest('#cz') || t.closest('#czToggle'))) return;
      closeCz();
    }, true);

    $('menuBtn').addEventListener('click', function () {
      $('sidebar').classList.toggle('open');
    });

    document.addEventListener('keydown', function (e) {
      var ae = document.activeElement;
      var typing = ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA');
      if (e.key === 'Escape') { closeDetail(); closeCz(); }
      if (e.key === '/' && !typing && ae !== searchInput) {
        e.preventDefault();
        searchInput.focus();
      }
    });
  }

  /* ---------- 启动 ---------- */
  try {
    var saved = localStorage.getItem('iconhub.lang');
    if (saved === 'zh' || saved === 'en') state.lang = saved;
  } catch (e) { /* file:// 或隐私模式下忽略 */ }

  // 支持可分享的 URL 状态：?lang=zh&q=user&cat=account&icon=user
  var params = new URLSearchParams(location.search);
  if (params.get('lang') === 'zh' || params.get('lang') === 'en') state.lang = params.get('lang');
  if (params.get('q')) {
    state.q = params.get('q');
    searchInput.value = state.q;
    $('clearSearch').hidden = false;
  }
  var pc = params.get('cat');
  if (pc === '__all__') {
    state.cat = '__all__';
  } else if (pc) {
    // 旧链接 ?cat=animals 默认指第一个源；新链接用 ?cat=lucide:animals
    if (pc.indexOf(':') === -1) pc = (DATA.sources[0] ? DATA.sources[0].key : '') + ':' + pc;
    if (byCat.has(pc)) state.cat = pc;
  }

  loadCz();
  renderChrome();
  renderCategories();
  renderGrid();
  syncCzControls();
  bind();

  var pi = params.get('icon');
  if (pi) {
    // 同上：?icon=user 默认指第一个源，?icon=tabler:user 指明确源
    if (pi.indexOf(':') === -1) pi = (DATA.sources[0] ? DATA.sources[0].key : '') + ':' + pi;
    if (byName.has(pi)) {
      var cell = grid.querySelector('.cell[data-name="' + pi + '"]');
      if (cell) cell.classList.add('on');
      openDetail(pi);
    }
  }

  // URL 覆盖自定义外观：?size=40&stroke=1.5&color=%23e11d48&nonscaling=1&cz=1
  var ps = +params.get('size');
  if (ps >= 16 && ps <= 96) state.cz.size = Math.round(ps);
  var pk = +params.get('stroke');
  if (pk >= 0.5 && pk <= 4) state.cz.stroke = Math.round(pk * 10) / 10;
  var pcol = normalizeHex(params.get('color') || '');
  if (pcol) state.cz.color = pcol;
  if (params.get('nonscaling') === '1') state.cz.nonScaling = true;
  if (ps || pk || pcol || params.get('nonscaling')) {
    applyCustomizer();
    $('czHex').value = state.cz.color;
  }
  if (params.get('cz') === '1') openCz();

  document.addEventListener('click', function (e) {
    if (e.target && e.target.closest && e.target.closest('#langSwitch')) {
      try { localStorage.setItem('iconhub.lang', state.lang); } catch (err) {}
    }
  }, true);
})();
