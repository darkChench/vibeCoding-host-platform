/*
 * chart.js —— Chart.js 封装
 *
 * 第二阶段新增：替换原型的 SVG 假折线，提供真实交互图表。
 * Chart.js 经 CDN 引入（见 index.html），符合 assets/AGENTS.md "不复制第三方库"约束。
 *
 * 与 docs/hmi/widget-qss-spec.md §7 图表规范对齐：
 *   - 主曲线 #0b6fb3 4px、副曲线 #11875d 3px
 *   - 背景 #fbfdff、网格 #e1e8f0
 *   - 高度 180px
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});

  /** 标准配色与网格 */
  const GRID_COLOR = "#e1e8f0";
  const BG_COLOR = "#fbfdff";

  /** 终端字体回退（与终端一致） */
  const FONT = { family: "Consolas, 'Courier New', monospace", size: 11 };

  const chart = {
    /**
     * 在容器内创建/替换折线图。
     * @param {HTMLElement} container  .chart 容器
     * @param {Object} data  {labels:[], series:[{name,color,data:[]}]}
     * @param {Object} opts  {realtime:false, yUnit:''}
     * @returns {Chart|null} Chart 实例（用于后续 destroy/update）
     */
    render(container, data, opts) {
      if (typeof Chart === "undefined") {
        container.innerHTML = `<div class="empty-state"><span class="empty-state-icon">📈</span>Chart.js 未加载（需联网从 CDN 获取）</div>`;
        return null;
      }
      opts = opts || {};
      // 清空旧 canvas/实例
      const old = container._chartInstance;
      if (old) { old.destroy(); delete container._chartInstance; }
      container.innerHTML = "";
      const canvas = document.createElement("canvas");
      container.appendChild(canvas);

      const datasets = data.series.map((s, i) => ({
        label: s.name,
        data: s.data,
        borderColor: s.color,
        backgroundColor: s.color + "22",
        borderWidth: i === 0 ? 4 : 3,
        tension: 0.35,
        pointRadius: 0,
        pointHoverRadius: 4,
        fill: false,
      }));

      const instance = new Chart(canvas.getContext("2d"), {
        type: "line",
        data: { labels: data.labels, datasets },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: { duration: opts.realtime ? 0 : 300 },
          interaction: { mode: "nearest", intersect: false, axis: "x" },
          plugins: {
            legend: {
              display: data.series.length > 1,
              position: "top",
              labels: { font: FONT, color: "#617083", boxWidth: 12, boxHeight: 12 },
            },
            tooltip: {
              backgroundColor: "#101a27",
              titleColor: "#dceafe",
              bodyColor: "#dceafe",
              titleFont: FONT,
              bodyFont: FONT,
              borderColor: GRID_COLOR,
              borderWidth: 1,
              padding: 8,
              callbacks: opts.yUnit ? { label: (c) => `${c.dataset.label}: ${c.parsed.y} ${opts.yUnit}` } : {},
            },
          },
          scales: {
            x: {
              grid: { color: GRID_COLOR, drawBorder: false },
              ticks: { font: FONT, color: "#617083", maxRotation: 0 },
            },
            y: {
              grid: { color: GRID_COLOR, drawBorder: false },
              ticks: { font: FONT, color: "#617083" },
            },
          },
        },
        plugins: [{
          // 背景色填充
          id: "bgColor",
          beforeDraw(chartInst) {
            const ctx = chartInst.canvas.ctx;
            ctx.save();
            ctx.globalCompositeOperation = "destination-over";
            ctx.fillStyle = BG_COLOR;
            ctx.fillRect(0, 0, chartInst.width, chartInst.height);
            ctx.restore();
          },
        }],
      });
      container._chartInstance = instance;
      return instance;
    },

    /** 销毁容器上的图表（页面切换前调用，避免内存泄漏） */
    destroy(container) {
      if (container && container._chartInstance) {
        container._chartInstance.destroy();
        delete container._chartInstance;
      }
    },
  };

  HMI.chart = chart;
})(window);
