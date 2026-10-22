"use strict";

// ---------- helpers ----------
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (n) => {
  if (n === null || n === undefined || n === "") return "—";
  const a = Math.abs(n);
  if (a >= 1e6) return (n / 1e6).toFixed(a >= 1e7 ? 0 : 1).replace(/\.0$/, "") + "M";
  if (a >= 1e3) return (n / 1e3).toFixed(a >= 1e4 ? 0 : 1).replace(/\.0$/, "") + "K";
  return String(n);
};
const pct = (p, digits = 1) => (p === null || p === undefined ? "—" : (p * 100).toFixed(digits) + "%");
const ago = (iso) => {
  if (!iso) return "—";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return Math.floor(s / 60) + " min ago";
  if (s < 86400) return Math.floor(s / 3600) + " h ago";
  if (s < 86400 * 45) return Math.floor(s / 86400) + " d ago";
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
};
const dateLabel = (iso) => new Date(iso + (iso.length === 10 ? "T12:00:00" : "")).toLocaleDateString(undefined, { month: "short", day: "numeric" });
const weekday = (iso) => new Date(iso + "T12:00:00").toLocaleDateString(undefined, { weekday: "short" });
const label = (v) => (v === null || v === undefined || v === "" ? "—" : String(v).replace(/_/g, " "));
const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : s);
const hue = (s) => [...String(s)].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7);
// Escape, highlight [[placeholders]], and turn outlier ids the planner cites into @handles.
const fills = (text) => {
  let html = esc(text).replace(/\[\[(.+?)\]\]/g, '<mark class="fill">$1</mark>');
  for (const o of S.outliers) if (html.includes(o.shortcode)) html = html.split(o.shortcode).join(`@${esc(o.username)}`);
  return html;
};
const STATIC = Boolean(window.SNAPSHOT);

async function api(path, opts = {}) {
  if (STATIC) return staticApi(path, opts);
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function staticApi(path, opts) {
  if (opts.method && opts.method !== "GET") throw new Error("This is a read-only snapshot. Run the app locally to change things.");
  const [base, query] = path.split("?");
  const q = new URLSearchParams(query || "");
  const routes = window.SNAPSHOT.routes;
  if (/\/outliers$/.test(base)) {
    const where = { active: (o) => o.status !== "dismissed", saved: (o) => o.status === "saved", dismissed: (o) => o.status === "dismissed", all: () => true }[q.get("status") || "active"];
    const order = { ratio: (a, b) => b.ratio - a.ratio, views: (a, b) => b.views - a.views, newest: (a, b) => (b.taken_at || "").localeCompare(a.taken_at || "") }[q.get("sort") || "ratio"];
    return (routes[base] || []).filter(where).sort(order);
  }
  if (base in routes) return routes[base];
  if (base.startsWith("/api/teardowns/")) return { status: "none" };
  return [];
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), 3500);
}

// The viewer may refuse the clipboard API (some app views do); fall back to a selected textarea.
function copyText(text, done) {
  if (!text) return toast("Nothing to copy yet.");
  const fallback = () => {
    const t = document.createElement("textarea");
    t.value = text; t.setAttribute("readonly", ""); t.style.position = "fixed"; t.style.opacity = "0";
    document.body.append(t); t.select();
    const ok = document.execCommand("copy");
    t.remove();
    toast(ok ? done : "Couldn't copy. Use Download instead.");
  };
  if (navigator.clipboard?.writeText) navigator.clipboard.writeText(text).then(() => toast(done), fallback);
  else fallback();
}

const SEALCAM = [["S", "Subject"], ["E", "Environment"], ["A", "Action"], ["L", "Lighting"], ["Ca", "Camera"], ["M", "Metatokens"]];
const sealcamRows = (item, fx = esc) => `<dl class="rows sealcam">${SEALCAM.filter(([k]) => item[k]).map(([k, name]) =>
  `<dt><b>${k}</b> ${name}</dt><dd>${fx(item[k])}</dd>`).join("")}</dl>`;

