# 05 — 实时监控页（曲线 + 协议层）

**What to build:** 实时监控页：采样参数的 metric 卡（显示名 + 实时值 + 单位，按 decimals 格式化）+ 短周期趋势曲线（QtCharts，每 1s 走协议层 read_param 刷新）。趋势曲线按 store.params 的采样参数动态生成，chip 点击显隐对应曲线。通信失败时 metric 显示 `--`。未连接/无采样参数时显示空态。

**Blocked by:** 03 — 协议层（read_param 供数据）, 04 — 参数配置页（读 store.params 的采样参数）

**Status:** ready-for-agent

- [ ] metric 卡数量 = store.params 的采样参数数，动态跟随增删
- [ ] metric 值每 1s 走协议层 read_param 刷新，按 decimals 格式化
- [ ] 趋势曲线（QtCharts）按采样参数动态生成，颜色按调色板分配
- [ ] 曲线 chip 点击显隐对应曲线（颜色稳定，隐藏不影响其他曲线色）
- [ ] 通信失败时 metric 显示 `--`
- [ ] 未连接时显示空态"串口未连接"
- [ ] 无采样参数时显示空态"暂无采样参数"
- [ ] 离开页面时停止刷新定时器
