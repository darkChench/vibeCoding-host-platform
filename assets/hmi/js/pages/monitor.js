/*
 * monitor.js —— 实时监控页
 * 布局见 docs/hmi/page-layout-spec.md §3。
 *
 * 数据联动（第二阶段增强）：
 *   metric 点位与趋势曲线都来自 store.params 中 category="采样参数" 的条目，
 *   不再使用写死的 mock.monitorPoints。
 *   在 params 页增删采样参数后，本页自动跟随。
 *
 * 数值来源：原型阶段无真实设备，metric 值在参数 min/max 范围内随机生成，
 *   每 1s 刷新一次，趋势曲线同步追加新点（模拟实时采集）。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;
  const store = HMI.store;

  /** 调色板：从设计系统语义色里取，避免曲线颜色游离于主题之外 */
  const PALETTE = ["#0b6fb3", "#11875d", "#b86b00", "#bf3a46", "#617083", "#07588e"];

  /** 趋势历史长度（点数） */
  const TREND_LEN = 12;

  let refreshTimer = null;
  /** 趋势历史数据：{paramName: [v1, v2, ...]}，跨刷新保留 */
  let trendHistory = {};

  /** 取采样参数（category === "采样参数"） */
  function sampleParams() {
    return store.params.filter((p) => p.category === "采样参数");
  }

  /** 取"启用显示曲线"的采样参数（受 store.curveVisible 控制，默认全部启用） */
  function visibleParams() {
    return sampleParams().filter((p) => store.curveVisible[p.name] !== false);
  }

  /** chip 配色：复用调色板，按采样参数在列表中的索引取色 */
  function chipColor(name) {
    const idx = sampleParams().findIndex((p) => p.name === name);
    return PALETTE[(idx < 0 ? 0 : idx) % PALETTE.length];
  }

  /** 在 [min,max] 范围内生成随机值，按小数位格式化 */
  function randomValue(p) {
    const min = Number(p.min);
    const max = Number(p.max);
    const lo = Number.isFinite(min) ? min : 0;
    const hi = Number.isFinite(max) ? max : 100;
    const safeLo = Math.min(lo, hi);
    const safeHi = Math.max(lo, hi);
    const raw = safeLo + Math.random() * (safeHi - safeLo);
    const d = Number.isFinite(Number(p.decimals)) ? Number(p.decimals) : 0;
    return { raw, text: raw.toFixed(d) };
  }

  /** 初始化/补齐某参数的历史趋势（不足 TREND_LEN 补随机点） */
  function ensureHistory(name) {
    if (!trendHistory[name]) trendHistory[name] = [];
    while (trendHistory[name].length < TREND_LEN) {
      const p = store.params.find((x) => x.name === name);
      trendHistory[name].push(p ? randomValue(p).raw : 0);
    }
  }

  HMI.pages.monitor = {
    render() {
      const connected = store.connectionState === "connected";
      const params = sampleParams();

      // 空态：未连接 或 无采样参数
      if (!connected || params.length === 0) {
        const reason = !connected ? "串口未连接" : "暂无采样参数（请在参数配置页新增 category=采样参数 的条目）";
        document.getElementById("content").innerHTML = `
          <div class="grid">
            <div class="card">
              <div class="card-head"><span>实时点位</span><span class="tag warn">${connected ? "无数据" : "未连接"}</span></div>
              <div class="card-body">
                <div class="empty-state"><span class="empty-state-icon">📊</span>${util.escapeHtml(reason)}</div>
              </div>
            </div>
            <div class="card">
              <div class="card-head"><span>短周期趋势</span><span class="tag">最近 ${TREND_LEN} 秒</span></div>
              <div class="card-body"><div class="chart empty-state"><span class="empty-state-icon">📈</span>${util.escapeHtml(reason)}</div></div>
            </div>
          </div>
        `;
        return;
      }

      // 正常态：渲染点位 + 占位图表容器（图表在 bind 阶段渲染，避免 render 时 Chart 未就绪）
      document.getElementById("content").innerHTML = `
        <div class="grid">
          <div class="card">
            <div class="card-head"><span>实时点位</span><span class="tag ok">运行</span></div>
            <div class="card-body grid cols-2" id="monitorMetrics">
              ${params.map((p) => this._metricHtml(p)).join("")}
            </div>
          </div>
          <div class="card">
            <div class="card-head">
              <span>短周期趋势</span>
              <div class="curve-chips" id="curveChips" role="group" aria-label="选择显示的曲线">
                ${params.map((p) => this._chipHtml(p)).join("")}
              </div>
            </div>
            <div class="card-body"><div class="chart" id="monitorChart"></div></div>
          </div>
        </div>
      `;
    },

    /** 单个点位卡 HTML（值随机生成） */
    _metricHtml(p) {
      const { text } = randomValue(p);
      return `
        <div class="metric" data-metric-name="${util.escapeHtml(p.name)}">
          <div class="metric-label">${util.escapeHtml(p.display || p.name)}</div>
          <div class="metric-value" data-metric-value>${util.escapeHtml(text)}<small>${util.escapeHtml(p.unit || "")}</small></div>
        </div>
      `;
    },

    /** 单个曲线筛选 chip HTML：active 显示色块+名，inactive 灰色 */
    _chipHtml(p) {
      const visible = store.curveVisible[p.name] !== false;
      const color = chipColor(p.name);
      const label = util.escapeHtml(p.display || p.name);
      const style = visible
        ? `style="--chip-color:${color};"`
        : 'style="--chip-color:#aab6c4;"';
      return `
        <button type="button" class="curve-chip${visible ? "" : " inactive"}" data-curve-name="${util.escapeHtml(p.name)}" ${style} aria-pressed="${visible}" title="${visible ? "点击隐藏" : "点击显示"} ${label} 曲线">
          <span class="curve-chip-dot"></span><span class="curve-chip-label">${label}</span>
        </button>
      `;
    },

    bind() {
      const params = sampleParams();
      if (store.connectionState !== "connected" || params.length === 0) return;

      // 初始化历史趋势
      params.forEach((p) => ensureHistory(p.name));
      // 清掉已不存在的采样参数的历史
      Object.keys(trendHistory).forEach((name) => {
        if (!store.params.find((x) => x.name === name && x.category === "采样参数")) {
          delete trendHistory[name];
        }
      });

      this._renderChart();
      this._startRefresh();
      this._bindChips();
    },

    /** 绑定曲线筛选 chip：点击切换显隐并重绘曲线 */
    _bindChips() {
      const chips = document.querySelectorAll("[data-curve-name]");
      chips.forEach((chip) => {
        chip.addEventListener("click", () => {
          const name = chip.dataset.curveName;
          const cur = store.curveVisible[name] !== false; // 默认 true
          store.curveVisible[name] = !cur;
          // 更新 chip 视觉
          const visible = !cur;
          chip.classList.toggle("inactive", !visible);
          chip.setAttribute("aria-pressed", String(visible));
          const color = chipColor(name);
          chip.style.setProperty("--chip-color", visible ? color : "#aab6c4");
          chip.title = (visible ? "点击隐藏" : "点击显示") + " " + (chip.querySelector(".curve-chip-label")?.textContent || "") + " 曲线";
          // 重绘曲线（启用集变化，需要重建 Chart 实例）
          this._renderChart();
        });
      });
    },

    /** 渲染/重建趋势曲线（仅画启用集 visibleParams） */
    _renderChart() {
      const container = document.getElementById("monitorChart");
      if (!container) return;
      const all = sampleParams();
      const vis = visibleParams();
      // 全部被隐藏时显示空态
      if (!vis.length) {
        HMI.chart.destroy(container);
        container.classList.add("empty-state");
        container.innerHTML = `<span class="empty-state-icon">📈</span>所有曲线已隐藏，点击上方标签显示`;
        return;
      }
      container.classList.remove("empty-state");
      const labels = Array.from({ length: TREND_LEN }, (_, i) => `-${TREND_LEN - 1 - i}s`);
      labels[TREND_LEN - 1] = "now";
      // 颜色按采样参数在完整列表中的索引取（隐藏/显示不影响其他曲线颜色）
      const series = vis.map((p) => ({
        name: p.display || p.name,
        color: chipColor(p.name),
        data: (trendHistory[p.name] || []).slice(),
      }));
      HMI.chart.render(container, { labels, series }, { realtime: true });
    },

    /** 1s 刷新：metric 重新随机 + 趋势追加新点 */
    _startRefresh() {
      this._stopRefresh();
      refreshTimer = setInterval(async () => {
        const params = sampleParams();
        if (!params.length) { this._stopRefresh(); return; }

        // 通过协议层读取每个采样参数（生成真实报文+模拟回包），刷新 metric 和趋势
        const decimalsMap = {};
        for (const p of params) {
          const result = await HMI.modbus.readParam(p);
          if (!result.ok) continue;
          const decimals = Number(p.decimals) || 0;
          const text = result.value.toFixed(decimals);
          decimalsMap[p.name] = decimals;
          // 刷新 metric 卡数值（直接改 DOM）
          const card = document.querySelector(`[data-metric-name="${CSS.escape(p.name)}"] [data-metric-value]`);
          if (card) card.innerHTML = `${util.escapeHtml(text)}<small>${util.escapeHtml(p.unit || "")}</small>`;
          // 追加趋势点
          ensureHistory(p.name);
          trendHistory[p.name].shift();
          trendHistory[p.name].push(result.value);
        }

        // 更新图表数据（不重建，仅 update）—— 按 visibleParams 对齐 datasets
        const inst = document.getElementById("monitorChart")?._chartInstance;
        if (inst) {
          const vis = visibleParams();
          vis.forEach((p, i) => {
            if (inst.data.datasets[i]) {
              inst.data.datasets[i].data = (trendHistory[p.name] || []).slice();
            }
          });
          inst.update("none");
        }
      }, 1000);
    },

    _stopRefresh() {
      if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
    },
  };
})(window);
