/*
 * util.js —— 通用工具函数
 *
 * 挂载到全局命名空间 window.HMI.util，供所有模块复用。
 * 来源：原型行 1317-1331 的 escapeHtml/normalizeText/escapeMarkdown 等。
 */
(function (global) {
  "use strict";

  const HMI = (global.HMI = global.HMI || {});

  const util = {
    /** 压缩空白并 trim */
    normalizeText(value) {
      return String(value == null ? "" : value).replace(/\s+/g, " ").trim();
    },

    /** HTML 转义，防注入 */
    escapeHtml(value) {
      return String(value == null ? "" : value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    },

    /** Markdown 表格单元格转义：先压缩空白，再把 | 转义 */
    escapeMarkdown(value) {
      return util.normalizeText(value).replace(/\|/g, "\\|");
    },

    /** 当前时间 HH:MM:SS */
    nowHMS() {
      const d = new Date();
      const p = (n) => String(n).padStart(2, "0");
      return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
    },

    /**
     * 把 HEX 字符串（如 "01 03 00 00"）解析为字节数组。
     * 非法字符返回 null。用于 serial 页发送解析。
     */
    parseHexFrame(text) {
      const cleaned = util.normalizeText(text).replace(/\s+/g, "");
      if (!cleaned) return null;
      if (!/^[0-9a-fA-F]+$/.test(cleaned) || cleaned.length % 2 !== 0) return null;
      const bytes = [];
      for (let i = 0; i < cleaned.length; i += 2) {
        bytes.push(parseInt(cleaned.slice(i, i + 2), 16));
      }
      return bytes;
    },

    /** 字节数组转 HEX 展示字符串（空格分隔，大写） */
    bytesToHex(bytes) {
      return Array.from(bytes)
        .map((b) => b.toString(16).toUpperCase().padStart(2, "0"))
        .join(" ");
    },

    /** ASCII 字符串转字节数组 */
    asciiToBytes(text) {
      return Array.from(text).map((c) => c.charCodeAt(0) & 0xff);
    },

    /** 行结束符名称 → 实际字符 */
    lineEndingBytes(name) {
      switch (name) {
        case "CR": return [0x0d];
        case "LF": return [0x0a];
        case "CRLF": return [0x0d, 0x0a];
        default: return []; // "无"
      }
    },

    /** 简单 HEX CRC16（Modbus），用于补全发送帧展示 */
    crc16(bytes) {
      let crc = 0xffff;
      for (let i = 0; i < bytes.length; i++) {
        crc ^= bytes[i];
        for (let j = 0; j < 8; j++) {
          crc = crc & 0x0001 ? (crc >> 1) ^ 0xa001 : crc >> 1;
        }
      }
      return crc & 0xffff;
    },
  };

  HMI.util = util;
})(window);
