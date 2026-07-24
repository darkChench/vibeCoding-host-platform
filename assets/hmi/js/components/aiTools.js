/*
 * aiTools.js —— AI 助手工具函数层
 *
 * 定义 4 个只读工具的 JSON Schema（给 LLM 的 tools 参数）和 handler 表（执行函数）。
 * handler 读 store.* 运行时状态（不读 mock.*），保证报警确认/参数增删后查到最新数据。
 *
 * 工具全部只读，原型阶段不写设备。
 * PySide6 阶段：handler 函数体替换为 pymodbus/数据库调用，tools 定义几乎不变。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const store = HMI.store;

  /** 工具的 JSON Schema 定义（OpenAI function calling tools 参数格式） */
  const TOOLS = [
    {
      type: "function",
      function: {
        name: "read_sensor",
        description: `读取指定采样点的实时值、单位和状态。当用户问"温度多少""压力多少""读传感器"时使用。`,
        parameters: {
          type: "object",
          properties: {
            point: {
              type: "string",
              description: "采样点名称（display 名），如 温度、压力",
            },
          },
          required: ["point"],
        },
      },
    },
    {
      type: "function",
      function: {
        name: "get_alarms",
        description: `查询报警记录，可按级别或是否未确认筛选。当用户问"有什么报警""未确认告警"时使用。`,
        parameters: {
          type: "object",
          properties: {
            level: {
              type: "string",
              description: "级别筛选：预警/一般/提示，不传则返回全部",
              enum: ["预警", "一般", "提示"],
            },
            unacknowledged: {
              type: "boolean",
              description: "true 只返回未确认报警",
            },
          },
        },
      },
    },
    {
      type: "function",
      function: {
        name: "get_trend",
        description: `查询指定采样点最近一段时间的趋势数据。当用户问"温度趋势""压力曲线""最近变化"时使用。`,
        parameters: {
          type: "object",
          properties: {
            point: {
              type: "string",
              description: "采样点名称，如 温度、压力",
            },
          },
          required: ["point"],
        },
      },
    },
    {
      type: "function",
      function: {
        name: "get_device_status",
        description: `获取所有设备的在线/告警/离线状态。当用户问"设备状态""哪些在线""离线设备"时使用。`,
        parameters: { type: "object", properties: {} },
      },
    },
  ];

  /** 按 display 名模糊查找采样参数 */
  function findParamByDisplay(display) {
    const norm = HMI.util.normalizeText(display);
    return store.sampleParams().find((p) => {
      const d = HMI.util.normalizeText(p.display);
      return d === norm || d.includes(norm) || norm.includes(d);
    });
  }

  /** handler 表：函数名 → (args) => {ok, data, summary}（read_sensor/get_trend 走协议层，是 async） */
  const HANDLERS = {
    async read_sensor({ point } = {}) {
      if (!point) return { ok: false, error: "缺少采样点名称" };
      const p = findParamByDisplay(point);
      if (!p) return { ok: false, error: `未找到采样点"${point}"` };
      // 走协议层：生成真实 Modbus 请求帧 → 模拟回包 → 解析工程值
      const result = await HMI.modbus.readParam(p);
      if (!result.ok) return { ok: false, error: "读取失败" };
      const decimals = Number(p.decimals) || 0;
      const value = result.value.toFixed(decimals);
      return {
        ok: true,
        data: { point: p.display, value: result.value, unit: p.unit, range: `${p.min} ~ ${p.max}` },
        summary: `${p.display} = ${value} ${p.unit || ""}（范围 ${p.min}~${p.max}）`,
      };
    },

    get_alarms({ level, unacknowledged } = {}) {
      let r = store.alarms;
      if (level) r = r.filter((a) => a.level === level);
      if (unacknowledged) r = r.filter((a) => !a.acknowledged);
      const list = r.map((a) => ({
        time: a.time,
        content: a.content,
        terminal: a.terminal,
        level: a.level,
        status: a.acknowledged ? "已确认" : "未确认",
      }));
      return {
        ok: true,
        data: list,
        summary: list.length
          ? `共 ${list.length} 条报警：\n` + list.map((a) => `• [${a.time}] ${a.content}（${a.terminal}，${a.level}，${a.status}）`).join("\n")
          : "没有符合条件的报警",
      };
    },

    async get_trend({ point } = {}) {
      if (!point) return { ok: false, error: "缺少采样点名称" };
      const p = findParamByDisplay(point);
      if (!p) return { ok: false, error: `未找到采样点"${point}"` };
      // 走协议层：连续读 12 次得到趋势数据（每次都生成真实报文+模拟回包）
      const decimals = Number(p.decimals) || 0;
      const data = [];
      for (let i = 0; i < 12; i++) {
        const r = await HMI.modbus.readParam(p);
        if (r.ok) data.push(Number(r.value.toFixed(decimals)));
      }
      if (!data.length) return { ok: false, error: "趋势数据读取失败" };
      const avg = (data.reduce((s, v) => s + v, 0) / data.length).toFixed(decimals);
      const peak = Math.max(...data).toFixed(decimals);
      return {
        ok: true,
        data: { point: p.display, unit: p.unit, points: data, avg: Number(avg), peak: Number(peak) },
        summary: `${p.display} 最近 12 个采样点：均值 ${avg}、峰值 ${peak} ${p.unit || ""}`,
      };
    },

    get_device_status() {
      const devices = HMI.mock.devices.map((d) => ({
        name: d.name,
        addr: d.addr,
        id: d.id,
        status: d.status,
        last: d.last,
        alarm: d.alarm,
      }));
      const online = devices.filter((d) => d.status === "online").length;
      const offline = devices.filter((d) => d.status === "offline").length;
      const alarm = devices.filter((d) => d.status === "alarm").length;
      return {
        ok: true,
        data: devices,
        summary: `设备状态：${online} 在线、${alarm} 告警、${offline} 离线\n` +
          devices.map((d) => `• ${d.name}（${d.addr}）：${d.status === "online" ? "在线" : d.status === "alarm" ? "告警" : "离线"}`).join("\n"),
      };
    },
  };

  HMI.aiTools = {
    TOOLS,
    HANDLERS,
    /** 执行工具调用，返回 {ok, data, summary} 或 {ok:false, error} */
    call(name, args) {
      const handler = HANDLERS[name];
      if (!handler) return { ok: false, error: `未知工具：${name}` };
      try {
        return handler(args || {});
      } catch (e) {
        return { ok: false, error: `工具执行异常：${e.message}` };
      }
    },
  };
})(window);
