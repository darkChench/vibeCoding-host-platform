/*
 * dropdown.js —— 自定义下拉组件（强制上拉）
 *
 * 为什么需要它：
 *   原生 <select> 的弹出方向由浏览器决定，无法用 CSS/HTML 控制。
 *   serial 页 sendbar 里"发送格式"（2 项）和"行结束符"（4 项）原生 select
 *   一个向下弹、一个向上弹，方向不一致。
 *   本组件用自定义弹层替换，统一强制向上弹出，保证视觉一致。
 *
 * 对 PySide6 重写的参考：
 *   QComboBox 的弹出方向由 view 的 position 控制，可自由设定，无此限制；
 *   本组件仅用于 Web 原型统一视觉，Qt 实现直接用 QComboBox 即可。
 *
 * 用法：
 *   const html = HMI.dropdown.html("format", ["HEX","ASCII"], "HEX");
 *   // 渲染后绑定（在页面 bind 阶段）：
 *   HMI.dropdown.bind(document.getElementById("content"));
 *   // 读值：
 *   HMI.dropdown.getValue(root, "format"); // → "HEX"
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;

  const dropdown = {
    /** 值变化监听器：{name: [cb, cb, ...]} */
    _listeners: {},

    /**
     * 注册值变化回调（覆盖式：同名只保留最后一次注册，避免重复绑定累积）。
     * @param {string} name  data-dropdown-name
     * @param {function} cb  (value) => void
     */
    onChange(name, cb) {
      this._listeners[name] = [cb];
    },
    /**
     * 生成下拉组件 HTML（替换原生 <select>）。
     * @param {string} name  逻辑名，用于 getValue 和 data-dropdown-name
     * @param {string[]} items  选项数组
     * @param {string} selected  默认选中项（单选模式）
     * @param {string} ariaLabel  无障碍标签
     * @param {string} drop  弹出方向：'up'（默认）/ 'down'
     * @param {Object} opts  扩展选项：{ multi:boolean, multiSelected:string[], placeholder:string }
     *   - multi:true 启用多选（点击不关闭、切换勾选、触发器显示汇总）
     *   - multiSelected 多选模式下默认选中的项
     *   - placeholder 多选模式下无选择时的占位文案
     */
    html(name, items, selected, ariaLabel, drop, opts) {
      const safeName = util.escapeHtml(name);
      const labelTxt = util.escapeHtml(ariaLabel || name);
      const safeDrop = drop === "down" ? "down" : "up";
      opts = opts || {};
      const multi = !!opts.multi;
      const placeholder = opts.placeholder || "请选择";

      let triggerText;
      let optionRows;
      if (multi) {
        const sel = Array.isArray(opts.multiSelected) ? opts.multiSelected : items.slice();
        triggerText = sel.length ? sel.join("、") : placeholder;
        optionRows = items.map((it) => `
          <button type="button" class="select-custom-option${sel.includes(it) ? " selected" : ""}" data-dropdown-option="${util.escapeHtml(it)}" role="option" aria-selected="${sel.includes(it)}">
            <span class="select-custom-check" aria-hidden="true">${sel.includes(it) ? "✓" : ""}</span>${util.escapeHtml(it)}
          </button>
        `).join("");
      } else {
        const current = items.includes(selected) ? selected : items[0];
        triggerText = current;
        optionRows = items.map((it) => `
          <button type="button" class="select-custom-option${it === current ? " selected" : ""}" data-dropdown-option="${util.escapeHtml(it)}" role="option">${util.escapeHtml(it)}</button>
        `).join("");
      }
      return `
        <div class="select-custom${multi ? " multi" : ""}" data-dropdown-name="${safeName}" data-drop="${safeDrop}" data-multi="${multi}" role="combobox" aria-label="${labelTxt}" tabindex="0">
          <span class="select-custom-value" data-dropdown-value>${util.escapeHtml(triggerText)}</span>
          <span class="select-custom-caret" aria-hidden="true">▾</span>
          <div class="select-custom-popup" data-dropdown-popup role="listbox">
            ${optionRows}
          </div>
        </div>
      `;
    },

    /**
     * 在指定根节点内绑定所有 .select-custom 的交互。
     * 切换弹出、点击选项、点外部关闭、键盘支持。
     */
    bind(root) {
      const roots = root ? root.querySelectorAll : null;
      const nodes = (root || document).querySelectorAll(".select-custom:not([data-dropdown-bound])");
      nodes.forEach((node) => {
        node.setAttribute("data-dropdown-bound", "true");
        const toggle = () => {
          // 关闭其他下拉
          root.querySelectorAll(".select-custom.open").forEach((other) => {
            if (other !== node) other.classList.remove("open");
          });
          node.classList.toggle("open");
        };
        // 点击触发器区域
        node.addEventListener("click", (e) => {
          if (e.target.closest("[data-dropdown-option]")) return; // 选项点击单独处理
          e.stopPropagation();
          toggle();
        });
        // 选项点击
        const nodeName = node.dataset.dropdownName;
        const isMulti = node.dataset.multi === "true";
        node.querySelectorAll("[data-dropdown-option]").forEach((opt) => {
          opt.addEventListener("click", (e) => {
            e.stopPropagation();
            const val = opt.dataset.dropdownOption;

            if (isMulti) {
              // 多选：切换该项选中态，不关闭弹层，更新勾选标记 + 触发器汇总
              const sel = !opt.classList.contains("selected");
              opt.classList.toggle("selected", sel);
              opt.setAttribute("aria-selected", String(sel));
              const check = opt.querySelector(".select-custom-check");
              if (check) check.textContent = sel ? "✓" : "";
              const selected = Array.from(node.querySelectorAll(".select-custom-option.selected"))
                .map((o) => o.dataset.dropdownOption);
              const placeholder = "请选择";
              const summary = selected.length ? selected.join("、") : placeholder;
              node.querySelector("[data-dropdown-value]").textContent = summary;
              if (HMI.dropdown._listeners[nodeName]) {
                HMI.dropdown._listeners[nodeName].forEach((cb) => cb(selected));
              }
            } else {
              // 单选：原逻辑
              const oldVal = node.querySelector("[data-dropdown-value]").textContent.trim();
              node.querySelector("[data-dropdown-value]").textContent = val;
              node.querySelectorAll(".select-custom-option").forEach((o) => o.classList.remove("selected"));
              opt.classList.add("selected");
              node.classList.remove("open");
              if (oldVal !== val && HMI.dropdown._listeners[nodeName]) {
                HMI.dropdown._listeners[nodeName].forEach((cb) => cb(val));
              }
            }
          });
        });
        // 键盘：Enter/Space 切换，Esc 关闭
        node.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); }
          else if (e.key === "Escape") node.classList.remove("open");
        });
      });

      // 一次性绑定"点外部关闭"（绑在 document，避免重复）
      if (!dropdown._docBound) {
        document.addEventListener("click", (e) => {
          if (!e.target.closest(".select-custom")) {
            document.querySelectorAll(".select-custom.open").forEach((n) => n.classList.remove("open"));
          }
        });
        dropdown._docBound = true;
      }
    },

    /**
     * 读取某个下拉的当前值。
     * @param {Element} root  查询范围
     * @param {string} name  data-dropdown-name
     */
    getValue(root, name) {
      const node = (root || document).querySelector(`.select-custom[data-dropdown-name="${name}"]`);
      return node ? util.normalizeText(node.querySelector("[data-dropdown-value]").textContent) : "";
    },
  };

  HMI.dropdown = dropdown;
})(window);
