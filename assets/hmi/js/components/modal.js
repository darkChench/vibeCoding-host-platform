/*
 * modal.js —— 通用动作模态
 *
 * 来源：原型行 1845-1886（showAction/handlePrototypeAction）。
 * 第二阶段增强：actionDetails 字典集中到此；新增 loading 支持与 confirm 回调。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;

  /** 18 个动作键 → 说明文本（来自原型 actionDetails） */
  const actionDetails = {
    "发送": "模拟发送当前输入框中的帧数据，并在原型中记录一次 TX 操作。",
    "保存定义": "保存当前参数模型定义。此页面只维护模型，不执行设备读写。",
    "校验定义": "检查参数名、Modbus 地址、数据类型、权限、范围等定义是否完整。",
    "取消修改": "放弃当前表单修改，恢复为表格中选中的参数定义。",
    "新增参数": "清空表单并进入新增参数定义状态。",
    "编辑勾选": "把当前唯一勾选的参数载入表单进行编辑。",
    "删除勾选": "删除当前勾选的参数定义，实际产品中需要二次确认。",
    "导入模板": "从本地配置文件导入参数模型定义。",
    "导出模板": "把当前参数模型导出为配置文件。",
    "确认勾选": "确认当前勾选的报警记录，并记录确认人和确认时间。",
    "确认全部未确认": "批量确认当前筛选结果中的未确认报警。",
    "导出报警": "导出报警记录为 CSV 或诊断附件。",
    "查询": "按当前时间范围和点位条件查询历史数据。",
    "导出 CSV": "导出当前查询结果。",
    "清理日志": "清理本地诊断日志，实际产品中需要确认保留时间范围。",
    "导出诊断": "打包运行日志、配置文件和通信统计信息。",
    "保存状态策略": "保存状态判定规则。在线或告警设备超过配置的无通讯时间后，在设备总览中切换为离线。",
    "恢复默认策略": "恢复默认离线策略：启用离线判定，无通讯 10 分钟后显示离线。",
  };

  let confirmCallback = null;

  const modal = {
    /** 打开通用动作框。confirmCb 为"确定"回调（可选） */
    showAction(title, detail, confirmCb) {
      const titleEl = document.getElementById("actionTitle");
      const bodyEl = document.getElementById("actionBody");
      if (titleEl) titleEl.textContent = title;
      if (bodyEl) {
        const pageName = HMI.store.currentPageId
          ? (HMI.store.pages.find((p) => p.id === HMI.store.currentPageId) || {}).page || ""
          : "";
        bodyEl.innerHTML =
          `<div><strong>${util.escapeHtml(pageName)}</strong></div>` +
          `<div>${util.escapeHtml(detail)}</div>`;
      }
      confirmCallback = typeof confirmCb === "function" ? confirmCb : null;
      document.getElementById("actionModal").classList.add("open");
    },

    closeAction() {
      document.getElementById("actionModal").classList.remove("open");
      confirmCallback = null;
    },

    /** 兜底：prototype 通用按钮（无专用逻辑）走此方法 */
    handlePrototypeAction(label) {
      const normalized = util.normalizeText(label);
      const pageId = HMI.mock.pageByLabel[normalized];
      if (pageId) {
        HMI.app.showPage(pageId);
        return;
      }
      const detail = actionDetails[normalized] ||
        "这是原型交互占位，用于评审该按钮是否需要保留、改名或补充真实流程。";
      this.showAction(normalized || "操作", detail);
    },

    /** 确认按钮：执行回调并关闭 */
    confirmAction() {
      const cb = confirmCallback;
      this.closeAction();
      if (cb) cb();
      else HMI.toast.show("操作已确认");
    },
  };

  HMI.modal = modal;
})(window);