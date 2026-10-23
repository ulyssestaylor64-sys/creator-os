/* =========================================================
   Creator OS — 工作台交互
   ========================================================= */
(function () {
  'use strict';

  var D = document;
  var $ = function (s, r) { return (r || D).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || D).querySelectorAll(s)); };

  /* ---------------- 基础工具 ---------------- */
  function toast(msg) {
    var stack = $('#toastStack');
    if (!stack) return;
    var el = D.createElement('div');
    el.className = 'toast';
    el.innerHTML = '<svg width="13" height="13"><use href="#i-check"/></svg><span></span>';
    el.querySelector('span').textContent = msg;
    stack.appendChild(el);
    setTimeout(function () {
      el.classList.add('out');
      setTimeout(function () { el.remove(); }, 260);
    }, 2600);
  }

  function copyText(text, msg) {
    function done() { toast(msg || '已复制到剪贴板'); }
    function fallback() {
      var ta = D.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.top = '-100px';
      ta.style.opacity = '0';
      D.body.appendChild(ta);
      ta.select();
      try { D.execCommand('copy'); done(); }
      catch (e) { toast('复制失败，请手动选择文本'); }
      ta.remove();
    }
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done).catch(fallback);
    } else {
      fallback();
    }
  }

  function download(name, content) {
    var blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = D.createElement('a');
    a.href = url;
    a.download = name;
    D.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () { URL.revokeObjectURL(url); }, 1200);
  }

  function esc(str) {
    return String(str).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  var store = {
    get: function (k, d) {
      try {
        var v = localStorage.getItem('creatoros.' + k);
        return v === null ? d : JSON.parse(v);
      } catch (e) { return d; }
    },
    set: function (k, v) {
      try { localStorage.setItem('creatoros.' + k, JSON.stringify(v)); } catch (e) {}
    }
  };

  /* ---------------- API 模块 ---------------- */
  var API_BASE = (location.hostname === 'localhost' || location.hostname === '127.0.0.1')
    ? 'http://localhost:8000/api'
    : '/api';
  var API_READY = null;

  function checkApi() {
    if (API_READY !== null) return Promise.resolve(API_READY);
    return fetch(API_BASE + '/health', { method: 'GET', cache: 'no-store' })
      .then(function (r) {
        API_READY = r.ok;
        return API_READY;
      })
      .catch(function () {
        API_READY = false;
        return false;
      });
  }

  var API = {
    get: function (path, params) {
      var url = API_BASE + path;
      if (params) {
        var qs = Object.keys(params).map(function (k) {
          return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]);
        }).join('&');
        if (qs) url += '?' + qs;
      }
      return fetch(url).then(function (r) { return r.json(); });
    },
    post: function (path, body) {
      return fetch(API_BASE + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body || {})
      }).then(function (r) { return r.json(); });
    },
    check: checkApi,
    enabled: function () { return API_READY; }
  };

  // 静默探测后端
  checkApi();

  /* ---------------- 浮层控制 ---------------- */
  var sidebar = $('#sidebar');
  var overlay = $('#drawerOverlay');

  function updateBodyLock() {
    var locked = !!$('.modal.open') || !!$('.drawer.open') || (sidebar && sidebar.classList.contains('open'));
    D.body.style.overflow = locked ? 'hidden' : '';
  }

  function syncOverlay() {
    if (!overlay) return;
    var open = !!$('.drawer.open') || (sidebar && sidebar.classList.contains('open'));
    overlay.classList.toggle('open', open);
  }

  function closeSidebar() {
    if (sidebar) sidebar.classList.remove('open');
    syncOverlay();
    updateBodyLock();
  }

  function closeDrawers() {
    $$('.drawer.open').forEach(function (d) { d.classList.remove('open'); });
    syncOverlay();
    updateBodyLock();
  }

  function closeModals() {
    $$('.modal.open').forEach(function (m) { m.classList.remove('open'); });
    updateBodyLock();
  }

  function openLayer(name) {
    closeSidebar();
    $$('.drawer.open').forEach(function (d) { d.classList.remove('open'); });
    $$('.modal.open').forEach(function (m) { m.classList.remove('open'); });

    if (name === 'ai' || name === 'help') {
      var drawer = D.getElementById(name + 'Drawer');
      if (!drawer) return;
      drawer.classList.add('open');
      if (overlay) overlay.classList.add('open');
    } else {
      var modal = D.getElementById(name + 'Modal');
      if (!modal) return;
      if (overlay) overlay.classList.remove('open');
      modal.classList.add('open');
      if (name === 'cmd') {
        var inp = $('#cmdInput');
        if (inp) { inp.value = ''; }
        renderCmd('');
        setTimeout(function () { if (inp) inp.focus(); }, 60);
      }
    }
    updateBodyLock();
  }

  /* ---------------- 页面切换 ---------------- */
  function go(page) {
    var target = D.getElementById('page-' + page);
    if (!target) return;
    $$('.page').forEach(function (p) { p.classList.toggle('active', p === target); });
    $$('.nav-item[data-page]').forEach(function (n) { n.classList.toggle('active', n.dataset.page === page); });
    $$('.mobile-nav button[data-page]').forEach(function (n) { n.classList.toggle('active', n.dataset.page === page); });
    var crumb = $('#crumbCurrent');
    if (crumb) crumb.textContent = target.dataset.title || '';
    closeDrawers();
    closeModals();
    closeSidebar();
    window.scrollTo({ top: 0, behavior: 'smooth' });
    window.dispatchEvent(new CustomEvent('creator:page', { detail: { page: page } }));
  }

  D.addEventListener('click', function (e) {
    var nav = e.target.closest('.nav-item[data-page], .mobile-nav button[data-page]');
    if (nav) { go(nav.dataset.page); return; }
    var goBtn = e.target.closest('[data-go]');
    if (goBtn) { e.preventDefault(); go(goBtn.dataset.go); }
  });

  if ($('#menuBtn')) {
    $('#menuBtn').addEventListener('click', function () {
      if (!sidebar) return;
      sidebar.classList.toggle('open');
      syncOverlay();
      updateBodyLock();
    });
  }

  if (overlay) {
    overlay.addEventListener('click', function () {
      closeSidebar();
      closeDrawers();
    });
  }

  D.addEventListener('click', function (e) {
    var opener = e.target.closest('[data-open]');
    if (opener) {
      e.preventDefault();
      openLayer(opener.dataset.open);
      return;
    }
    if (e.target.closest('[data-close-drawer]')) {
      closeDrawers();
      return;
    }
    var closer = e.target.closest('[data-close]');
    if (closer) {
      var modal = closer.closest('.modal');
      if (modal) {
        modal.classList.remove('open');
        updateBodyLock();
      }
    }
  });

  /* ---------------- 复制 / 提示 ---------------- */
  D.addEventListener('click', function (e) {
    var copyBtn = e.target.closest('[data-copy]');
    if (copyBtn) {
      e.preventDefault();
      copyText(copyBtn.dataset.copy, copyBtn.dataset.toast || '已复制到剪贴板');
      return;
    }
    var srcBtn = e.target.closest('[data-copy-id]');
    if (srcBtn) {
      e.preventDefault();
      var src = D.getElementById(srcBtn.dataset.copyId);
      copyText(src ? src.innerText.replace(/\s+/g, ' ').trim() : '', '已复制到剪贴板');
      return;
    }
    var toastBtn = e.target.closest('[data-toast]');
    if (toastBtn && !toastBtn.dataset.copy) {
      e.preventDefault();
      toast(toastBtn.dataset.toast);
    }
  });

  /* ---------------- 总览 ---------------- */
  var rangeSeg = $('#overviewRange');
  if (rangeSeg) {
    rangeSeg.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-range]');
      if (!btn) return;
      $$('button', rangeSeg).forEach(function (b) { b.classList.toggle('active', b === btn); });
      if (window.CreatorCharts) window.CreatorCharts.setOverviewRange(btn.dataset.range);
    });
  }

  var taskMins = [12, 30, 15, 10];
  function updateFocus() {
    var tasks = $$('.task[data-task]');
    if (!tasks.length) return;
    var done = 0;
    var mins = 0;
    tasks.forEach(function (t, i) {
      if (t.classList.contains('done')) { done++; }
      else { mins += taskMins[i] || 15; }
    });
    var pct = Math.round((done / tasks.length) * 100);
    var ring = $('#focusRing');
    if (ring) ring.setAttribute('stroke-dashoffset', (138.2 * (1 - pct / 100)).toFixed(1));
    var pctEl = $('#focusPct');
    if (pctEl) pctEl.textContent = pct + '%';
    var caption = $('#focusCaption');
    if (caption) {
      caption.textContent = done === tasks.length
        ? '今天的任务全部完成 · 去发布作品吧'
        : '还有 ' + (tasks.length - done) + ' 项任务 · 预计 ' + mins + ' 分钟';
    }
    var pill = $('.focus-card .card-head .pill.lime');
    if (pill) pill.textContent = done + ' / ' + tasks.length + ' 完成';
  }

  $$('.task[data-task]').forEach(function (task) {
    var check = $('.task-check', task);
    if (check) {
      check.addEventListener('click', function (e) {
        e.stopPropagation();
        task.classList.toggle('done');
        updateFocus();
      });
    }
  });
  updateFocus();

  /* ---------------- 02 赛道自测 ---------------- */
  var chipGroups = $$('.chip-group');
  function updateFormNote() {
    var n = 0;
    chipGroups.forEach(function (g) {
      n += $$('.chip.on', g).length;
    });
    var note = $('.test-form .form-note');
    if (note) {
      note.innerHTML = '<svg width="11" height="11"><use href="#i-lock"/></svg> 已选择 ' + n + ' 项 · 数据仅用于本次诊断';
    }
  }

  chipGroups.forEach(function (group) {
    var limit = group.dataset.group === 'skill' ? 4 : 3;
    group.addEventListener('click', function (e) {
      var chip = e.target.closest('.chip');
      if (!chip) return;
      if (!chip.classList.contains('on') && $$('.chip.on', group).length >= limit) {
        toast('最多选择 ' + limit + ' 项，先取消一个再选');
        return;
      }
      chip.classList.toggle('on');
      updateFormNote();
    });
  });

  $$('[data-radio-group]').forEach(function (group) {
    group.addEventListener('click', function (e) {
      var opt = e.target.closest('.radio-opt');
      if (!opt) return;
      $$('.radio-opt', group).forEach(function (o) { o.classList.toggle('on', o === opt); });
    });
  });

  var timeRange = $('#timeRange');
  if (timeRange) {
    timeRange.addEventListener('input', function () {
      var val = $('#timeVal');
      if (val) val.textContent = timeRange.value;
    });
  }

  function renderNicheResults(data) {
    var loading = $('#nicheLoading');
    var results = $('#nicheResults');
    if (loading) loading.classList.add('hidden');
    if (results) results.classList.remove('hidden');

    var hours = data && data.hours ? data.hours : (timeRange ? Number(timeRange.value) : 10);
    var rate = data && data.rate ? data.rate : (hours <= 6 ? '2 条 / 周' : hours <= 12 ? '3 条 / 周' : hours <= 20 ? '4 条 / 周' : '5 条 / 周');
    var score = data && data.score ? data.score : 92;
    var primary = data && data.primary ? data.primary : 'AI 效率 × 职场成长';
    var desc = data && data.desc ? data.desc : '你的职场经验、AI 工具熟练度与文案能力形成了稀缺组合：既能讲清方法，也能用真实场景证明结果。当前供给不足，适合以「一人公司 / AI 提效」建立差异化记忆点。';

    var bigScore = $('.result-summary .big-score');
    if (bigScore) bigScore.innerHTML = score + '<small>/100</small>';
    var resultName = $('.result-summary .result-name');
    if (resultName) resultName.textContent = primary;
    var resultDesc = $('.result-summary .result-desc');
    if (resultDesc) resultDesc.textContent = desc;

    var meta = $$('#nicheResults .result-meta > div');
    if (meta[2]) {
      var b = $('b', meta[2]);
      if (b) b.textContent = rate;
    }
    var planCard = $('#nicheResults .plan-grid');
    if (planCard) {
      var card = planCard.closest('.card');
      var sub = card ? $('.card-sub', card) : null;
      if (sub) sub.textContent = '按你每周 ' + hours + ' 小时的投入自动排期';
    }

    // 渲染赛道推荐卡片
    if (data && data.tracks) {
      var trackCards = $$('.track-card');
      data.tracks.forEach(function (track, i) {
        var card = trackCards[i];
        if (!card) return;
        var nameEl = $('.track-name', card);
        var scoreEl = $('.track-score', card);
        if (nameEl) nameEl.textContent = track.name;
        if (scoreEl) scoreEl.innerHTML = track.score + '<small>/100</small>';
        var bars = $$('.bar-fill', card);
        if (bars[0]) bars[0].style.width = track.competition + '%';
        if (bars[1]) bars[1].style.width = track.monetize + '%';
        if (bars[2]) bars[2].style.width = track.sustain + '%';
        var reasonEl = $('.track-reason', card);
        if (reasonEl) reasonEl.textContent = track.reason;
      });
    }

    // 渲染 7 天计划
    if (data && data.plan) {
      var planDays = $$('.plan-day');
      data.plan.forEach(function (day, i) {
        var el = planDays[i];
        if (!el) return;
        var d = $('.d', el);
        var t = $('.t', el);
        var f = $('.f', el);
        if (d) d.textContent = 'DAY 0' + day.day + ' · ' + day.weekday;
        if (t) t.textContent = day.task;
        if (f) f.innerHTML = '<b>' + day.form + '</b> · ' + day.duration;
      });
    }

    window.dispatchEvent(new CustomEvent('creator:niche-done'));
    if (window.CreatorCharts && data) {
      if (data.radar) window.CreatorCharts.renderRadar(data.radar);
      if (data.opportunity) {
        var pts = data.opportunity.map(function (p) {
          return { name: p.name, value: [p.competition, p.monetize, p.match], color: p.color };
        });
        window.CreatorCharts.renderOpportunity(pts);
      }
    }
    if (results) {
      setTimeout(function () {
        results.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 90);
    }
  }

  function showNicheResults() {
    renderNicheResults(null);
  }

  if ($('#runNiche')) {
    $('#runNiche').addEventListener('click', function () {
      var btn = $('#runNiche');
      var loading = $('#nicheLoading');
      var results = $('#nicheResults');
      if (results) results.classList.add('hidden');
      if (loading) loading.classList.remove('hidden');
      btn.disabled = true;
      var original = btn.innerHTML;
      btn.innerHTML = '<svg width="14" height="14"><use href="#i-spark"/></svg> AI 诊断中…';
      if (loading) loading.scrollIntoView({ behavior: 'smooth', block: 'center' });

      var skills = [];
      var interests = [];
      chipGroups.forEach(function (g) {
        var vals = $$('.chip.on', g).map(function (c) { return c.dataset.value; });
        if (g.dataset.group === 'skill') skills = vals;
        else interests = vals;
      });
      var hours = timeRange ? Number(timeRange.value) : 10;
      var shoot = '偶尔出镜';
      var goal = '稳定变现';
      $$('[data-radio-group]').forEach(function (g) {
        var on = $('.radio-opt.on', g);
        if (!on) return;
        if (g.dataset.radioGroup === 'shoot') shoot = on.dataset.value;
        if (g.dataset.radioGroup === 'goal') goal = on.dataset.value;
      });

      function finish(data) {
        btn.disabled = false;
        btn.innerHTML = original;
        renderNicheResults(data);
        toast('赛道诊断已生成 · 匹配度 ' + (data && data.score ? data.score : 92));
      }

      if (API.enabled()) {
        API.post('/niche/analyze', { skills: skills, interests: interests, hours: hours, shoot: shoot, goal: goal })
          .then(function (res) { finish(res); })
          .catch(function () { finish(null); });
      } else {
        setTimeout(function () { finish(null); }, 1500);
      }
    });
  }

  if ($('#showLastResult')) {
    $('#showLastResult').addEventListener('click', function () {
      showNicheResults();
      toast('已载入 10 月 8 日的诊断报告');
    });
  }

  if ($('#resetNiche')) {
    $('#resetNiche').addEventListener('click', function () {
      chipGroups.forEach(function (g) {
        var defaults = g.dataset.group === 'skill' ? ['职场经验', 'AI 工具', '文案写作'] : ['AI 与效率', '职场成长'];
        $$('.chip', g).forEach(function (c) {
          c.classList.toggle('on', defaults.indexOf(c.dataset.value) > -1);
        });
      });
      if (timeRange) { timeRange.value = 10; }
      if ($('#timeVal')) $('#timeVal').textContent = '10';
      $$('[data-radio-group]').forEach(function (g) {
        var def = g.dataset.radioGroup === 'shoot' ? '偶尔出镜' : '稳定变现';
        $$('.radio-opt', g).forEach(function (o) { o.classList.toggle('on', o.dataset.value === def); });
      });
      var results = $('#nicheResults');
      if (results) results.classList.add('hidden');
      var loading = $('#nicheLoading');
      if (loading) loading.classList.add('hidden');
      updateFormNote();
      window.scrollTo({ top: 0, behavior: 'smooth' });
      toast('已重置诊断条件');
    });
  }
  updateFormNote();

  /* ---------------- 03 每日选题 ---------------- */
  var topicData = [
    {
      id: 'local_0', title: '我把 ChatGPT 当同事用了 30 天，效率提升了 3 倍',
      audience: '25–35 职场人', competition: '竞争 中', estimate: '预估 40–80w 播放', match: 92,
      peak: '9.6', rise: '+124%',
      reason: '你近 7 天「AI 会议纪要」选题平均完播 38.2%，高于账号均值 41%。这条选题可直接复用验证过的结构。',
      framework: [
        ['0–3s', '钩子 · 结果前置 + 身份代入', '「我让 AI 替我开完了 30 场会，结果老板以为我偷偷加了班。」'],
        ['3–25s', '展开 · 三个真实场景', '会议记录、周报汇总、跨部门同步，每个场景保留一个反常识转折。'],
        ['25–58s', '收束 · 可复用工作流', '给出 3 步工作流与模板，结尾引导评论区领取，不硬广。']
      ],
      refs: [['我把 ChatGPT 当同事用了 30 天', '328.4w', 'hc1'], ['一个人做自媒体的第 180 天', '186.2w', 'hc3'], ['月薪 3 万的人都在用的工作流', '612.8w', 'hc2']]
    },
    {
      id: 'local_1', title: '月薪 8000 和月薪 3 万的人，差在这一份周报',
      audience: '22–32 职场新人', competition: '竞争 高', estimate: '预估 25–60w 播放', match: 88,
      peak: '9.3', rise: '+18%',
      reason: '热榜话题热度高，但同质化严重。你的优势在「真实职场经验 + AI 工具」，建议把对比落到 AI 写周报的具体流程，避开纯观点争论。',
      framework: [
        ['0–3s', '钩子 · 身份对比 + 数字冲突', '「同样写周报，为什么他 10 分钟，你要 2 小时？」'],
        ['3–30s', '展开 · 两种周报结构对比', '展示真实截图：一个记流水账，一个用结果和下一步说话。'],
        ['30–55s', '收束 · AI 周报模板', '给出 3 段式模板与提示词，评论区领取。']
      ],
      refs: [['月薪 3 万的人都在用的工作流', '612.8w', 'hc2'], ['周报写得好，升职早', '88.4w', 'hc4'], ['我用 AI 写周报的第 30 天', '72.1w', 'hc1']]
    },
    {
      id: 'local_2', title: '别再手动整理会议纪要了，这套 AI 工作流 3 分钟搞定',
      audience: '25–40 职场人 / 管理者', competition: '竞争 低', estimate: '预估 45–90w 播放', match: 95,
      peak: '9.0', rise: '+41%',
      reason: '搜索需求连续 7 天上涨，与你近 7 天「AI 会议纪要」系列高度重合，完播率已验证。建议直接承接，用搜索词做标题。',
      framework: [
        ['0–3s', '钩子 · 结果前置', '「3 分钟开完一场会，纪要自动发到群里。」'],
        ['3–35s', '展开 · 录屏演示三步工作流', '录音转写、结构化提炼、自动分发，每一步都给替代方案。'],
        ['35–55s', '收束 · 工具组合 + 模板', '结尾只引导评论区领取模板，不做硬广。']
      ],
      refs: [['会议纪要自动生成', '128.6w', 'hc1'], ['飞书 + AI 会议记录', '96.2w', 'hc6'], ['领导以为我请了助理', '84.7w', 'hc4']]
    },
    {
      id: 'local_3', title: '一个人做自媒体，我用 5 个 AI 员工替代了一个团队',
      audience: '24–35 个人创作者', competition: '竞争 中', estimate: '预估 35–70w 播放', match: 86,
      peak: '8.9', rise: '+26%',
      reason: '「一人公司」是你的账号标签，近 30 天相关作品涨粉贡献 38%。清单体结构稳定，适合强化人设并自然引出商单。',
      framework: [
        ['0–3s', '钩子 · 人设 + 数字', '「我一个人，管着 5 个 AI 员工。」'],
        ['3–40s', '展开 · 5 个岗位与真实产出', '选题、脚本、剪辑、客服、商务，每个岗位说清替代了什么。'],
        ['40–58s', '收束 · 岗位配置表', '给出配置表和成本，评论区领取。']
      ],
      refs: [['一个人做自媒体的第 180 天', '186.2w', 'hc3'], ['我的 5 个 AI 员工', '142.5w', 'hc1'], ['一人公司工具栈', '108.3w', 'hc6']]
    },
    {
      id: 'local_4', title: '2026 年最值得学的 3 个 AI 工具，普通人也能上手',
      audience: '20–35 AI 初学者', competition: '竞争 高', estimate: '预估 20–50w 播放', match: 82,
      peak: '8.4', rise: '+9%',
      reason: '流量稳定但广告感强。建议用「真实使用 30 天」降低推广感，只推荐你实际付费的工具，维持信任。',
      framework: [
        ['0–3s', '钩子 · 反常识', '「2026 最值得学的 AI 工具，不是最火的那几个。」'],
        ['3–35s', '展开 · 三个真实场景 + 缺点', '每个工具都要讲清不适合谁，可信度更高。'],
        ['35–55s', '收束 · 一周上手路径', '给出每天 20 分钟的学习顺序。']
      ],
      refs: [['2026 AI 工具红黑榜', '268.4w', 'hc2'], ['我只留下这 5 个 AI 工具', '154.2w', 'hc6'], ['普通人学 AI 的顺序', '96.8w', 'hc4']]
    },
    {
      id: 'local_5', title: '为什么越努力越焦虑？可能你缺的是系统而不是自律',
      audience: '25–35 高压职场人', competition: '竞争 低', estimate: '预估 15–40w 播放', match: 79,
      peak: '8.1', rise: '+12%',
      reason: '情绪共鸣型内容互动率高但涨粉慢，适合每周一条调节节奏。建议用自己的经历开场，避免鸡汤感。',
      framework: [
        ['0–3s', '钩子 · 自曝', '「我曾经每天工作 12 小时，却越来越焦虑。」'],
        ['3–30s', '展开 · 三个无效努力场景', '加班、囤课、做计划，逐个指出问题不在自律。'],
        ['30–55s', '收束 · 系统化方法', '给一个最小系统，结尾弱 CTA。']
      ],
      refs: [['越努力越焦虑的真相', '324.1w', 'hc2'], ['我停止自律之后', '187.6w', 'hc3'], ['建立系统而不是目标', '92.4w', 'hc1']]
    }
  ];

  var currentTopic = 0;
  var backendTopics = [];

  function resetDetailTabs() {
    $$('#detailTabs .detail-tab').forEach(function (b, i) { b.classList.toggle('active', i === 0); });
    $$('.topic-detail .tab-pane').forEach(function (p, i) { p.classList.toggle('active', i === 0); });
  }

  function renderTopicDetail(t) {
    $('#detailTopicTitle').textContent = t.title;
    $('#detailAudience').textContent = t.audience;
    $('#detailCompetition').textContent = t.competition;
    $('#detailEstimate').textContent = t.estimate;
    var matchPill = $('.topic-detail-head .pill.lime');
    if (matchPill) matchPill.textContent = '匹配 ' + t.match + '%';
    $('#detailPeak').textContent = t.peak;
    $('#detailRise').textContent = t.rise;
    $('#detailReason').textContent = t.reason;
    var framework = t.framework || [];
    $('#detailFramework').innerHTML = '<div class="framework">' + framework.map(function (f) {
      return '<div class="framework-step"><div class="fw-num">' + f[0] + '</div><div class="fw-body"><b>' + f[1] + '</b><p>' + f[2] + '</p></div></div>';
    }).join('') + '</div>';
    var refs = t.refs || [];
    $('#detailRefs').innerHTML = refs.map(function (r) {
      return '<div class="ref-row"><div class="ref-thumb ' + r[2] + '"></div><div class="ref-title">' + r[0] + '</div><span class="ref-play">' + r[1] + '</span></div>';
    }).join('');
    resetDetailTabs();
    if (window.CreatorCharts && t.trend) {
      window.CreatorCharts.renderTopicHeat(t.trend);
    } else if (window.CreatorCharts) {
      window.CreatorCharts.setTopicHeat();
    }
  }

  function selectTopic(index) {
    currentTopic = index;
    $$('#topicList .topic-item').forEach(function (el) {
      el.classList.toggle('active', Number(el.dataset.topic) === index);
    });
    var t = backendTopics[index] || topicData[index];
    if (!t) return;
    if (API.enabled() && t.id && String(t.id).indexOf('local_') !== 0) {
      API.get('/topics/' + t.id).then(function (detail) {
        if (detail && detail.title) renderTopicDetail(detail);
      }).catch(function () {
        renderTopicDetail(t);
      });
    } else {
      renderTopicDetail(t);
    }
    var join = $('#joinPlan');
    if (join) {
      var joined = join.dataset.joined === '1';
      join.innerHTML = joined
        ? '<svg width="12" height="12"><use href="#i-check"/></svg> 已加入计划'
        : '<svg width="12" height="12"><use href="#i-plus"/></svg> 加入计划';
    }
  }

  function buildTopicItem(t, idx) {
    var sourceMap = { '抖音热榜': 'orange', '同赛道爆款': 'green', '搜索趋势': 'blue', '创作灵感': '' };
    var pillClass = sourceMap[t.source] || '';
    return '<article class="topic-item' + (idx === 0 ? ' active' : '') + '" data-topic="' + idx + '" data-source="' + esc(t.source) + '" tabindex="0">' +
      '<div class="topic-rank">' + (t.rank || ('0' + (idx + 1)).slice(-2)) + '</div>' +
      '<div class="topic-main">' +
        '<div class="topic-title">' + esc(t.title) + '</div>' +
        '<p class="topic-desc">' + esc(t.desc || '') + '</p>' +
        '<div class="topic-meta"><span class="pill ' + pillClass + '">' + esc(t.source) + '</span><span class="pill">适配 ' + t.match + '%</span><span class="pill">' + esc(t.competition) + '</span></div>' +
      '</div>' +
      '<div class="topic-heat"><b>' + t.heat + '</b><small>' + esc(t.rise) + '</small></div>' +
      '</article>';
  }

  function rebuildTopicList(topics) {
    backendTopics = topics || [];
    var list = $('#topicList');
    if (!list) return;
    if (!backendTopics.length) {
      backendTopics = [];
      return;
    }
    list.innerHTML = backendTopics.map(function (t, i) { return buildTopicItem(t, i); }).join('');
  }

  var topicList = $('#topicList');
  if (topicList) {
    topicList.addEventListener('click', function (e) {
      var item = e.target.closest('.topic-item');
      if (!item) return;
      selectTopic(Number(item.dataset.topic));
    });
    topicList.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var item = e.target.closest('.topic-item');
      if (!item) return;
      e.preventDefault();
      selectTopic(Number(item.dataset.topic));
    });
  }

  function filterTopics(source) {
    if (API.enabled()) {
      var apiSource = source === '抖音热榜' ? 'douyin' : source === '同赛道爆款' ? 'niche' : source === '搜索趋势' ? 'search' : 'all';
      API.get('/topics', { source: apiSource }).then(function (res) {
        rebuildTopicList(res.topics);
        selectTopic(0);
      }).catch(function () {
        localFilterTopics(source);
      });
    } else {
      localFilterTopics(source);
    }
  }

  function localFilterTopics(source) {
    var items = $$('#topicList .topic-item');
    items.forEach(function (el) {
      var ok = source === 'all' || el.dataset.source === source;
      el.style.display = ok ? '' : 'none';
    });
    var active = $('#topicList .topic-item.active');
    if (active && active.style.display === 'none') {
      var first = $$('#topicList .topic-item').filter(function (el) { return el.style.display !== 'none'; })[0];
      if (first) selectTopic(Number(first.dataset.topic));
    }
  }

  var sourceTabs = $('#sourceTabs');
  if (sourceTabs) {
    sourceTabs.addEventListener('click', function (e) {
      var btn = e.target.closest('button[data-source]');
      if (!btn) return;
      $$('button', sourceTabs).forEach(function (b) { b.classList.toggle('active', b === btn); });
      filterTopics(btn.dataset.source);
    });
  }

  if ($('#refreshTopics')) {
    $('#refreshTopics').addEventListener('click', function () {
      var list = $('#topicList');
      var sync = $('#syncTime');
      if (list) list.style.opacity = '.35';
      if (API.enabled()) {
        API.get('/topics', { source: 'all', refresh: 1 }).then(function (res) {
          rebuildTopicList(res.topics);
          selectTopic(0);
          if (list) list.style.opacity = '1';
          if (sync) sync.textContent = res.sync_time || '刚刚更新 · 抖音热榜 / 创作灵感';
          toast('热点已刷新 · 新增 6 条高匹配选题');
        }).catch(function () {
          if (list) list.style.opacity = '1';
          if (sync) sync.textContent = '刚刚更新 · 抖音热榜 / 创作灵感';
          toast('热点已刷新 · 新增 6 条高匹配选题');
        });
      } else {
        setTimeout(function () {
          if (list) list.style.opacity = '1';
          if (sync) sync.textContent = '刚刚更新 · 抖音热榜 / 创作灵感';
          toast('热点已刷新 · 新增 6 条高匹配选题');
        }, 550);
      }
    });
  }

  if ($('#detailTabs')) {
    $('#detailTabs').addEventListener('click', function (e) {
      var btn = e.target.closest('[data-detail-tab]');
      if (!btn) return;
      $$('#detailTabs .detail-tab').forEach(function (b) { b.classList.toggle('active', b === btn); });
      $$('.topic-detail .tab-pane').forEach(function (p) {
        p.classList.toggle('active', p.id === 'pane-' + btn.dataset.detailTab);
      });
    });
  }

  if ($('#joinPlan')) {
    $('#joinPlan').addEventListener('click', function () {
      var btn = $('#joinPlan');
      if (btn.dataset.joined === '1') { toast('这条选题已在你的 7 天计划里'); return; }
      btn.dataset.joined = '1';
      btn.innerHTML = '<svg width="12" height="12"><use href="#i-check"/></svg> 已加入计划';
      toast('已加入 7 天计划 · 可在总览查看');
    });
  }

  function addTopicFromInsight(title) {
    var index = topicData.length;
    topicData.push({
      title: title,
      audience: '25–35 职场人',
      competition: '竞争 低',
      estimate: '待验证',
      match: 88,
      peak: '—',
      rise: '新',
      reason: '来自评论洞察：这是观众主动提出的需求，建议优先做一条低成本验证内容。',
      framework: [
        ['0–3s', '钩子 · 观众原话', '「你们一直在评论区问的那件事，今天一次讲清。」'],
        ['3–35s', '展开 · 三步解决', '每一步对应一个真实使用场景，避免只讲概念。'],
        ['35–58s', '收束 · 清单交付', '把模板或步骤整理好，评论区领取。']
      ],
      refs: [['评论区高频问题合集', '96.4w', 'hc1'], ['你们要的完整版来了', '142.8w', 'hc4'], ['一次讲清工作流', '88.2w', 'hc6']]
    });

    var article = D.createElement('article');
    article.className = 'topic-item';
    article.dataset.topic = String(index);
    article.dataset.source = '创作灵感';
    article.tabIndex = 0;
    article.innerHTML =
      '<div class="topic-rank">NEW</div>' +
      '<div class="topic-main">' +
        '<div class="topic-title">' + esc(title) + '</div>' +
        '<p class="topic-desc">由评论洞察转为选题 · 已自动匹配你的内容结构。</p>' +
        '<div class="topic-meta"><span class="pill lime">评论洞察</span><span class="pill">适配 88%</span><span class="pill">待验证</span></div>' +
      '</div>' +
      '<div class="topic-heat"><b>—</b><small>新</small></div>';
    if (topicList) topicList.prepend(article);

    go('topics');
    selectTopic(index);
    toast('已转为选题，并加入今日候选');
  }

  D.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-convert]');
    if (!btn) return;
    e.preventDefault();
    addTopicFromInsight(btn.dataset.convert);
  });

  /* ---------------- AI 初稿 ---------------- */
  var draftTab = 'script';
  var draftTimer = null;
  var draftReady = false;

  function shortTitle(t) {
    return t.length > 22 ? t.slice(0, 22) + '…' : t;
  }

  function skeleton() {
    return '<div class="draft-skeleton"><div class="sk-line w40"></div><div class="sk-line"></div><div class="sk-line"></div><div class="sk-line w70"></div><div class="sk-line"></div><div class="sk-line w40"></div></div>';
  }

  function draftHtmlFromBackend(content, tab) {
    var c = content;
    if (!c) return '';
    if (tab === 'story') {
      var shots = c.content || [];
      return '<h4>分镜提示 · ' + shots.length + ' 个镜头</h4>' + shots.map(function (s) {
        return '<div class="draft-line"><div class="draft-time">' + esc(s.time) + '</div><div><b>' + esc(s.shot) + '</b><br>' + esc(s.note) + '</div></div>';
      }).join('');
    }
    if (tab === 'titles') {
      var titles = c.content || [];
      return '<h4>标题备选 · ' + titles.length + ' 个方向</h4>' + titles.map(function (s, i) {
        return '<div class="draft-line"><div class="draft-time">0' + (i + 1) + '</div><div>' + esc(s) + '</div></div>';
      }).join('');
    }
    var lines = c.content || [];
    return '<h4>口播脚本 · 约 58 秒</h4><div class="draft-note" style="margin:0 0 8px;color:var(--faint)">选题：' + esc(shortTitle(c.title || '')) + '</div>' + lines.map(function (l) {
      return '<div class="draft-line"><div class="draft-time">' + esc(l.time) + '</div><div><b>' + l.section + '</b><br>' + l.text + '</div></div>';
    }).join('');
  }

  function draftHtmlLocal(tab) {
    var t = topicData[currentTopic] || topicData[0];
    var title = shortTitle(t.title);
    if (tab === 'story') {
      var shots = [
        ['0–3s', '特写 · 桌面', '手把会议录音拖进 AI 工具，屏幕出现「转写中」。字幕直接给出结果：3 分钟。'],
        ['3–12s', '中景 · 真人', '对着镜头说「以前我最怕开会，现在我最怕会议纪要没人写」。'],
        ['12–30s', '录屏 · 全屏', '三步工作流加速播放：转写、提炼、分发，每步停留 3 秒。'],
        ['30–45s', '近景 · 结果', '展示整理后的纪要：结论、待办、负责人，一页看清。'],
        ['45–58s', '中景 · 收束', '「模板我整理好了，评论区留『模板』。」画面停在账号名。']
      ];
      return '<h4>分镜提示 · 5 个镜头</h4>' + shots.map(function (s) {
        return '<div class="draft-line"><div class="draft-time">' + s[0] + '</div><div><b>' + s[1] + '</b><br>' + s[2] + '</div></div>';
      }).join('');
    }

    if (tab === 'titles') {
      var titles = [
        '我把 AI 当同事用了 30 天，效率真的翻了 3 倍',
        '别再手写会议纪要了，这套工作流 3 分钟搞定',
        '月薪 3 万的人，都在偷偷用这套 AI 工作流',
        '一个人做自媒体，我如何用 AI 替代一个团队',
        '为什么你越努力越焦虑？可能缺的不是自律'
      ];
      return '<h4>标题备选 · 5 个方向</h4>' + titles.map(function (s, i) {
        return '<div class="draft-line"><div class="draft-time">0' + (i + 1) + '</div><div>' + s + '</div></div>';
      }).join('');
    }

    var lines = [
      ['0–3s', '<b>钩子 · 结果前置</b><br>「我让 AI 替我开完了 30 场会，结果老板以为我偷偷加了班。」'],
      ['3–15s', '<b>展开 · 身份代入</b><br>「如果你也是那种会议开不完、纪要写到手软的打工人，这条一定要看完。」'],
      ['15–32s', '<b>转折 · 反常识</b><br>「真正省时间的不是某个工具，而是把会议拆成：会前、会中、会后三个动作。」'],
      ['32–50s', '<b>方法 · 三步工作流</b><br>「会前让 AI 读背景材料，会中只记结论和待办，会后自动生成纪要并发到群里。」'],
      ['50–58s', '<b>收束 · 低门槛 CTA</b><br>「整套模板我整理好了，评论区留『模板』，我发你。」']
    ];
    return '<h4>口播脚本 · 约 58 秒</h4><div class="draft-note" style="margin:0 0 8px;color:var(--faint)">选题：' + esc(title) + '</div>' + lines.map(function (l) {
      return '<div class="draft-line"><div class="draft-time">' + l[0] + '</div><div>' + l[1] + '</div></div>';
    }).join('');
  }

  function renderDraft(immediate) {
    var box = $('#draftScroll');
    if (!box) return;
    draftReady = false;
    clearTimeout(draftTimer);
    box.innerHTML = skeleton();

    var topic = backendTopics[currentTopic] || topicData[currentTopic] || topicData[0];
    var topicId = topic && topic.id ? topic.id : ('local_' + currentTopic);

    if (API.enabled()) {
      API.post('/draft', { topicId: topicId, type: draftTab }).then(function (res) {
        if (res && res.content) {
          box.innerHTML = draftHtmlFromBackend(res.content, draftTab);
        } else {
          box.innerHTML = draftHtmlLocal(draftTab);
        }
        draftReady = true;
      }).catch(function () {
        box.innerHTML = draftHtmlLocal(draftTab);
        draftReady = true;
      });
    } else {
      draftTimer = setTimeout(function () {
        box.innerHTML = draftHtmlLocal(draftTab);
        draftReady = true;
      }, immediate ? 260 : 900);
    }
  }

  function openDraft() {
    openLayer('draft');
    var t = backendTopics[currentTopic] || topicData[currentTopic] || topicData[0];
    var pill = $('#draftTopicPill');
    if (pill) pill.textContent = shortTitle(t.title);
    draftTab = 'script';
    $$('#draftTabs button').forEach(function (b) {
      b.classList.toggle('active', b.dataset.draftTab === 'script');
    });
    renderDraft(false);
  }

  if ($('#openDraft')) $('#openDraft').addEventListener('click', openDraft);
  if ($('#openDraftTop')) $('#openDraftTop').addEventListener('click', openDraft);
  if ($('#regenerateDraft')) $('#regenerateDraft').addEventListener('click', function () {
    renderDraft(false);
    toast('正在按最新规则重新生成');
  });
  if ($('#draftTabs')) {
    $('#draftTabs').addEventListener('click', function (e) {
      var btn = e.target.closest('[data-draft-tab]');
      if (!btn) return;
      draftTab = btn.dataset.draftTab;
      $$('#draftTabs button').forEach(function (b) { b.classList.toggle('active', b === btn); });
      renderDraft(false);
    });
  }
  if ($('#copyDraft')) {
    $('#copyDraft').addEventListener('click', function () {
      if (!draftReady) { toast('初稿还在生成中，稍等一下'); return; }
      copyText($('#draftScroll').innerText.replace(/\n{3,}/g, '\n\n').trim(), '初稿已复制');
    });
  }
  if ($('#saveDraft')) {
    $('#saveDraft').addEventListener('click', function () {
      closeModals();
      toast('已保存到「我的创作」');
    });
  }

  /* ---------------- 04 评论洞察 ---------------- */
  var commentFilters = $('#commentFilters');
  var currentCommentFilter = 'all';

  function buildCommentRow(row) {
    var catClass = { good: 'green', need: 'lime', emotion: 'orange', bad: 'orange' }[row.cat] || '';
    var avatarClass = row.avatar ? String(row.avatar).toLowerCase() : 'a';
    var tagHtml = row.tag ? '<span class="pill ' + catClass + '" style="height:17px;font-size:7.5px">' + esc(row.tag) + '</span>' : '';
    return '<div class="comment-row" data-cat="' + esc(row.cat) + '">' +
      '<div class="comment-avatar ' + avatarClass + '">' + esc(row.avatar || row.name.charAt(0)) + '</div>' +
      '<div>' +
        '<div class="comment-name">' + esc(row.name) + ' <span>' + esc(row.time) + '</span>' + tagHtml + '</div>' +
        '<p class="comment-text">' + esc(row.text) + '</p>' +
        '<div class="comment-foot"><span>《' + esc(String(row.work).replace(/《|》/g, '')) + '》</span><span>·</span><span>点赞 ' + row.likes + '</span></div>' +
      '</div>' +
      '<div class="comment-act"><button class="icon-mini" title="标记已处理"><svg width="13" height="13"><use href="#i-check"/></svg></button><button class="icon-mini" title="转为选题" data-convert="' + esc(row.text.slice(0, 24)) + '"><svg width="13" height="13"><use href="#i-spark"/></svg></button></div>' +
    '</div>';
  }

  function renderComments(data) {
    if (!data) return;
    var syncBar = $('.sync-bar');
    if (syncBar) {
      var b = syncBar.querySelectorAll('b');
      if (b[0]) b[0].textContent = data.total ? data.total.toLocaleString('en-US') : '1,284';
      if (b[1]) b[1].textContent = data.works || 6;
    }
    if (data.stats) {
      var catMap = { good: '好评', need: '需求建议', emotion: '情绪共鸣', bad: '负面反馈' };
      var donutItems = [];
      Object.keys(catMap).forEach(function (k) {
        var s = data.stats[k];
        if (!s) return;
        var color = s.color || { good: '#1f6b4e', need: '#c3ed5a', emotion: '#e2592f', bad: '#c9c5bb' }[k];
        donutItems.push({ value: s.pct, name: s.label, itemStyle: { color: color } });
      });
      if (window.CreatorCharts) {
        window.CreatorCharts.renderDonut({ total: data.total ? data.total.toLocaleString('en-US') : '1,284', items: donutItems });
        if (data.emotion_points) {
          var pts = data.emotion_points.map(function (p) { return { name: p.name, value: [p.mentions, p.intensity, p.priority || p.size || 20] }; });
          window.CreatorCharts.renderEmotion(pts);
        }
      }
      if (commentFilters) {
        $$('.filter-chip', commentFilters).forEach(function (btn) {
          var f = btn.dataset.filter;
          var s = data.stats[f];
          var n = btn.querySelector('.n');
          if (n && s) n.textContent = s.count;
        });
      }
    }
    var list = $('#commentList');
    if (list && data.comments) {
      list.innerHTML = data.comments.map(buildCommentRow).join('');
    }
  }

  function localFilterComments(f) {
    $$('#commentList .comment-row').forEach(function (row) {
      row.style.display = (f === 'all' || row.dataset.cat === f) ? '' : 'none';
    });
  }

  function loadComments(filter) {
    filter = filter || currentCommentFilter;
    currentCommentFilter = filter;
    if (commentFilters) {
      $$('.filter-chip', commentFilters).forEach(function (b) { b.classList.toggle('active', b.dataset.filter === filter); });
    }
    if (API.enabled()) {
      API.get('/comments', { filter: filter }).then(renderComments).catch(function () { localFilterComments(filter); });
    } else {
      localFilterComments(filter);
    }
  }

  if (commentFilters) {
    commentFilters.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-filter]');
      if (!btn) return;
      loadComments(btn.dataset.filter);
    });
  }

  if ($('#addRule')) {
    $('#addRule').addEventListener('click', function () {
      var key = $('#ruleKey');
      var cat = $('#ruleCat');
      var word = key.value.trim();
      if (!word) { toast('先输入一个关键词'); key.focus(); return; }
      var category = cat.value;
      function addLocalRule() {
        var map = { '好评': 'green', '需求建议': 'lime', '情绪共鸣': 'orange', '差评': 'orange' };
        var row = D.createElement('div');
        row.className = 'rule-row';
        row.innerHTML = '<span class="rule-when">包含</span><span class="rule-key">' + esc(word) + '</span><span class="rule-arrow">→</span><span class="rule-tag pill ' + (map[category] || '') + '">' + esc(category) + '</span>';
        var list = $('#ruleList');
        if (list) list.insertBefore(row, list.firstChild);
        key.value = '';
        var count = $$('#ruleList .rule-row').length;
        var pill = $('.rules-card .card-head .pill.green');
        if (pill) pill.textContent = count + ' 条生效';
        toast('规则已生效，正在回溯最近 7 天评论');
      }
      if (API.enabled()) {
        API.post('/comments/rules', { keyword: word, category: category })
          .then(function () { addLocalRule(); loadComments(currentCommentFilter); })
          .catch(addLocalRule);
      } else {
        addLocalRule();
      }
    });
  }

  if ($('#ruleKey')) {
    $('#ruleKey').addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); $('#addRule').click(); }
    });
  }

  if ($('#syncComments')) {
    $('#syncComments').addEventListener('click', function () {
      if (API.enabled()) {
        API.get('/comments', { filter: 'all' }).then(function (data) {
          renderComments(data);
          toast('已同步 ' + (data.total || 0).toLocaleString('en-US') + ' 条评论 · 新增 12 条');
        }).catch(function () {
          toast('已同步 1,284 条评论 · 新增 12 条');
        });
      } else {
        toast('已同步 1,284 条评论 · 新增 12 条');
      }
    });
  }

  if ($('#exportInsight')) {
    $('#exportInsight').addEventListener('click', function () {
      var md = [
        '# 评论洞察报告',
        '',
        '- 账号：林序 · AI 效率创作者',
        '- 数据范围：近 7 天 · 6 条作品 · 1,284 条评论',
        '- 生成时间：2026-10-22',
        '',
        '## 情绪分布',
        '- 好评认可 46%',
        '- 需求建议 28%',
        '- 情绪共鸣 17%',
        '- 负面反馈 9%',
        '',
        '## 三个行动信号',
        '1. 会议纪要模板完整版（47 条相似）→ 做 3 分钟教程，评论置顶。',
        '2. 讲得太快、第三步没跟上（23 条相似）→ 插入 5 秒图解卡。',
        '3. 30 天实验真实感强（61 条相似）→ 沉淀为账号亲测体公式。',
        '',
        '## 高频关键词',
        'AI 286 · 效率 214 · 打工人 188 · 周报 154 · 会议纪要 132 · 模板 118'
      ].join('\n');
      download('creator-os-评论洞察-2026-10-22.md', md);
      toast('洞察报告已导出');
    });
  }

  /* ---------------- 05 爆款知识库 ---------------- */
  var hitData = [
    {
      id: 'local_h0', title: '我把 ChatGPT 当同事用了 30 天，效率提升了 3 倍',
      meta: [['green', '完播率 38.2%'], ['', '3 秒留存 62.4%'], ['', '分享率 4.8%']],
      dims: {
        hook: '<b>结果前置 + 身份代入</b><br>第一句先给结果，第二句绑定「打工人」身份。',
        emotion: '<b>职场焦虑 → 掌控感</b><br>先承认被工作追着跑，再给出可控的小胜利。',
        structure: '<b>痛点 → 反常识 → 方法 → 结果</b><br>每个段落只承担一个叙事任务，信息密度高。',
        visual: '<b>大字幕 + 桌面实拍</b><br>关键结果用全屏大字卡停顿 0.8 秒，强化记忆。',
        cta: '<b>评论区领模板</b><br>用「整理好了」替代「点赞关注」，降低反感。'
      },
      formula: '可复用公式：<b>结果前置</b> → 真实实验 → 反常识转折 → 可复用清单 → 低门槛 CTA。',
      structure: [
        { label: '钩子 18%', w: 18, bg: '#c3ed5a', fg: '#1a2414', legend: '0–3s 钩子' },
        { label: '痛点 27%', w: 27, bg: '#1f6b4e', fg: '#fff', legend: '3–12s 痛点' },
        { label: '方法 38%', w: 38, bg: '#9cc7b3', fg: '', legend: '12–45s 方法' },
        { label: 'CTA 17%', w: 17, bg: '#e2592f', fg: '#fff', legend: '45–58s CTA' }
      ]
    },
    {
      id: 'local_h1', title: '月薪 8000 和月薪 3 万的人，差在这一份周报',
      meta: [['green', '完播率 42.6%'], ['', '3 秒留存 71.3%'], ['', '分享率 6.2%']],
      dims: {
        hook: '<b>身份对比 + 数字锚点</b><br>「8000」和「3 万」同时出现，制造即时落差。',
        emotion: '<b>不公平感 → 希望</b><br>先让观众代入委屈，再给出可复制的路径。',
        structure: '<b>对比 → 归因 → 方法 → 结果</b><br>用两份真实周报做视觉证据。',
        visual: '<b>双屏对比 + 工资条</b><br>左右分屏，关键差异用红框圈出。',
        cta: '<b>评论区领模板</b><br>把「你怎么看」换成「要不要模板」，转化更直接。'
      },
      formula: '可复用公式：<b>身份对比</b> → 数据落差 → 结构拆解 → 模板交付。',
      structure: [
        { label: '钩子 15%', w: 15, bg: '#c3ed5a', fg: '#1a2414', legend: '0–3s 对比' },
        { label: '落差 25%', w: 25, bg: '#1f6b4e', fg: '#fff', legend: '3–12s 落差' },
        { label: '拆解 42%', w: 42, bg: '#9cc7b3', fg: '', legend: '12–45s 拆解' },
        { label: 'CTA 18%', w: 18, bg: '#e2592f', fg: '#fff', legend: '45–58s CTA' }
      ]
    },
    {
      id: 'local_h2', title: '一个人做自媒体的第 180 天：我留下了这 5 条经验',
      meta: [['green', '完播率 35.8%'], ['', '3 秒留存 58.9%'], ['', '收藏率 9.4%']],
      dims: {
        hook: '<b>时间节点 + 自曝</b><br>「第 180 天」自带故事感，观众想知道结果。',
        emotion: '<b>迷茫 → 笃定</b><br>不回避失败，用真实困境换取信任。',
        structure: '<b>时间线 → 5 条经验 → 邀请</b><br>清单体降低理解成本。',
        visual: '<b>日记感实拍 + 手写字幕</b><br>画面不精致，但真实感强。',
        cta: '<b>关注追更</b><br>把 CTA 变成「下一条见」，更像连载。'
      },
      formula: '可复用公式：<b>时间节点</b> → 真实困境 → 5 条清单 → 轻 CTA。',
      structure: [
        { label: '钩子 12%', w: 12, bg: '#c3ed5a', fg: '#1a2414', legend: '0–3s 节点' },
        { label: '困境 30%', w: 30, bg: '#1f6b4e', fg: '#fff', legend: '3–20s 困境' },
        { label: '清单 43%', w: 43, bg: '#9cc7b3', fg: '', legend: '20–50s 清单' },
        { label: 'CTA 15%', w: 15, bg: '#e2592f', fg: '#fff', legend: '50–58s CTA' }
      ]
    },
    {
      id: 'local_h3', title: '别再手动写周报了，这套模板救了我 100 次',
      meta: [['green', '完播率 40.1%'], ['', '3 秒留存 66.7%'], ['', '分享率 5.3%']],
      dims: {
        hook: '<b>痛点直击 + 数字</b><br>「手动写周报」是高频痛点，「100 次」增加可信度。',
        emotion: '<b>疲惫 → 被解救</b><br>先让观众点头，再给解决方案。',
        structure: '<b>痛点 → 模板展示 → 场景 → 领取</b><br>录屏证明模板真的可用。',
        visual: '<b>录屏 + 大字卡</b><br>模板结构用大字卡逐条停留。',
        cta: '<b>评论区领模板</b><br>「救了我 100 次」自然引出领取动机。'
      },
      formula: '可复用公式：<b>痛点直击</b> → 3 秒方案 → 场景验证 → 领取。',
      structure: [
        { label: '钩子 10%', w: 10, bg: '#c3ed5a', fg: '#1a2414', legend: '0–3s 痛点' },
        { label: '展示 22%', w: 22, bg: '#1f6b4e', fg: '#fff', legend: '3–15s 展示' },
        { label: '场景 50%', w: 50, bg: '#9cc7b3', fg: '', legend: '15–48s 场景' },
        { label: 'CTA 18%', w: 18, bg: '#e2592f', fg: '#fff', legend: '48–58s CTA' }
      ]
    },
    {
      id: 'local_h4', title: '我拒绝了月薪 5 万的 offer，因为算清了这笔账',
      meta: [['green', '完播率 44.3%'], ['', '3 秒留存 74.8%'], ['', '评论率 3.9%']],
      dims: {
        hook: '<b>反常识 + 身份</b><br>拒绝高薪本身违反直觉，观众会追问原因。',
        emotion: '<b>羡慕 → 身份认同</b><br>把「钱多」重新定义为「代价高」，引发讨论。',
        structure: '<b>悬念 → 算账 → 选择 → 观点</b><br>用白板把隐性成本可视化。',
        visual: '<b>真人出镜 + 白板</b><br>算账过程保留手写痕迹，增强真实感。',
        cta: '<b>开放式提问</b><br>结尾问「你会怎么选」，评论区自然活跃。'
      },
      formula: '可复用公式：<b>反常识</b> → 真实账本 → 价值排序 → 开放式提问。',
      structure: [
        { label: '钩子 16%', w: 16, bg: '#c3ed5a', fg: '#1a2414', legend: '0–3s 反差' },
        { label: '账本 28%', w: 28, bg: '#1f6b4e', fg: '#fff', legend: '3–18s 算账' },
        { label: '观点 40%', w: 40, bg: '#9cc7b3', fg: '', legend: '18–48s 观点' },
        { label: '提问 16%', w: 16, bg: '#e2592f', fg: '#fff', legend: '48–58s 提问' }
      ]
    },
    {
      id: 'local_h5', title: 'AI 工具清单：用了 60 个之后，我只留下了这 5 个',
      meta: [['green', '完播率 37.4%'], ['', '3 秒留存 63.1%'], ['', '收藏率 11.2%']],
      dims: {
        hook: '<b>减法 + 数字</b><br>「60 选 5」天然带有筛选价值，降低观众决策成本。',
        emotion: '<b>信息焦虑 → 清晰</b><br>先承认工具太多，再给出极简答案。',
        structure: '<b>总 → 分（5 个）→ 总结</b><br>每个工具只讲一个非用不可的理由。',
        visual: '<b>桌面俯拍 + 工具图标</b><br>用真实桌面展示使用频率。',
        cta: '<b>收藏清单</b><br>收藏比点赞更符合工具类内容的用户行为。'
      },
      formula: '可复用公式：<b>数字反差</b> → 淘汰理由 → 5 个留下 → 收藏。',
      structure: [
        { label: '钩子 14%', w: 14, bg: '#c3ed5a', fg: '#1a2414', legend: '0–3s 反差' },
        { label: '淘汰 26%', w: 26, bg: '#1f6b4e', fg: '#fff', legend: '3–15s 淘汰' },
        { label: '清单 46%', w: 46, bg: '#9cc7b3', fg: '', legend: '15–50s 清单' },
        { label: '收藏 14%', w: 14, bg: '#e2592f', fg: '#fff', legend: '50–58s CTA' }
      ]
    }
  ];

  var hitGraphs = [
    { topic: '30 天实验', identity: '一人公司', hook: '结果前置', emotion: '焦虑→释然', visual: '大字幕', rhythm: '3 秒反转', structure: '痛点→方法', cta: '领模板', core: '328.4w' },
    { topic: '周报对比', identity: '打工人', hook: '身份对比', emotion: '落差→希望', visual: '双屏对比', rhythm: '5 秒反转', structure: '对比→拆解', cta: '领模板', core: '612.8w' },
    { topic: '180 天记录', identity: '个人 IP', hook: '时间节点', emotion: '迷茫→笃定', visual: '日记实拍', rhythm: '慢节奏', structure: '时间线→清单', cta: '关注追更', core: '186.2w' },
    { topic: '周报模板', identity: '职场人', hook: '痛点直击', emotion: '疲惫→解救', visual: '录屏大字卡', rhythm: '3 秒切入', structure: '痛点→方案', cta: '领模板', core: '241.6w' },
    { topic: '拒绝 offer', identity: '高薪职场人', hook: '反常识', emotion: '羡慕→认同', visual: '真人白板', rhythm: '算账节奏', structure: '悬念→观点', cta: '开放提问', core: '98.4w' },
    { topic: '60 选 5', identity: '工具控', hook: '减法数字', emotion: '焦虑→清晰', visual: '桌面俯拍', rhythm: '清单节奏', structure: '总→分→总', cta: '收藏', core: '154.2w' }
  ];

  var backendHits = [];
  var currentHit = 0;
  var currentHitObj = null;

  function updateGraph(graph) {
    var g = graph || (currentHitObj && currentHitObj.graph) || hitGraphs[currentHit] || hitGraphs[0];
    Object.keys(g).forEach(function (key) {
      var node = $('.graph-node[data-node="' + key + '"]');
      if (!node) return;
      var texts = node.querySelectorAll('text');
      var target = texts[texts.length - 1];
      if (target) target.textContent = g[key];
    });
  }

  function normalizeHit(h) {
    if (!h) return null;
    var norm = { id: h.id, title: h.title, structure: h.structure || [], graph: h.graph || null };
    norm.meta = (h.meta || []).map(function (m) { return Array.isArray(m) ? m : [m.type || '', m.text]; });
    norm.dims = {};
    if (h.dims) {
      ['hook', 'emotion', 'structure', 'visual', 'cta'].forEach(function (k) {
        var v = h.dims[k];
        if (!v) return;
        if (/<[a-z][\s\S]*>/i.test(v)) {
          norm.dims[k] = v;
        } else {
          norm.dims[k] = '<b>' + esc(v) + '</b><br>' + esc(h.dims[k + '_note'] || '');
        }
      });
    }
    norm.formula = h.formula || (h.dims && h.dims.formula) || '可复用公式：结果前置 → 真实实验 → 反常识转折 → 可复用清单 → 低门槛 CTA。';
    return norm;
  }

  function renderHitDetail(h) {
    var norm = normalizeHit(h);
    if (!norm) return;
    $('#libDetailTitle').textContent = norm.title;
    $('#libDetailMeta').innerHTML = norm.meta.map(function (m) {
      return '<span class="pill ' + m[0] + '">' + esc(m[1]) + '</span>';
    }).join('');
    $('#dimHook').innerHTML = norm.dims.hook || '';
    $('#dimEmotion').innerHTML = norm.dims.emotion || '';
    $('#dimStructure').innerHTML = norm.dims.structure || '';
    $('#dimVisual').innerHTML = norm.dims.visual || '';
    $('#dimCta').innerHTML = norm.dims.cta || '';
    $('#libFormula').innerHTML = norm.formula;
    $('#structureBar').innerHTML = norm.structure.map(function (s) {
      return '<div style="width:' + s.w + '%;background:' + s.bg + ';' + (s.fg ? 'color:' + s.fg + ';' : '') + '">' + s.label + '</div>';
    }).join('');
    var legend = $('.structure-legend');
    if (legend) {
      legend.innerHTML = norm.structure.map(function (s) {
        return '<span><i style="background:' + s.bg + '"></i>' + s.legend + '</span>';
      }).join('');
    }
    updateGraph(norm.graph);
  }

  function selectHit(index) {
    var h = backendHits[index] || hitData[index];
    if (!h) return;
    currentHit = index;
    currentHitObj = h;
    $$('#hitGrid .hit-card').forEach(function (c) {
      c.classList.toggle('active', Number(c.dataset.hit) === index);
    });
    if (API.enabled() && h.id && String(h.id).indexOf('local_') !== 0) {
      API.get('/hits/' + h.id).then(function (detail) {
        if (detail && detail.title) renderHitDetail(detail);
      }).catch(function () { renderHitDetail(h); });
    } else {
      renderHitDetail(h);
    }
  }

  function buildHitCard(h, idx) {
    var kindLabel = h.kind === 'analyzed' ? '已拆解' : '已收藏';
    var coverClass = 'hc' + ((idx % 6) + 1);
    var metric = '播放 ' + (h.plays || '—') + ' · 点赞 ' + (h.likes || '—');
    var tags = (h.tags || []).map(function (t) { return '<span class="pill ' + (t.indexOf('钩子') > -1 ? 'lime' : '') + '">' + esc(t) + '</span>'; }).join('');
    return '<article class="hit-card' + (idx === 0 ? ' active' : '') + '" data-hit="' + idx + '" data-kind="' + esc(h.kind) + '">' +
      '<div class="hit-cover ' + coverClass + '"><span class="idx">' + (h.idx || ('0' + (idx + 1)).slice(-2)) + '</span><span class="tag-abs">' + kindLabel + '</span><span class="metric">' + esc(metric) + '</span></div>' +
      '<div class="hit-info"><div class="hit-title">' + esc(h.title) + '</div><div class="hit-meta">' + tags + '</div></div>' +
    '</article>';
  }

  function renderHitGrid(data) {
    var grid = $('#hitGrid');
    if (!grid || !data || !data.hits || !data.hits.length) return;
    backendHits = data.hits;
    grid.innerHTML = backendHits.map(buildHitCard).join('');
    applyLibFilter();
    selectHit(0);
  }

  function loadHits(kind) {
    kind = kind || 'all';
    if (API.enabled()) {
      API.get('/hits', { kind: kind }).then(renderHitGrid).catch(function () {
        backendHits = [];
        applyLibFilter();
      });
    } else {
      backendHits = [];
      applyLibFilter();
    }
  }

  var hitGrid = $('#hitGrid');
  if (hitGrid) {
    hitGrid.addEventListener('click', function (e) {
      var card = e.target.closest('.hit-card');
      if (!card) return;
      selectHit(Number(card.dataset.hit));
    });
  }

  var libKind = 'all';
  var libQuery = '';
  function applyLibFilter() {
    var q = libQuery.trim().toLowerCase();
    var visible = 0;
    $$('#hitGrid .hit-card').forEach(function (card) {
      var kindOk = libKind === 'all' || card.dataset.kind === libKind;
      var textOk = !q || card.textContent.toLowerCase().indexOf(q) > -1;
      var ok = kindOk && textOk;
      card.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });
    var grid = $('#hitGrid');
    var empty = $('#libEmpty');
    if (!empty && grid) {
      empty = D.createElement('div');
      empty.id = 'libEmpty';
      empty.className = 'cmd-empty hidden';
      empty.textContent = '没有找到匹配的爆款，换个关键词试试';
      grid.parentNode.insertBefore(empty, grid.nextSibling);
    }
    if (empty) empty.classList.toggle('hidden', visible > 0);
  }

  if ($('#libTabs')) {
    $('#libTabs').addEventListener('click', function (e) {
      var btn = e.target.closest('[data-lib-tab]');
      if (!btn) return;
      libKind = btn.dataset.libTab;
      $$('#libTabs button').forEach(function (b) { b.classList.toggle('active', b === btn); });
      if (API.enabled()) {
        loadHits(libKind);
      } else {
        applyLibFilter();
      }
    });
  }

  if ($('#libSearch')) {
    $('#libSearch').addEventListener('input', function () {
      libQuery = $('#libSearch').value;
      applyLibFilter();
    });
  }

  var graphNodes = $$('.graph-node');
  var graphLinks = $$('.graph-link');
  function resetGraph() {
    graphNodes.forEach(function (n) { n.style.opacity = ''; });
    graphLinks.forEach(function (l) { l.style.opacity = ''; });
  }
  graphNodes.forEach(function (node) {
    node.addEventListener('mouseenter', function () {
      var id = node.dataset.node;
      var keep = {};
      keep[id] = true;
      graphLinks.forEach(function (l) {
        if (l.dataset.a === id) keep[l.dataset.b] = true;
        if (l.dataset.b === id) keep[l.dataset.a] = true;
      });
      graphNodes.forEach(function (n) {
        n.style.opacity = keep[n.dataset.node] ? '1' : '.22';
      });
      graphLinks.forEach(function (l) {
        l.style.opacity = (l.dataset.a === id || l.dataset.b === id) ? '1' : '.12';
      });
    });
    node.addEventListener('mouseleave', resetGraph);
  });

  function renderReco(rec) {
    var box = $('#recoResults');
    var texts = $$('.reco-text', box);
    var btns = $$('[data-copy]', box);
    if (texts[0]) texts[0].textContent = '“' + (rec.hook || '') + '”';
    if (texts[1]) texts[1].innerHTML = (rec.structure || '').replace(/；/g, ' · ');
    if (texts[2]) texts[2].textContent = rec.emotion || '';
    if (btns[0]) btns[0].dataset.copy = rec.hook || '';
    if (btns[1]) btns[1].dataset.copy = rec.structure || '';
    if (btns[2]) btns[2].dataset.copy = rec.emotion || '';
    box.style.opacity = '1';
  }

  function renderRecoLocal(topic) {
    renderReco({
      hook: '「' + topic + '」这件事，我一开始也不信，直到它帮我省下了每天 2 小时。今天把完整流程拆给你。',
      structure: '0–3s 结果前置；3–12s 真实场景；12–45s 三步方法；45–58s 评论区领模板。',
      emotion: '从「被琐事追着跑」的疲惫，过渡到「重新掌控时间」的轻松。'
    });
    toast('已按「' + topic + '」生成同款内容结构');
  }

  if ($('#genReco')) {
    $('#genReco').addEventListener('click', function () {
      var topic = $('#recoTopic').value.trim() || 'AI 会议纪要工作流';
      var box = $('#recoResults');
      box.style.opacity = '.3';
      if (API.enabled()) {
        var hit = backendHits[currentHit] || hitData[currentHit] || {};
        API.post('/hits/recommendations', { hitId: hit.id }).then(function (res) {
          renderReco(res.recommendation || res);
          toast('已按「' + topic + '」生成同款内容结构');
        }).catch(function () { renderRecoLocal(topic); });
      } else {
        setTimeout(function () { renderRecoLocal(topic); }, 700);
      }
    });
  }

  if ($('#applyStructure')) {
    $('#applyStructure').addEventListener('click', function () {
      go('topics');
      selectTopic(0);
      setTimeout(function () { openDraft(); toast('已把爆款结构应用到当前选题 · 可一键生成初稿'); }, 260);
    });
  }

  if ($('#exportLib')) {
    $('#exportLib').addEventListener('click', function () {
      var h = backendHits[currentHit] || hitData[currentHit];
      if (!h) return;
      var norm = normalizeHit(h);
      var md = [
        '# 爆款拆解 · ' + h.title,
        '',
        '## 六维拉片',
        '- Hook：' + (norm.dims.hook || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(),
        '- Emotion：' + (norm.dims.emotion || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(),
        '- Structure：' + (norm.dims.structure || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(),
        '- Visual：' + (norm.dims.visual || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(),
        '- CTA：' + (norm.dims.cta || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim(),
        '',
        '## 可复用公式',
        norm.formula.replace(/<[^>]+>/g, '').trim()
      ].join('\n');
      download('creator-os-爆款拆解-' + (currentHit + 1) + '.md', md);
      toast('拆解报告已导出');
    });
  }

  if ($('#importFileZone')) {
    $('#importFileZone').addEventListener('click', function () {
      $('#importFileZone').innerHTML = '<svg width="20" height="20"><use href="#i-check"/></svg> 已选择示例视频.mp4 · 点击开始拆解';
      $('#importFileZone').dataset.selected = '1';
    });
  }

  function addImportedHit(rawTitle) {
    var idx = hitData.length;
    var title = rawTitle || 'AI 效率工具盘点 · 新导入爆款';
    var short = title.length > 22 ? title.slice(0, 22) + '…' : title;
    hitData.push({
      id: 'local_h' + idx,
      title: title,
      meta: [['green', '完播率 36.5%'], ['', '3 秒留存 59.2%'], ['', '收藏率 7.8%']],
      dims: {
        hook: '<b>痛点提问 + 数字</b><br>先用一个高频问题抓住注意力。',
        emotion: '<b>焦虑 → 清晰</b><br>让观众从信息过载中感到被解救。',
        structure: '<b>问题 → 答案 → 清单</b><br>结构简单，降低理解成本。',
        visual: '<b>桌面实拍 + 大字卡</b><br>关键工具用大字卡停留 1 秒。',
        cta: '<b>收藏 + 关注</b><br>引导收藏，符合工具类内容行为。'
      },
      formula: '可复用公式：<b>痛点提问</b> → 数字锚点 → 3 个答案 → 收藏关注。',
      structure: [
        { label: '钩子 18%', w: 18, bg: '#c3ed5a', fg: '#1a2414', legend: '0–3s 提问' },
        { label: '答案 22%', w: 22, bg: '#1f6b4e', fg: '#fff', legend: '3–12s 答案' },
        { label: '清单 48%', w: 48, bg: '#9cc7b3', fg: '', legend: '12–50s 清单' },
        { label: 'CTA 12%', w: 12, bg: '#e2592f', fg: '#fff', legend: '50–58s 收藏' }
      ]
    });
    hitGraphs.push({ topic: '新导入', identity: '创作者', hook: '痛点提问', emotion: '焦虑→清晰', visual: '桌面实拍', rhythm: '清单节奏', structure: '问题→清单', cta: '收藏关注', core: '待验证' });
    var article = D.createElement('article');
    article.className = 'hit-card';
    article.dataset.hit = String(idx);
    article.dataset.kind = 'analyzed';
    article.innerHTML = '<div class="hit-cover hc6"><span class="idx">0' + (idx + 1) + '</span><span class="tag-abs">已拆解</span><span class="metric">导入作品 · 待验证</span></div><div class="hit-info"><div class="hit-title">' + esc(short) + '</div><div class="hit-meta"><span class="pill lime">导入</span><span class="pill">AI 自动拆解</span></div></div>';
    if (hitGrid) hitGrid.appendChild(article);
    selectHit(idx);
    go('library');
  }

  function addBackendHit(hit) {
    var idx = backendHits.length;
    backendHits.push(hit);
    var short = hit.title.length > 22 ? hit.title.slice(0, 22) + '…' : hit.title;
    var coverClass = 'hc' + ((idx % 6) + 1);
    var article = D.createElement('article');
    article.className = 'hit-card';
    article.dataset.hit = String(idx);
    article.dataset.kind = hit.kind || 'analyzed';
    var tags = (hit.tags || []).map(function (t) { return '<span class="pill ' + (t.indexOf('钩子') > -1 ? 'lime' : '') + '">' + esc(t) + '</span>'; }).join('');
    if (!tags) tags = '<span class="pill lime">导入</span><span class="pill">AI 自动拆解</span>';
    var metric = '导入作品 · ' + (hit.plays || '待验证');
    article.innerHTML = '<div class="hit-cover ' + coverClass + '"><span class="idx">0' + (idx + 1) + '</span><span class="tag-abs">已拆解</span><span class="metric">' + esc(metric) + '</span></div><div class="hit-info"><div class="hit-title">' + esc(short) + '</div><div class="hit-meta">' + tags + '</div></div>';
    if (hitGrid) hitGrid.appendChild(article);
    applyLibFilter();
    selectHit(idx);
    go('library');
  }

  if ($('#importStart')) {
    $('#importStart').addEventListener('click', function () {
      var link = $('#importLink').value.trim();
      var selected = $('#importFileZone').dataset.selected === '1';
      if (!link && !selected) {
        toast('先粘贴作品链接，或上传一个视频');
        return;
      }
      closeModals();
      toast('已开始 6 维拉片 · 预计 30 秒完成');
      if (API.enabled()) {
        API.post('/hits/analyze', { url: link || '示例视频' }).then(function (res) {
          var hit = res.hit || res;
          addBackendHit(hit);
          toast('拆解完成，已加入你的爆款知识库');
        }).catch(function () {
          setTimeout(function () {
            addImportedHit(link || '示例视频 · AI 会议纪要工作流');
            toast('拆解完成，已加入你的爆款知识库');
          }, 1500);
        });
      } else {
        setTimeout(function () {
          addImportedHit(link || '示例视频 · AI 会议纪要工作流');
          toast('拆解完成，已加入你的爆款知识库');
        }, 1500);
      }
    });
  }

  /* ---------------- 06 商业变现 ---------------- */
  var scripts = {
    first: '你好，感谢关注。我的账号主要面向 25–35 岁的职场效率人群，近 30 天平均播放 46 万、互动率 6.8%。<b>方便先同步一下品牌目标、预算区间和期望上线时间吗？</b>我会据此给出一版内容方案和报价。',
    quote: '理解预算差异。我的单条口播报价是 ¥18,500，包含脚本、拍摄、剪辑与一次修改；图文 + 授权套餐价 ¥26,000。这个价格基于近 30 天平均 46 万播放与 6.8% 互动率，<b>如果预算区间不同，我们可以调整内容形式，而不是压低价。</b>',
    follow: '你好，同步一下本期合作的尾款节点是 11 月 5 日，发票已在上周寄出。方便的话今天同步一下流程进度？<b>如果都已走完，麻烦回我一个确认，我好安排下一条排期。</b>'
  };

  function renderPipeline(pipeline) {
    var wrap = $('.pipeline');
    if (!wrap || !pipeline) return;
    wrap.innerHTML = pipeline.map(function (stage) {
      var cardsHtml = (stage.cards || []).map(function (c) {
        var statusClass = c.status === '待回复' ? 'orange' : c.status === '已发' ? '' : c.status === '高意向' ? 'lime' : c.status === '已结款' ? 'green' : '';
        return '<div class="pipe-card"><div class="pipe-brand"><div class="brand-logo">' + esc(c.logo) + '</div><b>' + esc(c.brand) + '</b>' + (statusClass ? '<span class="pill ' + statusClass + '" style="height:16px;font-size:7px">' + esc(c.status) + '</span>' : '') + '</div><div class="pipe-project">' + esc(c.project) + '</div><div class="pipe-foot"><span class="pipe-price">' + esc(c.price) + '</span><span class="pipe-date">' + esc(c.deadline) + '</span></div></div>';
      }).join('');
      return '<div class="pipe-col"><div class="pipe-head"><b>' + esc(stage.stage) + '</b><span>' + (stage.count || (stage.cards || []).length) + '</span></div><div class="pipe-cards">' + cardsHtml + '</div></div>';
    }).join('');
  }

  function renderBrands(brands) {
    var list = $('.eco-list');
    if (!list || !brands) return;
    list.innerHTML = brands.map(function (b) {
      var logo = b.name ? b.name.charAt(0) : '品';
      var tags = (b.tags || []).map(function (t) { return '<span class="pill">' + esc(t) + '</span>'; }).join('');
      var statusClass = b.status === '可对接' ? 'green' : b.status === '高意向' ? 'lime' : b.status === '沟通中' ? 'orange' : '';
      return '<div class="eco-row"><div class="eco-logo">' + esc(logo) + '</div><div class="eco-main"><b>' + esc(b.name) + '</b><span>' + esc(b.industry) + ' · ' + esc(b.status) + ' · 匹配度 ' + b.match + '%</span></div><div class="eco-tags">' + (statusClass ? '<span class="pill ' + statusClass + '">' + esc(b.status) + '</span>' : '') + tags + '</div><button class="btn btn-ghost btn-sm">发起合作</button></div>';
    }).join('');
  }

  function loadMoneyPage() {
    if (!API.enabled()) return;
    Promise.all([
      API.get('/monetize/brands', { refresh: 0 }),
      API.get('/monetize/pipeline')
    ]).then(function (res) {
      renderBrands(res[0].brands);
      renderPipeline(res[1].pipeline);
    }).catch(function () {});
  }

  if ($('#scriptTabs')) {
    $('#scriptTabs').addEventListener('click', function (e) {
      var btn = e.target.closest('[data-script-tab]');
      if (!btn) return;
      $$('.filter-chip', $('#scriptTabs')).forEach(function (b) { b.classList.toggle('active', b === btn); });
      var tab = btn.dataset.scriptTab;
      if (API.enabled()) {
        API.get('/monetize/scripts', { path: tab }).then(function (res) {
          var content = res.content || (res.data && res.data.content) || scripts[tab] || scripts.first;
          $('#scriptBlock').innerHTML = content;
          toast('已切换为「' + btn.textContent.trim() + '」话术');
        }).catch(function () {
          $('#scriptBlock').innerHTML = scripts[tab] || scripts.first;
          toast('已切换为「' + btn.textContent.trim() + '」话术');
        });
      } else {
        $('#scriptBlock').innerHTML = scripts[tab] || scripts.first;
        toast('已切换为「' + btn.textContent.trim() + '」话术');
      }
    });
  }

  if ($('#syncBrands')) {
    $('#syncBrands').addEventListener('click', function () {
      if (API.enabled()) {
        Promise.all([
          API.get('/monetize/brands', { refresh: 1 }),
          API.get('/monetize/pipeline')
        ]).then(function (res) {
          renderBrands(res[0].brands);
          renderPipeline(res[1].pipeline);
          toast('品牌库与合作管道已同步');
        }).catch(function () {
          toast('品牌库已同步 · 新增 3 个匹配品牌');
        });
      } else {
        var counts = [2, 3, 1, 4];
        $$('.pipeline .pipe-head span').forEach(function (el, i) {
          el.textContent = counts[i] || el.textContent;
        });
        toast('品牌库已同步 · 新增 3 个匹配品牌');
      }
    });
  }

  if ($('#applyEco')) {
    $('#applyEco').addEventListener('click', function () {
      toast('入驻申请已提交，顾问会在 1 个工作日内联系你');
    });
  }

  D.addEventListener('click', function (e) {
    var card = e.target.closest('.pipe-card');
    if (card) {
      var brand = $('.pipe-brand b', card);
      toast('已打开「' + (brand ? brand.textContent : '品牌') + '」合作详情');
      return;
    }
    var ecoBtn = e.target.closest('.eco-row .btn');
    if (ecoBtn) {
      toast(ecoBtn.textContent.trim() === '查看进度' ? '已打开 MOKA 合作进度' : '已发送合作意向');
    }
  });

  window.addEventListener('creator:page', function (e) {
    if (e.detail && e.detail.page === 'money') loadMoneyPage();
  });

  if ($('#publishPortfolio')) {
    $('#publishPortfolio').addEventListener('click', function () {
      var modal = $('#portfolioModal');
      var left = $('.modal-foot .left', modal);
      if (left) left.textContent = '最后更新 · 刚刚';
      var link = 'https://ulyssestaylor64-sys.github.io/creator-os/portfolio?u=linxu';
      copyText(link, '作品集链接已复制');
      toast('作品集已发布 · 旧链接自动失效');
    });
  }
  if ($('#exportPortfolio')) {
    $('#exportPortfolio').addEventListener('click', function () {
      var md = [
        '# 林序 · AI 效率创作者',
        '',
        '一人公司研究所 · 职场 AI 提效 · 25–35 岁职场人',
        '',
        '## 账号数据',
        '- 粉丝：12.8w',
        '- 累计播放：1,240w',
        '- 平均互动率：6.8%',
        '- 合作品牌：9',
        '',
        '## 代表作品',
        '1. 我把 ChatGPT 当同事用了 30 天（328.4w 播放）',
        '2. 别再手动写周报了（241.6w 播放）',
        '3. 一个人做自媒体的第 180 天（186.2w 播放）',
        '',
        '## 合作报价',
        '- 口播视频：¥18,500 / 条',
        '- 图文 + 授权：¥26,000 / 套'
      ].join('\n');
      download('creator-os-账号作品集.md', md);
      toast('作品集已导出');
    });
  }

  /* ---------------- 抽屉：AI 与数据设置 ---------------- */
  var selectedModel = store.get('model', 'GLM-5.3-Flash');
  var selectedStorage = store.get('storage', 'local');

  function labelForModel(m) {
    return m.indexOf('本地') === 0 ? 'Ollama 本地' : m;
  }

  function syncSettings() {
    $$('.model-option').forEach(function (opt) {
      opt.classList.toggle('on', opt.dataset.model === selectedModel);
    });
    $$('.storage-opt[data-storage]').forEach(function (opt) {
      opt.classList.toggle('on', opt.dataset.storage === selectedStorage);
    });
    var chip = $('#modelChipLabel');
    if (chip) chip.textContent = labelForModel(selectedModel);
    var rules = store.get('rules', null);
    if (rules && $('#aiRules')) $('#aiRules').value = rules;
  }

  $$('.model-option').forEach(function (opt) {
    opt.addEventListener('click', function () {
      selectedModel = opt.dataset.model;
      $$('.model-option').forEach(function (o) { o.classList.toggle('on', o === opt); });
    });
  });

  $$('.storage-opt[data-storage]').forEach(function (opt) {
    opt.addEventListener('click', function () {
      selectedStorage = opt.dataset.storage;
      $$('.storage-opt[data-storage]').forEach(function (o) { o.classList.toggle('on', o === opt); });
      toast(selectedStorage === 'local' ? '已切换为本地优先存储' : '已开启端到端加密云同步');
    });
  });

  if ($('#aiSave')) {
    $('#aiSave').addEventListener('click', function () {
      store.set('model', selectedModel);
      store.set('storage', selectedStorage);
      if ($('#aiRules')) store.set('rules', $('#aiRules').value);
      var chip = $('#modelChipLabel');
      if (chip) chip.textContent = labelForModel(selectedModel);
      closeDrawers();
      toast('AI 与数据设置已保存');
    });
  }

  if ($('#backupNow')) {
    $('#backupNow').addEventListener('click', function () {
      $$('#aiDrawer .setting-label span').forEach(function (s) {
        if (s.textContent.indexOf('最近') === 0) s.textContent = '刚刚';
      });
      toast('备份完成 · 128 MB 内容资产已加密上传');
    });
  }

  syncSettings();

  /* ---------------- 帮助抽屉 ---------------- */
  D.addEventListener('click', function (e) {
    var tab = e.target.closest('[data-tab]');
    if (!tab) return;
    var scope = tab.closest('.drawer') || tab.closest('.modal') || D;
    $$('.tab', scope).forEach(function (t) { t.classList.toggle('active', t === tab); });
    $$('[data-tab-pane]', scope).forEach(function (p) {
      p.classList.toggle('active', p.dataset.tabPane === tab.dataset.tab);
    });
  });

  $$('.faq-q').forEach(function (q) {
    q.addEventListener('click', function () {
      var item = q.closest('.faq-item');
      item.classList.toggle('open');
    });
  });

  if ($('#joinCommunity')) {
    $('#joinCommunity').addEventListener('click', function () {
      toast('已提交入群申请 · 请留意通知中心');
    });
  }
  if ($('#contactAdvisor')) {
    $('#contactAdvisor').addEventListener('click', function () {
      toast('已为你接通创作顾问，工作日 10:00–19:00 在线');
    });
  }

  /* ---------------- 签到与积分 ---------------- */
  var points = Number(store.get('points', 1280)) || 1280;
  var checkedIn = !!store.get('checkedIn', false);

  function refreshPoints() {
    var txt = points.toLocaleString('en-US');
    if ($('#sidePoints')) $('#sidePoints').textContent = txt + ' pts';
    if ($('#modalPoints')) $('#modalPoints').textContent = txt;
    if ($('#pointsBig')) $('#pointsBig').textContent = txt;
  }

  function refreshCheckinBtn() {
    var btn = $('#checkinAction');
    if (!btn) return;
    if (checkedIn) {
      btn.innerHTML = '<svg width="12" height="12"><use href="#i-check"/></svg> 今日已签到';
    } else {
      btn.innerHTML = '<svg width="12" height="12"><use href="#i-zap"/></svg> 签到 +10';
    }
    var side = $('#sideCheckin');
    if (side) {
      side.innerHTML = checkedIn
        ? '<svg width="12" height="12"><use href="#i-check"/></svg> 今日已签到'
        : '<svg width="12" height="12"><use href="#i-zap"/></svg> 今日签到 +10';
    }
    var today = $('.checkin-day.today');
    if (today && checkedIn) today.classList.add('on');
  }

  if ($('#sideCheckin')) {
    $('#sideCheckin').addEventListener('click', function () { openLayer('checkin'); });
  }
  if ($('#checkinAction')) {
    $('#checkinAction').addEventListener('click', function () {
      if (checkedIn) { toast('今天已经签到过了，明天再来'); return; }
      checkedIn = true;
      points += 10;
      store.set('points', points);
      store.set('checkedIn', true);
      refreshPoints();
      refreshCheckinBtn();
      toast('签到成功 · +10 创作积分');
    });
  }

  var prizes = [
    'AI 初稿生成次数 ×3',
    '创作者模板包 · 效率周报',
    'Pro 体验 3 天',
    '50 积分返还',
    '创作者周边 · 帆布包'
  ];

  if ($('#drawBtn')) {
    $('#drawBtn').addEventListener('click', function () {
      if (points < 50) { toast('积分不足，先完成今天的创作任务吧'); return; }
      points -= 50;
      store.set('points', points);
      refreshPoints();
      var prize = prizes[Math.floor(Math.random() * prizes.length)];
      var out = $('#prizeOut');
      if (out) out.textContent = '恭喜获得：' + prize;
      toast('抽奖结果：' + prize);
    });
  }

  refreshPoints();
  refreshCheckinBtn();

  /* ---------------- 定价 ---------------- */
  if ($('#billingToggle')) {
    $('#billingToggle').addEventListener('click', function (e) {
      var btn = e.target.closest('[data-billing]');
      if (!btn) return;
      var mode = btn.dataset.billing;
      $$('button', $('#billingToggle')).forEach(function (b) { b.classList.toggle('active', b === btn); });
      $$('.plan-price').forEach(function (p) {
        var val = mode === 'year' ? p.dataset.annual : p.dataset.monthly;
        if (val !== undefined) p.innerHTML = '¥<span>' + val + '</span><small>/月</small>';
      });
    });
  }

  D.addEventListener('click', function (e) {
    var planBtn = e.target.closest('[data-plan]');
    if (!planBtn) return;
    var plan = planBtn.dataset.plan;
    if (plan === '免费版') { toast('你当前正在使用免费版'); return; }
    closeModals();
    if (plan === '工作室') {
      toast('已提交工作室咨询，顾问会在 1 个工作日内联系你');
      return;
    }
    var profile = $('.profile-plan');
    if (profile) profile.textContent = plan + ' · 试用中';
    toast('已开启 7 天 ' + plan + ' 试用');
  });

  /* ---------------- 通知中心 ---------------- */
  if ($('#markAllRead')) {
    $('#markAllRead').addEventListener('click', function () {
      var dot = $('button[data-open="notifications"] .dot');
      if (dot) dot.remove();
      var head = $('#notificationsModal .modal-head p');
      if (head) head.textContent = '全部已读 · 暂无新通知';
      closeModals();
      toast('通知已全部标为已读');
    });
  }

  /* ---------------- 全局搜索 ---------------- */
  var commands = [
    { group: '页面', label: '工作台总览', hint: '01', icon: 'i-grid', run: function () { go('overview'); } },
    { group: '页面', label: '赛道自测', hint: '02', icon: 'i-compass', run: function () { go('niche'); } },
    { group: '页面', label: '每日选题', hint: '03', icon: 'i-spark', run: function () { go('topics'); } },
    { group: '页面', label: '评论洞察', hint: '04', icon: 'i-chat', run: function () { go('comments'); } },
    { group: '页面', label: '爆款知识库', hint: '05', icon: 'i-layers', run: function () { go('library'); } },
    { group: '页面', label: '商业变现', hint: '06', icon: 'i-wallet', run: function () { go('money'); } },
    { group: '操作', label: '今日签到 +10', hint: '积分', icon: 'i-zap', run: function () { openLayer('checkin'); } },
    { group: '操作', label: '生成 AI 初稿', hint: 'AI', icon: 'i-pen', run: openDraft },
    { group: '操作', label: 'AI 与数据设置', hint: '设置', icon: 'i-settings', run: function () { openLayer('ai'); } },
    { group: '操作', label: '升级创作者 Pro', hint: '价格', icon: 'i-zap', run: function () { openLayer('pricing'); } },
    { group: '操作', label: '导入作品拆解', hint: '知识库', icon: 'i-upload', run: function () { openLayer('import'); } },
    { group: '操作', label: '预览账号作品集', hint: '商业', icon: 'i-file', run: function () { openLayer('portfolio'); } }
  ];

  var baseCmdCount = commands.length;
  var cmdMatches = [];
  var cmdSelected = 0;

  function allCommands() {
    var list = commands.slice();
    topicData.forEach(function (t, i) {
      list.push({
        group: '选题',
        label: t.title,
        hint: '匹配 ' + t.match + '%',
        icon: 'i-spark',
        run: function () { go('topics'); selectTopic(i); }
      });
    });
    return list;
  }

  function renderCmd(query) {
    var box = $('#cmdResults');
    if (!box) return;
    var q = (query || '').toLowerCase().trim();
    cmdMatches = allCommands().filter(function (c) {
      return !q || (c.label + ' ' + c.group).toLowerCase().indexOf(q) > -1;
    });
    cmdSelected = 0;

    if (!cmdMatches.length) {
      box.innerHTML = '<div class="cmd-empty">没有找到相关内容，试试「选题」「签到」或「设置」</div>';
      return;
    }

    var html = '';
    var lastGroup = '';
    cmdMatches.forEach(function (c, i) {
      if (c.group !== lastGroup) {
        html += '<div class="cmd-group-label">' + c.group + '</div>';
        lastGroup = c.group;
      }
      html += '<button class="cmd-item' + (i === 0 ? ' sel' : '') + '" data-cmd-index="' + i + '">' +
        '<span class="ic"><svg width="13" height="13"><use href="#' + c.icon + '"/></svg></span>' +
        '<span>' + esc(c.label) + '</span>' +
        '<span class="go">' + c.hint + '</span>' +
        '</button>';
    });
    box.innerHTML = html;
  }

  function moveCmd(dir) {
    if (!cmdMatches.length) return;
    cmdSelected = (cmdSelected + dir + cmdMatches.length) % cmdMatches.length;
    $$('#cmdResults .cmd-item').forEach(function (el, i) {
      el.classList.toggle('sel', i === cmdSelected);
      if (i === cmdSelected) el.scrollIntoView({ block: 'nearest' });
    });
  }

  function runCmd(index) {
    var cmd = cmdMatches[index];
    if (!cmd) return;
    closeModals();
    setTimeout(function () { cmd.run(); }, 40);
  }

  if ($('#cmdTrigger')) {
    $('#cmdTrigger').addEventListener('click', function () { openLayer('cmd'); });
  }
  if ($('#cmdInput')) {
    $('#cmdInput').addEventListener('input', function () { renderCmd($('#cmdInput').value); });
    $('#cmdInput').addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); moveCmd(1); }
      if (e.key === 'ArrowUp') { e.preventDefault(); moveCmd(-1); }
      if (e.key === 'Enter') { e.preventDefault(); runCmd(cmdSelected); }
    });
  }
  if ($('#cmdResults')) {
    $('#cmdResults').addEventListener('click', function (e) {
      var item = e.target.closest('[data-cmd-index]');
      if (!item) return;
      runCmd(Number(item.dataset.cmdIndex));
    });
  }

  D.addEventListener('keydown', function (e) {
    var meta = e.metaKey || e.ctrlKey;
    if (meta && (e.key === 'k' || e.key === 'K')) {
      e.preventDefault();
      openLayer('cmd');
      return;
    }
    if (e.key === 'Escape') {
      closeModals();
      closeDrawers();
      closeSidebar();
      resetGraph();
    }
  });

  /* ---------------- 初始状态 ---------------- */
  resetGraph();
  selectTopic(0);
  selectHit(0);
  applyLibFilter();
})();
