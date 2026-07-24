/*
 * statusPolicy.js —— 状态策略页
 * 布局见 docs/hmi/page-layout-spec.md §4。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;

  HMI.pages.statusPolicy = {
    render() {
      const transitions = HMI.mock.statusTransitions;
      // 把"warn-text"映射成内联橙色样式，其余当 class 名用
      const cellAttr = (cls) => {
        if (!cls) return "";
        if (cls === "warn-text") return ' style="color: var(--warn);"';
        return ` class="${cls}"`;
      };
      document.getElementById("content").innerHTML = `
        <div class="grid cols-2">
          <div class="card">
            <div class="card-head"><span>离线判定策略</span><span class="tag">设备总览</span></div>
            <div class="card-body">
              <div class="form-grid">
                <label class="check-label"><input type="checkbox" checked aria-label="启用离线判定"><span>启用离线判定</span></label>
                <div class="field"><label>无通讯超时时间</label><input class="input" type="number" min="1" step="1" value="10" data-timeout-value></div>
                <div class="field"><label>时间单位</label><select class="select"><option>分钟</option><option>秒</option></select></div>
                <div class="field"><label>作用范围</label><select class="select"><option>全部设备</option><option>仅采样设备</option><option>自定义设备</option></select></div>
              </div>
              <table class="table" style="margin-top:12px;">
                <tbody>
                  <tr><td>判定依据</td><td>按设备地址统计最后一次有效 Modbus RTU 响应时间。</td></tr>
                  <tr><td>在线转离线</td><td>在线设备超过 <span data-timeout-preview>10</span> 分钟无有效数据，设备总览状态变为离线。</td></tr>
                  <tr><td>告警转离线</td><td>告警设备超过 <span data-timeout-preview>10</span> 分钟无有效数据，设备总览状态变为离线，并保留原告警记录。</td></tr>
                  <tr><td>离线恢复</td><td>收到该设备任意有效响应帧后恢复在线；若仍满足告警条件，再显示告警。</td></tr>
                </tbody>
              </table>
              <div style="display:flex; gap:8px; margin-top:12px;">
                <button class="btn" type="button">保存状态策略</button>
                <button class="btn secondary" type="button">恢复默认策略</button>
              </div>
            </div>
          </div>
          <div class="card">
            <div class="card-head"><span>状态转换预览</span><span class="tag warn" data-timeout-tag>10 min</span></div>
            <div class="card-body">
              <table class="table">
                <thead><tr><th>当前状态</th><th>条件</th><th>设备总览显示</th></tr></thead>
                <tbody>
                  ${transitions.map((t) => `
                    <tr>
                      <td${cellAttr(t.currentClass)}>${t.current}</td>
                      <td>${util.escapeHtml(t.condition)}</td>
                      <td${cellAttr(t.resultClass)}>${t.result}</td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    },

    bind() {
      // 第二阶段补全：超时值联动预览
      const input = document.querySelector("[data-timeout-value]");
      if (input) {
        input.addEventListener("input", () => {
          const v = util.normalizeText(input.value) || "10";
          document.querySelectorAll("[data-timeout-preview]").forEach((s) => (s.textContent = v));
          const tag = document.querySelector("[data-timeout-tag]");
          if (tag) tag.textContent = `${v} min`;
        });
      }
    },
  };
})(window);
