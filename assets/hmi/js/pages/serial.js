/*
 * serial.js —— 设备连接页
 * 布局见 docs/hmi/page-layout-spec.md §2，交互见 interaction-spec.md §2。
 * 实际逻辑委托给 HMI.console 组件（components/console.js）。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});

  HMI.pages.serial = {
    render() {
      HMI.console.render();
    },
    bind() {
      HMI.console.bind();
    },
  };
})(window);
