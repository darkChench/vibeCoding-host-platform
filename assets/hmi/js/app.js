/*
 * app.js —— 主入口、路由、全局事件
 *
 * 来源：原型行 1274-2214 的主流程（showPage/renderTabs/renderContent/bindDynamicActions/
 *       setConnectionState 及底部全局绑定）。
 *
 * 职责：
 *   - 维护 currentPageId、渲染 tabs 和 content
 *   - 分发到各页面的 render/bind
 *   - 处理连接状态机
 *   - 绑定全局事件（菜单栏、toolbar、tree 导航、模态按钮）
 *
 * 页面注册：HMI.pages 是 id → {render, bind} 的映射，各页面文件自行注册。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;
  const store = HMI.store;

  const app = {
    /** 切换页面 */
    showPage(pageId) {
      // 切页前清理当前页的资源：停止 monitor 实时刷新定时器 + 销毁 Chart 实例
      if (HMI.pages.monitor && typeof HMI.pages.monitor._stopRefresh === "function") {
        HMI.pages.monitor._stopRefresh();
      }
      const content = document.getElementById("content");
      HMI.chart.destroy(content);

      store.currentPageId = pageId;
      const page = store.pages.find((p) => p.id === pageId) || store.pages[0];
      document.getElementById("windowTitle").textContent = `Windows 上位机 - ${page.page}`;
      document.getElementById("statusPage").textContent = page.page;

      // 侧边栏 active
      document.querySelectorAll(".tree-item[data-page]").forEach((btn) => {
        btn.classList.toggle("active", btn.dataset.page === pageId);
      });

      this._renderTabs();
      this._renderContent(page);
    },

    /** 渲染顶部 tabs */
    _renderTabs() {
      const tabs = document.getElementById("tabs");
      tabs.innerHTML = store.pages.map((p) => `
        <button class="tab${p.id === store.currentPageId ? " active" : ""}" type="button" data-page="${p.id}">
          ${util.escapeHtml(p.page)}
        </button>
      `).join("");
      tabs.querySelectorAll("[data-page]").forEach((btn) => {
        btn.addEventListener("click", () => this.showPage(btn.dataset.page));
      });
    },

    /** 渲染主区内容，分发到各页面渲染器 */
    _renderContent(page) {
      const renderer = HMI.pages[page.id];
      if (renderer && typeof renderer.render === "function") {
        renderer.render();
      } else {
        // 未注册页面（如 PRD 新增的 custom-xxx）回退到 overview
        HMI.pages.overview.render();
        return;
      }
      // 绑定通用动作（兜底按钮）+ 页面专属绑定
      this._bindGenericActions();
      if (renderer && typeof renderer.bind === "function") {
        renderer.bind();
      }
    },

    /**
     * 兜底绑定：当前页所有未带专用 data-* 的 button，走 prototype action。
     * 来源：原型行 2058-2069。
     */
    _bindGenericActions() {
      const content = document.getElementById("content");
      content.querySelectorAll("button").forEach((btn) => {
        if (
          btn.dataset.jump ||
          btn.dataset.paramAction ||
          btn.dataset.alarmAction ||
          btn.dataset.sendAction !== undefined ||
          btn.dataset.sendHistoryToggle !== undefined ||
          btn.dataset.sendHistoryClear !== undefined ||
          btn.dataset.aiSend !== undefined ||
          btn.classList.contains("console-tab")
        ) return;
        btn.addEventListener("click", () => HMI.modal.handlePrototypeAction(btn.textContent));
      });
    },

    /** 连接状态机（toolbar 按钮 + 菜单联动） */
    setConnectionState(connected) {
      store.connectionState = connected ? "connected" : "disconnected";
      // 若断开，停止自动发送
      if (!connected) HMI.console._stopAutoSend();

      const status = document.querySelector(".stats-strip span");
      const connectBtn = document.querySelector(".toolbar .btn");
      if (status) {
        status.textContent = connected ? `${store.currentPort} 已连接` : `${store.currentPort} 未连接`;
        status.classList.toggle("stat-ok", connected);
      }
      if (connectBtn) connectBtn.textContent = connected ? "断开" : "连接";
      HMI.toast.show(connected ? "串口已连接" : "串口已断开");

      // 若当前在 serial 页，重渲以更新未连接提示与发送按钮 disabled
      if (store.currentPageId === "serial") this.showPage("serial");
    },

    /** 绑定全局事件（页面切换不影响） */
    _bindGlobal() {
      // 菜单栏
      document.querySelectorAll(".menu-item").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          HMI.menu.open(btn);
        });
      });
      // 点空白关菜单
      document.addEventListener("click", (e) => {
        const popup = document.getElementById("menuPopup");
        if (!popup.contains(e.target)) popup.classList.remove("open");
      });

      // toolbar 下拉 change
      document.querySelectorAll(".toolbar .select").forEach((sel) => {
        sel.addEventListener("change", () => {
          const label = sel.closest(".tool-group")?.querySelector(".tool-label")?.textContent || "参数";
          if (label === "串口") store.currentPort = sel.value;
          HMI.toast.show(`${util.normalizeText(label)}：${sel.value}`);
        });
      });

      // 连接按钮
      document.querySelector(".toolbar .btn")?.addEventListener("click", (e) => {
        const connected = util.normalizeText(e.currentTarget.textContent) === "连接";
        this.setConnectionState(connected);
      });
      // 刷新串口按钮
      document.querySelector(".toolbar .btn.secondary")?.addEventListener("click", () => {
        HMI.toast.show("串口列表已刷新");
      });

      // 侧边栏导航
      document.querySelectorAll(".tree-item[data-page]").forEach((btn) => {
        btn.addEventListener("click", () => this.showPage(btn.dataset.page));
      });

      // actionModal 按钮
      document.getElementById("actionCloseBtn")?.addEventListener("click", () => HMI.modal.closeAction());
      document.getElementById("actionCancelBtn")?.addEventListener("click", () => HMI.modal.closeAction());
      document.getElementById("actionConfirmBtn")?.addEventListener("click", () => HMI.modal.confirmAction());
      document.getElementById("actionModal")?.addEventListener("click", (e) => {
        if (e.target.id === "actionModal") HMI.modal.closeAction();
      });
    },

    /** 启动 */
    init() {
      this._bindGlobal();
      this.showPage("overview");
      this.updateAiStatus();
    },

    /** 更新工具栏 AI 状态指示（根据是否有启用的模型配置） */
    updateAiStatus() {
      const el = document.getElementById("aiStatus");
      if (!el) return;
      const cfg = HMI.store.activeModelConfig();
      if (cfg) {
        el.textContent = `AI ${cfg.provider}`;
        el.className = "stat-ok";
      } else {
        el.textContent = "AI 未配置";
        el.className = "stat-warn";
      }
    },
  };

  HMI.app = app;

  // DOM 就绪后启动
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => HMI.app.init());
  } else {
    HMI.app.init();
  }
})(window);