const I = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${d}</svg>`;
const ICON = {
  home: I('<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>'),
  search: I('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'),
  bell: I('<path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/>'),
  doc: I('<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>'),
  gear: I('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/>'),
  user: I('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="10" r="3"/><path d="M6.2 18.4a7 7 0 0 1 11.6 0"/>'),
  image: I('<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/>'),
  play: I('<path d="M7 4v16l13-8z"/>'),
  stop: I('<rect x="6" y="6" width="12" height="12" rx="1"/>'),
  star: I('<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1 6.2L12 17.3l-5.5 2.9 1-6.2L3 9.6l6.2-.9z"/>'),
  x: I('<path d="M18 6 6 18M6 6l12 12"/>'),
  ext: I('<path d="M14 4h6v6M20 4l-9 9M19 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h5"/>'),
  chev: I('<path d="m9 6 6 6-6 6"/>'),
  back: I('<path d="M19 12H5M11 18l-6-6 6-6"/>'),
  next: I('<path d="M5 12h14M13 6l6 6-6 6"/>'),
  cut: I('<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12"/>'),
  download: I('<path d="M12 4v12m0 0-5-5m5 5 5-5M4 20h16"/>'),
  refresh: I('<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>'),
  sparkle: I('<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6.3 6.3l2.5 2.5M15.2 15.2l2.5 2.5M6.3 17.7l2.5-2.5M15.2 8.8l2.5-2.5"/>'),
  edit: I('<path d="M4 20h4L19 9l-4-4L4 16z"/><path d="m13.5 6.5 4 4"/>'),
  alert: I('<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>'),
  calendar: I('<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>'),
  copy: I('<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V6a1 1 0 0 1 1-1h9"/>'),
  trash: I('<path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/>'),
};

// ---------- state ----------
const S = {
  view: "research", tab: "outliers", projects: [], projectId: null, outliers: [], creators: [], doubled: [], patterns: null, rates: null,
  runs: [], plans: [], planId: null, planForm: false, open: null, td: null, editing: null, edits: {},
  status: {}, vocab: null, sort: "ratio", filter: "active", events: [], seenEvents: 0,
};
const project = () => S.projects.find((p) => p.id === S.projectId);
const activeRun = () => (S.runs[0] && S.runs[0].status === "running" ? S.runs[0] : null);
const outlier = (sc) => S.outliers.find((o) => o.shortcode === sc);
const currentPlan = () => S.plans.find((p) => p.id === S.planId) || S.plans[0];

// ---------- data ----------
async function loadProjects() {
  S.projects = await api("/api/projects");
  if (!S.projects.find((p) => p.id === S.projectId)) S.projectId = S.projects[0]?.id ?? null;
}

async function loadProjectData() {
  if (!S.projectId) Object.assign(S, { outliers: [], creators: [], doubled: [], patterns: null, runs: [], plans: [], rates: null });
  if (!S.projectId) return;
  const id = S.projectId;
  const [outliers, creators, patterns, runs, plans, rates, doubled] = await Promise.all([
    api(`/api/projects/${id}/outliers?status=${S.filter}&sort=${S.sort}`), api(`/api/projects/${id}/creators`),
    api(`/api/projects/${id}/patterns`), api(`/api/projects/${id}/runs`), api(`/api/projects/${id}/plans`),
    api(`/api/projects/${id}/rates`), api(`/api/projects/${id}/doubled-down`),
  ]);
  if (id !== S.projectId) return;
  Object.assign(S, { outliers, creators, patterns, runs, plans, rates, doubled });
}

async function loadStatus(refresh = false) {
  if (STATIC) { S.status = window.SNAPSHOT.routes["/api/status"] || {}; return renderBottom(); }
  try { S.status = await api("/api/status" + (refresh ? "?refresh=true" : "")); } catch { /* keep last */ }
  renderBottom();
}

async function openTeardown(shortcode) {
  S.open = shortcode;
  S.editing = null; S.edits = {};
  S.td = { status: "loading" };
  S.view = "research";
  if (S.tab === "plan" || S.tab === "creators") S.tab = "outliers";
  render();
  $("#main").scrollTop = 0;
  const td = await api(`/api/teardowns/${shortcode}`);
  if (S.open !== shortcode) return;
  S.td = td;
  render();
  pollTeardown();
}

// ---------- polling ----------
function pollRun() {
  clearTimeout(pollRun.timer);
  const run = activeRun();
  if (!run || STATIC) return;
  pollRun.timer = setTimeout(async () => {
    try {
      const fresh = await api(`/api/runs/${run.id}`);
      S.runs[0] = fresh;
      if (fresh.status !== "running") {
        await Promise.all([loadProjects(), loadProjectData(), loadStatus(true)]);
        toast(fresh.message || "Research run finished");
        return render();
      }
      pollRun.ticks = (pollRun.ticks || 0) + 1;
      if (pollRun.ticks % 4 === 0) await loadProjectData();
      renderMain(); renderBottom();
    } catch { /* retry next tick */ }
    pollRun();
  }, 2000);
}

function pollTeardown() {
  clearTimeout(pollTeardown.timer);
  if (!S.td || S.td.status !== "running" || STATIC) return;
  const sc = S.open;
  pollTeardown.timer = setTimeout(async () => {
    const td = await api(`/api/teardowns/${sc}`).catch(() => null);
    if (td && S.open === sc) {
      S.td = { ...td, mode: S.td.mode };
      if (td.status !== "running") {
        await loadProjectData();
        toast(td.status === "done" ? "Teardown ready" : "Teardown failed: " + td.error);
        return render();
      }
    }
    pollTeardown();
  }, 2500);
}

function pollPlan() {
  clearTimeout(pollPlan.timer);
  const plan = currentPlan();
  if (!plan || plan.status !== "running" || STATIC) return;
  pollPlan.timer = setTimeout(async () => {
    S.plans = await api(`/api/projects/${S.projectId}/plans`).catch(() => S.plans);
    const fresh = S.plans.find((p) => p.id === plan.id);
    if (fresh && fresh.status !== "running") {
      toast(fresh.status === "done" ? "Your week is planned" : "Planning failed: " + fresh.error);
      return render();
    }
    pollPlan();
  }, 3000);
}

if (!STATIC) {
  setInterval(async () => {
    S.events = await api("/api/events?limit=60").catch(() => S.events);
    $("#activity-dot").hidden = !(S.events.length && S.events[0].id > S.seenEvents) || S.view === "activity";
  }, 15000);
  setInterval(() => loadStatus(false), 60000);
}

// ---------- actions ----------
async function setView(view) {
  S.view = view;
  S.open = null;
  if (view === "activity") {
    S.events = await api("/api/events?limit=60").catch(() => []);
    S.seenEvents = S.events[0]?.id || 0;
    $("#activity-dot").hidden = true;
  }
  render();
}

async function selectProject(id) {
  S.projectId = id;
  S.open = null; S.td = null; S.editing = null; S.planId = null; S.planForm = false;
  if (!["settings", "bank"].includes(S.view)) S.view = "research";
  await loadProjectData();
  render();
  pollRun(); pollPlan();
}

async function startRun() {
  try {
    await api(`/api/projects/${S.projectId}/runs`, { method: "POST" });
    S.runs = await api(`/api/projects/${S.projectId}/runs`);
    toast("Research started");
    render(); pollRun();
  } catch (e) { toast(e.message); }
}

async function stopRun() {
  const run = activeRun();
  if (run) { await api(`/api/runs/${run.id}/stop`, { method: "POST" }); toast("Stopping after the current request…"); }
}

async function setOutlierStatus(shortcode, status) {
  try {
    await api(`/api/projects/${S.projectId}/outliers/${shortcode}`, { method: "PATCH", body: { status } });
  } catch (e) { return toast(e.message); }
  await Promise.all([loadProjects(), loadProjectData()]);
  if (status === "dismissed") { S.open = null; toast("Dismissed"); }
  else toast(status === "saved" ? "Saved to bank" : "Removed from bank");
  render();
}

async function startTeardown(shortcode, mode = "") {
  try {
    await api(`/api/teardowns/${shortcode}${mode ? "/" + mode : ""}?project_id=${S.projectId}`, { method: "POST" });
    S.td = { ...(S.td || {}), status: "running", mode };
    render(); pollTeardown();
  } catch (e) { toast(e.message); }
}

async function saveSection() {
  try {
    const data = await api(`/api/teardowns/${S.open}`, { method: "PUT", body: { fields: S.edits } });
    S.td.data = data;
    S.editing = null; S.edits = {};
    toast("Saved");
    await loadProjectData();
    render();
  } catch (e) { toast(e.message); }
}

// ---------- render: shell ----------
function render() {
  document.querySelectorAll(".rail-btn[data-view]").forEach((b) => {
    const on = !b.classList.contains("avatar") && (b.dataset.view === S.view || (b.dataset.view === "research" && S.view === "new"));
    if (on) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  renderSidebar(); renderMain(); renderRight(); renderBottom();
}

function renderSidebar() {
  const p = project();
  $("#sidebar").innerHTML = `
    ${STATIC ? "" : `<button class="new-btn" data-action="new" ${S.view === "new" ? 'aria-current="page"' : ""}>New research ${ICON.chev}</button>`}
    <div class="side-group">Projects</div>
    ${S.projects.map((x) => `
      <button class="proj" data-project="${x.id}" ${x.id === S.projectId ? 'aria-current="true"' : ""}>
        <span class="avatar" style="background:hsl(${hue(x.name)} 50% 42%)">${esc(x.name.trim()[0]?.toUpperCase() || "?")}</span>
        <span class="meta"><div class="t">${esc(x.name)}</div>
          <div class="s">${x.outliers} outliers · ${x.keywords.length} keyword${x.keywords.length === 1 ? "" : "s"}${x.last_run?.status === "running" ? " · researching" : ""}</div></span>
      </button>`).join("") || `<div class="side-empty">No projects yet. Start one with New research.</div>`}
    ${p ? `<div class="side-group">Keywords</div><div class="kw-list">${p.keywords.map((k) => `<span class="chip">${esc(k)}</span>`).join("")}</div>` : ""}`;
}

function renderBottom() {
  const st = S.status;
  const run = activeRun();
  const credits = st.credits != null ? `${Number(st.credits).toLocaleString()} credits` : st.credits_error ? "balance unavailable" : "…";
  const model = (project()?.settings.ai_model || S.vocab?.defaults?.ai_model || "").split("/").pop();
  $("#bottombar").innerHTML = STATIC ? `
    <div class="grp"><span><span class="sd on"></span>Read-only snapshot · ${esc(ago(window.SNAPSHOT.generated_at))}</span></div>
    <div class="grp"><span>Run the app locally to research, tear down and plan</span></div>` : `
    <div class="grp">
      <span><span class="sd ${st.scrapecreators ? "on" : "off"}"></span>ScrapeCreators ${st.scrapecreators ? "· " + credits : "· key missing"}</span>
      <span><span class="sd ${st.openrouter ? "on" : ""}"></span>OpenRouter ${st.openrouter ? "· " + esc(model) : "· not set"}</span>
      <span><span class="sd ${st.ffmpeg ? "on" : "off"}"></span>ffmpeg ${st.ffmpeg ? "ready" : "missing"}</span>
    </div>
    <div class="grp">${run ? `<span><span class="sd busy"></span>Run #${run.id} · ${esc(run.message || "")} · ${run.credits_used} credits</span>` :
      S.runs[0] ? `<span>Last run ${ago(S.runs[0].finished_at || S.runs[0].started_at)}</span>` : "<span>Idle</span>"}</div>`;
}

// ---------- render: main ----------
function renderMain() {
  const main = $("#main");
  const views = { home: homeView, activity: activityView, settings: settingsView, bank: bankView, new: newResearchView };
  if (views[S.view]) return (main.innerHTML = `<div class="content plain">${views[S.view]()}</div>`);
  const p = project();
  if (!p) {
    main.innerHTML = `<div class="content plain"><div class="empty-state"><h1>Find outliers in a niche</h1>
      <p>Create a research project with a few keywords. The app searches Instagram reels and accounts, checks each creator's
      follower count and recent reels, and keeps the reels with 5× or more views than followers.</p>
      ${STATIC ? "" : `<button class="btn primary" data-action="new">${ICON.play} New research</button>`}</div></div>`;
    return;
  }
  const done = S.outliers.filter((o) => o.teardown_status === "done").length;
  const tabs = [["outliers", "Outliers", p.outliers - p.dismissed], ["doubled", "Doubled down", S.doubled.length], ["creators", "Creators", S.creators.length],
    ["teardowns", "Teardowns", done], ["plan", "Plan", S.plans.filter((x) => x.status === "done").length]];
  const body = S.open ? teardownPage() : { doubled: doubledTab, creators: creatorsTab, teardowns: teardownsTab, plan: planTab }[S.tab]?.() ?? outliersTab(p);
  main.innerHTML = `<div class="tabs" role="tablist">${tabs.map(([k, l, n]) =>
    `<button class="tab" role="tab" data-tab="${k}" aria-selected="${S.tab === k}">${l}<span class="tab-n">${n}</span></button>`).join("")}</div>
    <div class="content">${body}</div>`;
}

function outliersTab(p) {
  const run = activeRun();
  const s = p.settings;
  const cards = S.outliers.map((o) => {
    const hook = o.td?.verbal_hook || o.td?.written_hook;
    return `<button class="card" data-open="${esc(o.shortcode)}" aria-label="Open teardown of @${esc(o.username)}, ${o.ratio} times">
      <div class="thumb">${o.cover ? `<img src="${esc(o.cover)}" alt="" loading="lazy">` : `<div class="ph">${ICON.image}</div>`}
        <span class="ratio">${o.ratio}×</span>
        <span class="corner">${o.basis === "template" ? `<span class="chip info">Template</span>` : ""}${o.status === "saved" ? `<span class="chip accent">${ICON.star}Saved</span>` : ""}${o.sponsored ? `<span class="chip warn">Sponsored</span>` : ""}</span>
      </div>
      <div class="body">
        <div class="who">@${esc(o.username)}</div>
        <div class="nums">${fmt(o.views)} views · ${fmt(o.followers)} followers · ${ago(o.taken_at)}</div>
        ${o.td ? `<div class="hook ${hook ? "" : "none"}">${esc(hook || "No spoken or on-screen hook")}</div>`
               : `<div class="hook none">${esc((o.caption || "").split("\n")[0] || "Not torn down yet")}</div>`}
        ${o.td ? `<div class="chips">${[o.td.format, o.td.hook_pattern !== "niche_specific" && o.td.hook_pattern].filter(Boolean)
          .map((t) => `<span class="chip info">${esc(label(t))}</span>`).join("")}${o.teardown_status === "running" ? `<span class="chip warn">Tearing down</span>` : ""}</div>` : ""}
      </div></button>`;
  }).join("");
  const last = S.runs[0];
  const runCard = STATIC ? "" : `
    <div class="runcard">
      <div class="icon">${run ? ICON.refresh : ICON.search}</div>
      <div class="txt">
        <div class="t">${run ? `Researching: ${esc(run.phase || "")}` : last ? `Last run ${ago(last.finished_at || last.started_at)}` : "No research yet"}</div>
        <div class="s">${run ? esc(run.message || "") + ` · ${run.credits_used} credits used` : last ? esc(last.message || "") :
          `Searches ${p.keywords.length} keyword${p.keywords.length === 1 ? "" : "s"} and scans up to ${s.max_creators} creators. Hard cap: ${s.credit_budget} credits.`}</div>
        ${run ? `<div class="progress" role="progressbar" aria-valuenow="${Math.round((run.progress || 0) * 100)}" aria-valuemin="0" aria-valuemax="100"><div style="width:${Math.round((run.progress || 0) * 100)}%"></div></div>` : ""}
      </div>
      ${run ? `<button class="btn" data-action="stop">${ICON.stop} Stop</button>` : `<button class="btn primary" data-action="run">${ICON.play} ${last ? "Run again" : "Run research"}</button>`}
    </div>`;
  return `<div class="page-head"><h1>${esc(p.name)}</h1>
      <p>${p.niche ? esc(p.niche) + ". " : ""}Outliers have ${s.min_ratio}× or more views than their creator's followers, from creators with ${fmt(s.min_followers)}–${fmt(s.max_followers)} followers, posted in the last ${s.max_age_days} days.</p></div>
    <div class="toolbar">
      <select data-control="filter" aria-label="Show">${[["active", "Active"], ["saved", "Saved"], ["dismissed", "Dismissed"], ["all", "All"]].map(([v, l]) => `<option value="${v}" ${S.filter === v ? "selected" : ""}>${l}</option>`).join("")}</select>
      <select data-control="sort" aria-label="Sort by">${[["ratio", "Highest ratio"], ["views", "Most views"], ["newest", "Newest"]].map(([v, l]) => `<option value="${v}" ${S.sort === v ? "selected" : ""}>${l}</option>`).join("")}</select>
      <span class="spacer"></span><span class="small muted">${S.outliers.length} shown · click one for its teardown</span>
    </div>
    ${S.outliers.length ? `<div class="grid">${cards}</div>` : `<p class="muted">${run ? "Outliers appear here as creators are scanned." : "No outliers yet. Run research to find them."}</p>`}
    ${runCard}`;
}

function doubledTab() {
  const head = `<div class="page-head"><h1>Doubled down</h1><p>Creators who found a template that works and keep posting it.
    A template is a phrase that keeps coming back in their caption headlines. It counts when it shows up in 4 or more reels,
    its typical reel reaches at least 10% of their followers, and it's either a habit (1 in 5 of their reels) or beats their
    follower count. Copying a template that keeps working is often safer than copying one lucky reel.</p></div>`;
  if (!S.doubled.length) return head + `<p class="muted">None found yet. Run research: every scanned creator, including accounts you name to study and bigger accounts up to ${fmt(project()?.settings?.double_down_max_followers)} followers, is checked for a repeated template.</p>`;
  const example = (e) => `<div class="ex">
      ${e.cover ? `<img src="${esc(e.cover)}" alt="" loading="lazy">` : `<div class="ph">${ICON.image}</div>`}
      <div class="n">${fmt(e.views)} views · ${e.ratio}× followers</div>
      <div class="t" title="${esc(e.title)}">${esc(e.title || "No caption")}</div>
      ${e.outlier_status ? `<button class="btn sm" data-open="${esc(e.shortcode)}">${ICON.cut} ${e.teardown_status === "done" ? "Teardown" : "Open"}</button>`
        : STATIC ? `<a class="btn sm quiet" href="${esc(e.url)}" target="_blank" rel="noopener">${ICON.ext} Open reel</a>`
        : `<button class="btn sm" data-action="add-template" data-shortcode="${esc(e.shortcode)}">${ICON.cut} Tear down</button>`}
    </div>`;
  return head + `<div class="dd-list">${S.doubled.map((a) => `<section class="dd">
      <div class="dd-h"><a href="https://www.instagram.com/${encodeURIComponent(a.username)}/" target="_blank" rel="noopener">@${esc(a.username)}</a>
        <span class="small muted">${fmt(a.followers)} followers · ${a.reels} reels scanned · typical reel ${fmt(a.median_views)} views</span>
        ${a.study ? `<span class="chip accent">Account you named</span>` : ""}</div>
      ${a.templates.map((t) => `<div class="tpl ${t.qualifies ? "" : "minor"}">
        <div class="tpl-h"><b>“${esc(cap(t.phrase))}”</b><span class="chip ${t.qualifies ? "good" : ""}">${t.qualifies ? "Doubled down" : "Also repeats"}</span></div>
        <div class="small muted">${t.count} of ${t.of} reels (${pct(t.share, 0)}) · typical one ${fmt(t.median_views)} views, ${t.reach}× followers${t.vs_other_reels ? ` · ${t.vs_other_reels}× their other reels` : ""}</div>
        <div class="tpl-ex">${t.examples.map(example).join("")}</div></div>`).join("")}
    </section>`).join("")}</div>`;
}

function creatorsTab() {
  if (!S.creators.length) return `<p class="muted">Creators found by keyword search appear here.</p>`;
  const st = { scanned: ["good", "Scanned"], found: ["", "Not scanned"], too_big: ["warn", "Too big"], too_small: ["warn", "Too small"], private: ["bad", "Private"], error: ["bad", "Error"] };
  return `<div class="page-head"><h1>Creators</h1><p>Everyone the keyword and account searches surfaced, with why each was or wasn't scanned.</p></div>
    <div class="tablewrap"><table><thead><tr><th>Creator</th><th class="num">Followers</th><th class="num">Reels scanned</th><th class="num">Median views</th><th class="num">Outliers</th><th class="num">Best</th><th>Doubles down on</th><th>Status</th><th>Found via</th></tr></thead><tbody>
    ${S.creators.map((c) => `<tr>
      <td><a href="https://www.instagram.com/${encodeURIComponent(c.username)}/" target="_blank" rel="noopener">@${esc(c.username)}</a>${c.full_name ? `<div class="xs muted">${esc(c.full_name)}</div>` : ""}</td>
      <td class="num">${fmt(c.followers)}</td><td class="num">${c.reels || "—"}</td><td class="num">${fmt(c.median_views)}</td>
      <td class="num">${c.outliers || "—"}</td><td class="num">${c.best_ratio ? c.best_ratio + "×" : "—"}</td>
      <td>${(S.doubled.find((d) => d.username === c.username)?.templates || []).filter((t) => t.qualifies).map((t) => `<button class="chip good" data-tab="doubled">${esc(cap(t.phrase))}</button>`).join(" ") || "—"}</td>
      <td><span class="chip ${st[c.status]?.[0] || ""}">${st[c.status]?.[1] || esc(label(c.status))}</span></td>
      <td class="clip">${c.keywords.map(esc).join(", ")}</td></tr>`).join("")}
    </tbody></table></div>`;
}

function teardownsTab() {
  const rows = S.outliers.filter((o) => o.teardown_status === "done");
  if (!rows.length) return `<p class="muted">No teardowns yet. Open an outlier and press Tear down.</p>`;
  return `<div class="page-head"><h1>Teardowns</h1><p>Every torn-down outlier side by side. Open one to read or edit its full breakdown.</p></div>
    <div class="tablewrap"><table><thead><tr><th></th><th>Creator</th><th class="num">Ratio</th><th>Heard in the first 3 s</th><th>Pattern</th><th>Angle</th><th>Format</th><th>Structure</th><th>CTA</th><th>Check</th></tr></thead><tbody>
    ${rows.map((o) => `<tr class="click" data-open="${esc(o.shortcode)}">
      <td>${o.cover ? `<img class="mini" src="${esc(o.cover)}" alt="">` : `<div class="mini"></div>`}</td>
      <td>@${esc(o.username)}${o.sponsored ? ` <span class="chip warn">Sponsored</span>` : ""}</td><td class="num">${o.ratio}×</td>
      <td class="clip" title="${esc(o.td.verbal_hook || "")}">${esc(o.td.verbal_hook || o.td.written_hook || "—")}</td>
      <td>${esc(label(o.td.hook_pattern))}</td><td>${esc(label(o.td.angle))}</td><td>${esc(label(o.td.format))}</td>
      <td>${esc(label(o.td.complexity))} ${esc(label(o.td.delivery))}</td><td>${esc(label(o.td.cta_mechanic))}</td>
      <td>${o.td.review ? `<span class="chip bad">${o.td.review} to review</span>` : o.td.ai ? `<span class="chip ai">${o.td.ai} AI</span>` : `<span class="chip good">Reviewed</span>`}</td></tr>`).join("")}
    </tbody></table></div>`;
}

// ---------- teardown page ----------
const SECTIONS = {
  hook: { title: "Hook: the first 3 seconds", keys: ["verbal_hook", "written_hook", "visual_hook", "hook_pattern"] },
  structure: { title: "Structure", keys: ["structure_pattern", "angle", "video_type", "delivery", "story_type", "complexity"] },
  value: { title: "Value and call to action", keys: ["value_summary", "cta_type", "cta_mechanic", "cta_keyword", "cta_text"] },
  format: { title: "Format and editing", keys: ["format", "audio", "captions"] },
  position: { title: "Positioning and series", keys: ["topic", "content_type", "funnel", "post_type", "is_series", "series_type", "episode_marker"] },
};
const FIELD = {
  verbal_hook: "Heard", written_hook: "On screen", visual_hook: "Happens", hook_pattern: "Pattern", structure_pattern: "Beats",
  angle: "Angle", video_type: "Video type", delivery: "Delivery", story_type: "Story type", complexity: "Complexity",
  value_summary: "Takeaway", cta_type: "CTA type", cta_mechanic: "Mechanic", cta_keyword: "Keyword", cta_text: "Closing line",
  format: "Format", audio: "Audio", captions: "Captions", topic: "Topic", content_type: "Content type", funnel: "Funnel",
  post_type: "Post type", is_series: "Series", series_type: "Series type", episode_marker: "Episode marker",
};
const SOURCE = { api: "From Instagram data", auto: "Read from the data", heuristic: "Pattern match: check it", ai: "AI: check it against the frames",
  needs_review: "Needs review", human: "You set this" };
const QUOTED = new Set(["verbal_hook", "written_hook", "cta_text"]);
const LONG = new Set(["verbal_hook", "visual_hook", "value_summary", "cta_text", "structure_pattern"]);
let VOCAB_KEYS = new Set();

function value(f, key) {
  const v = f?.value;
  if (v === null || v === undefined || v === "") return `<span class="empty">${f?.source === "needs_review" ? "Needs review" : "None"}</span>`;
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (key === "funnel") return esc(String(v).toUpperCase());
  return QUOTED.has(key) ? `“${esc(v)}”` : esc(VOCAB_KEYS.has(key) ? cap(label(v)) : v);
}

function rows(fields, keys) {
  return `<dl class="rows">${keys.filter((k) => fields[k]).map((k) => {
    const f = fields[k];
    const note = f.note && f.source !== "auto" && f.source !== "api" ? `<span class="note">${esc(f.note)}</span>` : "";
    return `<dt>${FIELD[k] || k}</dt><dd class="${QUOTED.has(k) ? "quote" : ""}">${value(f, k)}<span class="prov ${esc(f.source)}" title="${esc(SOURCE[f.source] || f.source)}" aria-label="${esc(SOURCE[f.source] || f.source)}"></span>${note}</dd>`;
  }).join("")}</dl>`;
}

function editor(fields, keys) {
  return `<form class="edit-form"><div class="edit-grid">${keys.filter((k) => fields[k]).map((k) => {
    const v = k in S.edits ? S.edits[k] : fields[k].value;
    const id = `ed-${k}`;
    let input;
    if (k === "is_series") input = `<label class="check"><input id="${id}" type="checkbox" data-field="is_series" ${v ? "checked" : ""}> This is a series episode</label>`;
    else if (S.vocab?.vocab[k]) input = `<select id="${id}" data-field="${k}"><option value="">—</option>${S.vocab.vocab[k].map((o) => `<option value="${o}" ${o === v ? "selected" : ""}>${esc(cap(label(o)))}</option>`).join("")}</select>`;
    else if (LONG.has(k)) input = `<textarea id="${id}" data-field="${k}" rows="2">${esc(v ?? "")}</textarea>`;
    else input = `<input id="${id}" type="text" data-field="${k}" value="${esc(v ?? "")}">`;
    return `<label for="${id}">${FIELD[k] || k}</label>${input}`;
  }).join("")}</div>
  <div class="edit-actions"><button class="btn primary" type="submit">Save</button><button class="btn" type="button" data-action="cancel-edit">Cancel</button></div></form>`;
}

function section(key, fields, extraTop = "", extraBottom = "") {
  const sec = SECTIONS[key];
  const editing = S.editing === key;
  return `<section class="sec" aria-labelledby="sec-${key}">
    <div class="sec-h"><h2 id="sec-${key}">${sec.title}</h2>
      ${STATIC || editing ? "" : `<button class="btn sm quiet" data-edit="${key}">${ICON.edit} Edit</button>`}</div>
    ${extraTop}${editing ? editor(fields, sec.keys) : rows(fields, sec.keys.filter((k) => k !== "structure_pattern"))}${extraBottom}</section>`;
}

function beatsPills(pattern) {
  if (!pattern) return "";
  const parts = String(pattern).split(/\s*(?:→|->|>)\s*/).filter(Boolean);
  return `<div class="beats" aria-label="Beat sequence">${parts.map((p, i) => {
    const name = p.replace(/[×x]\d+$/, "").trim().toUpperCase();
    return `${i ? `<span class="arrow">${ICON.next}</span>` : ""}<span class="beat ${esc(name)}">${esc(p.trim())}</span>`;
  }).join("")}</div>`;
}

function teardownPage() {
  const o = outlier(S.open);
  const td = S.td || { status: "loading" };
  const back = `<button class="back" data-action="close-teardown">${ICON.back} All outliers</button>`;
  if (!o) return `${back}<p class="muted">This outlier isn't in the current list.</p>`;
  const data = td.data;
  const f = data?.fields || {};
  const stats = f.stats?.value || {};
  const duration = stats.duration_s || o.duration;
  const head = `${back}
    <div class="td-head">
      <div class="td-title"><h1>@${esc(o.username)}<span class="ratio-big">${o.ratio}×</span></h1>
        <div class="line">${fmt(stats.views ?? o.views)} views on ${fmt(o.followers)} followers${duration ? ` · ${Math.round(duration)} s` : ""} · posted ${ago(o.taken_at)}${o.keyword ? ` · found via “${esc(o.keyword)}”` : ""}</div></div>
      <div class="td-actions">
        ${STATIC ? "" : `<button class="btn ${o.status === "saved" ? "on" : ""}" data-action="${o.status === "saved" ? "unsave" : "save"}">${ICON.star} ${o.status === "saved" ? "Saved" : "Save to bank"}</button>
        <button class="btn quiet" data-action="dismiss">${ICON.x} Dismiss</button>`}
        <a class="btn quiet" href="${esc(o.url)}" target="_blank" rel="noopener">${ICON.ext} Open reel</a>
      </div>
    </div>`;
  if (td.status === "loading") return head + skeleton();
  if (td.status === "running") return head + `<p class="muted" style="margin:16px 0">${{ ai: "The AI is re-reading the frames and transcript…", scenes: "Fetching the video again and describing every scene in SEALCaM. Usually under a minute." }[td.mode] || "Pulling post details, transcript and frames, then running the AI analysis. Usually 30–90 seconds."}</p>` + skeleton();
  if (td.status === "none") return head + `<div class="empty-state"><h2>Not torn down yet</h2>
      <p>A teardown pulls the post details and transcript (about 2 ScrapeCreators credits), grabs frames from the video, then has the AI fill in the breakdown${S.status.openrouter ? " (a few cents)" : ""}.</p>
      ${STATIC ? "" : `<button class="btn primary" data-action="teardown">${ICON.cut} Tear down</button>`}</div>`;
  if (td.status === "failed" && !data) return head + `<div class="notice">${ICON.alert}<div>Teardown failed: ${esc(td.error)}</div></div>
      ${STATIC ? "" : `<button class="btn" data-action="teardown">${ICON.refresh} Try again</button>`}`;

  const chips = [["angle", "info"], ["video_type", "info"], ["delivery", "info"], ["story_type", "info"], ["format", "info"],
    ["content_type", ""], ["funnel", ""], ["complexity", ""]]
    .filter(([k]) => f[k]?.value && !["none", "unknown"].includes(f[k].value))
    .map(([k, c]) => [k === "funnel" ? f[k].value.toUpperCase() : cap(label(f[k].value)), c])
    .filter(([text], i, all) => all.findIndex(([t]) => t === text) === i)
    .map(([text, c]) => `<span class="chip ${c}">${esc(text)}</span>`).join("");
  const seriesChip = f.is_series?.value ? `<span class="chip accent">Series${f.series_type?.value ? ": " + esc(label(f.series_type.value)) : ""}</span>` : "";
  const notices = (data.notes || []).map((n) => `<div class="notice">${ICON.alert}<div>${esc(n)}</div></div>`).join("") +
    (td.error ? `<div class="notice">${ICON.alert}<div>${esc(td.error)}</div></div>` : "");
  const hookFrames = data.media?.hook_frames || [];
  const frames = data.media?.frames || [];
  const film = hookFrames.length ? `<div class="filmstrip">${hookFrames.map((src, i) =>
    `<figure><img src="${esc(src)}" alt="Frame at ${(i * 0.5).toFixed(1)} seconds" data-zoom="${esc(src)}"><figcaption>${(i * 0.5).toFixed(1)} s</figcaption></figure>`).join("")}</div>` : "";
  const facts = (items) => `<div class="facts">${items.filter(([, v]) => v !== null && v !== undefined).map(([k, v]) => `<div class="fact"><span class="k">${k}</span><span class="v">${esc(v)}</span></div>`).join("")}</div>`;
  const evidence = (f.series_evidence?.value || []).length ? `<p class="small muted" style="margin-top:12px">Sibling episodes: ${f.series_evidence.value.map((u, i) => `<a href="${esc(u)}" target="_blank" rel="noopener">episode ${i + 1}</a>`).join(" · ")}</p>` : "";
  const step = duration && frames.length ? Math.max(0.5, Math.round((duration / frames.length) * 2) / 2) : 2;
  const scenes = (data.scenes || []).filter((sc) => sc.S);
  const sceneTools = STATIC || !S.status.openrouter ? "" : `<button class="btn sm quiet" data-action="scenes">${ICON.sparkle} ${scenes.length ? "Redo scenes" : "Break down scenes"}</button>`;
  const scenesSec = `<section class="sec" aria-labelledby="sec-scenes">
    <div class="sec-h"><h2 id="sec-scenes">Scenes</h2>${sceneTools}</div>
    ${scenes.length ? `<p class="small muted" style="margin:0 0 16px">${scenes.length} scenes in SEALCaM: subject, environment, action, lighting, camera, metatokens. Long holds are split into segments of the same shot.</p>
      <ol class="scenes">${scenes.map((sc) => `<li class="scene">
        <div class="scene-frames">${(sc.frames || []).map((src) => `<img src="${esc(src)}" alt="" loading="lazy" data-zoom="${esc(src)}">`).join("")}</div>
        <div class="scene-body">
          <div class="scene-h"><b>Scene ${sc.i}</b><span class="tc">${sc.start.toFixed(1)}–${sc.end.toFixed(1)} s</span>${sc.beat ? `<span class="beat ${esc(sc.beat)}">${esc(sc.beat)}</span>` : ""}
            <span class="xs faint">${sc.cut === false ? "same shot continues" : "hard cut"}${sc.flash_cuts ? ` · ${sc.flash_cuts} flash cut${sc.flash_cuts === 1 ? "" : "s"}` : ""}</span></div>
          ${sc.said ? `<p class="say">“${esc(sc.said)}”</p>` : ""}${sc.on_screen_text ? `<p class="small"><b>On screen:</b> ${esc(sc.on_screen_text)}</p>` : ""}
          ${sealcamRows(sc)}</div></li>`).join("")}</ol>`
      : `<p class="muted">Not broken down yet. This fetches the video again (the post lookup is cached) and describes every scene in SEALCaM${S.status.openrouter ? ", for a few cents" : ""}.</p>`}</section>`;
  const tools = STATIC ? "" : `<div class="toolbar" style="margin:0">
      ${S.status.openrouter ? `<button class="btn sm" data-action="ai">${ICON.sparkle} ${data.ai ? "Re-analyze with AI" : "Analyze with AI"}</button>` : ""}
      <button class="btn sm quiet" data-action="teardown" title="Re-fetch data and frames; keeps your edits">${ICON.refresh} Re-run teardown</button></div>`;

  return `${head}
    <div class="chips td-summary">${chips}${seriesChip}</div>
    ${notices}
    ${section("hook", f, film)}
    ${section("structure", f, S.editing === "structure" ? "" : beatsPills(f.structure_pattern?.value),
      facts([["Words", f.word_count?.value], ["Words per second", f.words_per_second?.value], ["Length", duration ? Math.round(duration) + " s" : null]]))}
    ${section("value", f)}
    ${section("format", f, "", facts([["Average shot", f.avg_shot_s?.value != null ? f.avg_shot_s.value + " s" : null], ["Hard cuts", f.cuts?.value]]) +
      (frames.length ? `<p class="small muted" style="margin:16px 0 8px">The whole video, about one frame every ${step} s</p><div class="timeline">${frames.map((src) => `<img src="${esc(src)}" alt="" loading="lazy" data-zoom="${esc(src)}">`).join("")}</div>` : ""))}
    ${scenesSec}
    ${section("position", f, "", evidence)}
    ${data.transcript ? `<details class="raw"><summary>Transcript</summary><div class="prose">${esc(data.transcript.text)}</div></details>` : ""}
    ${data.caption ? `<details class="raw"><summary>Caption</summary><div class="prose">${esc(data.caption)}</div></details>` : ""}
    <div class="sec">${tools}</div>`;
}

