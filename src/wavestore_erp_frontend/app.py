from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse


def create_app() -> FastAPI:
    app = FastAPI(title="WaveStore ERP Frontend")
    sts = os.environ.get("WAVE_STS_URL", "http://127.0.0.1:8801")
    erp_api = os.environ.get("WAVESTORE_ERP_API_URL", "http://127.0.0.1:8802")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": "wavestore-erp-frontend"}

    @app.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>WaveStore ERP Admin</title>
  <style>
    :root {
      --bg:#f5f1ff;
      --panel:#ffffff;
      --soft:#f8f4ff;
      --line:#d9cfef;
      --text:#1b1230;
      --muted:#6a5f85;
      --accent:#593196;
      --accent-2:#e06c00;
      --nav:#2d0f5e;
      --danger:#a91f40;
    }
    * { box-sizing:border-box; }
    body { margin:0; font-family:"Segoe UI", Aptos, Calibri, sans-serif; background:var(--bg); color:var(--text); }
    .wrap { max-width:1320px; margin:0 auto; padding:20px; }
    .hero { background:linear-gradient(135deg, var(--nav) 0%, var(--accent) 55%, var(--accent-2) 100%); color:#fff; border-radius:16px; padding:18px 20px; margin-bottom:14px; }
    .brand { font-size:28px; font-weight:900; letter-spacing:-.04em; }
    .muted { color:var(--muted); }
    .panel { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:14px; box-shadow:0 6px 24px rgba(45,15,94,.08); }
    .layout { display:grid; grid-template-columns:250px 1fr; gap:12px; }
    .menu button { width:100%; border:1px solid var(--line); border-radius:10px; padding:10px; text-align:left; background:var(--soft); color:var(--text); font-weight:700; cursor:pointer; margin-bottom:8px; }
    .menu button.active { background:var(--accent); color:#fff; border-color:var(--accent); }
    .row { display:grid; gap:8px; grid-template-columns:repeat(12, minmax(0, 1fr)); }
    .col-3 { grid-column:span 3; }
    .col-4 { grid-column:span 4; }
    .col-6 { grid-column:span 6; }
    .col-8 { grid-column:span 8; }
    .col-9 { grid-column:span 9; }
    .col-12 { grid-column:span 12; }
    input, select { width:100%; border:1px solid var(--line); border-radius:10px; padding:10px; background:var(--soft); color:var(--text); }
    label { display:block; font-size:12px; color:var(--muted); margin:0 0 4px; }
    button { border:0; border-radius:10px; padding:10px 12px; background:var(--accent); color:#fff; font-weight:700; cursor:pointer; }
    button.secondary { background:#fff; color:var(--accent); border:1px solid var(--accent); }
    button.danger { background:var(--danger); }
    .toolbar { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin:8px 0 12px; }
    .table-wrap { overflow:auto; border:1px solid var(--line); border-radius:12px; }
    table { width:100%; border-collapse:collapse; min-width:780px; background:#fff; }
    th, td { padding:10px; border-bottom:1px solid var(--line); text-align:left; font-size:14px; vertical-align:top; }
    th { background:var(--soft); color:var(--muted); font-weight:700; }
    .pill { border-radius:999px; background:var(--soft); border:1px solid var(--line); padding:3px 8px; font-size:12px; display:inline-block; }
    .pager { display:flex; gap:8px; align-items:center; justify-content:flex-end; margin-top:10px; }
    .status { margin-top:8px; color:var(--muted); min-height:20px; }
    .modal-backdrop { position:fixed; inset:0; background:rgba(22, 14, 44, .45); display:none; align-items:center; justify-content:center; padding:20px; z-index:1000; }
    .modal-backdrop.open { display:flex; }
    .modal { width:min(860px, 100%); background:#fff; border:1px solid var(--line); border-radius:14px; padding:14px; }
    .modal h3 { margin:0 0 10px; }
    .modal-actions { margin-top:12px; display:flex; justify-content:flex-end; gap:8px; }
    .error { color:var(--danger); font-size:13px; min-height:18px; margin-top:8px; }
    @media (max-width:980px) {
      .layout { grid-template-columns:1fr; }
      .col-3, .col-4, .col-6, .col-8, .col-9 { grid-column:span 12; }
      table { min-width:640px; }
    }
  </style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <div class="brand">WaveStore ERP Admin</div>
    <div>Paged query lists with modal CRUD editors for Products, Promotions, Customers, Orders and Invoices.</div>
  </div>

  <div class="panel" style="margin-bottom:12px;">
    <div class="row">
      <div class="col-3"><label>Tenant</label><input id="tenant" value="demo-tenant"></div>
      <div class="col-3"><label>User</label><input id="user" value="erp.admin"></div>
      <div class="col-3"><label>Password</label><input id="password" type="password" value="demo123!"></div>
      <div class="col-3" style="display:flex;align-items:flex-end;"><button id="signInBtn" class="col-12">Sign in</button></div>
    </div>
    <div class="toolbar">
      <a href="https://orchestrator.retail.demos.wavefunctionlabs.com" target="_blank" rel="noopener"><button type="button" class="secondary">Demo Orchestrator</button></a>
      <span id="authState" class="muted">Signed out</span>
    </div>
  </div>

  <div class="layout">
    <div class="panel menu">
      <h3 style="margin-top:0;">Menu</h3>
      <button data-entity="products" class="active">Products</button>
      <button data-entity="promotions">Promotions</button>
      <button data-entity="customers">Customers</button>
      <button data-entity="orders">Orders</button>
      <button data-entity="invoices">Invoices</button>
      <button data-entity="branding">Branding</button>
    </div>

    <div class="panel">
      <h3 id="entityTitle" style="margin-top:0;">Products</h3>
      <div class="toolbar" id="tableToolbar">
        <button id="refreshBtn" class="secondary">Refresh</button>
        <button id="createBtn">New</button>
        <input id="customerFilter" placeholder="Customer ID filter (orders/invoices)" style="max-width:300px;">
      </div>
      <div class="table-wrap" id="tableWrap">
        <table>
          <thead><tr id="tableHead"></tr></thead>
          <tbody id="tableBody"></tbody>
        </table>
      </div>
      <div class="pager" id="pagerWrap">
        <button id="prevBtn" class="secondary">Prev</button>
        <span id="pageInfo" class="muted">Page 1 / 1</span>
        <button id="nextBtn" class="secondary">Next</button>
      </div>
      <div id="brandingPanel" style="display:none;">
        <p class="muted">Storefront whitelabel config -- controls the store name, logo, favicon, hero tagline, and accent color shown on WaveStore. Changes are picked up by the storefront within 30 seconds (short cache).</p>
        <div class="row">
          <div class="col-6"><label>Store name</label><input id="brandStoreName" placeholder="WaveStore"></div>
          <div class="col-6"><label>Primary color</label><input id="brandPrimaryColor" type="color" value="#0d6efd"></div>
          <div class="col-12"><label>Hero tagline</label><input id="brandTagline" placeholder="Discover deals..."></div>
          <div class="col-6"><label>Logo URL</label><input id="brandLogoUrl" placeholder="/static/images/wavestore-hero-mini.jpg"></div>
          <div class="col-6"><label>Favicon URL</label><input id="brandFaviconUrl" placeholder="/static/images/favicon.ico"></div>
        </div>
        <div class="toolbar" style="margin-top:10px;">
          <button id="saveBrandingBtn">Save branding</button>
          <button id="resetBrandingBtn" class="secondary">Reset to defaults</button>
        </div>
        <div id="brandingStatus" class="status"></div>
      </div>
      <div id="status" class="status"></div>
    </div>
  </div>
</div>

<div id="modalBackdrop" class="modal-backdrop">
  <div class="modal">
    <h3 id="modalTitle">Edit</h3>
    <div id="modalForm" class="row"></div>
    <div id="modalError" class="error"></div>
    <div class="modal-actions">
      <button id="cancelBtn" class="secondary">Cancel</button>
      <button id="saveBtn">Save</button>
    </div>
  </div>
</div>

<script>
const cfg = { sts: "__STS_URL__", erp: "__ERP_API_URL__" };
const state = { token: "", entity: "products", page: 0, pageSize: 10, rows: [], editing: null, mode: "create" };

const schemas = {
  products: {
    title: "Products",
    listPath: () => "/erp/products",
    idField: "id",
    columns: ["id", "title", "price", "currencyCode", "availableQuantity", "availability"],
    fields: [
      { name: "id", label: "Product ID", type: "text", required: true, col: 6 },
      { name: "title", label: "Title", type: "text", required: true, col: 6 },
      { name: "description", label: "Description", type: "text", required: false, col: 12 },
      { name: "price", label: "Price", type: "number", required: true, min: 0, col: 4 },
      { name: "currencyCode", label: "Currency", type: "text", required: true, col: 4, default: "GBP" },
      { name: "availableQuantity", label: "Stock", type: "number", required: true, min: 0, col: 4 },
      { name: "availability", label: "Availability", type: "select", required: true, col: 6, options: ["IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK"] },
      { name: "brand", label: "Brand", type: "text", required: false, col: 6 },
    ],
    buildPayload(values) {
      return {
        id: values.id.trim(),
        title: values.title.trim(),
        description: values.description.trim(),
        price: Number(values.price),
        currencyCode: (values.currencyCode || "GBP").trim().toUpperCase(),
        availableQuantity: Number(values.availableQuantity),
        availability: values.availability,
        brands: values.brand ? [values.brand.trim()] : [],
      };
    },
    upsertPath(values) { return "/erp/products"; },
    upsertMethod(values, mode) { return "POST"; },
    deletePath(record) { return "/erp/products/" + encodeURIComponent(record.id); },
  },
  promotions: {
    title: "Promotions",
    listPath: () => "/erp/promotions",
    idField: "id",
    columns: ["id", "title", "subtitle", "query", "cta"],
    fields: [
      { name: "id", label: "Promotion ID", type: "text", required: true, col: 6 },
      { name: "title", label: "Title", type: "text", required: true, col: 6 },
      { name: "subtitle", label: "Subtitle", type: "text", required: false, col: 12 },
      { name: "query", label: "Search query", type: "text", required: false, col: 6 },
      { name: "cta", label: "CTA text", type: "text", required: false, col: 6 },
    ],
    buildPayload(values) { return { id: values.id.trim(), title: values.title.trim(), subtitle: values.subtitle.trim(), query: values.query.trim(), cta: values.cta.trim() }; },
    upsertPath(values) { return "/erp/promotions"; },
    upsertMethod(values, mode) { return "POST"; },
    deletePath(record) { return "/erp/promotions/" + encodeURIComponent(record.id); },
  },
  customers: {
    title: "Customers",
    listPath: () => "/erp/customers",
    idField: "id",
    columns: ["id", "name", "email", "loyaltyTier"],
    fields: [
      { name: "id", label: "Customer ID", type: "text", required: true, col: 6 },
      { name: "name", label: "Name", type: "text", required: true, col: 6 },
      { name: "email", label: "Email", type: "email", required: true, col: 6 },
      { name: "loyaltyTier", label: "Loyalty tier", type: "text", required: false, col: 6 },
    ],
    buildPayload(values) { return { id: values.id.trim(), name: values.name.trim(), email: values.email.trim(), loyaltyTier: values.loyaltyTier.trim() }; },
    upsertPath(values) { return "/erp/customers"; },
    upsertMethod(values, mode) { return "POST"; },
    deletePath(record) { return "/erp/customers/" + encodeURIComponent(record.id); },
  },
  orders: {
    title: "Orders",
    listPath: () => {
      const customerId = (document.getElementById("customerFilter").value || "").trim();
      return customerId ? "/erp/orders?customerId=" + encodeURIComponent(customerId) : "/erp/orders";
    },
    idField: "id",
    columns: ["id", "customerId", "status", "total", "currencyCode", "createdAt"],
    fields: [
      { name: "id", label: "Order ID (required for update)", type: "text", required: false, col: 6 },
      { name: "customerId", label: "Customer ID", type: "text", required: true, col: 6 },
      { name: "productId", label: "Product ID", type: "text", required: true, col: 6 },
      { name: "quantity", label: "Quantity", type: "number", required: true, min: 1, col: 6, default: 1 },
      { name: "status", label: "Status", type: "select", required: false, col: 6, options: ["PLACED", "PAID", "CANCELLED", "COMPLETED"] },
    ],
    buildPayload(values, mode) {
      const payload = {
        customerId: values.customerId.trim(),
        items: [{ productId: values.productId.trim(), quantity: Number(values.quantity) }],
      };
      if (values.status) payload.status = values.status;
      if (mode === "update" && values.id.trim()) payload.id = values.id.trim();
      return payload;
    },
    upsertPath(values, mode) { return mode === "update" && values.id.trim() ? "/erp/orders/" + encodeURIComponent(values.id.trim()) : "/erp/orders"; },
    upsertMethod(values, mode) { return mode === "update" && values.id.trim() ? "PUT" : "POST"; },
    deletePath(record) { return "/erp/orders/" + encodeURIComponent(record.id); },
  },
  invoices: {
    title: "Invoices",
    listPath: () => {
      const customerId = (document.getElementById("customerFilter").value || "").trim();
      return customerId ? "/erp/invoices?customerId=" + encodeURIComponent(customerId) : "/erp/invoices";
    },
    idField: "id",
    columns: ["id", "orderId", "customerId", "status", "amount", "currencyCode"],
    fields: [
      { name: "id", label: "Invoice ID (optional for create)", type: "text", required: false, col: 6 },
      { name: "orderId", label: "Order ID", type: "text", required: true, col: 6 },
      { name: "customerId", label: "Customer ID", type: "text", required: true, col: 6 },
      { name: "amount", label: "Amount", type: "number", required: true, min: 0, col: 6 },
      { name: "currencyCode", label: "Currency", type: "text", required: true, col: 6, default: "GBP" },
      { name: "status", label: "Status", type: "select", required: true, col: 6, options: ["OPEN", "PAID", "CANCELLED", "VOID"] },
    ],
    buildPayload(values, mode) {
      const payload = {
        orderId: values.orderId.trim(),
        customerId: values.customerId.trim(),
        amount: Number(values.amount),
        currencyCode: (values.currencyCode || "GBP").trim().toUpperCase(),
        status: values.status,
      };
      if (values.id.trim()) payload.id = values.id.trim();
      return payload;
    },
    upsertPath(values, mode) { return mode === "update" && values.id.trim() ? "/erp/invoices/" + encodeURIComponent(values.id.trim()) : "/erp/invoices"; },
    upsertMethod(values, mode) { return mode === "update" && values.id.trim() ? "PUT" : "POST"; },
    deletePath(record) { return "/erp/invoices/" + encodeURIComponent(record.id); },
  },
};

function setStatus(msg) { document.getElementById("status").textContent = msg || ""; }
function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (ch) => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[ch]));
}

function authHeaders() {
  const tenant = (document.getElementById("tenant").value || "demo-tenant").trim() || "demo-tenant";
  const headers = { "Content-Type": "application/json", "X-Tenant-Id": tenant };
  if (state.token) headers.Authorization = "Bearer " + state.token;
  return headers;
}

async function callApi(path, method = "GET", body = null) {
  const resp = await fetch(cfg.erp + path, { method, headers: authHeaders(), body: body ? JSON.stringify(body) : null });
  const txt = await resp.text();
  let data = {};
  try { data = JSON.parse(txt); } catch { data = { raw: txt }; }
  if (!resp.ok) throw new Error(data.detail || data.error || txt || ("HTTP " + resp.status));
  return data;
}

async function signIn() {
  const tenant = (document.getElementById("tenant").value || "demo-tenant").trim() || "demo-tenant";
  const username = (document.getElementById("user").value || "").trim();
  const password = document.getElementById("password").value || "";
  const resp = await fetch(cfg.sts + "/sts/login", {
    method: "POST",
    headers: { "Content-Type":"application/json", "X-Tenant-Id": tenant },
    body: JSON.stringify({ tenant, username, password, audience: "wavestore-erp-api", scopes: ["erp.read","erp.write","erp.order","erp.export"] }),
  });
  const data = await resp.json();
  if (!resp.ok || !data.access_token) throw new Error(data.detail || "Sign in failed");
  state.token = data.access_token;
  document.getElementById("authState").textContent = "Signed in as " + username;
}

function normalizedRows(data) {
  const key = state.entity;
  const payload = data?.[key];
  return Array.isArray(payload) ? payload : [];
}

function renderTable() {
  const schema = schemas[state.entity];
  const head = document.getElementById("tableHead");
  const body = document.getElementById("tableBody");
  head.innerHTML = schema.columns.map((c) => "<th>" + esc(c) + "</th>").join("") + "<th>Actions</th>";

  const start = state.page * state.pageSize;
  const pageRows = state.rows.slice(start, start + state.pageSize);
  body.innerHTML = pageRows.map((row, idx) => {
    const cells = schema.columns.map((c) => "<td>" + esc(row[c]) + "</td>").join("");
    const actions = `<td>
      <button class="secondary" data-edit="${start + idx}">Edit</button>
      <button class="danger" data-del="${start + idx}">Delete</button>
    </td>`;
    return "<tr>" + cells + actions + "</tr>";
  }).join("");

  const pages = Math.max(1, Math.ceil(state.rows.length / state.pageSize));
  document.getElementById("pageInfo").textContent = "Page " + (state.page + 1) + " / " + pages;
  document.getElementById("prevBtn").disabled = state.page <= 0;
  document.getElementById("nextBtn").disabled = state.page >= pages - 1;

  body.querySelectorAll("[data-edit]").forEach((btn) => {
    btn.addEventListener("click", () => openModal("update", state.rows[Number(btn.dataset.edit)]));
  });
  body.querySelectorAll("[data-del]").forEach((btn) => {
    btn.addEventListener("click", () => deleteRecord(state.rows[Number(btn.dataset.del)]));
  });
}

async function loadEntity(resetPage = false) {
  const schema = schemas[state.entity];
  if (resetPage) state.page = 0;
  setStatus("Loading " + schema.title + "...");
  const data = await callApi(schema.listPath(), "GET");
  state.rows = normalizedRows(data);
  renderTable();
  setStatus("Loaded " + state.rows.length + " " + schema.title.toLowerCase() + ".");
}

function openModal(mode, row) {
  const schema = schemas[state.entity];
  state.mode = mode;
  state.editing = row || null;
  document.getElementById("modalTitle").textContent = (mode === "create" ? "Create " : "Edit ") + schema.title.slice(0, -1);
  document.getElementById("modalError").textContent = "";

  const form = document.getElementById("modalForm");
  form.innerHTML = schema.fields.map((f) => {
    let value = "";
    if (row) {
      if (f.name === "productId") value = row.items && row.items[0] ? row.items[0].productId || "" : "";
      else if (f.name === "quantity") value = row.items && row.items[0] ? row.items[0].quantity || 1 : 1;
      else if (row[f.name] !== undefined && row[f.name] !== null) value = row[f.name];
      else if (f.default !== undefined) value = f.default;
    } else if (f.default !== undefined) {
      value = f.default;
    }
    const inputId = "f_" + f.name;
    const ctl = f.type === "select"
      ? `<select id="${inputId}">${(f.options || []).map((o) => `<option value="${esc(o)}"${String(value)===String(o) ? " selected" : ""}>${esc(o)}</option>`).join("")}</select>`
      : `<input id="${inputId}" type="${f.type === "number" ? "number" : (f.type === "email" ? "email" : "text")}" value="${esc(value)}"${f.min !== undefined ? ` min="${f.min}"` : ""}>`;
    return `<div class="col-${f.col || 6}"><label>${esc(f.label)}${f.required ? " *" : ""}</label>${ctl}</div>`;
  }).join("");

  document.getElementById("modalBackdrop").classList.add("open");
}

function closeModal() {
  document.getElementById("modalBackdrop").classList.remove("open");
}

function collectAndValidate() {
  const schema = schemas[state.entity];
  const errors = [];
  const values = {};
  for (const f of schema.fields) {
    const el = document.getElementById("f_" + f.name);
    let raw = el ? String(el.value || "") : "";
    if (f.required && !raw.trim()) errors.push(f.label + " is required");
    if (f.type === "number" && raw.trim()) {
      const n = Number(raw);
      if (!Number.isFinite(n)) errors.push(f.label + " must be a number");
      if (f.min !== undefined && n < f.min) errors.push(f.label + " must be >= " + f.min);
    }
    if (f.type === "email" && raw.trim() && !/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(raw.trim())) errors.push("Invalid email format");
    values[f.name] = raw;
  }
  if (state.entity === "orders" && state.mode === "update" && !(values.id || "").trim()) errors.push("Order ID is required for update");
  if (state.entity === "invoices" && state.mode === "update" && !(values.id || "").trim()) errors.push("Invoice ID is required for update");
  return { values, errors };
}

async function saveModal() {
  const { values, errors } = collectAndValidate();
  const errBox = document.getElementById("modalError");
  if (errors.length) {
    errBox.textContent = errors.join(" | ");
    return;
  }
  const schema = schemas[state.entity];
  const payload = schema.buildPayload(values, state.mode);
  const path = schema.upsertPath(values, state.mode);
  const method = schema.upsertMethod(values, state.mode);
  await callApi(path, method, payload);
  closeModal();
  await loadEntity();
}

async function deleteRecord(row) {
  const schema = schemas[state.entity];
  const id = row?.[schema.idField];
  if (!id) return;
  if (!confirm("Delete " + id + "?")) return;
  await callApi(schema.deletePath(row), "DELETE");
  await loadEntity();
}

function setEntity(next) {
  state.entity = next;
  state.page = 0;
  document.getElementById("entityTitle").textContent = next === "branding" ? "Branding" : schemas[next].title;
  document.querySelectorAll("[data-entity]").forEach((b) => b.classList.toggle("active", b.dataset.entity === next));
  const isBranding = next === "branding";
  document.getElementById("tableToolbar").style.display = isBranding ? "none" : "";
  document.getElementById("tableWrap").style.display = isBranding ? "none" : "";
  document.getElementById("pagerWrap").style.display = isBranding ? "none" : "";
  document.getElementById("brandingPanel").style.display = isBranding ? "" : "none";
  if (isBranding) { loadBranding().catch((err) => setBrandingStatus(err.message)); return; }
  loadEntity(true).catch((err) => setStatus(err.message));
}

function setBrandingStatus(msg) { document.getElementById("brandingStatus").textContent = msg || ""; }

async function loadBranding() {
  const b = await callApi("/erp/branding", "GET");
  document.getElementById("brandStoreName").value = b.storeName || "";
  document.getElementById("brandTagline").value = b.tagline || "";
  document.getElementById("brandLogoUrl").value = b.logoUrl || "";
  document.getElementById("brandFaviconUrl").value = b.faviconUrl || "";
  document.getElementById("brandPrimaryColor").value = b.primaryColor || "#0d6efd";
  setBrandingStatus("Loaded current branding.");
}

async function saveBranding() {
  const payload = {
    storeName: document.getElementById("brandStoreName").value.trim(),
    tagline: document.getElementById("brandTagline").value.trim(),
    logoUrl: document.getElementById("brandLogoUrl").value.trim(),
    faviconUrl: document.getElementById("brandFaviconUrl").value.trim(),
    primaryColor: document.getElementById("brandPrimaryColor").value.trim(),
  };
  await callApi("/erp/branding", "POST", payload);
  setBrandingStatus("Branding saved -- storefront picks this up within 30 seconds.");
}

async function resetBranding() {
  if (!confirm("Reset branding to WaveStore defaults?")) return;
  await callApi("/erp/branding", "DELETE");
  await loadBranding();
  setBrandingStatus("Branding reset to defaults.");
}

document.getElementById("signInBtn").addEventListener("click", () => signIn().then(() => loadEntity(true)).catch((err) => setStatus(err.message)));
document.getElementById("refreshBtn").addEventListener("click", () => loadEntity().catch((err) => setStatus(err.message)));
document.getElementById("createBtn").addEventListener("click", () => openModal("create", null));
document.getElementById("customerFilter").addEventListener("change", () => { if (state.entity === "orders" || state.entity === "invoices") loadEntity(true).catch((err) => setStatus(err.message)); });
document.getElementById("prevBtn").addEventListener("click", () => { if (state.page > 0) { state.page -= 1; renderTable(); } });
document.getElementById("nextBtn").addEventListener("click", () => {
  const pages = Math.max(1, Math.ceil(state.rows.length / state.pageSize));
  if (state.page < pages - 1) { state.page += 1; renderTable(); }
});
document.getElementById("cancelBtn").addEventListener("click", closeModal);
document.getElementById("saveBtn").addEventListener("click", () => saveModal().catch((err) => { document.getElementById("modalError").textContent = err.message; }));
document.getElementById("saveBrandingBtn").addEventListener("click", () => saveBranding().catch((err) => setBrandingStatus(err.message)));
document.getElementById("resetBrandingBtn").addEventListener("click", () => resetBranding().catch((err) => setBrandingStatus(err.message)));
document.querySelectorAll("[data-entity]").forEach((b) => b.addEventListener("click", () => setEntity(b.dataset.entity)));

setEntity("products");
</script>
</body>
</html>"""
        return HTMLResponse(html.replace("__STS_URL__", sts).replace("__ERP_API_URL__", erp_api))

    return app
