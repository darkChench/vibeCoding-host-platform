/*
 * overview.js —— 首页/总览
 * 布局见 docs/hmi/page-layout-spec.md §1。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;
  const store = HMI.store;

  function statusCell(s) {
    if (s === "online") return `<td class="stat-ok">在线</td>`;
    if (s === "alarm") return `<td style="color: var(--warn);">告警</td>`;
    return `<td>离线</td>`;
  }

  function quickCard(page, icon, title, desc) {
    return `
      <button class="quick-card" type="button" data-jump="${page}">
        <span class="quick-icon">${util.escapeHtml(icon)}</span>
        <span>
          <span class="quick-title">${util.escapeHtml(title)}</span>
          <span class="quick-desc">${util.escapeHtml(desc)}</span>
        </span>
      </button>
    `;
  }

  HMI.pages.overview = {
    render() {
      const devices = HMI.mock.devices;
      const connected = store.connectionState === "connected";
      document.getElementById("content").innerHTML = `
        <div class="grid cols-2">
          <div class="card">
            <div class="card-head"><span>运行总览</span><span class="tag ${connected ? "ok" : "warn"}">${connected ? "在线" : "未连接"}</span></div>
            <div class="card-body grid cols-3">
              <div class="metric"><div class="metric-label">当前串口</div><div class="metric-value">${util.escapeHtml(store.currentPort)}</div></div>
              <div class="metric"><div class="metric-label">在线设备</div><div class="metric-value">${devices.filter((d) => d.status !== "offline").length}</div></div>
              <div class="metric"><div class="metric-label">当前告警</div><div class="metric-value">${devices.filter((d) => d.status === "alarm").length}</div></div>
              <div class="metric"><div class="metric-label">离线阈值</div><div class="metric-value">10<small>min</small></div></div>
            </div>
          </div>
          <div class="card">
            <div class="card-head"><span>快捷操作</span><span class="tag">工作台</span></div>
            <div class="card-body grid cols-2">
              ${quickCard("serial", "↔", "设备连接", "配置串口、查看原始日志")}
              ${quickCard("monitor", "▥", "实时监控", "查看点位和趋势")}
              ${quickCard("alarms", "!", "报警记录", "确认报警和导出")}
              ${quickCard("history", "◇", "历史数据", "查询曲线和 CSV")}
            </div>
          </div>
        </div>
        <div class="card" style="margin-top: 10px;">
          <div class="card-head"><span>设备列表</span><span class="tag ok">${devices.filter((d) => d.status !== "offline").length} 在线</span></div>
          <div class="card-body">
            <table class="table">
              <thead><tr><th>设备</th><th>设备地址</th><th>设备 ID</th><th>状态</th><th>最后通讯</th><th>离线判定</th><th>告警</th></tr></thead>
              <tbody>
                ${devices.map((d) => `
                  <tr>
                    <td>${util.escapeHtml(d.name)}</td><td>${util.escapeHtml(d.addr)}</td><td>${util.escapeHtml(d.id)}</td>
                    ${statusCell(d.status)}
                    <td>${util.escapeHtml(d.last)}</td><td>${util.escapeHtml(d.offlineLimit)}</td><td>${d.alarm}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        </div>
      `;
    },

    bind() {
      const content = document.getElementById("content");
      // 快捷卡跳转
      content.querySelectorAll("[data-jump]").forEach((btn) => {
        btn.addEventListener("click", () => HMI.app.showPage(btn.dataset.jump));
      });
      // 普通表行点击选中
      content.querySelectorAll(".table tbody tr").forEach((row) => {
        row.addEventListener("click", () => {
          const tbody = row.closest("tbody");
          if (tbody) tbody.querySelectorAll("tr").forEach((i) => i.classList.remove("selected"));
          row.classList.add("selected");
          const first = row.querySelector("td");
          if (first) HMI.toast.show(`已选中：${util.normalizeText(first.textContent)}`);
        });
      });
    },
  };
})(window);