function skeleton() {
  return `<div aria-hidden="true"><div class="skel line" style="width:40%"></div><div class="filmstrip" style="margin-top:24px">${"<div class='skel block' style='height:180px'></div>".repeat(6)}</div>
    <div class="skel line" style="width:70%"></div><div class="skel line" style="width:55%"></div><div class="skel line" style="width:62%"></div></div>`;
}

// ---------- plan ----------
function planTab() {
  const plan = currentPlan();
  const teardowns = S.outliers.filter((o) => o.teardown_status === "done" && !o.sponsored).length;
  if (S.planForm || !plan) return planForm(teardowns);
  const picker = `<div class="toolbar">
      ${S.plans.length > 1 ? `<select data-control="plan" aria-label="Choose a plan">${S.plans.map((x) => `<option value="${x.id}" ${x.id === plan.id ? "selected" : ""}>Plan #${x.id} · ${ago(x.created_at)} · ${esc(x.status)}</option>`).join("")}</select>` : ""}
      <span class="spacer"></span>
      ${plan.export ? `${plan.export.week ? `<button class="btn sm" data-action="copy-week">${ICON.copy} Copy week</button>` : ""}${STATIC ? "" : `<a class="btn sm" href="/api/plans/${plan.id}/export.md" download>${ICON.download} Export week</a>`}` : ""}
      ${STATIC ? "" : `<button class="btn sm quiet" data-action="delete-plan">${ICON.trash} Delete</button><button class="btn sm" data-action="new-plan">${ICON.calendar} New plan</button>`}</div>`;
  if (plan.status === "running") return picker + `<div class="page-head"><h1>Planning your week…</h1><p>The AI is adapting proven structures from your teardowns, then writing a shot list for each post. Usually 3–4 minutes.</p></div>
    <div class="week" aria-hidden="true">${"<div class='skel block' style='height:76px'></div>".repeat(plan.input?.posts || 7)}</div>`;
  if (plan.status === "failed") return picker + `<div class="notice">${ICON.alert}<div>Planning failed: ${esc(plan.error)}</div></div>
    ${STATIC ? "" : `<button class="btn primary" data-action="new-plan">${ICON.refresh} Try again</button>`}`;
  const d = plan.data;
  const first = d.posts[0]?.date;
  return picker + `<div class="page-head"><h1>Week of ${first ? dateLabel(first) : ""}</h1>
      <p>${d.posts.length} posts adapted from ${d.teardowns_used} teardowns. Each one names the outliers it borrows from. The odds are this niche's real base rates, adjusted for how strongly the teardowns back each choice; open a post to see the math.</p></div>
    <div class="week">${d.posts.map((p, i) => planDay(p, i, d.rates, plan.id)).join("")}</div>`;
}

