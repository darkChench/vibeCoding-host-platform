/*
 * history.js —— 历史数据页
 * 布局见 docs/hmi/page-layout-spec.md §7。
 *
 * 第二阶段增强：
 *   - 点位字段改为多选下拉，选项来自 store.params 的采样参数
 *   - 查询后趋势曲线按选中的点位生成（颜色按采样参数索引固定，与 monitor 页一致）
 *   - 查询/导出按钮支持 loading
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;
  const store = HMI.store;

  /** 调色板：与 monitor 页一致 */
  const PALETTE = ["#0b6fb3", "#11875d", "#b86b00", "#bf3a46", "#617083", "#07588e"];

  /** 取采样参数 */
  function sampleParams() {
    return store.params.filter((p) => p.category === "采样参数");
  }

  /** 取当前选中的采样参数（historySelectedPoints 为 null 时返回全部） */
  function selectedParams() {
    const all = sampleParams();
    if (!store.historySelectedPoints) return all;
    return all.filter((p) => store.historySelectedPoints.includes(p.name));
  }

  HMI.pages.history = {
    render() {
      const params = sampleParams();
      // 默认全选
      const sel = store.historySelectedPoints || params.map((p) => p.name);
      document.getElementById("content").innerHTML = `
        <div class="grid cols-2">
          <div class="card">
            <div class="card-head"><span>查询条件</span><span class="tag">CSV</span></div>
            <div class="card-body">
              <div class="form-grid">
                <div class="field"><label>开始时间</label><input class="input" value="2026-06-10 00:00" data-start></div>
                <div class="field"><label>结束时间</label><input class="input" value="2026-06-10 23:59" data-end></div>
                <div class="field">
                  <label>点位</label>
                  ${params.length
                    ? HMI.dropdown.html("historyPoints", params.map((p) => p.display || p.name), null, "选择查询的采样点位", "up",
                        { multi: true, multiSelected: sel.map((n) => params.find((p) => p.name === n)).map((p) => p.display || p.name), placeholder: "请选择点位" })
                    : `<input class="input" value="暂无采样参数" disabled>`
                  }
                </div>
                <div class="field"><label>导出格式</label><select class="select"><option>CSV</option><option>Excel</option></select></div>
              </div>
              <div style="display:flex; gap:8px; margin-top:12px;">
                <button class="btn" type="button" data-query-btn>查询</button>
                <button class="btn secondary" type="button" data-export-btn>导出</button>
              </div>
            </div>
          </div>
          <div class="card">
            <div class="card-head"><span>趋势曲线</span><span class="tag">统计</span></div>
            <div class="card-body"><div class="chart empty-state" id="historyChart"><span class="empty-state-icon">📈</span>请点击"查询"加载数据</div></div>
          </div>
        </div>
      `;
    },

    bind() {
      // 绑定多选下拉
      if (sampleParams().length) {
        HMI.dropdown.bind(document.getElementById("content"));
        HMI.dropdown.onChange("historyPoints", (selectedDisplays) => {
          // 把显示名反查回 name 存入 store
          const params = sampleParams();
          store.historySelectedPoints = params
            .filter((p) => selectedDisplays.includes(p.display || p.name))
            .map((p) => p.name);
        });
      }

      document.querySelector("[data-query-btn]")?.addEventListener("click", (e) => this._handleQuery(e.target));
      document.querySelector("[data-export-btn]")?.addEventListener("click", (e) => this._handleExport(e.target));
    },

    _handleQuery(btn) {
      const start = document.querySelector("[data-start]")?.value;
      const end = document.querySelector("[data-end]")?.value;
      if (start && end && start >= end) {
        HMI.toast.show("开始时间必须早于结束时间");
        return;
      }
      const sel = selectedParams();
      if (!sel.length) {
        HMI.toast.show("请至少选择一个点位");
        return;
      }
      btn.classList.add("loading");
      setTimeout(() => {
        btn.classList.remove("loading");
        const container = document.getElementById("historyChart");
        // 无选中点位 → 空态
        if (!sel.length) {
          container.classList.add("empty-state");
          container.innerHTML = `<span class="empty-state-icon">📈</span>未选择点位`;
          return;
        }
        container.classList.remove("empty-state");
        container.innerHTML = "";
        // 按选中点位生成曲线（颜色按采样参数在完整列表中的索引固定）
        const all = sampleParams();
        const labels = Array.from({ length: 12 }, (_, i) => `${i}:00`);
        const series = sel.map((p) => {
          const idx = all.findIndex((x) => x.name === p.name);
          return {
            name: p.display || p.name,
            color: PALETTE[(idx < 0 ? 0 : idx) % PALETTE.length],
            data: Array.from({ length: 12 }, () => {
              const lo = Number(p.min) || 0;
              const hi = Number(p.max) || 100;
              return lo + Math.random() * (hi - lo);
            }),
          };
        });
        HMI.chart.render(container, { labels, series }, { yUnit: "" });
        HMI.toast.show(`查询完成（${sel.length} 个点位）`);
      }, 800);
    },

    _handleExport(btn) {
      const sel = selectedParams();
      if (!sel.length) {
        HMI.toast.show("请先选择点位并查询");
        return;
      }
      btn.classList.add("loading");
      setTimeout(() => {
        btn.classList.remove("loading");
        HMI.modal.showAction("导出 CSV", `已将 ${sel.length} 个点位（${sel.map((p) => p.display || p.name).join("、")}）的查询结果导出为 CSV，保存到 ./save 目录。`);
      }, 800);
    },
  };
})(window);
