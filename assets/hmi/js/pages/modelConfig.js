/*
 * modelConfig.js —— 模型配置页
 * 布局见 docs/hmi/page-layout-spec.md（新增章节），仿 settings.js。
 *
 * 管理 AI 助手使用的 LLM 提供商：provider/baseUrl/apiKey/model/enabled。
 * 数据持久化到 store.modelConfig（localStorage）。
 * 选预设提供商自动填 baseUrl + 推荐 model，用户只需填 key。
 */
(function (global) {
  "use strict";
  const HMI = (global.HMI = global.HMI || {});
  const util = HMI.util;
  const store = HMI.store;

  const PROVIDERS = HMI.mock.providerPresets.map((p) => p.provider);

  function emptyForm() {
    return { id: null, provider: "OpenAI", baseUrl: "", apiKey: "", model: "", enabled: true };
  }

  HMI.pages.modelConfig = {
    form: emptyForm(),
    editMode: "create", // 'create' | 'edit'

    render() {
      const list = store.modelConfig;
      const enabledCount = list.filter((c) => c.enabled).length;
      document.getElementById("content").innerHTML = `
        <div class="grid cols-2">
          <div class="card">
            <div class="card-head">
              <span>模型提供商</span>
              <span class="tag ${enabledCount ? "ok" : "warn"}">${enabledCount ? `${enabledCount} 个启用` : "未配置"}</span>
            </div>
            <div class="card-body">
              <div style="display:flex; gap:8px; margin-bottom:10px;">
                <button class="btn" type="button" data-mc-toolbar="create">新增提供商</button>
                <button class="btn danger" type="button" data-mc-toolbar="delete" disabled>删除勾选</button>
              </div>
              ${list.length === 0
                ? `<div class="empty-state"><span class="empty-state-icon">🤖</span>尚未配置任何模型提供商，点击"新增提供商"开始</div>`
                : `<table class="table param-table">
                    <thead>
                      <tr>
                        <th class="select-cell"><input type="checkbox" data-mc-check-all aria-label="全选"></th>
                        <th>提供商</th><th>base_url</th><th>模型</th><th>API Key</th><th>启用</th>
                      </tr>
                    </thead>
                    <tbody id="mcTbody"></tbody>
                  </table>`
              }
            </div>
          </div>
          <div class="card">
            <div class="card-head"><span id="mcFormTitle">新增提供商</span><span class="tag">表单</span></div>
            <div class="card-body" id="mcFormBody"></div>
          </div>
        </div>
      `;
      this._renderTable();
      this._renderForm();
    },

    bind() {
      document.querySelectorAll("[data-mc-toolbar]").forEach((btn) => {
        btn.addEventListener("click", () => this._handleToolbar(btn.dataset.mcToolbar));
      });
      document.querySelector("[data-mc-check-all]")?.addEventListener("change", (e) => {
        document.querySelectorAll("[data-mc-check]").forEach((cb) => (cb.checked = e.target.checked));
        this._updateToolbarState();
      });
    },

    _renderTable() {
      const tbody = document.getElementById("mcTbody");
      if (!tbody) return;
      tbody.innerHTML = store.modelConfig.map((c) => `
        <tr>
          <td class="select-cell"><input type="checkbox" data-mc-check aria-label="勾选 ${util.escapeHtml(c.provider)}"></td>
          <td>${util.escapeHtml(c.provider)}</td>
          <td style="font-family: Consolas, monospace; font-size: 12px;">${util.escapeHtml(c.baseUrl)}</td>
          <td>${util.escapeHtml(c.model)}</td>
          <td>${c.apiKey ? "••••" + util.escapeHtml(c.apiKey.slice(-4)) : "<span style='color:var(--muted)'>未设置</span>"}</td>
          <td>${c.enabled ? '<span class="stat-ok">✓</span>' : '<span style="color:var(--muted)">—</span>'}</td>
        </tr>
      `).join("");
      // 单行 checkbox
      tbody.querySelectorAll("[data-mc-check]").forEach((cb) => {
        cb.addEventListener("change", () => this._updateToolbarState());
      });
      this._updateToolbarState();
    },

    _renderForm() {
      const f = this.form;
      const presets = HMI.mock.providerPresets;
      document.getElementById("mcFormTitle").textContent =
        this.editMode === "edit" ? `编辑：${f.provider}` : "新增提供商";
      document.getElementById("mcFormBody").innerHTML = `
        <div class="form-grid">
          <div class="field">
            <label>提供商</label>
            <select class="select" data-mc-field="provider" id="mcProvider">
              ${PROVIDERS.map((p) => `<option ${p === f.provider ? "selected" : ""}>${p}</option>`).join("")}
              <option value="_custom" ${f.provider && !PROVIDERS.includes(f.provider) ? "selected" : ""}>自定义...</option>
            </select>
          </div>
          <div class="field"><label>base_url</label><input class="input" data-mc-field="baseUrl" value="${util.escapeHtml(f.baseUrl)}" placeholder="https://..."></div>
          <div class="field"><label>API Key</label><input class="input" type="password" data-mc-field="apiKey" value="${util.escapeHtml(f.apiKey)}" placeholder="sk-..."></div>
          <div class="field"><label>模型名</label><input class="input" data-mc-field="model" value="${util.escapeHtml(f.model)}" placeholder="gpt-4o-mini"></div>
          <label class="check-label" style="grid-column: 1 / -1;">
            <input type="checkbox" data-mc-field="enabled" ${f.enabled ? "checked" : ""}>
            <span>启用（AI 助手默认使用第一个启用的提供商）</span>
          </label>
        </div>
        <div style="display:flex; gap:8px; margin-top:12px;">
          <button class="btn" type="button" data-mc-form="save">保存</button>
          <button class="btn secondary" type="button" data-mc-form="test">测试连接</button>
          <button class="btn secondary" type="button" data-mc-form="cancel">取消</button>
        </div>
        <div style="margin-top:10px; padding:8px 10px; background:var(--tag-warn-bg); color:var(--warn); border-radius:6px; font-size:12px; font-weight:700;">
          ⚠ 原型阶段不真联网调用 LLM（浏览器 CORS 限制）。API Key 仅本地存储，PySide6 阶段启用真实调用。
        </div>
      `;
      // 提供商切换 → 自动填 baseUrl + 推荐 model
      document.getElementById("mcProvider")?.addEventListener("change", (e) => this._onProviderChange(e.target.value));
      // 表单按钮
      document.querySelectorAll("[data-mc-form]").forEach((btn) => {
        btn.addEventListener("click", () => this._handleFormAction(btn.dataset.mcForm));
      });
    },

    /** 选预设提供商时自动填 baseUrl + model（自定义则不填） */
    _onProviderChange(value) {
      if (value === "_custom") return;
      const preset = HMI.mock.providerPresets.find((p) => p.provider === value);
      if (!preset) return;
      document.querySelector('[data-mc-field="baseUrl"]').value = preset.baseUrl;
      document.querySelector('[data-mc-field="model"]').value = preset.model;
    },

    _collectForm() {
      const data = emptyForm();
      document.querySelectorAll("[data-mc-field]").forEach((el) => {
        const k = el.dataset.mcField;
        if (el.type === "checkbox") data[k] = el.checked;
        else data[k] = el.value;
      });
      // 自定义提供商名
      if (data.provider === "_custom") {
        data.provider = document.querySelector('[data-mc-field="provider"]')?.value || "自定义";
      }
      data.id = this.form.id;
      return data;
    },

    _validate(data) {
      const errors = {};
      if (!data.provider || data.provider === "_custom") errors.provider = "请选择或填写提供商";
      if (!data.baseUrl) errors.baseUrl = "base_url 不能为空";
      if (!/^https?:\/\//.test(data.baseUrl)) errors.baseUrl = "base_url 须以 http:// 或 https:// 开头";
      if (!data.model) errors.model = "模型名不能为空";
      if (!data.apiKey) errors.apiKey = "API Key 不能为空（测试连接和真实调用需要）";
      return { ok: Object.keys(errors).length === 0, errors };
    },

    _handleFormAction(action) {
      if (action === "cancel") {
        this.form = emptyForm();
        this.editMode = "create";
        this._renderForm();
        HMI.toast.show("已取消");
        return;
      }
      const data = this._collectForm();
      if (action === "test") {
        const { ok, errors } = this._validate(data);
        if (!ok) { this._showErrors(errors); HMI.toast.show("配置不完整，无法测试"); return; }
        HMI.toast.show("连接测试成功（模拟，原型不真联网）");
        return;
      }
      if (action === "save") {
        const { ok, errors } = this._validate(data);
        if (!ok) { this._showErrors(errors); HMI.toast.show("保存失败，请补全字段"); return; }
        if (this.editMode === "edit") {
          const idx = store.modelConfig.findIndex((c) => c.id === data.id);
          if (idx >= 0) store.modelConfig[idx] = data;
        } else {
          data.id = `mc-${Date.now()}`;
          store.modelConfig.push(data);
        }
        store.persistModelConfig();
        this.form = emptyForm();
        this.editMode = "create";
        this.render();
        HMI.app.updateAiStatus();
        HMI.toast.show(this.editMode === "edit" ? "已更新" : "已新增提供商");
      }
    },

    _handleToolbar(action) {
      if (action === "create") {
        this.form = emptyForm();
        this.editMode = "create";
        this._renderForm();
        return;
      }
      if (action === "delete") {
        const checked = Array.from(document.querySelectorAll("[data-mc-check]:checked"))
          .map((cb) => Number(cb.closest("tr").rowIndex) - 1);
        if (!checked.length) { HMI.toast.show("请先勾选要删除的提供商"); return; }
        const names = checked.map((i) => store.modelConfig[i]?.provider).filter(Boolean);
        HMI.modal.showAction("删除提供商", `确认删除 ${checked.length} 个：${names.join("、")}？`, () => {
          store.modelConfig = store.modelConfig.filter((_, i) => !checked.includes(i));
          store.persistModelConfig();
          this.render();
          HMI.app.updateAiStatus();
          HMI.toast.show(`已删除 ${checked.length} 个`);
        });
      }
    },

    _showErrors(errors) {
      document.querySelectorAll(".field-error").forEach((e) => e.remove());
      document.querySelectorAll(".field.has-error").forEach((f) => f.classList.remove("has-error"));
      Object.entries(errors).forEach(([field, msg]) => {
        const el = document.querySelector(`[data-mc-field="${field}"]`);
        if (el) {
          const fieldEl = el.closest(".field");
          fieldEl?.classList.add("has-error");
          fieldEl?.insertAdjacentHTML("beforeend", `<div class="field-error">${util.escapeHtml(msg)}</div>`);
        }
      });
    },

    _updateToolbarState() {
      const checked = document.querySelectorAll("[data-mc-check]:checked");
      const delBtn = document.querySelector('[data-mc-toolbar="delete"]');
      if (delBtn) delBtn.disabled = checked.length === 0;
    },
  };
})(window);