function planForm(teardowns) {
  const input = currentPlan()?.input || {};
  const tomorrow = new Date(Date.now() + 86400000).toISOString().slice(0, 10);
  return `<div class="page-head"><h1>Plan a week</h1>
      <p>Builds a week of posts from your ${teardowns} teardowns. The AI adapts proven hooks, structures and formats to your niche;
      the odds come from the ${S.rates?.reels ?? "scanned"} reels in this project, not from the AI.</p></div>
    ${teardowns < 3 ? `<div class="notice">${ICON.alert}<div>Tear down at least 3 outliers first. The plan is built from teardowns.</div></div>` : ""}
    <form id="plan-form" class="form">
      <label class="field"><span>About you</span>
        <textarea name="about" rows="6" placeholder="Who you are, who you help, what you sell. Results, client wins and stories you're happy to share.">${esc(input.about || "")}</textarea>
        <span class="help">The plan only states facts you write here. Anything else it needs becomes a highlighted placeholder for you to fill in.</span></label>
      <div class="grid-3">
        <label class="field"><span>Your followers</span><input type="number" name="followers" min="0" value="${input.followers ?? ""}" placeholder="e.g. 850"></label>
        <label class="field"><span>First post</span><input type="date" name="start_date" value="${esc(input.start_date || tomorrow)}"></label>
        <label class="field"><span>Posts</span><select name="posts">${[7, 6, 5, 4, 3].map((n) => `<option ${n === (input.posts || 7) ? "selected" : ""}>${n}</option>`).join("")}</select></label>
      </div>
      <div class="toolbar"><button class="btn primary" type="submit" ${teardowns < 3 || STATIC ? "disabled" : ""}>${ICON.calendar} Plan my week</button>
        ${S.plans.length ? `<button class="btn quiet" type="button" data-action="cancel-plan">Cancel</button>` : ""}
        <span class="small muted">About $1 of AI · 3–4 minutes, shot lists included</span></div>
    </form>`;
}

