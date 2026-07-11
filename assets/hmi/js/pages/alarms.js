/*
 * alarms.js —— 报警记录页
 * 布局见 docs/hmi/page-layout-spec.md §6，交互见 interaction-spec.md §4。
 *
 * 第二阶段：基于 store.alarms 模型渲染，确认状态写回模型（替代原型的 DOM 不可逆操作）。
 * tag.warn "N 未确认" 计数联动。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;
  const store = HMI.store;

  HMI.pages.alarms = {
    render() {
      const unack = store.unackAlarmCount();
      document.getElementById("content").innerHTML = `
        <div class="card">
          <div class="card-head">
            <span>报警记录</span>
            <span class="tag ${unack > 0 ? "warn" : "ok"}" id="alarmCountTag">${unack > 0 ? `${unack} 未确认` : "全部已确认"}</span>
          </div>
          <div class="card-body">
            <div style="display:flex; gap:8px; margin-bottom:10px;">
              <button class="btn" type="button" data-alarm-toolbar="ack" disabled>确认勾选</button>
              <button class="btn secondary" type="button" data-alarm-toolbar="ack-all">确认全部未确认</button>
              <button class="btn secondary" type="button" data-alarm-toolbar="export">导出报警</button>
            </div>
            <table class="table alarm-table">
              <thead><tr>
                <th class="select-cell"><input type="checkbox" data-alarm-check-all aria-label="全选报警"></th>
                <th>时间</th><th>内容</th><th>终端</th><th>级别</th><th>状态</th><th>确认信息</th>
              </tr></thead>
              <tbody id="alarmTbody"></tbody>
            </table>
          </div>
        </div>
      `;
      this._renderTable();
    },

    bind() {
      document.querySelectorAll("[data-alarm-toolbar]").forEach((btn) => {
        btn.addEventListener("click", () => this._handleToolbar(btn.dataset.alarmToolbar));
      });
      document.querySelector("[data-alarm-check-all]")?.addEventListener("change", (e) => {
        document.querySelectorAll("[data-alarm-check]:not(:disabled)").forEach((cb) => (cb.checked = e.target.checked));
        this._updateToolbarState();
      });
    },

    _renderTable() {
      const tbody = document.getElementById("alarmTbody");
      tbody.innerHTML = store.alarms.map((a) => `
        <tr data-alarm-id="${a.id}">
          <td class="select-cell"><input type="checkbox" data-alarm-check ${a.acknowledged ? "disabled" : ""} aria-label="勾选 ${util.escapeHtml(a.content)}"></td>
          <td>${util.escapeHtml(a.time)}</td>
          <td>${util.escapeHtml(a.content)}</td>
          <td>${util.escapeHtml(a.terminal)}</td>
          <td>${util.escapeHtml(a.level)}</td>
          <td${a.acknowledged ? "" : ' style="color: var(--warn);"'}>${a.acknowledged ? "已确认" : "未确认"}</td>
          <td>${a.acknowledged ? `${util.escapeHtml(a.ackUser)} ${util.escapeHtml(a.ackTime)}` : "-"}</td>
        </tr>
      `).join("");
      // 绑定单行 checkbox
      tbody.querySelectorAll("[data-alarm-check]").forEach((cb) => {
        cb.addEventListener("change", () => this._updateToolbarState());
      });
      this._updateToolbarState();
      this._updateCountTag();
    },

    _checkedIds() {
      return Array.from(document.querySelectorAll("[data-alarm-check]:checked"))
        .map((cb) => Number(cb.closest("tr").dataset.alarmId));
    },

    _updateToolbarState() {
      const checked = this._checkedIds();
      const ackBtn = document.querySelector('[data-alarm-toolbar="ack"]');
      const checkAll = document.querySelector("[data-alarm-check-all]");
      const checks = Array.from(document.querySelectorAll("[data-alarm-check]:not(:disabled)"));
      if (ackBtn) ackBtn.disabled = checked.length === 0;
      if (checkAll && checks.length) {
        checkAll.checked = checked.length === checks.length;
        checkAll.indeterminate = checked.length > 0 && checked.length < checks.length;
      }
    },

    _updateCountTag() {
      const unack = store.unackAlarmCount();
      const tag = document.getElementById("alarmCountTag");
      if (!tag) return;
      tag.textContent = unack > 0 ? `${unack} 未确认` : "全部已确认";
      tag.classList.toggle("warn", unack > 0);
      tag.classList.toggle("ok", unack === 0);
    },

    _handleToolbar(action) {
      if (action === "export") {
        HMI.modal.showAction("导出报警", `将导出 ${store.alarms.length} 条报警记录为 CSV（原型占位，待接入文件保存对话框）。`);
        return;
      }
      if (action === "ack") {
        const ids = this._checkedIds();
        if (!ids.length) { HMI.toast.show("请先勾选未确认报警"); return; }
        this._acknowledge(ids);
        return;
      }
      if (action === "ack-all") {
        const ids = store.alarms.filter((a) => !a.acknowledged).map((a) => a.id);
        if (!ids.length) { HMI.toast.show("没有未确认报警"); return; }
        this._acknowledge(ids);
      }
    },

    /** 确认：写回模型 + 重渲 + 弹动作框 */
    _acknowledge(ids) {
      const time = util.nowHMS();
      ids.forEach((id) => {
        const a = store.alarms.find((x) => x.id === id);
        if (a && !a.acknowledged) {
          a.acknowledged = true;
          a.ackUser = "工程师";
          a.ackTime = time;
        }
      });
      this._renderTable();
      HMI.modal.showAction("报警确认", `已确认 ${ids.length} 条报警。确认记录包含确认人、确认时间和报警原始信息。`);
    },
  };
})(window);
