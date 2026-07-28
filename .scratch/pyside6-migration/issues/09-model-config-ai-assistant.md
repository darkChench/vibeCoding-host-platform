# 09 — 模型配置页 + AI 助手页

**What to build:** 模型配置页：LLM 提供商 CRUD（provider/base_url/api_key/model/enabled），选预设（OpenAI/通义/DeepSeek/智谱/Kimi）自动填 base_url+model，测试连接，持久化 JSON。AI 助手页：对话 UI（消息历史 + 输入框 + 发送），接入真实 LLM（OpenAI 兼容 /chat/completions + tools 参数 function calling），4 个工具（read_sensor/get_alarms/get_trend/get_device_status）调协议层。思考动画、工具调用卡片、对话历史保留。

**Blocked by:** 03 — 协议层（AI 工具 read_sensor/get_trend 调协议层）, 04 — 参数配置页（工具读 store.params 找点位）

**Status:** done

- [x] 模型配置：提供商表 CRUD + 选预设自动填 + 校验（base_url http 开头/key 必填）+ 测试连接
- [x] 模型配置持久化 JSON，重启不丢
- [x] AI 助手页：对话历史区 + 输入框 + 发送按钮 + Ctrl+Enter 快捷
- [x] 真实 LLM 调用：OpenAI 兼容 /chat/completions + tools 参数（4 工具 JSON Schema）
- [x] function calling：LLM 返回 tool_call → 执行 aiTools handler → 结果回灌 → LLM 总结
- [x] 工具 read_sensor/get_trend 调协议层 read_param
- [x] 思考动画 + 工具调用卡片（函数名+参数+结果摘要）
- [x] 对话历史切页保留
- [x] 未配置模型时提示去模型配置页
