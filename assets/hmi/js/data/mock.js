/*
 * mock.js —— 模拟数据
 *
 * 集中管理所有页面的 mock 数据，便于后续接入真实通信层时统一替换。
 * 后续接入 pymodbus 后，只需把这里的取数函数改为异步读设备即可。
 */
(function (global) {
  "use strict";

  const HMI = (global.HMI = global.HMI || {});

  const mock = {
    /** 页面定义（PRD §9 表格的 8 个页面） */
    pages: [
      {
        id: "overview", page: "首页/总览",
        feature: "展示当前串口连接状态、同一总线下设备在线状态、通信质量、当前告警、关键采样值和最近操作记录；作为开机后的默认工作台。",
        controls: "状态卡片、设备地址列表、设备 ID 列表、告警条、实时指标卡、最近日志、快捷导航按钮。",
        note: "上位机同一时间只连接一个串口；总线设备通过 Modbus 地址或设备 ID 区分。",
      },
      {
        id: "serial", page: "设备连接",
        feature: "完成串口扫描、串口参数配置、连接/断开、原始串口日志查看、手动发送帧和自动发送测试。",
        controls: "串口号下拉、波特率、数据位、停止位、校验位、连接按钮、HEX/ASCII 切换、行结束符、自动发送间隔、发送历史。",
        note: "同一时间只允许连接一个串口；连接失败、超时、端口占用必须给出明确提示；串口层不要直接耦合 UI。",
      },
      {
        id: "monitor", page: "实时监控",
        feature: "根据设备物模型显示采样点实时值、单位、状态、更新时间和短周期趋势。",
        controls: "设备选择、点位表、状态标签、趋势图、刷新周期、暂停/恢复采集按钮。",
        note: "需要支持异常值、离线、超限、CRC 错误等状态展示。",
      },
      {
        id: "statusPolicy", page: "状态策略",
        feature: "配置设备在线、告警、离线之间的状态判定规则；当指定时间内没有接收到设备通讯数据时，将设备总览中的在线或告警状态切换为离线。",
        controls: "启用离线判定、无通讯超时时间、时间单位、作用范围、状态转换规则、保存策略、恢复默认策略。",
        note: "状态策略只负责设备状态判定；报警是否产生和是否自动恢复由报警规则单独控制。",
      },
      {
        id: "params", page: "参数配置",
        feature: "维护设备配置参数模型定义，描述每个配置项对应的 Modbus RTU 地址、数据类型、权限、单位和约束。",
        controls: "新增参数、编辑参数、删除参数、参数表、Modbus 地址、参数分类、数据类型、访问权限、单位、小数位、上下限、说明。",
        note: "本页面只维护参数模型，不直接读取或写入设备；新增和修改必须校验地址、类型、权限、上下限和小数位。",
      },
      {
        id: "alarms", page: "报警记录",
        feature: "展示报警触发、恢复、确认和历史查询，支持按设备、级别、状态和时间筛选。",
        controls: "报警表格、级别筛选、状态筛选、时间范围、确认按钮、导出按钮。",
        note: "报警规则要能追溯到点位、阈值和触发条件；不能静默清除。",
      },
      {
        id: "history", page: "历史数据",
        feature: "查询指定时间范围内的采样数据，展示趋势曲线、峰值、均值和导出结果。",
        controls: "时间范围选择、点位多选、曲线图、统计卡片、CSV/Excel 导出按钮。",
        note: "MVP 优先 CSV；Excel 可作为后续增强。需要明确数据保存周期和文件路径。",
      },
      {
        id: "settings", page: "系统设置",
        feature: "配置数据保存路径、日志保留周期、通信默认参数、主题、诊断导出和版本信息。",
        controls: "保存路径选择、保留周期、默认串口参数、诊断包导出、清理日志、版本信息。",
        note: "真实配置文件不得提交到 Git；提供 example 配置和错误提示。",
      },
      {
        id: "modelConfig", page: "模型配置",
        feature: "管理 AI 助手使用的 LLM 提供商、base_url、API key 和模型，供自然语言操作设备使用。",
        controls: "提供商下拉（预置 OpenAI/通义/DeepSeek/智谱/Kimi）、base_url、api_key、模型名、启用开关、测试连接。",
        note: "API key 属敏感信息，本地 localStorage 存储；原型阶段不真联网，PySide6 阶段启用真实调用。",
      },
      {
        id: "aiAssistant", page: "AI 助手",
        feature: "通过自然语言对话操作设备：查采样数据、查报警、查趋势、查设备状态。LLM 通过 function calling 调用工具函数。",
        controls: "对话历史区（用户气泡/助手气泡/工具调用卡片/思考动画）、输入框、发送按钮、Ctrl+Enter 快捷发送。",
        note: "原型阶段用模拟响应（关键词匹配触发工具），PySide6 阶段启用真实 LLM（OpenAI 兼容 API + tools 参数）。",
      },
    ],

    /** LLM 提供商预设（选某项自动填 baseUrl 和推荐 model，用户只需填 key） */
    providerPresets: [
      { provider: "OpenAI", baseUrl: "https://api.openai.com/v1", model: "gpt-4o-mini" },
      { provider: "通义千问", baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", model: "qwen-plus" },
      { provider: "DeepSeek", baseUrl: "https://api.deepseek.com", model: "deepseek-chat" },
      { provider: "智谱GLM", baseUrl: "https://open.bigmodel.cn/api/paas/v4/", model: "glm-4-flash" },
      { provider: "Moonshot", baseUrl: "https://api.moonshot.cn/v1", model: "moonshot-v1-8k" },
    ],

    /** 默认模型配置（首次进入或 localStorage 空时回退；空数组表示未配置） */
    defaultModelConfig: [],

    /** 默认发送历史（localStorage 空时回退） */
    defaultSendHistory: [
      "01 03 00 00 00 04",
      "01 06 00 10 00 01",
      "01 03 00 04 00 02",
      "01 10 00 20 00 02 04 00 64 00 C8",
    ],

    /** 串口终端 mock 日志 */
    consoleLines: {
      raw: [
        ["rx", "RX", "14:28:32", "01 03 08 00 FA 01 2C 13 88 00 64"],
        ["tx", "TX", "14:28:33", "01 03 00 00 00 04 44 09"],
        ["rx", "RX", "14:28:34", "01 03 08 00 FB 01 30 13 84 00 66"],
        ["tx", "TX", "14:28:36", "01 06 00 10 00 01 49 CF"],
        ["rx", "RX", "14:28:37", "01 06 00 10 00 01 49 CF"],
        ["tx", "TX", "14:28:39", "01 03 00 04 00 02 85 CA"],
      ],
      stats: [
        ["rx", "RX", "累计", "12,486 B / 286 帧"],
        ["tx", "TX", "累计", "1,024 B / 48 帧"],
        ["rx", "OK", "成功率", "99.7%"],
        ["tx", "CRC", "错误", "0"],
        ["rx", "TIMEOUT", "超时", "0"],
      ],
      diagnostic: [
        ["rx", "INFO", "14:28:30", "串口 COM3 已连接，115200 8N1"],
        ["tx", "INFO", "14:28:31", "Modbus RTU 轮询任务已启动"],
        ["rx", "WARN", "14:27:58", "上一帧 CRC 异常已丢弃"],
        ["tx", "INFO", "14:27:50", "自动发送处于关闭状态"],
      ],
    },

    /** 设备总览表（overview 页） */
    devices: [
      { name: "F407-USB-UART", addr: "01", id: "UART-001", status: "online", last: "28 ms 前", offlineLimit: "< 10 min", alarm: 0 },
      { name: "温湿度终端", addr: "02", id: "TH-002", status: "online", last: "1.2 s 前", offlineLimit: "< 10 min", alarm: 0 },
      { name: "压力采集器", addr: "03", id: "PRS-003", status: "alarm", last: "3.5 s 前", offlineLimit: "< 10 min", alarm: 1 },
      { name: "备用终端", addr: "04", id: "BK-004", status: "offline", last: "12 min 前", offlineLimit: ">= 10 min", alarm: 0 },
    ],

    /** 实时监控点位（monitor 页） */
    monitorPoints: [
      { label: "温度（温湿度终端）", value: 25.0, unit: "℃" },
      { label: "压力（压力采集器）", value: 30.0, unit: "MPa" },
      { label: "密度（压力采集器）", value: 5.0, unit: "MPa" },
      { label: "流量（F407-USB）", value: 1.0, unit: "L/min" },
    ],

    /** monitor 趋势曲线数据（双曲线，最近 12 个点） */
    monitorTrend: {
      labels: ["-11", "-10", "-9", "-8", "-7", "-6", "-5", "-4", "-3", "-2", "-1", "now"],
      series: [
        { name: "温度", color: "#0b6fb3", data: [20, 21, 19, 22, 24, 23, 25, 24, 26, 25, 24, 25] },
        { name: "压力", color: "#11875d", data: [28, 29, 29, 30, 31, 30, 30, 31, 30, 29, 30, 30] },
      ],
    },

    /** 状态策略转换预览（statusPolicy 页右卡） */
    statusTransitions: [
      { current: "在线", currentClass: "stat-ok", condition: "10 分钟内收到有效数据", result: "在线", resultClass: "stat-ok" },
      { current: "在线", currentClass: "stat-ok", condition: "超过 10 分钟未收到有效数据", result: "离线", resultClass: "" },
      { current: "告警", currentClass: "warn-text", condition: "10 分钟内收到有效数据", result: "告警", resultClass: "warn-text" },
      { current: "告警", currentClass: "warn-text", condition: "超过 10 分钟未收到有效数据", result: "离线", resultClass: "" },
    ],

    /** Modbus 参数定义（params 页，预置 4 行） */
    params: [
      { name: "temperature", display: "温度", address: "0x0000", category: "采样参数", type: "float32", access: "只读", unit: "℃", decimals: 1, min: -40, max: 125, desc: "缩放 0.1" },
      { name: "pressure", display: "压力", address: "0x0002", category: "采样参数", type: "float32", access: "只读", unit: "MPa", decimals: 2, min: 0, max: 60, desc: "缩放 0.01" },
      { name: "sample_period", display: "采样周期", address: "0x0010", category: "配置参数", type: "uint16", access: "读写", unit: "ms", decimals: 0, min: 200, max: 5000, desc: "写入需确认" },
      { name: "device_addr", display: "设备地址", address: "0x0011", category: "配置参数", type: "uint8", access: "读写", unit: "-", decimals: 0, min: 1, max: 247, desc: "Modbus 从站地址" },
    ],

    /** 报警记录（alarms 页，预置 3 行） */
    alarms: [
      { id: 1, time: "18:27:58", content: "压力接近上限", terminal: "压力采集器", level: "预警", acknowledged: false },
      { id: 2, time: "18:18:22", content: "CRC 异常帧已丢弃", terminal: "COM3", level: "一般", acknowledged: true, ackUser: "工程师", ackTime: "18:19:04" },
      { id: 3, time: "17:52:09", content: "备用终端离线超过 10 分钟", terminal: "备用终端", level: "提示", acknowledged: true, ackUser: "工程师", ackTime: "17:55:21" },
    ],

    /** 软件信息（settings 页左卡） */
    softwareInfo: [
      ["软件名称", "multi-protocol-hmi"],
      ["应用版本", "v0.1.0"],
      ["运行平台", "Windows 10/11"],
      ["运行时长", "12:36:18"],
    ],

    /** 维护信息（settings 页右卡） */
    maintenanceInfo: [
      ["数据保存路径", "./save"],
      ["日志空间", "128 / 512 MB"],
      ["配置文件", "config.example.json"],
      ["帧错误计数", "1"],
    ],

    /** 菜单栏结构（menuActions） */
    menuActions: {
      "文件": ["新建项目", "打开配置", "保存配置", "导入参数模型", "导出参数模型", "退出"],
      "连接": ["连接串口", "断开串口", "刷新串口", "清空串口日志"],
      "设备": ["设备总览", "串口连接", "实时监控", "状态策略", "参数配置"],
      "数据": ["报警记录", "历史数据", "导出 CSV", "清空历史缓存"],
      "工具": ["诊断包", "日志清理", "系统设置"],
      "帮助": ["关于软件", "快捷键", "使用文档"],
    },

    /** 页面名 → id 映射（pageByLabel，用于菜单跳转） */
    pageByLabel: {
      "设备总览": "overview",
      "首页/总览": "overview",
      "串口连接": "serial",
      "实时监控": "monitor",
      "状态策略": "statusPolicy",
      "参数配置": "params",
      "报警记录": "alarms",
      "历史数据": "history",
      "系统设置": "settings",
      "模型配置": "modelConfig",
      "AI 助手": "aiAssistant",
    },
  };

  HMI.mock = mock;
})(window);