// "DS__AHijRFc scene 2" -> a link that opens that outlier's teardown.
function shotRef(ref) {
  const sc = String(ref).split(/\s+/)[0];
  const o = outlier(sc);
  return o ? `<button class="linkish xs" data-open="${esc(sc)}">borrows from ${fills(ref)}</button>` : `<span class="xs faint">borrows from ${fills(ref)}</span>`;
}

function planDay(p, i, rates, planId) {
  const o = p.odds;
  const ceiling = (rates.p5 || 0.01) * 3;
  const sources = (p.source_outliers || []).map((sc) => outlier(sc)).filter(Boolean);
  const rung = (k, lbl, base) => `<div class="rung"><div class="v">${pct(o[k])}</div><div class="k">${lbl}</div><div class="b">niche base ${pct(base)}</div></div>`;
  return `<details class="day" ${i === 0 ? "open" : ""}>
    <summary>
      <div class="when"><span class="d">${weekday(p.date)}</span><span class="date">${dateLabel(p.date)}</span></div>
      <div class="what"><div class="title">${fills(p.title)}</div>
        <div class="chips"><span class="chip">${esc(p.funnel.toUpperCase())}</span><span class="chip">${esc(cap(label(p.content_type)))}</span>
          ${p.format ? `<span class="chip info">${esc(cap(label(p.format)))}</span>` : ""}${p.angle ? `<span class="chip info">${esc(cap(label(p.angle)))}</span>` : ""}
          ${p.series_marker ? `<span class="chip accent">${esc(p.series_marker)}</span>` : ""}</div></div>
      <div class="oddsbox"><span class="pct">${pct(o.p5)}</span><span class="lbl">chance of a 5× outlier · ${esc(o.band)}</span>
        <div class="meter ${o.band.split(" ")[0]}"><div style="width:${Math.min(100, (o.p5 / ceiling) * 100)}%"></div></div></div>
    </summary>
    <div class="day-body">
      <div class="toolbar brief-tools"><span class="small muted">The brief: idea, script, shot list and the reference scenes</span><span class="spacer"></span>
        <button class="btn sm" data-action="copy-brief" data-slot="${p.slot}">${ICON.copy} Copy brief</button>
        ${STATIC ? "" : `<a class="btn sm quiet" href="/api/plans/${planId}/export.md?post=${p.slot}" download>${ICON.download} Download .md</a>`}</div>
      ${sources.length ? `<div class="refs"><span class="small muted">Reference videos</span><div class="sources">${sources.map((x) => `<button class="source" data-open="${esc(x.shortcode)}">${x.cover ? `<img src="${esc(x.cover)}" alt="">` : `<span class="noimg"></span>`}@${esc(x.username)} · ${x.ratio}×</button>`).join("")}</div></div>` : ""}
      <div class="ladder">${rung("p1", "beats your follower count", rates.p1)}${rung("p2", "2× your followers", rates.p2)}${rung("p5", "5× (an outlier)", rates.p5)}${rung("p10", "10×", rates.p10)}</div>
      <ul class="why-odds">
        <li>${o.multiplier}× the niche base rate: evidence ×${o.factors.evidence} · funnel stage ×${o.factors.funnel}${o.factors.source_median_ratio ? ` · its sources median ${o.factors.source_median_ratio}×` : ""}.</li>
        ${o.support.map((s) => `<li>${esc(cap(label(s.attr)))} “${esc(label(s.value))}”: used by ${s.count} of ${s.of} outliers.</li>`).join("")}
        <li>${cap(o.confidence)} confidence: ${rates.reels} reels scanned, ${o.support[0]?.of ?? 0} teardowns. Treat it as a guide, not a forecast.</li>
      </ul>
      <section class="sec"><div class="sec-h"><h2>Hook</h2></div>
        <dl class="rows"><dt>Say</dt><dd class="quote">“${fills(p.hook?.verbal)}”</dd><dt>On screen</dt><dd>${fills(p.hook?.written)}</dd><dt>Show</dt><dd>${fills(p.hook?.visual)}</dd></dl></section>
      <section class="sec"><div class="sec-h"><h2>Script</h2><span class="small muted">${p.length_s ? `about ${p.length_s} s · ` : ""}${esc(cap(label(p.complexity)))} ${esc(label(p.delivery))}${p.story_type ? ` · ${esc(label(p.story_type))} story` : ""}</span></div>
        <ol class="script">${(p.beats || []).map((b) => `<li><span class="beat ${esc(b.label)}">${esc(b.label)}</span><div>
          <div class="say">${fills(b.say)}</div>
          <div class="dir">${b.show ? `<b>Film:</b> ${fills(b.show)}` : ""}${b.show && b.edit ? " · " : ""}${b.edit ? `<b>Edit:</b> ${fills(b.edit)}` : ""}</div></div></li>`).join("")}</ol></section>
      ${(p.shots || []).length ? `<section class="sec"><div class="sec-h"><h2>Shot list</h2><span class="small muted">SEALCaM · one shot per setup or cut</span></div>
        <ol class="shots">${p.shots.map((sh, k) => `<li class="shot">
          <div class="scene-h"><b>Shot ${k + 1}</b>${sh.beat ? `<span class="beat ${esc(sh.beat)}">${esc(sh.beat)}</span>` : ""}${sh.duration_s ? `<span class="tc">about ${sh.duration_s} s</span>` : ""}
            ${sh.reference ? shotRef(sh.reference) : ""}</div>
          ${sh.say ? `<p class="say">“${fills(sh.say)}”</p>` : ""}${sh.on_screen_text ? `<p class="small"><b>On screen:</b> ${fills(sh.on_screen_text)}</p>` : ""}
          ${sealcamRows(sh, fills)}</li>`).join("")}</ol></section>` : p.shots_error ? `<div class="notice">${ICON.alert}<div>The shot list failed: ${esc(p.shots_error)}</div></div>` : ""}
      <section class="sec"><div class="sec-h"><h2>Close and post</h2></div>
        <dl class="rows"><dt>Call to action</dt><dd class="quote">“${fills(p.cta?.line)}”<span class="note">${esc(cap(label(p.cta_type)))} · ${esc(label(p.cta?.mechanic))}</span></dd>
          <dt>Caption</dt><dd>${fills(p.caption_first_line)}<span class="note">${(p.hashtags || []).map((h) => "#" + esc(String(h).replace(/^#/, ""))).join(" ")}</span></dd></dl></section>
      <section class="sec"><div class="sec-h"><h2>Why it should work</h2></div>
        <p>${fills(p.why)}</p>
        <p class="small muted" style="margin-top:12px"><b>Risk:</b> ${fills(p.risk)}</p>
        ${(p.needs_from_you || []).length ? `<p class="small" style="margin-top:12px"><b>You need to fill in:</b></p><ul class="why-odds">${p.needs_from_you.map((n) => `<li>${fills(n)}</li>`).join("")}</ul>` : ""}
      </section>
    </div></details>`;
}

