/*
 * console.js —— 串口控制台组件（serial 页核心）
 *
 * 来源：原型行 1446-1579。
 * 第二阶段补全：
 *   - HEX/ASCII 切换影响发送解析
 *   - 行结束符追加
 *   - 自动发送定时（按间隔，min 100ms）
 *   - 发送历史完整 CRUD（持久化在 store.js）
 *   - 未连接态提示
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;
  const store = HMI.store;

  const consoleComp = {
    /** 当前 console tab：raw/stats/diagnostic */
    currentTab: "raw",

    /** 运行时累积的终端行（不再用硬编码，可被发送动作追加） */
    lines: {
      raw: JSON.parse(JSON.stringify(HMI.mock.consoleLines.raw)),
      stats: JSON.parse(JSON.stringify(HMI.mock.consoleLines.stats)),
      diagnostic: JSON.parse(JSON.stringify(HMI.mock.consoleLines.diagnostic)),
    },

    /** 渲染 console 骨架到 content 容器 */
    render() {
      const content = document.getElementById("content");
      const connected = store.connectionState === "connected";
      content.innerHTML = `
        <div class="serial-workbench">
          <section class="console">
            ${connected ? "" : `<div class="console-notice">⚠ 串口未连接，请先在顶部工具栏点击"连接"</div>`}
            <div class="console-tabs">
              <button class="console-tab active" type="button" data-console="raw">串口原始日志</button>
              <button class="console-tab" type="button" data-console="stats">通信统计</button>
              <button class="console-tab" type="button" data-console="diagnostic">诊断日志</button>
              <span></span>
              <label class="check-label"><input type="checkbox" checked aria-label="显示时间戳"><span>时间戳</span></label>
            </div>
            <div class="terminal" aria-label="serial raw log">${this._linesHtml(this.currentTab)}</div>
            <div class="history-popover" data-send-history-panel>
              <div class="history-head"><span>最近发送 20 条</span><button class="btn secondary" type="button" data-send-history-clear>清空</button></div>
              <div class="history-list" data-send-history-list></div>
            </div>
            <div class="sendbar">
              <div class="send-input-wrap">
                <input class="send-input" value="01 03 00 00 00 04" aria-label="发送帧">
                <button class="btn secondary" type="button" data-send-history-toggle>历史</button>
              </div>
              ${HMI.dropdown.html("sendFormat", ["HEX", "ASCII"], "HEX", "发送格式")}
              <span class="tool-label">行结束符</span>
              ${HMI.dropdown.html("lineEnding", ["无", "CR", "LF", "CRLF"], "无", "行结束符")}
              <label class="check-label"><input type="checkbox" aria-label="启用自动发送" data-auto-send><span>自动发送</span></label>
              <input class="input short" type="number" min="100" step="100" value="1000" aria-label="自动发送间隔" data-auto-interval>
              <span class="tool-label">ms</span>
              <button class="btn" type="button" data-send-action ${connected ? "" : "disabled"}>发送</button>
            </div>
          </section>
        </div>
      `;
      this._renderHistory();
    },

    /** 绑定 console 内部事件（render 后调用） */
    bind() {
      const content = document.getElementById("content");

      // 自定义下拉（发送格式 / 行结束符）
      HMI.dropdown.bind(content);

      // tab 切换
      content.querySelectorAll(".console-tab[data-console]").forEach((btn) => {
        btn.addEventListener("click", () => {
          content.querySelectorAll(".console-tab[data-console]").forEach((i) => i.classList.remove("active"));
          btn.classList.add("active");
          this.currentTab = btn.dataset.console;
          const terminal = content.querySelector(".terminal");
          if (terminal) terminal.innerHTML = this._linesHtml(this.currentTab);
        });
      });

      // 发送历史开关
      content.querySelector("[data-send-history-toggle]")?.addEventListener("click", () => {
        this._renderHistory();
        content.querySelector("[data-send-history-panel]")?.classList.toggle("open");
      });

      // 清空历史
      content.querySelector("[data-send-history-clear]")?.addEventListener("click", () => {
        store.sendHistory = [];
        store.persistSendHistory();
        this._renderHistory();
        HMI.toast.show("发送历史已清空");
      });

      // 发送按钮
      content.querySelector("[data-send-action]")?.addEventListener("click", () => this.handleSend());

      // 自动发送开关
      content.querySelector("[data-auto-send]")?.addEventListener("change", (e) => {
        if (e.target.checked) this._startAutoSend();
        else this._stopAutoSend();
      });

      // 间隔输入：失焦时夹紧到 100
      content.querySelector("[data-auto-interval]")?.addEventListener("blur", (e) => {
        if (Number(e.target.value) < 100) {
          e.target.value = 100;
          HMI.toast.show("自动发送间隔最小 100 ms");
        }
      });
    },

    /** 发送动作（HEX/ASCII 解析 + 行结束符 + 写历史 + TX 行） */
    handleSend() {
      const content = document.getElementById("content");
      const input = content.querySelector(".send-input");
      if (!input) return;

      const raw = util.normalizeText(input.value);
      if (!raw) {
        HMI.toast.show("发送帧不能为空");
        return;
      }
      if (store.connectionState !== "connected") {
        HMI.toast.show("串口未连接，无法发送");
        return;
      }

      const format = HMI.dropdown.getValue(content, "sendFormat") || "HEX";
      const ending = HMI.dropdown.getValue(content, "lineEnding") || "无";

      // 解析为字节
      let bytes;
      if (format === "HEX") {
        bytes = util.parseHexFrame(raw);
        if (!bytes) {
          HMI.toast.show("HEX 格式非法，请输入如 01 03 00 00");
          return;
        }
      } else {
        bytes = util.asciiToBytes(raw);
      }
      // 追加行结束符
      bytes = bytes.concat(util.lineEndingBytes(ending));

      // 写入发送历史（用归一化后的原文，不含行结束符）
      store.pushSendHistory(raw);

      // 终端追加 TX 行
      this.lines.raw.push(["tx", "TX", util.nowHMS(), util.bytesToHex(bytes)]);
      this._appendLine(["tx", "TX", util.nowHMS(), util.bytesToHex(bytes)]);

      // 统计累计 +1 帧（简化）
      const stats = this.lines.stats;
      const txStat = stats.find((s) => s[1] === "TX");
      if (txStat) {
        const m = /([\d,]+) B \/ (\d+) 帧/.exec(txStat[3]);
        if (m) {
          const bytes2 = parseInt(m[1].replace(/,/g, ""), 10) + bytes.length;
          const frames = parseInt(m[2], 10) + 1;
          txStat[3] = `${bytes2.toLocaleString()} B / ${frames} 帧`;
        }
      }

      HMI.toast.show("已发送并保存到最近");
    },

    _startAutoSend() {
      if (store.connectionState !== "connected") {
        document.querySelector("[data-auto-send]").checked = false;
        HMI.toast.show("串口未连接，无法自动发送");
        return;
      }
      this._stopAutoSend();
      const interval = Number(document.querySelector("[data-auto-interval]")?.value) || 1000;
      const safe = Math.max(100, interval);
      store.autoSendTimer = setInterval(() => this.handleSend(), safe);
      this.lines.diagnostic.push(["tx", "INFO", util.nowHMS(), `自动发送已启动，间隔 ${safe} ms`]);
      HMI.toast.show(`自动发送已启动（${safe} ms）`);
    },

    _stopAutoSend() {
      if (store.autoSendTimer) {
        clearInterval(store.autoSendTimer);
        store.autoSendTimer = null;
        this.lines.diagnostic.push(["tx", "INFO", util.nowHMS(), "自动发送已停止"]);
      }
    },

    /** 渲染发送历史列表 */
    _renderHistory() {
      const list = document.getElementById("content").querySelector("[data-send-history-list]");
      if (!list) return;
      if (!store.sendHistory.length) {
        list.innerHTML = `<div class="history-empty">暂无发送历史</div>`;
        return;
      }
      list.innerHTML = store.sendHistory.slice(0, 20).map((item) => `
        <div class="history-item">
          <button class="history-pick" type="button" data-send-history-item="${util.escapeHtml(item)}">
            <span>${util.escapeHtml(item)}</span>
          </button>
          <button class="history-delete" type="button" data-send-history-delete="${util.escapeHtml(item)}" aria-label="删除 ${util.escapeHtml(item)}">x</button>
        </div>
      `).join("");
      list.querySelectorAll("[data-send-history-item]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const input = document.getElementById("content").querySelector(".send-input");
          if (input) { input.value = btn.dataset.sendHistoryItem; input.focus(); }
          document.getElementById("content").querySelector("[data-send-history-panel]")?.classList.remove("open");
        });
      });
      list.querySelectorAll("[data-send-history-delete]").forEach((btn) => {
        btn.addEventListener("click", () => {
          store.sendHistory = store.sendHistory.filter((i) => i !== btn.dataset.sendHistoryDelete);
          store.persistSendHistory();
          this._renderHistory();
          HMI.toast.show("已删除发送历史");
        });
      });
    },

    /** 终端行 HTML */
    _linesHtml(type) {
      return (this.lines[type] || []).map((item) =>
        `<div class="terminal-line"><span class="${item[0]}">${util.escapeHtml(item[1])}</span><span>${util.escapeHtml(item[2])}</span><span>${util.escapeHtml(item[3])}</span></div>`
      ).join("");
    },

    /** 追加一行到终端（保持滚动到底部） */
    _appendLine(item) {
      if (this.currentTab !== "raw") return;
      const terminal = document.getElementById("content").querySelector(".terminal");
      if (!terminal) return;
      const wasAtBottom = terminal.scrollHeight - terminal.scrollTop - terminal.clientHeight < 30;
      terminal.insertAdjacentHTML("beforeend",
        `<div class="terminal-line"><span class="${item[0]}">${util.escapeHtml(item[1])}</span><span>${util.escapeHtml(item[2])}</span><span>${util.escapeHtml(item[3])}</span></div>`);
      if (wasAtBottom) terminal.scrollTop = terminal.scrollHeight;
    },
  };

  HMI.console = consoleComp;
})(window);
