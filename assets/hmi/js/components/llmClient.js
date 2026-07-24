/*
 * llmClient.js —— LLM 调用层
 *
 * 原型阶段：用模拟响应（关键词匹配触发工具调用），不真联网，避免浏览器 CORS。
 * PySide6 阶段：取消下方"真实调用"注释块，启用 OpenAI 兼容请求（Qt 无 CORS）。
 *
 * 模拟真实 function calling 的两步流程：
 *   1. send(userText) → 返回 {type:"tool_call", name, args} 或 {type:"text", content}
 *   2. summarize(toolName, toolResult) → 返回基于工具结果的自然语言总结
 * 让原型交互体验和真实 LLM 一致。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;

  /** 延时工具（模拟网络/推理耗时） */
  function delay(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  /**
   * 第一步：用户输入 → 决定调用哪个工具（或直接回复）
   * @param {string} userText
   * @returns {Promise<{type:"tool_call", name, args, display} | {type:"text", content}>}
   */
  async function send(userText) {
    await delay(400 + Math.random() * 400); // 模拟推理耗时
    const t = util.normalizeText(userText);

    // 关键词匹配 → 工具调用（模拟 LLM 的意图识别）
    // 趋势要放最前面（"温度趋势"同时含"温度"，应优先匹配趋势）
    if (/趋势|曲线|变化|波动/.test(t)) {
      const point = extractPoint(t) || "温度";
      return {
        type: "tool_call",
        name: "get_trend",
        args: { point },
        display: `get_trend(point="${point}")`,
      };
    }
    if (/报警|告警|异常.*记录|未确认/.test(t)) {
      const unack = /未确认|未处理/.test(t);
      const levelMatch = t.match(/预警|一般|提示/);
      return {
        type: "tool_call",
        name: "get_alarms",
        args: levelMatch ? { level: levelMatch[0], unacknowledged: unack } : { unacknowledged: unack },
        display: `get_alarms(${levelMatch ? `level="${levelMatch[0]}", ` : ""}unacknowledged=${unack})`,
      };
    }
    if (/设备|状态|在线|离线|哪些.*线/.test(t)) {
      return {
        type: "tool_call",
        name: "get_device_status",
        args: {},
        display: "get_device_status()",
      };
    }
    if (/温度|压力|密度|流量|采样|读|多少|当前/.test(t)) {
      const point = extractPoint(t) || "温度";
      return {
        type: "tool_call",
        name: "read_sensor",
        args: { point },
        display: `read_sensor(point="${point}")`,
      };
    }

    // 无匹配 → 兜底引导
    return {
      type: "text",
      content: `我可以帮你查询这些信息：\n• 采样数据（如"查温度"）\n• 报警记录（如"有哪些报警"）\n• 趋势数据（如"压力趋势"）\n• 设备状态（如"哪些设备在线"）`,
    };
  }

  /** 从用户输入里提取采样点名（温度/压力/密度/流量） */
  function extractPoint(text) {
    const map = [
      ["温度", "温度"], ["temperature", "温度"],
      ["压力", "压力"], ["pressure", "压力"],
      ["密度", "密度"], ["density", "密度"],
      ["流量", "流量"], ["flow", "流量"],
    ];
    for (const [kw, name] of map) {
      if (text.toLowerCase().includes(kw.toLowerCase())) return name;
    }
    return null;
  }

  /**
   * 第二步：基于工具结果生成自然语言总结（模拟 LLM 的总结能力）
   * @param {string} toolName
   * @param {{ok, summary?, data?, error?}} toolResult
   * @returns {Promise<string>}
   */
  async function summarize(toolName, toolResult) {
    await delay(300 + Math.random() * 300);
    if (!toolResult.ok) {
      return `查询失败：${toolResult.error || "未知错误"}`;
    }
    // 工具 handler 已生成 summary，直接用（真实 LLM 会基于 data 重新组织语言）
    return toolResult.summary || "查询完成。";
  }

  /* ===========================================================================
   * 真实 LLM 调用（PySide6 阶段启用，浏览器因 CORS 不可用）
   * ---------------------------------------------------------------------------
   * 取消下面注释，并把 send/summarize 改为调用 realSend/realSummarize 即可。
   * 需在模型配置页启用至少一个提供商。
   *
   * async function realSend(userText, messages) {
   *   const cfg = HMI.store.activeModelConfig();
   *   if (!cfg) throw new Error("未配置启用的模型，请到模型配置页添加");
   *   const newMessages = [...messages, { role: "user", content: userText }];
   *   const resp = await fetch(`${cfg.baseUrl}/chat/completions`, {
   *     method: "POST",
   *     headers: {
   *       "Content-Type": "application/json",
   *       "Authorization": `Bearer ${cfg.apiKey}`,
   *     },
   *     body: JSON.stringify({
   *       model: cfg.model,
   *       messages: newMessages,
   *       tools: HMI.aiTools.TOOLS,
   *       tool_choice: "auto",
   *     }),
   *   });
   *   const data = await resp.json();
   *   const msg = data.choices[0].message;
   *   if (msg.tool_calls && msg.tool_calls.length) {
   *     const tc = msg.tool_calls[0];
   *     return {
   *       type: "tool_call",
   *       name: tc.function.name,
   *       args: JSON.parse(tc.function.arguments),
   *       display: `${tc.function.name}(${tc.function.arguments})`,
   *       toolCallId: tc.id,
   *       rawAssistantMsg: msg,
   *     };
   *   }
   *   return { type: "text", content: msg.content };
   * }
   * ===========================================================================
   */

  HMI.llmClient = { send, summarize, delay };
})(window);
