/*
 * modbusProtocol.js —— Modbus RTU 协议层
 *
 * 职责：把参数表（address/type/access）翻译成真实的 Modbus RTU 报文，
 *       模拟设备回包，解析响应，返回工程值。每次收发自动注入串口日志。
 *
 * 这是"内部逻辑"——报文格式（从站地址+功能码+数据+CRC16）是 Modbus 规范固定的，
 * 不让用户在 UI 上拼报文。用户只在参数配置页填地址/类型/权限，协议层自动组帧。
 *
 * 原型阶段用模拟回包（在 min/max 范围随机）；PySide6 阶段把 simulateResponse
 * 换成 pymodbus 的 client.read_holding_registers / write_register，接口不变。
 *
 * 报文格式参考 docs/hmi 相关规范 + Modbus RTU 标准。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;

  /** Modbus 功能码 */
  const FC_READ_HOLDING = 0x03;
  const FC_WRITE_SINGLE = 0x06;

  /** type → 寄存器数量映射 */
  function typeToRegCount(type) {
    switch (type) {
      case "uint8":
      case "int8":
      case "uint16":
      case "int16":
      case "bool":
        return 1;
      case "uint32":
      case "int32":
      case "float32":
        return 2;
      default:
        return 1;
    }
  }

  /** 给字节数组追加 CRC16（低字节在前，Modbus 规范） */
  function appendCrc(bytes) {
    const crc = util.crc16(bytes);
    bytes.push(crc & 0xff, (crc >> 8) & 0xff);
    return bytes;
  }

  /**
   * 生成读保持寄存器请求帧（功能码 03）。
   * 帧: [slaveId, 0x03, addrHi, addrLo, qtyHi, qtyLo, crcLo, crcHi]
   */
  function buildReadFrame(slaveId, address, regCount) {
    const addr = parseInt(address, 16);
    const frame = [
      slaveId & 0xff,
      FC_READ_HOLDING,
      (addr >> 8) & 0xff, addr & 0xff,
      (regCount >> 8) & 0xff, regCount & 0xff,
    ];
    return appendCrc(frame);
  }

  /**
   * 生成写单寄存器请求帧（功能码 06）。
   * 帧: [slaveId, 0x06, addrHi, addrLo, valHi, valLo, crcLo, crcHi]
   */
  function buildWriteFrame(slaveId, address, value) {
    const addr = parseInt(address, 16);
    const frame = [
      slaveId & 0xff,
      FC_WRITE_SINGLE,
      (addr >> 8) & 0xff, addr & 0xff,
      (value >> 8) & 0xff, value & 0xff,
    ];
    return appendCrc(frame);
  }

  /**
   * float32 ↔ 4 字节（IEEE754，Big-Endian word order，高字在前）。
   * Modbus 常见的 float32 是 2 个寄存器，高字在前（ABCD 字节序）。
   */
  function float32ToBytes(value) {
    const buf = new ArrayBuffer(4);
    new DataView(buf).setFloat32(0, value, false); // false = Big-Endian
    return Array.from(new Uint8Array(buf));
  }

  function bytesToFloat32(bytes) {
    const buf = new ArrayBuffer(4);
    const view = new DataView(buf);
    bytes.forEach((b, i) => view.setUint8(i, b));
    return view.getFloat32(0, false);
  }

  /**
   * 模拟设备响应读请求（功能码 03）。
   * 在参数 min/max 范围内生成随机工程值，按 type 编码进响应帧。
   * 帧: [slaveId, 0x03, byteCount, data..., crcLo, crcHi]
   */
  function simulateReadResponse(frame, param) {
    const slaveId = frame[0];
    const regCount = typeToRegCount(param.type);
    const byteCount = regCount * 2;

    // 在 min/max 范围内生成随机工程值
    const min = Number(param.min);
    const max = Number(param.max);
    const safeMin = Number.isFinite(min) ? min : 0;
    const safeMax = Number.isFinite(max) ? max : 100;
    const engValue = safeMin + Math.random() * (safeMax - safeMin);

    // 按 type 编码数据字节
    const decimals = Number(param.decimals) || 0;
    const scale = Math.pow(10, decimals);
    let dataBytes = [];
    let rawValue;
    if (param.type === "float32") {
      // float32: IEEE754 编码，工程值直接作为浮点存储（不再 decimals 缩放）
      dataBytes = float32ToBytes(engValue);
      rawValue = engValue;
    } else if (regCount === 1) {
      // 16 位整数类型：工程值 × scale 取整
      rawValue = Math.round(engValue * scale);
      dataBytes.push((rawValue >> 8) & 0xff, rawValue & 0xff);
    } else {
      // 32 位整数类型：高字在前
      rawValue = Math.round(engValue * scale);
      dataBytes.push(
        (rawValue >> 24) & 0xff, (rawValue >> 16) & 0xff,
        (rawValue >> 8) & 0xff, rawValue & 0xff
      );
    }

    const resp = appendCrc([slaveId, FC_READ_HOLDING, byteCount, ...dataBytes]);
    return { resp, rawValue, engValue };
  }

  /**
   * 模拟设备响应写请求（功能码 06）。
   * Modbus 规范：写单寄存器响应 = 请求帧原样返回（echo）。
   */
  function simulateWriteResponse(frame) {
    return frame.slice(); // echo
  }

  /**
   * 解析读响应，提取原始值并按 decimals 缩放为工程值。
   * @returns {rawValue:number, engValue:number}
   */
  function parseReadResponse(respBytes, param) {
    const regCount = typeToRegCount(param.type);
    const dataBytes = respBytes.slice(3, 3 + regCount * 2);
    let rawValue;
    let engValue;
    if (param.type === "float32") {
      // float32: IEEE754 解码，工程值即浮点本身（不再 decimals 缩放）
      rawValue = bytesToFloat32(dataBytes);
      const decimals = Number(param.decimals) || 0;
      engValue = Number(rawValue.toFixed(decimals));
    } else if (regCount === 1) {
      rawValue = (dataBytes[0] << 8) | dataBytes[1];
      const decimals = Number(param.decimals) || 0;
      engValue = Number((rawValue / Math.pow(10, decimals)).toFixed(decimals));
    } else {
      rawValue = (dataBytes[0] << 24) | (dataBytes[1] << 16) | (dataBytes[2] << 8) | dataBytes[3];
      const decimals = Number(param.decimals) || 0;
      engValue = Number((rawValue / Math.pow(10, decimals)).toFixed(decimals));
    }
    return { rawValue, engValue };
  }

  /** 往串口控制台注入一条日志 */
  function logToConsole(direction, label, content) {
    if (!HMI.console || !HMI.console.lines) return;
    const item = [direction, label, util.nowHMS(), content];
    HMI.console.lines.raw.push(item);
    // _appendLine 只在当前是 raw tab 时实时显示，但 push 到数组保证切回时可见
    if (typeof HMI.console._appendLine === "function") {
      HMI.console._appendLine(item);
    }
  }

  /** 模拟串口往返延迟 */
  function delay(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  /**
   * 协议层配置（模拟异常概率，PySide6 阶段这些由真实设备决定）。
   * 概率值用于原型演示异常流程；生产环境这些异常来自真实通信。
   */
  const CONFIG = {
    timeoutMs: 100,          // 超时阈值（PRD §6.3：100ms）
    maxRetries: 1,           // 重试次数（PRD §6.3：1 次）
    noResponseRate: 0.08,    // 模拟"从站无响应"概率（8%）
    crcErrorRate: 0.03,      // 模拟"CRC 校验失败"概率（3%）
  };

  /** 报警自增 id */
  let alarmSeq = 1000;

  /**
   * 往报警表注入一条记录（CRC 错误/无响应等通信异常）。
   * 复用 store.alarms 结构：{id, time, content, terminal, level, acknowledged}
   */
  function pushAlarm(content, level) {
    if (!HMI.store || !Array.isArray(HMI.store.alarms)) return;
    HMI.store.alarms.push({
      id: alarmSeq++,
      time: util.nowHMS(),
      content,
      terminal: HMI.store.currentPort || "COM",
      level: level || "一般",
      acknowledged: false,
    });
  }

  /**
   * 校验回包 CRC：末两字节（LE）应等于前面字节的 crc16。
   * @returns {boolean} true=CRC 正确
   */
  function verifyCrc(bytes) {
    if (bytes.length < 3) return false;
    const payload = bytes.slice(0, bytes.length - 2);
    const crc = util.crc16(payload);
    return (crc & 0xff) === bytes[bytes.length - 2] && ((crc >> 8) & 0xff) === bytes[bytes.length - 1];
  }

  /**
   * 模拟一次"带异常的收发"：可能正常回包、可能无响应（超时）、可能 CRC 错。
   * @param {number[]} frame 请求帧
   * @param {Object} param 参数对象（读时用，写时可传 null）
   * @param {boolean} isWrite 是否写操作
   * @returns {Promise<{type:"ok", resp:number[]} | {type:"timeout"} | {type:"crc_error"}>}
   */
  async function transactOnce(frame, param, isWrite) {
    logToConsole("tx", "TX", util.bytesToHex(frame));

    // 模拟无响应（从站不回）
    if (Math.random() < CONFIG.noResponseRate) {
      await delay(CONFIG.timeoutMs);
      return { type: "timeout" };
    }

    await delay(50 + Math.random() * 100);

    // 生成正常回包
    let resp;
    if (isWrite) {
      resp = simulateWriteResponse(frame);
    } else {
      resp = simulateReadResponse(frame, param).resp;
    }

    // 模拟 CRC 错误：篡改回包最后一字节
    if (Math.random() < CONFIG.crcErrorRate) {
      resp = resp.slice();
      resp[resp.length - 1] ^= 0xff; // 破坏 CRC
      logToConsole("rx", "RX", util.bytesToHex(resp));
      return { type: "crc_error", resp };
    }

    logToConsole("rx", "RX", util.bytesToHex(resp));
    return { type: "ok", resp };
  }

  const modbus = {
    /**
     * 读取单个参数。含断线检测、超时重试、CRC 校验、异常报警。
     * @returns {Promise<{ok:true,...} | {ok:false, error:string, retried:number}>}
     */
    async readParam(param) {
      // 断线检测
      if (HMI.store.connectionState !== "connected") {
        return { ok: false, error: "串口未连接", retried: 0 };
      }

      const slaveId = HMI.store.slaveId || 1;
      const regCount = typeToRegCount(param.type);
      let lastError = "";
      let retried = 0;

      for (let attempt = 0; attempt <= CONFIG.maxRetries; attempt++) {
        const frame = buildReadFrame(slaveId, param.address, regCount);
        const result = await transactOnce(frame, param, false);

        if (result.type === "ok") {
          // CRC 二次校验（回包自身完整性）
          if (!verifyCrc(result.resp)) {
            lastError = "CRC 校验失败";
            logToConsole("rx", "CRC", `回包校验失败：${util.bytesToHex(result.resp)}`);
            if (attempt < CONFIG.maxRetries) { retried++; continue; }
            pushAlarm(`读取 ${param.display || param.name} 时 CRC 校验失败`, "一般");
            return { ok: false, error: lastError, retried };
          }
          const parsed = parseReadResponse(result.resp, param);
          return { ok: true, value: parsed.engValue, raw: parsed.rawValue, frame, response: result.resp, retried };
        }

        if (result.type === "timeout") {
          lastError = "从站无响应（超时）";
          logToConsole("rx", "TIMEOUT", `等待 ${CONFIG.timeoutMs}ms 无响应`);
          if (attempt < CONFIG.maxRetries) { retried++; continue; }
          pushAlarm(`读取 ${param.display || param.name} 时从站无响应`, "预警");
          return { ok: false, error: lastError, retried };
        }

        if (result.type === "crc_error") {
          lastError = "回包 CRC 错误";
          if (attempt < CONFIG.maxRetries) { retried++; continue; }
          pushAlarm(`读取 ${param.display || param.name} 时回包 CRC 错误`, "一般");
          return { ok: false, error: lastError, retried };
        }
      }
      return { ok: false, error: lastError || "未知错误", retried };
    },

    /**
     * 写入单个参数（功能码 06）。含断线检测、超时重试、CRC 校验。
     */
    async writeParam(param, engValue) {
      if (HMI.store.connectionState !== "connected") {
        return { ok: false, error: "串口未连接", retried: 0 };
      }

      const slaveId = HMI.store.slaveId || 1;
      const decimals = Number(param.decimals) || 0;
      const scale = Math.pow(10, decimals);
      const rawValue = Math.round(Number(engValue) * scale);

      let lastError = "";
      let retried = 0;
      for (let attempt = 0; attempt <= CONFIG.maxRetries; attempt++) {
        const frame = buildWriteFrame(slaveId, param.address, rawValue);
        const result = await transactOnce(frame, null, true);

        if (result.type === "ok") {
          // 写响应=echo，校验是否与请求一致
          if (util.bytesToHex(result.resp) !== util.bytesToHex(frame)) {
            lastError = "写响应与请求不匹配";
            if (attempt < CONFIG.maxRetries) { retried++; continue; }
            return { ok: false, error: lastError, retried };
          }
          return { ok: true, frame, response: result.resp, retried };
        }
        if (result.type === "timeout") {
          lastError = "从站无响应（超时）";
          logToConsole("rx", "TIMEOUT", `等待 ${CONFIG.timeoutMs}ms 无响应`);
          if (attempt < CONFIG.maxRetries) { retried++; continue; }
          pushAlarm(`写入 ${param.display || param.name} 时从站无响应`, "预警");
          return { ok: false, error: lastError, retried };
        }
        if (result.type === "crc_error") {
          lastError = "回包 CRC 错误";
          if (attempt < CONFIG.maxRetries) { retried++; continue; }
          return { ok: false, error: lastError, retried };
        }
      }
      return { ok: false, error: lastError || "未知错误", retried };
    },

    /** 协议层配置（供测试/调试读取） */
    CONFIG,

    /** 暴露内部方法供测试/调试 */
    _internal: { typeToRegCount, appendCrc, buildReadFrame, buildWriteFrame, simulateReadResponse, parseReadResponse, verifyCrc, transactOnce },
  };

  HMI.modbus = modbus;
})(window);
