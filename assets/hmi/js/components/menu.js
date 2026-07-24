/*
 * menu.js —— 菜单栏弹窗
 *
 * 来源：原型行 2072-2118（openMenu/handleMenuAction/setConnectionState）。
 * 连接/断开/刷新 是少数有真实副作用的菜单项。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;

  const menu = {
    /** 点击菜单栏项，弹出下拉 */
    open(button) {
      const menuName = util.normalizeText(button.textContent);
      const items = HMI.mock.menuActions[menuName] || [];
      const rect = button.getBoundingClientRect();
      const popup = document.getElementById("menuPopup");
      popup.innerHTML = items
        .map((item) => `<button type="button" data-menu-action="${util.escapeHtml(item)}">${util.escapeHtml(item)}</button>`)
        .join("");
      popup.style.left = `${rect.left}px`;
      popup.style.top = `${rect.bottom + 2}px`;
      popup.classList.add("open");
      popup.querySelectorAll("button").forEach((item) => {
        item.addEventListener("click", () => {
          popup.classList.remove("open");
          this.handleAction(item.dataset.menuAction);
        });
      });
    },

    /** 菜单项动作分发 */
    handleAction(action) {
      switch (action) {
        case "连接串口":
          HMI.app.setConnectionState(true);
          return;
        case "断开串口":
          HMI.app.setConnectionState(false);
          return;
        case "刷新串口":
          HMI.toast.show("串口列表已刷新");
          return;
        default:
          HMI.modal.handlePrototypeAction(action);
      }
    },
  };

  HMI.menu = menu;
})(window);
