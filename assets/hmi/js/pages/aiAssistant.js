/*
 * aiAssistant.js —— AI 助手页（标准页面）
 *
 * 第三阶段改造：从右侧浮动侧栏改为独立页面，注册到 HMI.pages。
 * 走标准页面路由（showPage），对话 UI 渲染进 #content。
 *
 * 对话流程不变（见 interaction-spec.md §9）：
 *   用户输入 → 思考动画 → llmClient.send → 工具调用卡片 → aiTools.call → 结果摘要 → 自然语言回复
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;
  const store = HMI.store;

  HMI.pages.aiAssistant = {
    render() {
      const cfg = store.activeModelConfig();
      const cfgTag = cfg
        ? `<span class="tag ok">${util.escapeHtml(cfg.provider)} · ${util.escapeHtml(cfg.model)}</span>`
        : `<span class="tag warn">未配置模型</span>`;
      document.getElementById("content").innerHTML = `
        <div class="ai-page">
          <div class="card">
            <div class="card-head">
              <span><span class="ai-icon">✦</span> AI 运维助手</span>
              ${cfgTag}
            </div>
            <div class="card-body ai-page-body">
              <div class="ai-messages" id="aiMessages"></div>
              <div class="ai-input-wrap">
                <textarea class="ai-input" id="aiInput" placeholder="输入问题，如“查一下温度”、“有哪些报警”、“压力趋势”、“哪些设备在线”..." rows="2"></textarea>
                <button class="btn" type="button" id="aiSendBtn" data-ai-send>发送</button>
              </div>
              <div class="ai-hint">Ctrl/⌘ + Enter 快速发送 · 原型阶段用模拟响应（PySide6 阶段启用真实 LLM）</div>
            </div>
          </div>
        </div>
      `;
      // 首次进入显示欢迎语
      if (store.aiMessages.length === 0) {
        this._addMessage("assistant",
          "你好，我是设备运维助手。可以问我：\n• 查温度/压力等采样数据\n• 有哪些报警\n• 压力趋势\n• 哪些设备在线");
      } else {
        // 恢复历史对话
        store.aiMessages.forEach((m) => {
          if (m.role === "user") this._addMessage("user", m.content, false);
          else if (m.role === "assistant") this._addMessage("assistant", m.content, false);
        });
      }
    },

    bind() {
      document.getElementById("aiSendBtn")?.addEventListener("click", () => this.handleSend());
      document.getElementById("aiInput")?.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          this.handleSend();
        }
      });
      setTimeout(() => {
        document.getElementById("aiInput")?.focus();
        this._scrollToBottom();
      }, 50);
    },

    /** 处理发送（与原组件逻辑一致） */
    async handleSend() {
      const input = document.getElementById("aiInput");
      if (!input) return;
      const text = util.normalizeText(input.value);
      if (!text) return;
      input.value = "";

      this._addMessage("user", text);
      store.aiMessages.push({ role: "user", content: text });

      const thinkingId = this._addThinking();
      try {
        const decision = await HMI.llmClient.send(text);
        if (decision.type === "tool_call") {
          this._removeThinking(thinkingId);
          this._addToolCard(decision.display, "running");
          await HMI.llmClient.delay(300);
          const result = await HMI.aiTools.call(decision.name, decision.args);
          this._updateLastToolCard(result.ok ? "done" : "error", result.ok ? result.summary : result.error);
          const thinking2 = this._addThinking();
          const summary = await HMI.llmClient.summarize(decision.name, result);
          this._removeThinking(thinking2);
          this._addMessage("assistant", summary);
          store.aiMessages.push({ role: "assistant", content: summary });
        } else {
          this._removeThinking(thinkingId);
          this._addMessage("assistant", decision.content);
          store.aiMessages.push({ role: "assistant", content: decision.content });
        }
      } catch (e) {
        this._removeThinking(thinkingId);
        this._addMessage("assistant", `⚠ 出错了：${e.message}`);
      }
      this._scrollToBottom();
    },

    /** 追加对话气泡。record=true 时记入历史（恢复历史时传 false 避免重复） */
    _addMessage(role, content) {
      const wrap = document.getElementById("aiMessages");
      if (!wrap) return;
      const isUser = role === "user";
      const div = document.createElement("div");
      div.className = `ai-bubble ${isUser ? "ai-bubble-user" : "ai-bubble-assistant"}`;
      div.innerHTML = util.escapeHtml(content).replace(/\n/g, "<br>");
      wrap.appendChild(div);
      this._scrollToBottom();
    },

    _addToolCard(display, status) {
      const wrap = document.getElementById("aiMessages");
      if (!wrap) return;
      const div = document.createElement("div");
      div.className = "ai-tool-card";
      div.innerHTML = `
        <span class="ai-tool-icon">${status === "running" ? "⏳" : status === "done" ? "✓" : "✗"}</span>
        <div class="ai-tool-body">
          <div class="ai-tool-name">调用工具</div>
          <code class="ai-tool-display">${util.escapeHtml(display)}</code>
          <div class="ai-tool-result"></div>
        </div>
      `;
      wrap.appendChild(div);
      this._scrollToBottom();
    },

    _updateLastToolCard(status, resultText) {
      const cards = document.querySelectorAll(".ai-tool-card");
      const last = cards[cards.length - 1];
      if (!last) return;
      const icon = last.querySelector(".ai-tool-icon");
      if (icon) icon.textContent = status === "done" ? "✓" : "✗";
      last.classList.toggle("error", status === "error");
      const result = last.querySelector(".ai-tool-result");
      if (result && resultText) result.innerHTML = util.escapeHtml(resultText).replace(/\n/g, "<br>");
    },

    _addThinking() {
      const wrap = document.getElementById("aiMessages");
      if (!wrap) return null;
      const div = document.createElement("div");
      div.className = "ai-thinking";
      div.innerHTML = `<span></span><span></span><span></span>`;
      wrap.appendChild(div);
      this._scrollToBottom();
      return div;
    },

    _removeThinking(el) {
      if (el && el.parentNode) el.parentNode.removeChild(el);
    },

    _scrollToBottom() {
      const wrap = document.getElementById("aiMessages");
      if (wrap) wrap.scrollTop = wrap.scrollHeight;
    },
  };
})(window);
