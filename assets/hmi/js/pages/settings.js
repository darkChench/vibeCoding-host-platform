/*
 * settings.js —— 系统设置页
 * 布局见 docs/hmi/page-layout-spec.md §8。
 * 第二阶段：清理日志/导出诊断加二次确认 + loading。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;

  function kvTable(rows) {
    return `<table class="table"><tbody>${rows.map((r) => `<tr><td>${util.escapeHtml(r[0])}</td><td>${util.escapeHtml(r[1])}</td></tr>`).join("")}</tbody></table>`;
  }

  HMI.pages.settings = {
    render() {
      document.getElementById("content").innerHTML = `
        <div class="grid cols-2">
          <div class="card">
            <div class="card-head"><span>软件信息</span><span class="tag ok">正常</span></div>
            <div class="card-body">${kvTable(HMI.mock.softwareInfo)}</div>
          </div>
          <div class="card">
            <div class="card-head"><span>维护操作</span><span class="tag">诊断</span></div>
            <div class="card-body">
              ${kvTable(HMI.mock.maintenanceInfo)}
              <div style="display:flex; gap:8px; margin-top:12px;">
                <button class="btn secondary" type="button" data-clean-log>清理日志</button>
                <button class="btn" type="button" data-export-diag>导出诊断</button>
              </div>
            </div>
          </div>
        </div>
      `;
    },

    bind() {
      // 清理日志：二次确认
      document.querySelector("[data-clean-log]")?.addEventListener("click", () => {
        HMI.modal.showAction("清理日志", "将清理本地诊断日志，请确认保留时间范围（默认保留最近 7 天）。", () => {
          HMI.toast.show("日志已清理（保留最近 7 天）");
        });
      });
      // 导出诊断：loading 后成功提示
      document.querySelector("[data-export-diag]")?.addEventListener("click", (e) => {
        const btn = e.currentTarget;
        btn.classList.add("loading");
        setTimeout(() => {
          btn.classList.remove("loading");
          HMI.modal.showAction("导出诊断", "已打包运行日志、配置文件和通信统计，保存到 ./save/diag.zip。");
        }, 1000);
      });
    },
  };
})(window);
