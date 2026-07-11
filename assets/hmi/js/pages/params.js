/*
 * params.js —— 参数配置页
 * 布局见 docs/hmi/page-layout-spec.md §5，交互见 interaction-spec.md §3。
 *
 * 第二阶段补全（相对原型的"仅弹框"）：
 *   - 真实 CRUD：新增/编辑载入表单/删除移除行/保存更新
 *   - 字段校验：名称非空唯一、地址合法hex且不重复、范围 min<=max、小数位>=0
 *   - 未保存标记（store.paramsDirty 驱动 tag.warn）
 *   - 全选三态
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;
  const store = HMI.store;

  const TYPES = ["uint8", "uint16", "int16", "uint32", "int32", "float32", "bool"];
  const ACCESSES = ["只读", "只写", "读写"];
  const CATEGORIES = ["采样参数", "配置参数"];

  function emptyForm() {
    return { name: "", display: "", address: "", category: "采样参数", type: "uint16", access: "读写", unit: "", decimals: 0, min: "", max: "", desc: "" };
  }

  HMI.pages.params = {
    /** 当前表单数据 */
    form: emptyForm(),

    render() {
      document.getElementById("content").innerHTML = `
        <div class="grid">
          <div class="card">
            <div class="card-head">
              <span>Modbus RTU 参数定义</span>
              <span class="tag ${store.paramsDirty ? "warn" : ""}" id="paramDirtyTag">${store.paramsDirty ? "未保存" : "已同步"}</span>
            </div>
            <div class="card-body">
              <div style="display:flex; gap:8px; margin-bottom:10px; align-items:center;">
                <button class="btn" type="button" data-param-toolbar="create">新增参数</button>
                <button class="btn secondary" type="button" data-param-toolbar="edit" disabled>编辑勾选</button>
                <button class="btn danger" type="button" data-param-toolbar="delete" disabled>删除勾选</button>
                <button class="btn secondary" type="button" data-param-toolbar="import">导入模板</button>
                <button class="btn secondary" type="button" data-param-toolbar="export">导出模板</button>
                <span style="flex:1;"></span>
                <span class="tool-label">设备地址</span>
                <input class="input short" type="number" min="1" max="247" value="${store.slaveId}" data-slave-id aria-label="当前设备从站地址（Modbus 报文第一字节）" title="Modbus 从站地址（1-247），决定协议层组帧的第一字节">
                <span class="tool-label">分类筛选</span>
                ${HMI.dropdown.html("paramFilter", ["全部", "采样参数", "配置参数"], this._filterLabel(store.paramFilter), "按分类筛选参数", "down")}
              </div>
              <table class="table param-table">
                <thead>
                  <tr>
                    <th class="select-cell"><input type="checkbox" data-param-check-all aria-label="全选参数"></th>
                    <th>参数名</th><th>显示名</th><th>地址</th><th>分类</th><th>类型</th><th>权限</th><th>单位</th><th>小数</th><th>范围</th><th>说明</th>
                  </tr>
                </thead>
                <tbody id="paramTbody"></tbody>
              </table>
            </div>
          </div>
          <div class="card">
            <div class="card-head"><span id="paramFormTitle">新增参数</span><span class="tag">表单</span></div>
            <div class="card-body" id="paramFormBody"></div>
          </div>
        </div>
      `;
      this._renderTable();
      this._renderForm();
    },

    bind() {
      // 工具栏按钮
      document.querySelectorAll("[data-param-toolbar]").forEach((btn) => {
        btn.addEventListener("click", () => this._handleToolbar(btn.dataset.paramToolbar));
      });
      // 当前设备从站地址（协议层组帧第一字节）
      document.querySelector("[data-slave-id]")?.addEventListener("change", (e) => {
        const v = Number(e.target.value);
        if (v >= 1 && v <= 247) {
          store.slaveId = v;
          HMI.toast.show(`设备地址已设为 ${v}`);
        } else {
          e.target.value = store.slaveId;
          HMI.toast.show("设备地址须在 1-247 范围");
        }
      });
      // 分类筛选下拉：先绑定交互，再注册值变化回调
      HMI.dropdown.bind(document.getElementById("content"));
      HMI.dropdown.onChange("paramFilter", (label) => {
        store.paramFilter = label === "全部" ? "all" : label;
        this._renderTable();
        HMI.toast.show(`已筛选：${label}`);
      });
      // 全选
      document.querySelector("[data-param-check-all]")?.addEventListener("change", (e) => {
        document.querySelectorAll("[data-param-check]").forEach((cb) => (cb.checked = e.target.checked));
        this._updateToolbarState();
      });
      // 单行 checkbox
      document.addEventListener("change", this._onRowCheck = (e) => {
        if (e.target.matches("[data-param-check]")) this._updateToolbarState();
      });
    },

    /** 按当前筛选条件过滤后的参数列表 */
    _filteredParams() {
      if (store.paramFilter === "all") return store.params;
      return store.params.filter((p) => p.category === store.paramFilter);
    },

    /** 状态值 → 下拉显示文案（all→全部） */
    _filterLabel(value) {
      return value === "all" ? "全部" : value;
    },

    _renderTable() {
      const tbody = document.getElementById("paramTbody");
      const list = this._filteredParams();
      if (!list.length) {
        tbody.innerHTML = `<tr><td colspan="11" class="empty-state"><span class="empty-state-icon">∅</span>当前筛选下无参数</td></tr>`;
        this._updateToolbarState();
        return;
      }
      tbody.innerHTML = list.map((p) => `
        <tr>
          <td class="select-cell"><input type="checkbox" data-param-check aria-label="勾选 ${util.escapeHtml(p.name)}"></td>
          <td>${util.escapeHtml(p.name)}</td>
          <td>${util.escapeHtml(p.display)}</td>
          <td>${util.escapeHtml(p.address)}</td>
          <td>${util.escapeHtml(p.category)}</td>
          <td>${util.escapeHtml(p.type)}</td>
          <td>${util.escapeHtml(p.access)}</td>
          <td>${util.escapeHtml(p.unit)}</td>
          <td>${p.decimals}</td>
          <td>${p.min} ~ ${p.max}</td>
          <td>${util.escapeHtml(p.desc)}</td>
        </tr>
      `).join("");
      this._updateToolbarState();
    },

    _renderForm() {
      const f = this.form;
      const isEdit = store.paramEditMode === "edit";
      document.getElementById("paramFormTitle").textContent = isEdit ? `编辑参数：${f.name}` : "新增参数";
      document.getElementById("paramFormBody").innerHTML = `
        <div class="form-grid">
          <div class="field"><label>参数名</label><input class="input" data-field="name" value="${util.escapeHtml(f.name)}"></div>
          <div class="field"><label>显示名</label><input class="input" data-field="display" value="${util.escapeHtml(f.display)}"></div>
          <div class="field"><label>Modbus 地址</label><input class="input" data-field="address" value="${util.escapeHtml(f.address)}"></div>
          <div class="field"><label>参数分类</label><select class="select" data-field="category">${CATEGORIES.map((c) => `<option ${c === f.category ? "selected" : ""}>${c}</option>`).join("")}</select></div>
          <div class="field"><label>数据类型</label><select class="select" data-field="type">${TYPES.map((t) => `<option ${t === f.type ? "selected" : ""}>${t}</option>`).join("")}</select></div>
          <div class="field"><label>访问权限</label><select class="select" data-field="access">${ACCESSES.map((a) => `<option ${a === f.access ? "selected" : ""}>${a}</option>`).join("")}</select></div>
          <div class="field"><label>单位</label><input class="input" data-field="unit" value="${util.escapeHtml(f.unit)}"></div>
          <div class="field"><label>小数位数</label><input class="input" type="number" min="0" step="1" data-field="decimals" value="${f.decimals}"></div>
          <div class="field"><label>最小值</label><input class="input" type="number" data-field="min" value="${f.min}"></div>
          <div class="field"><label>最大值</label><input class="input" type="number" data-field="max" value="${f.max}"></div>
          <div class="field" style="grid-column: 1 / -1;"><label>说明（可选）</label><input class="input" data-field="desc" value="${util.escapeHtml(f.desc)}"></div>
        </div>
        <div style="display:flex; gap:8px; margin-top:12px;">
          <button class="btn" type="button" data-form-action="save">保存定义</button>
          <button class="btn secondary" type="button" data-form-action="validate">校验定义</button>
          <button class="btn secondary" type="button" data-form-action="cancel">取消修改</button>
        </div>
      `;
      // 表单按钮
      document.querySelectorAll("[data-form-action]").forEach((btn) => {
        btn.addEventListener("click", () => this._handleFormAction(btn.dataset.formAction));
      });
    },

    /** 从表单 DOM 收集数据 */
    _collectForm() {
      const data = emptyForm();
      document.querySelectorAll("[data-field]").forEach((el) => {
        const k = el.dataset.field;
        data[k] = el.value;
      });
      data.decimals = Number(data.decimals);
      data.min = data.min === "" ? "" : Number(data.min);
      data.max = data.max === "" ? "" : Number(data.max);
      return data;
    },

    /** 校验，返回 {ok, errors:{field:msg}} */
    _validate(data, {excludeName} = {}) {
      const errors = {};
      if (!data.name) errors.name = "参数名不能为空";
      else if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(data.name)) errors.name = "仅允许字母数字下划线，且不以数字开头";
      else {
        const dup = store.params.find((p) => p.name === data.name && p.name !== excludeName);
        if (dup) errors.name = `参数名 "${data.name}" 已存在`;
      }
      if (!/^0x[0-9a-fA-F]{4}$/.test(data.address)) errors.address = "地址格式应为 0x0000~0xFFFF";
      else {
        const dupAddr = store.params.find((p) => p.address.toLowerCase() === data.address.toLowerCase() && p.name !== excludeName);
        if (dupAddr) errors.address = `地址 ${data.address} 已被 "${dupAddr.name}" 占用`;
      }
      if (!TYPES.includes(data.type)) errors.type = "数据类型非法";
      if (!ACCESSES.includes(data.access)) errors.access = "访问权限非法";
      if (!CATEGORIES.includes(data.category)) errors.category = "分类非法";
      if (!(data.decimals >= 0) || !Number.isInteger(data.decimals)) errors.decimals = "小数位须为非负整数";
      if (data.min !== "" && data.max !== "" && Number(data.min) > Number(data.max)) errors.max = "最大值不能小于最小值";
      return { ok: Object.keys(errors).length === 0, errors };
    },

    _showErrors(errors) {
      document.querySelectorAll(".field-error").forEach((e) => e.remove());
      document.querySelectorAll(".field.has-error").forEach((f) => f.classList.remove("has-error"));
      Object.entries(errors).forEach(([field, msg]) => {
        const el = document.querySelector(`[data-field="${field}"]`);
        if (el) {
          const fieldEl = el.closest(".field");
          fieldEl?.classList.add("has-error");
          fieldEl?.insertAdjacentHTML("beforeend", `<div class="field-error">${util.escapeHtml(msg)}</div>`);
        }
      });
    },

    _handleFormAction(action) {
      const data = this._collectForm();
      if (action === "cancel") {
        this.form = emptyForm();
        store.paramEditMode = "create";
        store.paramEditingName = null;
        this._renderForm();
        HMI.toast.show("已取消修改");
        return;
      }
      const isEdit = store.paramEditMode === "edit";
      const { ok, errors } = this._validate(data, { excludeName: isEdit ? store.paramEditingName : null });
      if (action === "validate") {
        if (ok) HMI.toast.show("校验通过");
        else { this._showErrors(errors); HMI.toast.show(`校验失败：${Object.keys(errors).length} 处错误`); }
        return;
      }
      if (action === "save") {
        if (!ok) { this._showErrors(errors); HMI.toast.show("保存失败，请修正错误"); return; }
        if (isEdit) {
          const idx = store.params.findIndex((p) => p.name === store.paramEditingName);
          if (idx >= 0) store.params[idx] = data;
        } else {
          store.params.push(data);
        }
        store.paramsDirty = true;
        this.form = emptyForm();
        store.paramEditMode = "create";
        store.paramEditingName = null;
        this._renderTable();
        this._renderForm();
        this._updateDirtyTag();
        HMI.toast.show(isEdit ? "已更新参数" : "已新增参数");
      }
    },

    _handleToolbar(action) {
      if (action === "create") {
        this.form = emptyForm();
        store.paramEditMode = "create";
        store.paramEditingName = null;
        this._renderForm();
        HMI.toast.show("已进入新增参数模式");
        return;
      }
      const checked = this._checkedRows();
      const names = checked.map((r) => util.normalizeText(r.children[1].textContent));
      if (action === "edit") {
        if (checked.length !== 1) { HMI.toast.show("编辑参数时只能勾选 1 条"); return; }
        const target = store.findParam(names[0]);
        if (!target) return;
        this.form = { ...target, min: target.min, max: target.max };
        store.paramEditMode = "edit";
        store.paramEditingName = target.name;
        this._renderForm();
        HMI.toast.show(`已载入参数 ${names[0]} 到表单`);
        return;
      }
      if (action === "delete") {
        if (!checked.length) { HMI.toast.show("请先勾选要删除的参数"); return; }
        HMI.modal.showAction("删除勾选", `准备删除 ${checked.length} 条参数：${names.join("、")}。确认后将从模型移除。`, () => {
          store.params = store.params.filter((p) => !names.includes(p.name));
          store.paramsDirty = true;
          this._renderTable();
          this._updateDirtyTag();
          HMI.toast.show(`已删除 ${names.length} 条参数`);
        });
        return;
      }
      if (action === "import") {
        HMI.modal.showAction("导入模板", "将从本地配置文件导入参数模型定义（原型占位，待接入文件选择对话框）。");
        return;
      }
      if (action === "export") {
        HMI.modal.showAction("导出模板", `将导出当前 ${store.params.length} 条参数定义为配置文件（原型占位，待接入文件保存对话框）。`);
      }
    },

    _checkedRows() {
      return Array.from(document.querySelectorAll("[data-param-check]:checked")).map((cb) => cb.closest("tr"));
    },

    _updateToolbarState() {
      const checked = this._checkedRows();
      const editBtn = document.querySelector('[data-param-toolbar="edit"]');
      const delBtn = document.querySelector('[data-param-toolbar="delete"]');
      const checkAll = document.querySelector("[data-param-check-all]");
      const checks = Array.from(document.querySelectorAll("[data-param-check]"));
      if (editBtn) editBtn.disabled = checked.length !== 1;
      if (delBtn) delBtn.disabled = checked.length === 0;
      if (checkAll && checks.length) {
        checkAll.checked = checked.length === checks.length;
        checkAll.indeterminate = checked.length > 0 && checked.length < checks.length;
      }
    },

    _updateDirtyTag() {
      const tag = document.getElementById("paramDirtyTag");
      if (!tag) return;
      tag.textContent = store.paramsDirty ? "未保存" : "已同步";
      tag.classList.toggle("warn", store.paramsDirty);
    },
  };
})(window);