// ---------- other views ----------
function homeView() {
  const total = S.projects.reduce((a, p) => a + p.outliers, 0);
  const saved = S.projects.reduce((a, p) => a + p.saved, 0);
  return `<div class="page-head"><h1>Home</h1><p>${S.projects.length} project${S.projects.length === 1 ? "" : "s"} · ${total} outliers found · ${saved} saved to the bank</p></div>
    <div class="cards2">${S.projects.map((p) => `<button class="pcard" data-project="${p.id}">
      <h3>${esc(p.name)}</h3><span class="small muted">${p.keywords.map(esc).join(" · ")}</span>
      <div class="stat-row"><div><div class="stat-v">${p.outliers}</div><div class="xs faint">Outliers</div></div>
      <div><div class="stat-v">${p.saved}</div><div class="xs faint">Saved</div></div>
      <div><div class="stat-v">${p.last_run ? p.last_run.credits_used : 0}</div><div class="xs faint">Credits, last run</div></div></div>
      <span class="xs faint">${p.last_run ? "Last run " + ago(p.last_run.finished_at || p.last_run.started_at) : "Never run"}</span></button>`).join("") ||
      (STATIC ? "" : `<div class="empty-state"><button class="btn primary" data-action="new">${ICON.play} New research</button></div>`)}</div>`;
}

function activityView() {
  return `<div class="page-head"><h1>Activity</h1><p>Research runs, teardowns, plans and errors.</p></div>
    ${S.events.length ? S.events.map((e) => `<div class="event"><span class="lvl ${esc(e.level)}"></span><span class="faint">${ago(e.created_at)}</span>
      <span>${e.project ? `<b>${esc(e.project)}</b> · ` : ""}${esc(e.message)}</span></div>`).join("") : `<p class="muted">Nothing yet.</p>`}`;
}

function bankView() {
  const p = project();
  if (!p) return `<p class="muted">No project selected.</p>`;
  const saved = S.outliers.filter((o) => o.status === "saved");
  return `<div class="page-head"><h1>Bank</h1><p>Outliers you saved from ${esc(p.name)}. Export them, with their teardowns, as JSON for the templating step.</p></div>
    <div class="toolbar">${STATIC ? "" : `<a class="btn primary" href="/api/projects/${p.id}/export" download="${esc(p.name)}-outliers.json">${ICON.download} Export ${p.saved} saved</a>`}
      <button class="btn" data-action="show-saved">Show saved in Research</button></div>
    ${saved.length ? `<div class="grid">${saved.map((o) => `<button class="card" data-open="${esc(o.shortcode)}"><div class="thumb">${o.cover ? `<img src="${esc(o.cover)}" alt="" loading="lazy">` : `<div class="ph">${ICON.image}</div>`}<span class="ratio">${o.ratio}×</span></div>
      <div class="body"><div class="who">@${esc(o.username)}</div><div class="hook">${esc(o.td?.verbal_hook || o.td?.written_hook || "")}</div></div></button>`).join("")}</div>`
      : `<p class="muted">Nothing saved yet. Open an outlier and press Save to bank.</p>`}`;
}

function newResearchView() {
  const d = S.vocab?.defaults || {};
  const num = (k, lbl, attrs = "") => `<label class="field"><span>${lbl}</span><input type="number" name="${k}" value="${esc(d[k])}" ${attrs}></label>`;
  return `<div class="page-head"><h1>New research</h1><p>Pick keywords for your niche, and name any accounts you want to study. The app finds creators with 1K–500K followers and keeps their reels that got 5× or more views than followers.</p></div>
    <form id="new-form" class="form">
      <label class="field"><span>Project name</span><input type="text" name="name" required placeholder="e.g. Dog training"></label>
      <label class="field"><span>Niche</span><input type="text" name="niche" placeholder="e.g. Puppy training for first-time owners"><span class="help">Optional. The planner uses it.</span></label>
      <label class="field"><span>Keywords</span><textarea name="keywords" rows="5" required placeholder="dog training&#10;crate training puppy&#10;puppy biting&#10;dog trainer"></textarea>
        <span class="help">One per line: your niche, each sub-niche, your job title, and a variation or two.</span></label>
      <label class="field"><span>Accounts to study</span><input type="text" name="study_accounts" placeholder="e.g. @stylegenai @boopwithme">
        <span class="help">Optional. Always scanned, deeper and whatever their size, with the same outlier test.</span></label>
      <details class="more"><summary>Thresholds and budget</summary>
        <div class="form" style="gap:12px">
          <div class="grid-3">${num("min_ratio", "Min ratio", 'step="0.5"')}${num("min_followers", "Min followers")}${num("max_followers", "Max followers")}</div>
          <div class="grid-3">${num("search_pages", "Search pages", 'min="1" max="11"')}${num("reel_pages", "Reel pages")}${num("max_creators", "Max creators", 'min="1"')}</div>
          <div class="grid-3">${num("credit_budget", "Credit budget", 'min="1"')}${num("max_age_days", "Max age (days)")}<div></div></div>
        </div></details>
      <label class="check"><input type="checkbox" name="start" checked> Start research right away</label>
      <div class="toolbar"><button class="btn primary" type="submit">${ICON.play} Create</button><button class="btn quiet" type="button" data-action="cancel-new">Cancel</button>
        <span class="small muted" id="estimate">Add keywords to see a credit estimate</span></div>
    </form>`;
}

