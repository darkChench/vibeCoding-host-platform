/*
 * toast.js —— 轻量操作反馈
 *
 * 来源：原型行 2120-2124 的 showToast。
 * 用法：HMI.toast.show("已保存");
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  let timer = null;

  HMI.toast = {
    /** @param {string} message */
    show(message) {
      const el = document.getElementById("toast");
      if (!el) return;
      el.textContent = message;
      el.classList.add("show");
      if (timer) clearTimeout(timer);
      timer = setTimeout(() => el.classList.remove("show"), 1600);
    },
  };
})(window);
