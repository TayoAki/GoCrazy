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
const ago = (iso) => {
  if (!iso) return "—";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return Math.floor(s / 60) + " min ago";
  if (s < 86400) return Math.floor(s / 3600) + " h ago";
  if (s < 86400 * 60) return Math.floor(s / 86400) + " d ago";
  return new Date(iso).toLocaleDateString();
};
const label = (v) => (v === null || v === undefined || v === "" ? "—" : String(v).replace(/_/g, " "));
const hue = (s) => [...String(s)].reduce((h, c) => (h * 31 + c.charCodeAt(0)) % 360, 7);

async function api(path, opts = {}) {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), 3500);
}

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
  cut: I('<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12"/>'),
  download: I('<path d="M12 4v12m0 0-5-5m5 5 5-5M4 20h16"/>'),
  refresh: I('<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>'),
};

// ---------- state ----------
const S = {
  view: "research", tab: "outliers", projects: [], projectId: null, outliers: [], creators: [], patterns: null,
  runs: [], selected: null, teardown: null, edits: {}, status: {}, vocab: null, sort: "ratio", filter: "active",
  events: [], seenEvents: 0,
};
const project = () => S.projects.find((p) => p.id === S.projectId);
const activeRun = () => (S.runs[0] && S.runs[0].status === "running" ? S.runs[0] : null);

// ---------- data ----------
async function loadProjects() {
  S.projects = await api("/api/projects");
  if (!S.projects.find((p) => p.id === S.projectId)) S.projectId = S.projects[0]?.id ?? null;
}

async function loadProjectData() {
  if (!S.projectId) { S.outliers = []; S.creators = []; S.patterns = null; S.runs = []; return; }
  const id = S.projectId;
  const [outliers, creators, patterns, runs] = await Promise.all([
    api(`/api/projects/${id}/outliers?status=${S.filter}&sort=${S.sort}`),
    api(`/api/projects/${id}/creators`),
    api(`/api/projects/${id}/patterns`),
    api(`/api/projects/${id}/runs`),
  ]);
  if (id !== S.projectId) return;
  Object.assign(S, { outliers, creators, patterns, runs });
}

async function loadStatus(refresh = false) {
  try { S.status = await api("/api/status" + (refresh ? "?refresh=true" : "")); } catch { /* keep last */ }
  renderBottom();
}

async function selectOutlier(shortcode) {
  S.selected = shortcode;
  S.edits = {};
  S.teardown = { status: "loading" };
  $("#right").classList.remove("closed");
  render();
  S.teardown = await api(`/api/teardowns/${shortcode}`);
  if (S.selected === shortcode) { renderRight(); pollTeardown(); }
}

// ---------- polling ----------
function pollRun() {
  clearTimeout(pollRun.timer);
  const run = activeRun();
  if (!run) return;
  pollRun.timer = setTimeout(async () => {
    try {
      const fresh = await api(`/api/runs/${run.id}`);
      S.runs[0] = fresh;
      if (fresh.status !== "running") {
        await Promise.all([loadProjects(), loadProjectData(), loadStatus(true)]);
        toast(fresh.message || "Research run finished");
        render();
        return;
      }
      // Refresh the grid every few ticks so outliers appear while the run is still going.
      pollRun.ticks = (pollRun.ticks || 0) + 1;
      if (pollRun.ticks % 4 === 0) await loadProjectData();
      renderMain(); renderBottom();
    } catch { /* retry next tick */ }
    pollRun();
  }, 2000);
}

function pollTeardown() {
  clearTimeout(pollTeardown.timer);
  if (!S.teardown || S.teardown.status !== "running") return;
  const sc = S.selected;
  pollTeardown.timer = setTimeout(async () => {
    const td = await api(`/api/teardowns/${sc}`).catch(() => null);
    if (td && S.selected === sc) {
      S.teardown = td;
      if (td.status !== "running") {
        await loadProjectData();
        toast(td.status === "done" ? "Teardown ready" : "Teardown failed: " + td.error);
        render();
        return;
      }
    }
    pollTeardown();
  }, 2500);
}

setInterval(async () => {
  S.events = await api("/api/events?limit=60").catch(() => S.events);
  $("#activity-dot").hidden = !(S.events.length && S.events[0].id > S.seenEvents) || S.view === "activity";
}, 15000);
setInterval(() => loadStatus(false), 60000);

// ---------- actions ----------
async function setView(view) {
  S.view = view;
  if (view === "activity") {
    S.events = await api("/api/events?limit=60").catch(() => []);
    S.seenEvents = S.events[0]?.id || 0;
    $("#activity-dot").hidden = true;
  }
  render();
}

async function selectProject(id) {
  S.projectId = id;
  S.selected = null; S.teardown = null; S.edits = {};
  if (S.view !== "settings" && S.view !== "bank") S.view = "research";
  await loadProjectData();
  render();
  pollRun();
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
  await api(`/api/projects/${S.projectId}/outliers/${shortcode}`, { method: "PATCH", body: { status } });
  const o = S.outliers.find((x) => x.shortcode === shortcode);
  if (o) o.status = status;
  if (status === "dismissed" && S.filter === "active") {
    S.outliers = S.outliers.filter((x) => x.shortcode !== shortcode);
    S.selected = null; S.teardown = null;
  }
  await loadProjects();
  toast(status === "saved" ? "Saved to bank" : status === "dismissed" ? "Dismissed" : "Unsaved");
  render();
}