function settingsView() {
  const st = S.status;
  const p = project();
  const s = p ? p.settings : S.vocab?.defaults || {};
  const num = (k, lbl, step = 1) => `<label class="field"><span>${lbl}</span><input type="number" step="${step}" name="${k}" value="${esc(s[k])}"></label>`;
  return `<div class="page-head"><h1>Settings</h1><p>Connections and the current project's thresholds.</p></div>
    <div class="panel"><div class="kv">
      <div><span class="k">ScrapeCreators</span><span class="v">${st.scrapecreators ? "Connected" : "Key missing"}</span></div>
      <div><span class="k">Credits</span><span class="v">${st.credits != null ? Number(st.credits).toLocaleString() : "—"}</span></div>
      <div><span class="k">OpenRouter</span><span class="v">${st.openrouter ? "Connected" : "Not set"}</span></div>
      <div><span class="k">ffmpeg</span><span class="v">${st.ffmpeg ? "Installed" : "Missing"}</span></div></div></div>
    <p class="small muted" style="margin:12px 0">Keys come from environment variables or the repo's .env file (SCRAPECREATORS_API_KEY, OPENROUTER_API_KEY). They are never shown or sent to the browser.</p>
    ${STATIC ? "" : `<button class="btn sm" data-action="refresh-balance">${ICON.refresh} Refresh balance</button>`}
    ${STATIC ? "" : `<h2 class="section-gap" style="margin-bottom:8px">Backup</h2>
    <p class="small muted" style="margin:0 0 12px">Everything in one file: all projects, outliers, teardowns, plans and frames. Use it to move your research to another machine or a server.</p>
    <div class="toolbar"><a class="btn sm" href="/api/backup" download>${ICON.download} Download backup</a>
      <label class="btn sm quiet" for="restore-file">${ICON.refresh} Restore from a backup…</label>
      <input type="file" id="restore-file" accept=".gz,.tgz,application/gzip" hidden></div>`}
    ${p && !STATIC ? `<h2 class="section-gap" style="margin-bottom:16px">${esc(p.name)}</h2>
    <form id="settings-form" class="form">
      <label class="field"><span>Name</span><input type="text" name="name" value="${esc(p.name)}"></label>
      <label class="field"><span>Niche</span><input type="text" name="niche" value="${esc(p.niche || "")}"></label>
      <label class="field"><span>Keywords</span><textarea name="keywords" rows="4">${esc(p.keywords.join("\n"))}</textarea><span class="help">One per line</span></label>
      <label class="field"><span>Accounts to study</span><input type="text" name="study_accounts" value="${esc((p.settings.study_accounts || []).map((h) => "@" + h).join(" "))}"></label>
      <div class="grid-3">${num("min_ratio", "Min ratio", 0.5)}${num("min_followers", "Min followers")}${num("max_followers", "Max followers")}</div>
      <div class="grid-3">${num("search_pages", "Search pages per keyword")}${num("reel_pages", "Reel pages per creator")}${num("max_creators", "Max creators")}</div>
      <div class="grid-3">${num("credit_budget", "Credit budget per run")}${num("max_age_days", "Max age (days)")}<div></div></div>
      <label class="field"><span>AI model</span><input type="text" name="ai_model" value="${esc(s.ai_model)}"><span class="help">An OpenRouter model that reads images. Default: anthropic/claude-sonnet-5.5</span></label>
      <label class="check"><input type="checkbox" name="ai_annotation" ${s.ai_annotation ? "checked" : ""}> Run AI analysis at the end of every teardown</label>
      <label class="check"><input type="checkbox" name="account_search" ${s.account_search ? "checked" : ""}> Also search Instagram accounts for each keyword (1 credit each)</label>
      <label class="check"><input type="checkbox" name="allow_long_transcription" ${s.allow_long_transcription ? "checked" : ""}> Transcribe reels over 2 minutes (10 credits per started minute)</label>
      <div class="toolbar"><button class="btn primary" type="submit">Save project</button><button class="btn quiet" type="button" data-action="delete-project">${ICON.trash} Delete project</button></div>
    </form>` : ""}`;
}

// ---------- inspector (right sidebar) ----------
function renderRight() {
  const right = $("#right");
  let html;
  if (S.open && S.view === "research") html = teardownInspector();
  else if (S.view === "research" && S.tab === "plan" && !S.planForm && currentPlan()?.status === "done") html = planInspector(currentPlan().data);
  else html = nicheInspector();
  right.innerHTML = html;
  right.classList.toggle("closed", !S.open);
}

function ratesPanel(r) {
  if (!r || !r.reels) return `<p class="small muted">Run research to measure this niche's base rates.</p>`;
  return `<div class="panel"><div class="kv">
      <div><span class="k">Beat their followers</span><span class="v">${pct(r.p1)}</span></div>
      <div><span class="k">2× followers</span><span class="v">${pct(r.p2)}</span></div>
      <div><span class="k">5× (outlier)</span><span class="v">${pct(r.p5)}</span></div>
      <div><span class="k">10×</span><span class="v">${pct(r.p10)}</span></div></div></div>
    <p class="xs faint">Share of ${r.reels} reels from in-range creators that beat each multiple of their follower count.</p>`;
}

function bars(list) {
  if (!list?.length) return `<p class="small faint">Nothing yet</p>`;
  const max = Math.max(...list.map((r) => r[1]));
  return `<div class="bars">${list.map(([k, n]) => `<div class="bar"><span class="lbl">${esc(cap(label(k)))}</span><span class="track"><span class="fill" style="display:block;width:${(n / max) * 100}%"></span></span><span class="n">${n}</span></div>`).join("")}</div>`;
}

function nicheInspector() {
  const pt = S.patterns;
  if (!project()) return `<div class="insp-empty"><h3>Niche at a glance</h3><p class="small">Base rates and the most common patterns show here once you have research.</p></div>`;
  // Without the AI pass, hook pattern, format and angle are only pattern matches: say so rather than present them as findings.
  const torn = S.outliers.filter((o) => o.teardown_status === "done" && o.td);
  const noAi = torn.filter((o) => !o.td.ai).length;
  const pending = noAi ? `<div class="notice">${ICON.alert}<div>${noAi} of ${torn.length} teardowns are still waiting for the AI pass, so the counts below come from pattern matching only.</div></div>` : "";
  return `<div class="insp-sec"><h3>How often reels take off here</h3>${ratesPanel(S.rates)}</div>
    ${pt && pt.teardowns ? `${pending}
    <div class="insp-sec"><h3>Hook patterns</h3>${bars(pt.hook_pattern)}</div>
    <div class="insp-sec"><h3>Formats</h3>${bars(pt.format)}</div>
    <div class="insp-sec"><h3>Angles</h3>${bars(pt.angle)}</div>
    <div class="insp-sec"><h3>Video types</h3>${bars(pt.video_type)}</div>
    <p class="xs faint">From ${pt.teardowns} teardown${pt.teardowns === 1 ? "" : "s"}${pt.series ? `, ${pt.series} series` : ""}.</p>`
    : `<div class="insp-sec"><h3>Patterns</h3><p class="small muted">Tear down a few outliers and their most common hooks, formats and angles show here.</p></div>`}`;
}

function teardownInspector() {
  const o = outlier(S.open);
  if (!o) return "";
  const data = S.td?.data;
  const f = data?.fields || {};
  const counts = {};
  Object.values(f).forEach((x) => { const k = x.source === "api" ? "auto" : x.source; counts[k] = (counts[k] || 0) + 1; });
  const legend = [["auto", "From the data"], ["heuristic", "Pattern match, check it"], ["ai", "AI, check against the frames"], ["needs_review", "Needs review"], ["human", "You set it"]];
  return `<div class="insp-top"><div class="panel"><div class="kv">
      <div><span class="k">Views</span><span class="v">${fmt(f.stats?.value?.views ?? o.views)}</span></div>
      <div><span class="k">Followers</span><span class="v">${fmt(o.followers)}</span></div>
      <div><span class="k">Likes</span><span class="v">${fmt(o.likes)}</span></div>
      <div><span class="k">Comments</span><span class="v">${fmt(o.comments)}</span></div>
    </div></div>${o.cover ? `<img class="insp-cover" src="${esc(o.cover)}" alt="Cover of the reel" data-zoom="${esc(o.cover)}">` : ""}</div>
    ${data ? `<div class="insp-sec"><h3>Where each value came from</h3><div class="legend">${legend.map(([k, l]) =>
      `<span><span class="prov ${k}"></span>${l}${counts[k] ? `<span class="faint">· ${counts[k]}</span>` : ""}</span>`).join("")}</div></div>` : ""}
    ${data?.ai ? `<div class="insp-sec"><h3>AI reviewer note</h3><p class="ai-note">${esc(data.ai.notes || "No notes.")}</p>
      <p class="xs faint">${esc((data.ai.model || "").split("/").pop())}${data.ai.cost != null ? ` · $${Number(data.ai.cost).toFixed(3)}` : ""}${data.credits_used != null ? ` · ${data.credits_used} ScrapeCreators credits` : ""}</p></div>` : ""}
    <div class="insp-sec"><h3>Niche base rates</h3>${ratesPanel(S.rates)}</div>`;
}

