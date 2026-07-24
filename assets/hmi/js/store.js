/*
 * store.js —— 全局可变状态
 *
 * 集中管理运行时可变状态，配合各页面模块。
 * 第二阶段相对原型的增强：
 *   - params/alarms 用模型对象数组（替代原型的 DOM 操作），便于真实 CRUD
 *   - 增加 paramsDirty（未保存标记）、autoSendTimer（自动发送句柄）
 *   - 增加 connectionState 显式状态机
 */
(function (global) {
  "use strict";

  const HMI = (global.HMI = global.HMI || {});
  const SEND_HISTORY_KEY = "multi-protocol-hmi-send-history";
  const MODEL_CONFIG_KEY = "multi-protocol-hmi-model-config";

  // 页面渲染器注册表：id → {render, bind}。
  // 必须在此（早于所有 pages/*.js）初始化，否则页面文件注册时 HMI.pages 为 undefined。
  HMI.pages = HMI.pages || {};

  /** 深拷贝（JSON 安全的数据） */
  function clone(obj) {
    return JSON.parse(JSON.stringify(obj));
  }

  /** 从 localStorage 读取发送历史，失败回退默认 */
  function loadSendHistory() {
    try {
      const saved = JSON.parse(localStorage.getItem(SEND_HISTORY_KEY) || "[]");
      if (Array.isArray(saved) && saved.length) return saved.slice(0, 20);
    } catch (e) {
      return HMI.mock.defaultSendHistory.slice();
    }
    return HMI.mock.defaultSendHistory.slice();
  }

  /** 从 localStorage 读取模型配置，失败/空回退默认（空数组） */
  function loadModelConfig() {
    try {
      const saved = JSON.parse(localStorage.getItem(MODEL_CONFIG_KEY) || "[]");
      if (Array.isArray(saved)) return saved;
    } catch (e) {
      return clone(HMI.mock.defaultModelConfig);
    }
    return clone(HMI.mock.defaultModelConfig);
  }

  const store = {
    /** 当前页面 id */
    currentPageId: "overview",

    /** 当前从站地址（Modbus 报文第一字节，参数页可配，默认 1） */
    slaveId: 1,

    /** PRD 页面定义的运行时副本（PRD 编辑器可改） */
    pages: clone(HMI.mock.pages),

    /** 连接状态：'connected' | 'disconnected' */
    connectionState: "connected",

    /** 发送历史（最多 20 条，去重置顶） */
    sendHistory: loadSendHistory(),

    /** 参数定义运行时副本（支持真实 CRUD） */
    params: clone(HMI.mock.params),

    /** 参数是否有未保存修改（驱动 tag.warn "未保存"） */
    paramsDirty: false,

    /** 参数表筛选：'all' | '采样参数' | '配置参数' */
    paramFilter: "all",

    /** 实时监控曲线显示状态：{paramName: true|false}，默认未记录的视为 true（显示） */
    curveVisible: {},

    /** 历史数据页选中的点位（采样参数 name 数组）；null 表示"全部采样参数"（默认） */
    historySelectedPoints: null,

    /** 模型配置列表：[{id, provider, baseUrl, apiKey, model, enabled}]，localStorage 持久化 */
    modelConfig: loadModelConfig(),

    /** AI 对话历史：[{role:"user"|"assistant"|"tool", content/tool_calls/tool_call_id}] */
    aiMessages: [],

    /** 参数表单当前编辑模式：'create' | 'edit' + 编辑中的参数名 */
    paramEditMode: "create",
    paramEditingName: null,

    /** 报警记录运行时副本（支持确认状态机） */
    alarms: clone(HMI.mock.alarms),

    /** 自动发送定时器句柄（serial 页） */
    autoSendTimer: null,

    /** 串口号（与工具栏/状态联动） */
    currentPort: "COM3",

    /** 持久化发送历史 */
    persistSendHistory() {
      try {
        localStorage.setItem(SEND_HISTORY_KEY, JSON.stringify(this.sendHistory.slice(0, 20)));
        return true;
      } catch (e) {
        return false;
      }
    },

    /** 保存发送帧：去重、置顶、截断 20 */
    pushSendHistory(value) {
      const frame = HMI.util.normalizeText(value);
      if (!frame) return false;
      this.sendHistory = [frame, ...this.sendHistory.filter((item) => item !== frame)].slice(0, 20);
      this.persistSendHistory();
      return true;
    },

    /** 报警未确认数量 */
    unackAlarmCount() {
      return this.alarms.filter((a) => !a.acknowledged).length;
    },

    /** 按 name 查找参数 */
    findParam(name) {
      return this.params.find((p) => p.name === name) || null;
    },

    /** 持久化模型配置到 localStorage */
    persistModelConfig() {
      try {
        localStorage.setItem(MODEL_CONFIG_KEY, JSON.stringify(this.modelConfig));
        return true;
      } catch (e) {
        return false;
      }
    },

    /** 取第一个启用的模型配置（AI 助手默认用它），无则 null */
    activeModelConfig() {
      return this.modelConfig.find((c) => c.enabled) || null;
    },

    /** 取采样参数（多处复用：monitor/history/aiTools） */
    sampleParams() {
      return this.params.filter((p) => p.category === "采样参数");
    },
  };

  HMI.store = store;
})(window);