async function startTeardown(shortcode) {
  try {
    await api(`/api/teardowns/${shortcode}?project_id=${S.projectId}`, { method: "POST" });
    S.teardown = { status: "running" };
    renderRight(); pollTeardown();
  } catch (e) { toast(e.message); }
}

async function startAi(shortcode) {
  try {
    await api(`/api/teardowns/${shortcode}/ai?project_id=${S.projectId}`, { method: "POST" });
    S.teardown = { ...S.teardown, status: "running", aiOnly: true };
    renderRight(); pollTeardown();
  } catch (e) { toast(e.message); }
}

async function saveEdits() {
  try {
    const data = await api(`/api/teardowns/${S.selected}`, { method: "PUT", body: { fields: S.edits } });
    S.teardown.data = data;
    S.edits = {};
    toast("Teardown saved");
    await loadProjectData();
    render();
  } catch (e) { toast(e.message); }
}

// ---------- render: shell ----------
function render() {
  document.querySelectorAll(".rail-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === S.view && !b.classList.contains("avatar")));
  renderSidebar(); renderMain(); renderRight(); renderBottom();
}

function renderSidebar() {
  const items = S.projects.map((p) => `
    <button class="proj ${p.id === S.projectId ? "active" : ""}" data-project="${p.id}">
      <span class="circle" style="background:hsl(${hue(p.name)} 55% 48%)">${esc(p.name.trim()[0]?.toUpperCase() || "?")}</span>
      <span class="meta"><div class="t">${esc(p.name)}</div>
      <div class="s">${p.outliers} outliers · ${p.keywords.length} keyword${p.keywords.length === 1 ? "" : "s"}${p.last_run?.status === "running" ? " · running" : ""}</div></span>
    </button>`).join("");
  const p = project();
  $("#sidebar").innerHTML = `
    <button class="new-btn" data-action="new">New research ${ICON.chev.replace("<svg", '<svg width="16" height="16"')}</button>
    <div class="side-label">Projects</div>
    ${items || `<div class="empty-side">No projects yet. Start one with “New research”.</div>`}
    ${p ? `<div class="side-label">Keywords</div><div class="kw-list">${p.keywords.map((k) => `<span class="chip">${esc(k)}</span>`).join("")}</div>` : ""}`;
}

function renderBottom() {
  const st = S.status;
  const run = activeRun();
  const credits = st.credits !== null && st.credits !== undefined ? `${Number(st.credits).toLocaleString()} credits` : st.credits_error ? "balance unavailable" : "…";
  $("#bottombar").innerHTML = `
    <div class="grp">
      <span><span class="sd ${st.scrapecreators ? "on" : "off"}"></span>ScrapeCreators ${st.scrapecreators ? "· " + credits : "· key missing"}</span>
      <span><span class="sd ${st.openrouter ? "on" : ""}"></span>OpenRouter ${st.openrouter ? "· " + esc((project()?.settings.ai_model || S.vocab?.defaults.ai_model || "").split("/").pop()) : "not set (AI annotation off)"}</span>
      <span><span class="sd ${st.ffmpeg ? "on" : "off"}"></span>ffmpeg ${st.ffmpeg ? "ready" : "missing"}</span>
    </div>
    <div class="grp">${run ? `<span><span class="sd busy"></span>Run #${run.id} · ${esc(run.message || "")} · ${run.credits_used} credits</span>` :
      S.runs[0] ? `<span>Last run ${ago(S.runs[0].finished_at || S.runs[0].started_at)}</span>` : "<span>Idle</span>"}</div>`;
}

// ---------- render: main ----------
function renderMain() {
  const main = $("#main");
  if (S.view === "home") return (main.innerHTML = homeView());
  if (S.view === "activity") return (main.innerHTML = activityView());
  if (S.view === "settings") return (main.innerHTML = settingsView());
  if (S.view === "bank") return (main.innerHTML = bankView());
  const p = project();
  if (!p) {
    main.innerHTML = `<div class="content plain"><div class="empty-main">${ICON.search.replace("<svg", '<svg width="48" height="48"')}
      <h1>Find outliers in a niche</h1><p>Create a research project with a few keywords. The app searches Instagram reels,
      checks each creator's follower count and recent reels, and keeps the ones with 5× or more views than followers.</p>
      <button class="btn primary" data-action="new">${ICON.play} New research</button></div></div>`;
    return;
  }
  const tabs = [["outliers", "Outliers", p.outliers - p.dismissed], ["creators", "Creators", S.creators.length],
    ["teardowns", "Teardowns", S.outliers.filter((o) => o.teardown_status === "done").length]];
  const body = S.tab === "creators" ? creatorsTab() : S.tab === "teardowns" ? teardownsTab() : outliersTab(p);
  main.innerHTML = `<div class="tabs" role="tablist">${tabs.map(([k, l, n]) =>
    `<button class="tab ${S.tab === k ? "active" : ""}" role="tab" data-tab="${k}">${l}<span class="n">${n}</span></button>`).join("")}</div>
    <div class="content">${body}</div>`;
}

function projectHeader(p) {
  const s = p.settings;
  return `<h1>${esc(p.name)}</h1>
    <p class="sub">${p.niche ? esc(p.niche) + " · " : ""}Outlier = ${s.min_ratio}× views vs followers · creators ${fmt(s.min_followers)}–${fmt(s.max_followers)} followers · posted within ${s.max_age_days} days</p>`;
}

function outliersTab(p) {
  const run = activeRun();
  const cards = S.outliers.map((o) => `
    <article class="card ${S.selected === o.shortcode ? "selected" : ""}" data-select="${esc(o.shortcode)}">
      <div class="thumb">${o.cover ? `<img src="${esc(o.cover)}" alt="" loading="lazy">` : `<div class="ph">${ICON.image}</div>`}
        <span class="ratio">${o.ratio}×</span>
        <span class="badge-r">${o.status === "saved" ? `<span class="chip accent">★ saved</span>` : o.teardown_status === "done" ? `<span class="chip good">torn down</span>` : o.teardown_status === "running" ? `<span class="chip warn">tearing down</span>` : ""}</span>
      </div>
      <div class="body">
        <div class="who">@${esc(o.username)}</div>
        <div class="nums">${fmt(o.views)} views · ${fmt(o.followers)} followers · ${ago(o.taken_at)}</div>
        <div class="cap">${esc(o.hook || (o.caption || "").split("\n")[0] || "No caption")}</div>
        ${o.tags?.length ? `<div class="tags">${o.tags.map((t) => `<span class="chip info">${esc(label(t))}</span>`).join("")}</div>` : ""}
      </div>
    </article>`).join("");
  const last = S.runs[0];
  const runCard = `
    <div class="runcard">
      <div class="icon">${run ? `<span class="spinner"></span>` : ICON.search}</div>
      <div class="txt">
        <div class="t">${run ? `Researching… ${esc(run.phase || "")}` : last ? `Last run ${ago(last.finished_at || last.started_at)} · ${esc(last.status)}` : "No research yet"}</div>
        <div class="s">${run ? esc(run.message || "") + ` · ${run.credits_used} credits used` : last ? esc(last.message || "") : `Searches ${p.keywords.length} keyword${p.keywords.length === 1 ? "" : "s"} and scans up to ${p.settings.max_creators} creators. Hard cap: ${p.settings.credit_budget} credits.`}</div>
        ${run ? `<div class="progress"><div style="width:${Math.round((run.progress || 0) * 100)}%"></div></div>` : ""}
      </div>
      ${run ? `<button class="btn" data-action="stop">${ICON.stop} Stop</button>` : `<button class="btn primary" data-action="run">${ICON.play} ${last ? "Run again" : "Run research"}</button>`}
    </div>`;
  return `${projectHeader(p)}
    <div class="toolbar">
      <select data-control="filter" aria-label="Show">${[["active", "Active"], ["saved", "Saved"], ["dismissed", "Dismissed"], ["all", "All"]].map(([v, l]) => `<option value="${v}" ${S.filter === v ? "selected" : ""}>${l}</option>`).join("")}</select>
      <select data-control="sort" aria-label="Sort">${[["ratio", "Highest ratio"], ["views", "Most views"], ["newest", "Newest"]].map(([v, l]) => `<option value="${v}" ${S.sort === v ? "selected" : ""}>${l}</option>`).join("")}</select>
      <span class="spacer"></span><span class="hint">${S.outliers.length} shown</span>
    </div>
    ${S.outliers.length ? `<div class="grid">${cards}</div>` : `<p class="hint">${run ? "Outliers will appear here as creators are scanned." : "No outliers yet. Run research to find them."}</p>`}
    <h2>Patterns across torn-down outliers</h2>
    ${patternsBlock()}
    ${runCard}`;
}

function patternsBlock() {
  const pt = S.patterns;
  if (!pt || !pt.teardowns) return `<p class="hint">Tear down a few outliers (select one, then “Tear down”) and the most common hook patterns, formats, video types and CTAs will show here.</p>`;
  const box = (title, rows) => {
    const max = Math.max(1, ...rows.map((r) => r[1]));
    return `<div class="pbox"><h3>${title}</h3>${rows.length ? rows.map(([k, n]) => `<div class="bar"><span class="lbl">${esc(label(k))}</span><span class="track"><span class="fill" style="display:block;width:${(n / max) * 100}%"></span></span><span>${n}</span></div>`).join("") : `<span class="hint">Nothing yet</span>`}</div>`;
  };
  return `<p class="hint">${pt.teardowns} teardown${pt.teardowns === 1 ? "" : "s"} · ${pt.series} series</p>
    <div class="patterns">${box("Hook patterns", pt.hook_pattern)}${box("Formats", pt.format)}${box("Video types", pt.video_type)}${box("Structure", pt.complexity)}${box("CTA mechanics", pt.cta_mechanic)}${box("Angles", pt.angle)}</div>`;
}

function creatorsTab() {
  if (!S.creators.length) return `<p class="hint">Creators found by keyword search will appear here.</p>`;
  const stCls = { scanned: "good", found: "", too_big: "warn", too_small: "warn", private: "bad", error: "bad" };
  return `<div class="tablewrap"><table><thead><tr><th>Creator</th><th class="num">Followers</th><th class="num">Reels scanned</th><th class="num">Median views</th><th class="num">Outliers</th><th class="num">Best</th><th>Status</th><th>Found via</th></tr></thead><tbody>
    ${S.creators.map((c) => `<tr>
      <td><a href="https://www.instagram.com/${encodeURIComponent(c.username)}/" target="_blank" rel="noopener">@${esc(c.username)}</a>${c.full_name ? `<div class="hint">${esc(c.full_name)}</div>` : ""}</td>
      <td class="num">${fmt(c.followers)}</td><td class="num">${c.reels || "—"}</td><td class="num">${fmt(c.median_views)}</td>
      <td class="num">${c.outliers || "—"}</td><td class="num">${c.best_ratio ? c.best_ratio + "×" : "—"}</td>
      <td><span class="chip ${stCls[c.status] || ""}">${esc(label(c.status))}</span></td>
      <td class="clip">${c.keywords.map(esc).join(", ")}</td></tr>`).join("")}
    </tbody></table></div>`;
}

function teardownsTab() {
  const rows = S.outliers.filter((o) => o.teardown_status === "done");
  if (!rows.length) return `<p class="hint">No teardowns yet. Select an outlier and press “Tear down”.</p>`;
  return `<div class="tablewrap"><table><thead><tr><th></th><th>Creator</th><th class="num">Ratio</th><th>Verbal hook</th><th>Tags</th><th>Status</th></tr></thead><tbody>
    ${rows.map((o) => `<tr class="click" data-select="${esc(o.shortcode)}">
      <td>${o.cover ? `<img class="mini" src="${esc(o.cover)}" alt="">` : `<div class="mini"></div>`}</td>
      <td>@${esc(o.username)}</td><td class="num">${o.ratio}×</td>
      <td class="clip" title="${esc(o.hook || "")}">${esc(o.hook || "—")}</td>
      <td>${(o.tags || []).map((t) => `<span class="chip info">${esc(label(t))}</span>`).join(" ")}</td>
      <td>${o.status === "saved" ? `<span class="chip accent">★ saved</span>` : ""}</td></tr>`).join("")}
    </tbody></table></div>`;
}

function homeView() {
  const total = S.projects.reduce((a, p) => a + p.outliers, 0);
  const saved = S.projects.reduce((a, p) => a + p.saved, 0);
  return `<div class="content plain"><h1>Home</h1><p class="sub">${S.projects.length} projects · ${total} outliers found · ${saved} saved to the bank</p>
    <div class="cards2">${S.projects.map((p) => `<div class="pcard" data-project="${p.id}">
      <div class="t">${esc(p.name)}</div><div class="hint">${p.keywords.map(esc).join(" · ")}</div>
      <div class="stat-row"><div class="stat"><div class="n">${p.outliers}</div><div class="l">Outliers</div></div>
      <div class="stat"><div class="n">${p.saved}</div><div class="l">Saved</div></div>
      <div class="stat"><div class="n">${p.last_run ? p.last_run.credits_used : 0}</div><div class="l">Credits last run</div></div></div>
      <div class="hint" style="margin-top:8px">${p.last_run ? "Last run " + ago(p.last_run.finished_at || p.last_run.started_at) : "Never run"}</div></div>`).join("") ||
      `<div class="empty-main"><button class="btn primary" data-action="new">${ICON.play} New research</button></div>`}</div></div>`;
}

function activityView() {
  return `<div class="content plain"><h1>Activity</h1><p class="sub">Research runs, teardowns and errors.</p>
    ${S.events.length ? S.events.map((e) => `<div class="event"><span class="lvl ${esc(e.level)}"></span><span class="when">${ago(e.created_at)}</span>
      <span>${e.project ? `<b>${esc(e.project)}</b> · ` : ""}${esc(e.message)}</span></div>`).join("") : `<p class="hint">Nothing yet.</p>`}</div>`;
}

function bankView() {
  const p = project();
  if (!p) return `<div class="content plain"><p class="hint">No project selected.</p></div>`;
  return `<div class="content plain"><h1>Bank · ${esc(p.name)}</h1>
    <p class="sub">Outliers you saved. Export them, with their teardowns, as JSON for the templatizing step (playbook Phase 4).</p>
    <div class="toolbar"><a class="btn primary" href="/api/projects/${p.id}/export" download="${esc(p.name)}-outliers.json">${ICON.download} Export saved (${p.saved})</a>
    <button class="btn" data-action="show-saved">Show saved in Research</button></div>
    <p class="hint">Tip: tear down every saved outlier and fill in the fields marked “needs review” before exporting.</p></div>`;
}

function settingsView() {
  const st = S.status;
  const p = project();
  const s = p ? p.settings : S.vocab?.defaults || {};
  const num = (k, lbl, step = 1, help = "") => `<label class="fld">${lbl}<input type="number" step="${step}" name="${k}" value="${esc(s[k])}">${help ? `<span class="help">${help}</span>` : ""}</label>`;
  return `<div class="content plain"><h1>Settings</h1>
    <h2>Connections</h2>
    <div class="box"><div class="kv">
      <div><span class="k">ScrapeCreators</span><span class="v">${st.scrapecreators ? "Connected" : "Key missing"}</span></div>
      <div><span class="k">Credits</span><span class="v">${st.credits != null ? Number(st.credits).toLocaleString() : "—"}</span></div>
      <div><span class="k">OpenRouter</span><span class="v">${st.openrouter ? "Connected" : "Not set"}</span></div>
      <div><span class="k">ffmpeg</span><span class="v">${st.ffmpeg ? "Installed" : "Missing"}</span></div></div></div>
    <p class="hint">Keys are read from environment variables or the repo's <code>.env</code> file (<code>SCRAPECREATORS_API_KEY</code>, <code>OPENROUTER_API_KEY</code>). They are never shown or sent to the browser.</p>
    <button class="btn" data-action="refresh-balance">${ICON.refresh} Refresh balance</button>
    ${p ? `<h2>Project: ${esc(p.name)}</h2>
    <form id="settings-form" class="mbody" style="padding:0">
      <label class="fld">Name<input type="text" name="name" value="${esc(p.name)}"></label>
      <label class="fld">Keywords<span class="help">One per line</span><textarea name="keywords" rows="4">${esc(p.keywords.join("\n"))}</textarea></label>
      <div class="row3">${num("min_ratio", "Min ratio", 0.5)}${num("min_followers", "Min followers")}${num("max_followers", "Max followers")}</div>
      <div class="row3">${num("search_pages", "Search pages / keyword")}${num("reel_pages", "Reel pages / creator")}${num("max_creators", "Max creators")}</div>
      <div class="row3">${num("credit_budget", "Credit budget / run")}${num("max_age_days", "Max age (days)")}<div></div></div>
      <label class="fld">AI model (OpenRouter id)<input type="text" name="ai_model" value="${esc(s.ai_model)}"><span class="help">Must read images. Default: anthropic/claude-sonnet-5.5</span></label>
      <label class="check"><input type="checkbox" name="ai_annotation" ${s.ai_annotation ? "checked" : ""}> Run AI analysis at the end of every teardown</label>
      <label class="check"><input type="checkbox" name="account_search" ${s.account_search ? "checked" : ""}> Also search Instagram accounts for each keyword (1 credit each)</label>
      <label class="check"><input type="checkbox" name="allow_long_transcription" ${s.allow_long_transcription ? "checked" : ""}> Transcribe reels over 2 minutes (10 credits per started minute)</label>
      <div class="actions"><button class="btn primary" type="submit">Save project</button><button class="btn" type="button" data-action="delete-project">Delete project</button></div>
    </form>` : ""}</div>`;
}

// ---------- render: right panel ----------
const FIELD_LABELS = {
  post_type: "Post type", topic: "Topic", verbal_hook: "Heard (0–3 s)", written_hook: "On screen", visual_hook: "What happens",
  hook_pattern: "Pattern", angle: "Angle", video_type: "Video type", delivery: "Delivery", story_type: "Story type",
  is_series: "Is a series", series_type: "Series type", episode_marker: "Marker", series_evidence: "Episodes",
  content_type: "Content type", funnel: "Funnel", complexity: "Complexity", structure_pattern: "Beats",
  word_count: "Words", words_per_second: "Words / sec", value_summary: "Takeaway", cta_type: "CTA type",
  cta_mechanic: "Mechanic", cta_keyword: "Keyword", cta_text: "CTA words", format: "Format", audio: "Audio",
  avg_shot_s: "Avg shot (s)", cuts: "Hard cuts", captions: "Captions",
};
const TEXTAREA = new Set(["verbal_hook", "visual_hook", "value_summary", "cta_text", "structure_pattern"]);
const READONLY = new Set(["word_count", "words_per_second", "avg_shot_s", "cuts", "series_evidence"]);

function fieldEditor(key, f) {
  const value = key in S.edits ? S.edits[key] : f.value;
  const dirty = key in S.edits;
  const src = dirty ? "human" : f.source;
  const badge = `<span class="src ${esc(src)}">${esc(src === "needs_review" ? "needs review" : src === "ai" ? "ai" : src)}</span>`;
  let input;
  if (READONLY.has(key)) {
    input = key === "series_evidence"
      ? `<div class="ro">${(value || []).length ? value.map((u, i) => `<a href="${esc(u)}" target="_blank" rel="noopener">episode ${i + 1}</a>`).join(" · ") : "—"}</div>`
      : `<div class="ro">${esc(value ?? "—")}</div>`;
  } else if (key === "is_series") {
    input = `<label class="check"><input type="checkbox" data-field="is_series" ${value ? "checked" : ""}> Yes</label>`;
  } else if (S.vocab?.vocab[key]) {
    input = `<select data-field="${key}"><option value="">—</option>${S.vocab.vocab[key].map((v) => `<option value="${v}" ${v === value ? "selected" : ""}>${esc(label(v))}</option>`).join("")}</select>`;
  } else if (TEXTAREA.has(key)) {
    input = `<textarea data-field="${key}" rows="2">${esc(value ?? "")}</textarea>`;
  } else {
    input = `<input type="text" data-field="${key}" value="${esc(value ?? "")}">`;
  }
  return `<div class="f ${dirty ? "dirty" : ""}"><div class="fk">${esc(FIELD_LABELS[key] || key)}</div>
    <div class="fv">${input}<div style="display:flex;gap:6px;align-items:center">${badge}${f.note && !dirty ? `<span class="note">${esc(f.note)}</span>` : ""}</div></div></div>`;
}

function renderRight() {
  const right = $("#right");
  const o = S.outliers.find((x) => x.shortcode === S.selected);
  if (!S.selected || !o) {
    right.innerHTML = `<div class="empty">${ICON.cut}<p>Select an outlier to see its stats and teardown.</p>
      <p class="hint">A teardown pulls the transcript and the video frames and pre-fills the 17-element card from the playbook.</p></div>`;
    right.classList.add("closed");
    return;
  }
  const td = S.teardown || { status: "loading" };
  const data = td.data;
  const stats = data?.fields?.stats?.value;
  let teardownHtml;
  if (td.status === "loading") teardownHtml = `<p class="hint"><span class="spinner"></span> Loading…</p>`;
  else if (td.status === "running") teardownHtml = `<div class="box" style="display:flex;gap:10px;align-items:center"><span class="spinner"></span><div><b>${td.aiOnly ? "Analyzing with AI…" : "Tearing down…"}</b><div class="hint">${td.aiOnly ? "The model is reading the frames and transcript." : "Post details, transcript, video frames, cut count" + (S.status.openrouter ? ", then AI analysis" : "") + ". Usually 30–90 s."}</div></div></div>`;
  else if (td.status === "failed") teardownHtml = `<div class="box"><b>Teardown failed</b><div class="notes">${esc(td.error)}</div><button class="btn small" data-action="teardown">${ICON.refresh} Try again</button></div>`;
  else if (td.status === "none") teardownHtml = `<div class="box"><b>Not torn down yet</b><div class="hint" style="margin:4px 0 10px">About 2 ScrapeCreators credits (post details + transcript). Frames and cuts are free${S.status.openrouter ? "; the AI pass costs a few cents on OpenRouter" : ""}.</div>
    <button class="btn primary" data-action="teardown">${ICON.cut} Tear down</button></div>`;
  else {
    const fields = data.fields;
    const review = Object.values(fields).filter((f) => f.source === "needs_review").length;
    const aiCount = Object.values(fields).filter((f) => f.source === "ai").length;
    const aiInfo = data.ai ? `<div class="aibox"><b>AI analysis</b> · ${esc((data.ai.model || "").split("/").pop())}${data.ai.cost != null ? ` · $${Number(data.ai.cost).toFixed(3)}` : ""} · ${aiCount} field${aiCount === 1 ? "" : "s"} filled, marked <span class="src ai">ai</span>: check them against the frames.${data.ai.notes ? `<div style="margin-top:4px">Reviewer note: ${esc(data.ai.notes)}</div>` : ""}</div>` : "";
    const els = (S.vocab?.elements || []).filter(([n]) => n !== 1).map(([n, lbl, keys]) => `
      <div class="el"><div class="el-h"><span class="num">${n}</span>${esc(lbl)}</div>
      ${keys.filter((k) => fields[k]).map((k) => fieldEditor(k, fields[k])).join("")}</div>`).join("");
    teardownHtml = `
      ${data.media?.hook_frames?.length ? `<div class="caption-txt">First 3 seconds</div><div class="frames">${data.media.hook_frames.map((src) => `<img src="${esc(src)}" alt="" data-zoom="${esc(src)}">`).join("")}</div>` : ""}
      ${data.notes?.length ? data.notes.map((n) => `<div class="notes">${esc(n)}</div>`).join("") : ""}
      <div class="toolbar" style="margin:10px 0 0"><span class="chip ${review ? "bad" : aiCount ? "ai" : "good"}">${review ? `${review} field${review === 1 ? "" : "s"} need review` : aiCount ? `${aiCount} AI field${aiCount === 1 ? "" : "s"} to check` : "All fields reviewed"}</span>
        <span class="spacer"></span>${S.status.openrouter ? `<button class="btn small" data-action="ai" title="Re-run only the AI pass (no ScrapeCreators credits)">✦ ${data.ai ? "Re-analyze" : "Analyze with AI"}</button>` : ""}<button class="btn small ghost" data-action="teardown" title="Re-run everything (keeps your edits)">${ICON.refresh} Re-run</button></div>
      ${aiInfo}
      ${els}
      ${data.transcript ? `<details><summary>Transcript</summary><div class="transcript">${esc(data.transcript.text)}</div></details>` : ""}
      ${data.media?.frames?.length ? `<details><summary>All frames (${data.media.frames.length}, every 2 s)</summary><div class="frames many">${data.media.frames.map((src) => `<img src="${esc(src)}" alt="" loading="lazy" data-zoom="${esc(src)}">`).join("")}</div></details>` : ""}
      ${data.caption ? `<details><summary>Caption</summary><div class="transcript">${esc(data.caption)}</div></details>` : ""}
      ${Object.keys(S.edits).length ? `<div class="savebar"><button class="btn primary" data-action="save-edits">Save ${Object.keys(S.edits).length} change${Object.keys(S.edits).length === 1 ? "" : "s"}</button><button class="btn" data-action="discard-edits">Discard</button></div>` : ""}`;
  }
  right.classList.remove("closed");
  right.innerHTML = `
    <div class="rhead"><div style="flex:1;min-width:0"><div class="who">@${esc(o.username)}</div><div class="full">${esc(o.full_name || "")}</div></div>
      <span class="chip accent" style="font-size:14px;font-weight:700">${o.ratio}×</span>
      <button class="btn small ghost" data-action="close-right" aria-label="Close">${ICON.x}</button></div>
    <div class="rtop"><div class="box"><div class="kv">
      <div><span class="k">Views</span><span class="v">${fmt(stats?.views ?? o.views)}</span></div>
      <div><span class="k">Followers</span><span class="v">${fmt(o.followers)}</span></div>
      <div><span class="k">Likes</span><span class="v">${fmt(o.likes)}</span></div>
      <div><span class="k">Comments</span><span class="v">${fmt(o.comments)}</span></div>
      <div><span class="k">Posted</span><span class="v">${ago(o.taken_at)}</span></div>
      <div><span class="k">Length</span><span class="v">${stats?.duration_s ? Math.round(stats.duration_s) + " s" : o.duration ? Math.round(o.duration) + " s" : "—"}</span></div>
    </div></div>${o.cover ? `<img class="cover" src="${esc(o.cover)}" alt="Cover of the reel" data-zoom="${esc(o.cover)}">` : ""}</div>
    <div class="actions">
      <button class="btn ${o.status === "saved" ? "" : "primary"}" data-action="${o.status === "saved" ? "unsave" : "save"}">${ICON.star} ${o.status === "saved" ? "Saved" : "Save to bank"}</button>
      <button class="btn" data-action="dismiss">${ICON.x} Dismiss</button>
      <a class="btn" href="${esc(o.url)}" target="_blank" rel="noopener">${ICON.ext} Open reel</a>
    </div>
    <div class="caption-txt" style="margin-bottom:10px">Found via “${esc(o.keyword || "")}”</div>
    ${teardownHtml}`;
}

// ---------- modal: new research ----------
function openNewResearch() {
  const d = S.vocab?.defaults || {};
  const m = $("#modal");
  m.innerHTML = `<form method="dialog" id="new-form">
    <div class="mhead">New research</div>
    <div class="mbody">
      <label class="fld">Project name<input type="text" name="name" required placeholder="e.g. Dog training"></label>
      <label class="fld">Niche <span class="help">Optional, for your reference</span><input type="text" name="niche" placeholder="e.g. Puppy training for first-time owners"></label>
      <label class="fld">Keywords <span class="help">One per line: your niche, each sub-niche, your job title, and a variation or two</span>
        <textarea name="keywords" rows="5" required placeholder="dog training&#10;crate training puppy&#10;puppy biting&#10;dog trainer"></textarea></label>
      <details><summary>Advanced</summary>
        <div class="mbody" style="padding:10px 0 0">
          <div class="row3"><label class="fld">Min ratio<input type="number" step="0.5" name="min_ratio" value="${d.min_ratio}"></label>
          <label class="fld">Min followers<input type="number" name="min_followers" value="${d.min_followers}"></label>
          <label class="fld">Max followers<input type="number" name="max_followers" value="${d.max_followers}"></label></div>
          <div class="row3"><label class="fld">Search pages<input type="number" name="search_pages" min="1" max="11" value="${d.search_pages}"></label>
          <label class="fld">Reel pages<input type="number" name="reel_pages" min="1" value="${d.reel_pages}"></label>
          <label class="fld">Max creators<input type="number" name="max_creators" min="1" value="${d.max_creators}"></label></div>
          <div class="row3"><label class="fld">Credit budget<input type="number" name="credit_budget" min="1" value="${d.credit_budget}"></label>
          <label class="fld">Max age (days)<input type="number" name="max_age_days" value="${d.max_age_days}"></label><div></div></div>
        </div></details>
      <label class="check"><input type="checkbox" name="start" checked> Start research right away</label>
    </div>
    <div class="mfoot"><span class="est" id="estimate"></span><button class="btn" value="cancel" formnovalidate>Cancel</button><button class="btn primary" value="create">Create</button></div>
  </form>`;
  const form = $("#new-form");
  const estimate = () => {
    const v = Object.fromEntries(new FormData(form));
    const kws = (v.keywords || "").split("\n").filter((k) => k.trim()).length;
    // Reel-search pages plus one account search per keyword; each surfaces roughly 5-7 new creators.
    const searches = kws * (Number(v.search_pages || 1) + 1);
    const creators = Math.min(Number(v.max_creators || 30), searches * 6);
    const est = searches + creators * (1 + Number(v.reel_pages || 2));
    $("#estimate").textContent = kws ? `≈ ${est} credits (cap ${v.credit_budget}) · ~${Math.ceil((searches * 12 + creators * 6) / 60)} min` : "Add keywords to see a credit estimate";
  };
  form.addEventListener("input", estimate);
  estimate();
  form.addEventListener("submit", async (ev) => {
    if (ev.submitter?.value !== "create") return;
    ev.preventDefault();
    const v = Object.fromEntries(new FormData(form));
    const settings = {};
    for (const k of ["min_ratio", "min_followers", "max_followers", "search_pages", "reel_pages", "max_creators", "credit_budget", "max_age_days"]) settings[k] = Number(v[k]);
    try {
      const p = await api("/api/projects", { method: "POST", body: { name: v.name, niche: v.niche, keywords: v.keywords.split("\n"), settings } });
      m.close();
      await loadProjects();
      S.tab = "outliers";
      await selectProject(p.id);
      if (v.start) await startRun();
    } catch (e) { toast(e.message); }
  });
  m.showModal();
}

// ---------- events ----------
document.addEventListener("click", async (ev) => {
  const zoom = ev.target.closest("[data-zoom]");
  if (zoom) {
    const lb = document.createElement("div");
    lb.className = "lightbox";
    lb.innerHTML = `<img src="${esc(zoom.dataset.zoom)}" alt="">`;
    lb.addEventListener("click", () => lb.remove());
    document.body.appendChild(lb);
    return;
  }
  const el = ev.target.closest("[data-view],[data-project],[data-tab],[data-select],[data-action]");
  if (!el) return;
  if (el.dataset.view) return setView(el.dataset.view);
  if (el.dataset.project) return selectProject(Number(el.dataset.project));
  if (el.dataset.tab) { S.tab = el.dataset.tab; return renderMain(); }
  if (el.dataset.select) return selectOutlier(el.dataset.select);
  const a = el.dataset.action;
  if (a === "new") return openNewResearch();
  if (a === "run") return startRun();
  if (a === "stop") return stopRun();
  if (a === "teardown") return startTeardown(S.selected);
  if (a === "ai") return startAi(S.selected);
  if (a === "save") return setOutlierStatus(S.selected, "saved");
  if (a === "unsave") return setOutlierStatus(S.selected, "new");
  if (a === "dismiss") return setOutlierStatus(S.selected, "dismissed");
  if (a === "save-edits") return saveEdits();
  if (a === "discard-edits") { S.edits = {}; return renderRight(); }
  if (a === "close-right") { S.selected = null; return render(); }
  if (a === "refresh-balance") { await loadStatus(true); toast("Balance refreshed"); return renderMain(); }
  if (a === "show-saved") { S.filter = "saved"; S.view = "research"; S.tab = "outliers"; await loadProjectData(); return render(); }
  if (a === "delete-project") {
    if (!confirm("Delete this project and its outliers? Teardowns are kept.")) return;
    await api(`/api/projects/${S.projectId}`, { method: "DELETE" });
    S.projectId = null; await loadProjects(); await loadProjectData(); S.view = "research"; return render();
  }
});

document.addEventListener("change", async (ev) => {
  const t = ev.target;
  if (t.dataset.control === "filter" || t.dataset.control === "sort") {
    S[t.dataset.control] = t.value;
    await loadProjectData();
    return renderMain();
  }
  if (t.dataset.field) {
    const key = t.dataset.field;
    const value = t.type === "checkbox" ? t.checked : t.value === "" ? null : t.value;
    const original = S.teardown?.data?.fields?.[key]?.value ?? null;
    if (value === original) delete S.edits[key];
    else S.edits[key] = value;
    renderRight();
  }
});

document.addEventListener("submit", async (ev) => {
  if (ev.target.id !== "settings-form") return;
  ev.preventDefault();
  const v = Object.fromEntries(new FormData(ev.target));
  const settings = { allow_long_transcription: ev.target.allow_long_transcription.checked, account_search: ev.target.account_search.checked, ai_annotation: ev.target.ai_annotation.checked, ai_model: v.ai_model };
  for (const k of ["min_ratio", "min_followers", "max_followers", "search_pages", "reel_pages", "max_creators", "credit_budget", "max_age_days"]) settings[k] = Number(v[k]);
  try {
    await api(`/api/projects/${S.projectId}`, { method: "PATCH", body: { name: v.name, keywords: v.keywords.split("\n"), settings } });
    await loadProjects();
    toast("Project saved");
    render();
  } catch (e) { toast(e.message); }
});

document.addEventListener("keydown", (ev) => {
  if (ev.key === "Escape" && S.selected && !$("#modal").open) { S.selected = null; render(); }
});

// ---------- boot ----------
(async function init() {
  document.querySelectorAll(".rail-btn").forEach((b) => {
    const icon = { home: ICON.home, research: ICON.search, activity: ICON.bell, bank: ICON.doc, settings: ICON.gear }[b.dataset.view];
    b.insertAdjacentHTML("afterbegin", b.classList.contains("avatar") ? ICON.user : icon);
  });
  [S.vocab] = await Promise.all([api("/api/vocab"), loadProjects()]);
  await loadProjectData();
  S.events = await api("/api/events?limit=60").catch(() => []);
  S.seenEvents = S.events[0]?.id || 0;
  render();
  loadStatus(false);
  pollRun();
})();