function planInspector(d) {
  const funnel = {};
  d.posts.forEach((p) => { funnel[p.funnel.toUpperCase()] = (funnel[p.funnel.toUpperCase()] || 0) + 1; });
  const needs = d.posts.reduce((a, p) => a + (p.needs_from_you || []).length, 0);
  return `<div class="insp-sec"><h3>This week's mix</h3>${bars(Object.entries(funnel))}</div>
    <div class="insp-sec"><h3>Formats</h3>${bars(d.format_mix.filter(([k]) => k))}</div>
    <div class="insp-sec"><h3>Before you film</h3><p class="small">${needs ? `${needs} placeholder${needs === 1 ? "" : "s"} to fill with your own facts. They're highlighted in each script.` : "No placeholders: every fact came from what you wrote."}</p></div>
    <div class="insp-sec"><h3>How the odds work</h3><p class="small muted">${esc(d.method)}</p>${ratesPanel(d.rates)}</div>
    <p class="xs faint">${esc((d.model || "").split("/").pop())}${d.cost ? ` · $${Number(d.cost).toFixed(3)}` : ""}</p>`;
}

// ---------- events ----------
document.addEventListener("click", async (ev) => {
  const zoom = ev.target.closest("[data-zoom]");
  if (zoom) {
    const lb = document.createElement("button");
    lb.className = "lightbox";
    lb.setAttribute("aria-label", "Close image");
    lb.innerHTML = `<img src="${esc(zoom.dataset.zoom)}" alt="">`;
    lb.addEventListener("click", () => lb.remove());
    document.body.appendChild(lb);
    lb.focus();
    return;
  }
  const el = ev.target.closest("[data-view],[data-project],[data-tab],[data-open],[data-edit],[data-action]");
  if (!el) return;
  if (el.dataset.view) return setView(el.dataset.view);
  if (el.dataset.project) return selectProject(Number(el.dataset.project));
  if (el.dataset.tab) { S.tab = el.dataset.tab; S.open = null; S.planForm = false; render(); return pollPlan(); }
  if (el.dataset.open) return openTeardown(el.dataset.open);
  if (el.dataset.edit) { S.editing = el.dataset.edit; S.edits = {}; return renderMain(); }
  const actions = {
    new: () => { S.view = "new"; S.open = null; render(); },
    "cancel-new": () => { S.view = "research"; render(); },
    run: startRun, stop: stopRun,
    teardown: () => startTeardown(S.open), ai: () => startTeardown(S.open, "ai"), scenes: () => startTeardown(S.open, "scenes"),
    "add-template": async () => {
      const sc = el.dataset.shortcode;
      await api(`/api/projects/${S.projectId}/outliers`, { method: "POST", body: { shortcode: sc } });
      await loadProjectData();
      await openTeardown(sc);
      await startTeardown(sc);
    },
    "copy-brief": () => copyText(currentPlan()?.export?.posts?.[el.dataset.slot]?.markdown, "Brief copied"),
    "copy-week": () => copyText(currentPlan()?.export?.week?.markdown, "Week copied"),
    save: () => setOutlierStatus(S.open, "saved"), unsave: () => setOutlierStatus(S.open, "new"), dismiss: () => setOutlierStatus(S.open, "dismissed"),
    "close-teardown": () => { S.open = null; render(); },
    "cancel-edit": () => { S.editing = null; S.edits = {}; renderMain(); },
    "new-plan": () => { S.planForm = true; render(); },
    "cancel-plan": () => { S.planForm = false; render(); },
    "delete-plan": async () => {
      const plan = currentPlan();
      if (!plan || !confirm("Delete this plan?")) return;
      await api(`/api/plans/${plan.id}`, { method: "DELETE" });
      S.planId = null; await loadProjectData(); render();
    },
    "refresh-balance": async () => { await loadStatus(true); toast("Balance refreshed"); renderMain(); },
    "show-saved": async () => { S.filter = "saved"; S.view = "research"; S.tab = "outliers"; await loadProjectData(); render(); },
    "delete-project": async () => {
      if (!confirm("Delete this project and its outliers? Teardowns are kept.")) return;
      await api(`/api/projects/${S.projectId}`, { method: "DELETE" });
      S.projectId = null; await loadProjects(); await loadProjectData(); S.view = "research"; render();
    },
  };
  const action = actions[el.dataset.action];
  if (action) {
    try { await action(); } catch (e) { toast(e.message); }
  }
});

// Restore uploads the backup in 8 MB parts, so a proxy's request size limit can't get in the way.
async function restoreBackup(file) {
  if (!confirm(`Replace ALL data here with "${file.name}"? Projects, outliers, teardowns and plans on this copy are overwritten.`)) return;
  const size = 8 * 1024 * 1024, parts = Math.max(1, Math.ceil(file.size / size));
  const upload = Math.random().toString(36).slice(2, 12) + Date.now().toString(36);
  try {
    for (let i = 0; i < parts; i++) {
      toast(`Uploading backup… ${Math.round((i / parts) * 100)}%`);
      const res = await fetch(`/api/restore?upload=${upload}&part=${i}&parts=${parts}`, { method: "POST", body: file.slice(i * size, (i + 1) * size) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Restore failed (${res.status})`);
      if (data.restored) toast(`Restored ${data.restored.projects} projects, ${data.restored.outliers} outliers, ${data.restored.teardowns} teardowns`);
    }
    S.projectId = null; await loadProjects(); await loadProjectData(); render();
  } catch (e) { toast(e.message); }
}

document.addEventListener("change", async (ev) => {
  const t = ev.target;
  if (t.id === "restore-file" && t.files[0]) { await restoreBackup(t.files[0]); t.value = ""; return; }
  if (t.dataset.control === "filter" || t.dataset.control === "sort") {
    S[t.dataset.control] = t.value;
    await loadProjectData();
    return renderMain();
  }
  if (t.dataset.control === "plan") { S.planId = Number(t.value); render(); return pollPlan(); }
  if (t.dataset.field) S.edits[t.dataset.field] = t.type === "checkbox" ? t.checked : t.value === "" ? null : t.value;
});

document.addEventListener("input", (ev) => {
  if (ev.target.dataset.field && ev.target.type !== "checkbox") S.edits[ev.target.dataset.field] = ev.target.value === "" ? null : ev.target.value;
  const form = ev.target.closest("#new-form");
  if (form) estimate(form);
});

function estimate(form) {
  const v = Object.fromEntries(new FormData(form));
  const kws = (v.keywords || "").split("\n").filter((k) => k.trim()).length;
  // Reel-search pages plus one account search per keyword; each surfaces roughly 5-7 new creators.
  const searches = kws * (Number(v.search_pages || 1) + 1);
  const creators = Math.min(Number(v.max_creators || 30), searches * 6);
  const est = searches + creators * (1 + Number(v.reel_pages || 2)) + handles(v.study_accounts).length * 9;
  $("#estimate").textContent = kws ? `About ${est} credits (cap ${v.credit_budget}) · roughly ${Math.ceil((searches * 12 + creators * 6) / 60)} min` : "Add keywords to see a credit estimate";
}

const handles = (text) => [...new Set(String(text || "").split(/[\s,]+/).map((h) => h.replace(/^@/, "").trim().toLowerCase()).filter(Boolean))];
const NUMERIC = ["min_ratio", "min_followers", "max_followers", "search_pages", "reel_pages", "max_creators", "credit_budget", "max_age_days"];
document.addEventListener("submit", async (ev) => {
  const form = ev.target;
  ev.preventDefault();
  try {
    if (form.id === "new-form") {
      const v = Object.fromEntries(new FormData(form));
      const settings = { ...Object.fromEntries(NUMERIC.map((k) => [k, Number(v[k])])), study_accounts: handles(v.study_accounts) };
      const p = await api("/api/projects", { method: "POST", body: { name: v.name, niche: v.niche, keywords: v.keywords.split("\n"), settings } });
      await loadProjects();
      S.tab = "outliers";
      await selectProject(p.id);
      if (v.start) await startRun();
    } else if (form.id === "settings-form") {
      const v = Object.fromEntries(new FormData(form));
      const settings = { ...Object.fromEntries(NUMERIC.map((k) => [k, Number(v[k])])), ai_model: v.ai_model,
        ai_annotation: form.ai_annotation.checked, account_search: form.account_search.checked, allow_long_transcription: form.allow_long_transcription.checked,
        study_accounts: handles(v.study_accounts) };
      await api(`/api/projects/${S.projectId}`, { method: "PATCH", body: { name: v.name, niche: v.niche, keywords: v.keywords.split("\n"), settings } });
      await loadProjects();
      toast("Project saved");
      render();
    } else if (form.id === "plan-form") {
      const v = Object.fromEntries(new FormData(form));
      const res = await api(`/api/projects/${S.projectId}/plans`, { method: "POST", body: {
        about: v.about, followers: v.followers === "" ? null : Number(v.followers), start_date: v.start_date || null, posts: Number(v.posts) } });
      S.plans = await api(`/api/projects/${S.projectId}/plans`);
      S.planId = res.plan_id; S.planForm = false;
      render(); pollPlan();
    } else if (form.matches(".edit-form")) {
      await saveSection();
    }
  } catch (e) { toast(e.message); }
});

document.addEventListener("keydown", (ev) => {
  if (ev.key !== "Escape") return;
  const lb = $(".lightbox");
  if (lb) return lb.remove();
  if (S.editing) { S.editing = null; S.edits = {}; return renderMain(); }
  if (S.open) { S.open = null; render(); }
});

// ---------- boot ----------
(async function init() {
  document.querySelectorAll(".rail-btn").forEach((b) => {
    const icon = { home: ICON.home, research: ICON.search, activity: ICON.bell, bank: ICON.doc, settings: ICON.gear }[b.dataset.view];
    b.insertAdjacentHTML("afterbegin", b.classList.contains("avatar") ? ICON.user : icon);
  });
  [S.vocab] = await Promise.all([api("/api/vocab"), loadProjects()]);
  VOCAB_KEYS = new Set(Object.keys(S.vocab.vocab));
  await loadProjectData();
  S.events = await api("/api/events?limit=60").catch(() => []);
  S.seenEvents = S.events[0]?.id || 0;
  render();
  loadStatus(false);
  pollRun(); pollPlan();
})();
