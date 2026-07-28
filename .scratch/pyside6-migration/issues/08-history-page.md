# 08 — 历史数据页（查询 + 导出）

**What to build:** 历史数据页：查询条件（开始时间/结束时间/点位多选/导出格式）+ 趋势曲线 + CSV 导出。点位多选下拉选项来自 store.params 的采样参数。查询后曲线按选中点位生成（QtCharts）。导出用 pandas 写 CSV 到 ./save 目录。查询/导出有 loading 态，未选点位时拦截。

**Blocked by:** 05 — 实时监控页（复用 QtCharts 曲线渲染逻辑 + 采样参数读取）

**Status:** done

- [x] 查询条件表单：开始时间/结束时间/点位多选/导出格式（CSV/Excel）
- [x] 点位多选下拉，选项来自 store.params 的采样参数
- [x] 查询按钮：校验时间范围（开始<结束）+ 选中点位非空 → loading → 曲线渲染
- [x] 趋势曲线（QtCharts）按选中点位生成，颜色按调色板分配
- [x] 导出按钮：pandas 写 CSV 到 ./save，loading 后成功提示
- [x] 未选点位时查询/导出拦截
- [x] 空查询结果显示空态
