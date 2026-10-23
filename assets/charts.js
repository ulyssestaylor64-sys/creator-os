/* =========================================================
   Creator OS — 图表模块
   ECharts 初始化、主题读取与页面联动
   ========================================================= */
(function () {
  'use strict';

  if (!window.echarts) return;

  var charts = {};
  var overviewRange = '30';
  var topicIndex = 0;

  function css(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  }

  function rgba(hex, alpha) {
    var h = hex.replace('#', '');
    if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2];
    var n = parseInt(h, 16);
    return 'rgba(' + ((n >> 16) & 255) + ',' + ((n >> 8) & 255) + ',' + (n & 255) + ',' + alpha + ')';
  }

  var C = {
    accent: css('--accent', '#1f6b4e'),
    lime: css('--lime-strong', '#c3ed5a'),
    orange: css('--orange', '#e2592f'),
    blue: css('--blue', '#3a6392'),
    ink: css('--ink', '#171a17'),
    muted: css('--muted', '#73786f'),
    faint: css('--faint', '#9a9f94'),
    line: css('--line', '#e5e1d7'),
    surface: css('--bg2', '#faf9f4')
  };

  var FONT = "'Instrument Sans', sans-serif";
  var MONO = "'DM Mono', monospace";

  function axisBase(extra) {
    var base = {
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: C.faint, fontSize: 8.5, fontFamily: MONO },
      splitLine: { lineStyle: { color: C.line, type: 'dashed' } }
    };
    return Object.assign(base, extra || {});
  }

  function tooltipBase(extra) {
    return Object.assign({
      backgroundColor: '#171a17',
      borderWidth: 0,
      padding: [8, 10],
      textStyle: { color: '#f2f4ec', fontSize: 10, fontFamily: FONT },
      extraCssText: 'border-radius:8px;box-shadow:0 12px 30px -12px rgba(0,0,0,.5);',
      appendToBody: true
    }, extra || {});
  }

  function ensure(id, option) {
    var el = document.getElementById(id);
    if (!el || el.clientWidth < 10 || el.clientHeight < 10) return null;
    var chart = charts[id];
    if (!chart) {
      chart = echarts.init(el, null, { renderer: 'svg' });
      charts[id] = chart;
    }
    chart.setOption(option, true);
    return chart;
  }

  /* ---------- 01 内容表现 ---------- */
  var overviewData = {
    '7': {
      labels: ['10.16', '10.17', '10.18', '10.19', '10.20', '10.21', '10.22'],
      plays: [22.1, 24.6, 21.8, 28.4, 25.2, 30.6, 32.8],
      fans: [0.24, 0.31, 0.27, 0.38, 0.33, 0.41, 0.37]
    },
    '30': {
      labels: ['9.23', '9.26', '9.29', '10.02', '10.05', '10.08', '10.11', '10.14', '10.17', '10.20', '10.22'],
      plays: [12.4, 15.1, 13.8, 18.6, 21.2, 19.4, 25.8, 27.2, 24.6, 31.4, 32.8],
      fans: [0.14, 0.18, 0.15, 0.23, 0.26, 0.21, 0.31, 0.34, 0.29, 0.39, 0.41]
    },
    '90': {
      labels: ['8.01', '8.08', '8.15', '8.22', '8.29', '9.05', '9.12', '9.19', '9.26', '10.03', '10.10', '10.17', '10.22'],
      plays: [9.8, 11.2, 10.6, 13.4, 12.1, 15.8, 14.2, 18.6, 17.4, 21.2, 23.8, 26.4, 32.8],
      fans: [0.09, 0.11, 0.10, 0.14, 0.12, 0.16, 0.15, 0.19, 0.18, 0.22, 0.24, 0.27, 0.32]
    }
  };

  function overviewOption() {
    var d = overviewData[overviewRange] || overviewData['30'];
    return {
      animation: false,
      grid: { left: 6, right: 8, top: 18, bottom: 4, containLabel: true },
      tooltip: tooltipBase({
        trigger: 'axis',
        axisPointer: { type: 'line', lineStyle: { color: C.line, width: 1 } },
        formatter: function (ps) {
          var out = '<div style="font-family:' + MONO + ';font-size:8px;opacity:.6;margin-bottom:4px">' + ps[0].axisValue + '</div>';
          ps.forEach(function (p) {
            var val = p.seriesName === '播放量' ? p.value + ' 万' : Math.round(p.value * 1000) + ' 人';
            out += '<div style="display:flex;gap:12px;justify-content:space-between"><span>' + p.marker + ' ' + p.seriesName + '</span><b style="font-weight:600">' + val + '</b></div>';
          });
          return out;
        }
      }),
      xAxis: axisBase({
        type: 'category',
        boundaryGap: false,
        data: d.labels,
        splitLine: { show: false },
        axisLabel: { color: C.faint, fontSize: 8, fontFamily: MONO, margin: 10 }
      }),
      yAxis: [
        axisBase({ type: 'value', min: 0, axisLabel: { color: C.faint, fontSize: 8, fontFamily: MONO, formatter: '{value}' } }),
        axisBase({ type: 'value', min: 0, splitLine: { show: false }, axisLabel: { color: C.faint, fontSize: 8, fontFamily: MONO, formatter: '{value}' } })
      ],
      series: [
        {
          name: '播放量',
          type: 'line',
          smooth: true,
          symbol: 'circle',
          symbolSize: 4,
          showSymbol: false,
          lineStyle: { width: 2.2, color: C.accent },
          itemStyle: { color: C.accent, borderColor: '#fff', borderWidth: 1.5 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: rgba(C.accent, 0.22) },
              { offset: 1, color: rgba(C.accent, 0.01) }
            ])
          },
          emphasis: { focus: 'series' },
          data: d.plays
        },
        {
          name: '新增粉丝',
          type: 'bar',
          yAxisIndex: 1,
          barWidth: 9,
          itemStyle: { color: C.lime, borderRadius: [3, 3, 0, 0] },
          emphasis: { focus: 'series', itemStyle: { color: C.accent } },
          data: d.fans
        }
      ]
    };
  }

  /* ---------- 02 六维雷达 ---------- */
  function radarOption() {
    return {
      animation: false,
      tooltip: tooltipBase({ trigger: 'item' }),
      radar: {
        center: ['50%', '53%'],
        radius: '62%',
        splitNumber: 4,
        indicator: [
          { name: '能力匹配', max: 100 },
          { name: '兴趣匹配', max: 100 },
          { name: '变现潜力', max: 100 },
          { name: '持续输出', max: 100 },
          { name: '竞争空间', max: 100 },
          { name: '内容差异', max: 100 }
        ],
        axisName: { color: C.muted, fontSize: 8.5, fontFamily: FONT },
        axisLine: { lineStyle: { color: C.line } },
        splitLine: { lineStyle: { color: C.line } },
        splitArea: { areaStyle: { color: ['rgba(255,255,255,0)', 'rgba(255,255,255,.4)'] } }
      },
      series: [{
        type: 'radar',
        symbolSize: 3,
        data: [
          {
            name: '你的匹配度',
            value: [94, 88, 86, 79, 72, 90],
            lineStyle: { color: C.accent, width: 2 },
            itemStyle: { color: C.accent },
            areaStyle: { color: rgba(C.accent, 0.18) }
          },
          {
            name: '同量级均值',
            value: [72, 70, 68, 74, 60, 64],
            lineStyle: { color: C.faint, width: 1.2, type: 'dashed' },
            itemStyle: { color: C.faint },
            areaStyle: { color: 'rgba(154,159,148,.06)' }
          }
        ]
      }]
    };
  }

  /* ---------- 02 机会矩阵 ---------- */
  function opportunityOption() {
    var pts = [
      { name: 'AI 效率 × 职场成长', value: [62, 86, 92], color: C.accent },
      { name: 'AI 工具测评', value: [84, 81, 78], color: rgba(C.accent, .5) },
      { name: '个人成长记录', value: [48, 60, 72], color: C.lime },
      { name: '职场干货口播', value: [76, 64, 68], color: 'rgba(58,99,146,.55)' },
      { name: '数码效率', value: [88, 72, 55], color: 'rgba(226,89,47,.45)' },
      { name: '知识科普', value: [42, 66, 62], color: 'rgba(115,120,111,.35)' }
    ];
    return {
      animation: false,
      grid: { left: 6, right: 18, top: 24, bottom: 6, containLabel: true },
      tooltip: tooltipBase({
        formatter: function (p) {
          return '<b>' + p.name + '</b><br>竞争度 ' + p.value[0] + ' · 变现潜力 ' + p.value[1] + '<br>与你的匹配度 ' + p.value[2];
        }
      }),
      xAxis: axisBase({
        type: 'value', min: 30, max: 100,
        name: '竞争度 →', nameGap: 12,
        nameTextStyle: { color: C.faint, fontSize: 8, fontFamily: MONO, align: 'right' }
      }),
      yAxis: axisBase({
        type: 'value', min: 40, max: 100,
        name: '变现潜力 →', nameGap: 8,
        nameTextStyle: { color: C.faint, fontSize: 8, fontFamily: MONO }
      }),
      series: [{
        type: 'scatter',
        symbolSize: function (v) { return v[2] * 0.5; },
        label: {
          show: true,
          position: 'top',
          formatter: function (p) { return p.name; },
          color: C.ink,
          fontSize: 7.5,
          fontFamily: FONT
        },
        labelLayout: { hideOverlap: true },
        data: pts.map(function (p) {
          return {
            name: p.name,
            value: p.value,
            itemStyle: {
              color: p.color,
              borderColor: p.color === C.accent ? C.accent : 'rgba(255,255,255,.9)',
              borderWidth: 1,
              opacity: 0.86
            }
          };
        })
      }]
    };
  }

  /* ---------- 03 选题热度 ---------- */
  var topicHeat = [
    [5.2, 5.8, 6.3, 6.9, 7.6, 8.5, 9.4],
    [7.9, 8.1, 8.0, 8.3, 8.6, 8.9, 9.1],
    [4.6, 5.1, 5.6, 6.2, 7.1, 8.0, 8.8],
    [5.4, 5.9, 6.3, 6.8, 7.4, 8.1, 8.6],
    [6.8, 6.9, 7.1, 7.4, 7.6, 7.9, 8.2],
    [6.2, 6.5, 6.8, 7.0, 7.3, 7.6, 7.9]
  ];

  function topicHeatOption() {
    var values = topicHeat[topicIndex] || topicHeat[0];
    return {
      animation: false,
      grid: { left: 2, right: 14, top: 14, bottom: 2, containLabel: true },
      tooltip: tooltipBase({
        trigger: 'axis',
        formatter: function (ps) {
          var p = ps[0];
          return '<div style="font-family:' + MONO + ';font-size:8px;opacity:.6;margin-bottom:3px">' + p.axisValue + '</div>热度指数 <b>' + p.value + '</b> / 10';
        }
      }),
      xAxis: axisBase({
        type: 'category',
        boundaryGap: false,
        data: ['10.16', '10.17', '10.18', '10.19', '10.20', '10.21', '10.22'],
        splitLine: { show: false },
        axisLabel: { color: C.faint, fontSize: 7.5, fontFamily: MONO, margin: 8 }
      }),
      yAxis: axisBase({
        type: 'value', min: 4, max: 10,
        splitNumber: 3,
        axisLabel: { color: C.faint, fontSize: 7.5, fontFamily: MONO }
      }),
      series: [{
        type: 'line',
        smooth: true,
        showSymbol: false,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 2, color: C.accent },
        itemStyle: { color: C.accent, borderColor: '#fff', borderWidth: 1.5 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: rgba(C.accent, 0.2) },
            { offset: 1, color: rgba(C.accent, 0.01) }
          ])
        },
        markPoint: {
          symbol: 'circle',
          symbolSize: 7,
          itemStyle: { color: C.accent },
          label: {
            show: true,
            position: 'top',
            formatter: '{c}',
            color: C.accent,
            fontSize: 8,
            fontFamily: MONO
          },
          data: [{ type: 'max', name: '峰值' }]
        },
        data: values
      }]
    };
  }

  /* ---------- 04 评论情绪 ---------- */
  function donutOption() {
    return {
      animation: false,
      tooltip: tooltipBase({
        trigger: 'item',
        formatter: function (p) {
          return p.marker + ' ' + p.name + '<br><b>' + p.value + '%</b> · ' + Math.round(p.value * 12.84) + ' 条';
        }
      }),
      title: {
        text: '1,284',
        subtext: '条评论',
        left: 'center',
        top: '37%',
        textAlign: 'center',
        textStyle: { fontFamily: "'Instrument Serif', serif", fontSize: 27, fontWeight: 400, color: C.ink },
        subtextStyle: { fontFamily: MONO, fontSize: 8, color: C.faint, letterSpacing: 1 }
      },
      series: [{
        type: 'pie',
        radius: ['63%', '84%'],
        center: ['50%', '50%'],
        avoidLabelOverlap: true,
        padAngle: 2,
        itemStyle: { borderColor: C.surface, borderWidth: 2, borderRadius: 3 },
        label: { show: false },
        labelLine: { show: false },
        emphasis: { scale: false, itemStyle: { borderWidth: 3 } },
        data: [
          { value: 46, name: '好评认可', itemStyle: { color: C.accent } },
          { value: 28, name: '需求建议', itemStyle: { color: C.lime } },
          { value: 17, name: '情绪共鸣', itemStyle: { color: C.orange } },
          { value: 9, name: '负面反馈', itemStyle: { color: '#c9c5bb' } }
        ]
      }]
    };
  }

  /* ---------- 04 情绪需求地图 ---------- */
  function emotionOption() {
    var pts = [
      { name: '模板完整版', value: [186, 82, 34] },
      { name: '汇报话术', value: [150, 74, 28] },
      { name: '新手教程', value: [132, 62, 24] },
      { name: '工具对比', value: [98, 58, 20] },
      { name: '价格敏感', value: [76, 66, 17] },
      { name: '真实案例', value: [64, 80, 16] },
      { name: '时间管理', value: [54, 48, 13] },
      { name: '直播带货', value: [42, 38, 11] }
    ];
    return {
      animation: false,
      grid: { left: 6, right: 16, top: 16, bottom: 6, containLabel: true },
      tooltip: tooltipBase({
        formatter: function (p) {
          return '<b>' + p.name + '</b><br>提及 ' + p.value[0] + ' 次 · 情绪强度 ' + p.value[1] + '<br>建议优先级 ' + (p.value[1] > 70 && p.value[0] > 100 ? '高' : '中');
        }
      }),
      xAxis: axisBase({
        type: 'value', min: 20, max: 210,
        name: '讨论量 →', nameGap: 10,
        nameTextStyle: { color: C.faint, fontSize: 8, fontFamily: MONO, align: 'right' }
      }),
      yAxis: axisBase({
        type: 'value', min: 30, max: 95,
        name: '情绪强度 →', nameGap: 8,
        nameTextStyle: { color: C.faint, fontSize: 8, fontFamily: MONO }
      }),
      series: [{
        type: 'scatter',
        symbolSize: function (v) { return v[2]; },
        label: {
          show: true, position: 'top',
          formatter: function (p) { return p.name; },
          color: C.ink, fontSize: 7.5, fontFamily: FONT
        },
        labelLayout: { hideOverlap: true },
        itemStyle: { color: rgba(C.accent, .62), borderColor: '#fff', borderWidth: 1 },
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: { color: C.line, type: 'dashed', width: 1 },
          label: { show: false },
          data: [{ xAxis: 110 }, { yAxis: 60 }]
        },
        markArea: {
          silent: true,
          itemStyle: { color: rgba(C.accent, 0.045) },
          data: [[{ xAxis: 110, yAxis: 60 }, { xAxis: 210, yAxis: 95 }]]
        },
        data: pts
      }]
    };
  }

  /* ---------- 06 收入结构 ---------- */
  function revenueOption() {
    var months = ['5 月', '6 月', '7 月', '8 月', '9 月', '10 月'];
    var ads = [12000, 14500, 16000, 18500, 21000, 24800];
    var goods = [3200, 4800, 5200, 6800, 8900, 10500];
    var priv = [1800, 2400, 3200, 4200, 5600, 7500];
    return {
      animation: false,
      grid: { left: 6, right: 6, top: 20, bottom: 6, containLabel: true },
      tooltip: tooltipBase({
        trigger: 'axis',
        axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(23,26,23,.04)' } },
        formatter: function (ps) {
          var total = 0;
          var out = '<div style="font-family:' + MONO + ';font-size:8px;opacity:.6;margin-bottom:5px">' + ps[0].axisValue + '</div>';
          ps.forEach(function (p) {
            total += p.value;
            out += '<div style="display:flex;gap:14px;justify-content:space-between"><span>' + p.marker + ' ' + p.seriesName + '</span><b>¥' + p.value.toLocaleString() + '</b></div>';
          });
          out += '<div style="margin-top:4px;padding-top:4px;border-top:1px solid rgba(255,255,255,.18);display:flex;gap:14px;justify-content:space-between"><span>合计</span><b>¥' + total.toLocaleString() + '</b></div>';
          return out;
        }
      }),
      xAxis: axisBase({
        type: 'category',
        data: months,
        splitLine: { show: false },
        axisLabel: { color: C.faint, fontSize: 8, fontFamily: MONO, margin: 9 }
      }),
      yAxis: axisBase({
        type: 'value',
        axisLabel: { color: C.faint, fontSize: 8, fontFamily: MONO, formatter: function (v) { return v / 1000 + 'k'; } }
      }),
      series: [
        {
          name: '广告', type: 'bar', stack: 'rev', barWidth: 24,
          itemStyle: { color: C.accent },
          emphasis: { focus: 'series' },
          data: ads
        },
        {
          name: '带货', type: 'bar', stack: 'rev', barWidth: 24,
          itemStyle: { color: C.lime },
          emphasis: { focus: 'series' },
          data: goods
        },
        {
          name: '私域', type: 'bar', stack: 'rev', barWidth: 24,
          itemStyle: { color: C.orange, borderRadius: [4, 4, 0, 0] },
          emphasis: { focus: 'series' },
          data: priv
        }
      ]
    };
  }

  var builders = {
    'chart-overview': overviewOption,
    'chart-radar': radarOption,
    'chart-opportunity': opportunityOption,
    'chart-topic-heat': topicHeatOption,
    'chart-donut': donutOption,
    'chart-emotion': emotionOption,
    'chart-revenue': revenueOption
  };

  var pageCharts = {
    overview: ['chart-overview'],
    niche: ['chart-radar', 'chart-opportunity'],
    topics: ['chart-topic-heat'],
    comments: ['chart-donut', 'chart-emotion'],
    money: ['chart-revenue']
  };

  function initFor(page) {
    (pageCharts[page] || []).forEach(function (id) {
      ensure(id, builders[id]());
    });
  }

  function resizeAll() {
    Object.keys(charts).forEach(function (id) {
      var el = charts[id] && charts[id].getDom();
      if (el && el.clientWidth > 0) charts[id].resize();
    });
  }

  window.CreatorCharts = {
    initFor: initFor,
    resize: resizeAll,
    setOverviewRange: function (range) {
      overviewRange = String(range);
      if (charts['chart-overview']) ensure('chart-overview', overviewOption());
    },
    setTopicHeat: function (index) {
      topicIndex = Number(index) || 0;
      if (charts['chart-topic-heat']) ensure('chart-topic-heat', topicHeatOption());
    }
  };

  window.addEventListener('resize', function () {
    clearTimeout(window.__creatorChartTimer);
    window.__creatorChartTimer = setTimeout(resizeAll, 120);
  });

  window.addEventListener('creator:page', function (e) {
    var page = e.detail && e.detail.page;
    requestAnimationFrame(function () {
      requestAnimationFrame(function () { initFor(page); resizeAll(); });
    });
  });

  window.addEventListener('creator:niche-done', function () {
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        ensure('chart-radar', radarOption());
        ensure('chart-opportunity', opportunityOption());
      });
    });
  });

  initFor('overview');
})();
