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
   * 模拟设备响应读请求（功能码 03）。
   * 在参数 min/max 范围内生成随机原始整数值，按 type 编码进响应帧。
   * 帧: [slaveId, 0x03, byteCount, data..., crcLo, crcHi]
   */
  function simulateReadResponse(frame, param) {
    const slaveId = frame[0];
    const regCount = typeToRegCount(param.type);
    const byteCount = regCount * 2;

    // 在 min/max 范围内生成随机原始值（整数，考虑 decimals 缩放）
    const decimals = Number(param.decimals) || 0;
    const scale = Math.pow(10, decimals);
    const min = Number(param.min);
    const max = Number(param.max);
    const safeMin = Number.isFinite(min) ? min : 0;
    const safeMax = Number.isFinite(max) ? max : 100;
    const engValue = safeMin + Math.random() * (safeMax - safeMin);
    const rawValue = Math.round(engValue * scale);

    // 按 type 编码数据字节（Big-Endian，高字在前）
    const dataBytes = [];
    if (regCount === 1) {
      dataBytes.push((rawValue >> 8) & 0xff, rawValue & 0xff);
    } else {
      // 32 位：高字在前（Big-Endian word order）
      dataBytes.push(
        (rawValue >> 24) & 0xff, (rawValue >> 16) & 0xff,
        (rawValue >> 8) & 0xff, rawValue & 0xff
      );
    }

    const resp = [slaveId, FC_READ_HOLDING, byteCount, ...dataBytes];
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
    if (regCount === 1) {
      rawValue = (dataBytes[0] << 8) | dataBytes[1];
    } else {
      rawValue = (dataBytes[0] << 24) | (dataBytes[1] << 16) | (dataBytes[2] << 8) | dataBytes[3];
    }
    const decimals = Number(param.decimals) || 0;
    const engValue = Number((rawValue / Math.pow(10, decimals)).toFixed(decimals));
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

  const modbus = {
    /**
     * 读取单个参数的值。生成请求帧 → 注入 TX → 模拟延迟 → 模拟回包 → 注入 RX → 解析。
     * @param {Object} param 参数对象（需有 address/type/decimals/min/max）
     * @returns {Promise<{ok:true, value:number, raw:number, frame:number[], response:number[]} | {ok:false, error:string}>}
     */
    async readParam(param) {
      const slaveId = HMI.store.slaveId || 1;
      const regCount = typeToRegCount(param.type);
      const frame = buildReadFrame(slaveId, param.address, regCount);

      // 注入 TX 日志
      logToConsole("tx", "TX", util.bytesToHex(frame));

      // 模拟串口往返延迟（50-150ms）
      await delay(50 + Math.random() * 100);

      // 模拟设备回包
      const { resp, rawValue, engValue } = simulateReadResponse(frame, param);
      logToConsole("rx", "RX", util.bytesToHex(resp));

      // 解析校验（回包应能解析出同样的值）
      const parsed = parseReadResponse(resp, param);

      return {
        ok: true,
        value: parsed.engValue,
        raw: parsed.rawValue,
        frame,
        response: resp,
      };
    },

    /**
     * 写入单个参数（功能码 06）。生成写帧 → 注入 TX → 模拟延迟 → echo 回包 → 注入 RX。
     * @param {Object} param 参数对象
     * @param {number} engValue 要写入的工程值
     * @returns {Promise<{ok:true, frame:number[], response:number[]} | {ok:false, error:string}>}
     */
    async writeParam(param, engValue) {
      const slaveId = HMI.store.slaveId || 1;
      const decimals = Number(param.decimals) || 0;
      const scale = Math.pow(10, decimals);
      const rawValue = Math.round(Number(engValue) * scale);

      const frame = buildWriteFrame(slaveId, param.address, rawValue);
      logToConsole("tx", "TX", util.bytesToHex(frame));

      await delay(50 + Math.random() * 100);

      const resp = simulateWriteResponse(frame);
      logToConsole("rx", "RX", util.bytesToHex(resp));

      return { ok: true, frame, response: resp };
    },

    /** 暴露内部方法供测试/调试 */
    _internal: { typeToRegCount, appendCrc, buildReadFrame, buildWriteFrame, simulateReadResponse, parseReadResponse },
  };

  HMI.modbus = modbus;
})(window);
