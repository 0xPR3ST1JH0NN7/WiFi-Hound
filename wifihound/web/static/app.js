/* WiFi-Hound frontend — Cytoscape graph + interaction. */
"use strict";

const API = {
  async import(file) {
    const fd = new FormData();
    fd.append("file", file);
    return fetchJSON("/api/import", { method: "POST", body: fd });
  },
  graph: () => fetchJSON("/api/graph"),
  node: (id) => fetchJSON(`/api/node/${encodeURIComponent(id)}`),
  search: (q) => fetchJSON(`/api/search?q=${encodeURIComponent(q)}`),
  config: () => fetchJSON("/api/config"),
  enrich: () => fetchJSON("/api/enrich/oui", { method: "POST" }),
  deauth: (payload) =>
    fetchJSON("/api/operations/deauth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
};

async function fetchJSON(url, opts) {
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `${res.status} ${res.statusText}`);
  return data;
}

/* --------------------------------------------------------------- Cytoscape */
const cy = cytoscape({
  container: document.getElementById("cy"),
  wheelSensitivity: 0.25,
  minZoom: 0.1,
  maxZoom: 4,
  style: [
    {
      selector: "node",
      style: {
        label: "data(label)",
        color: "#cfe3ea",
        "font-size": 10,
        "text-valign": "bottom",
        "text-margin-y": 4,
        "text-wrap": "ellipsis",
        "text-max-width": 120,
        "border-width": 2,
        "border-color": "#0a1016",
        width: 26,
        height: 26,
      },
    },
    {
      selector: 'node[kind = "ap"]',
      style: {
        "background-color": "#ff5d6c",
        width: "mapData(degree, 0, 12, 34, 64)",
        height: "mapData(degree, 0, 12, 34, 64)",
        "font-size": 12,
        "font-weight": "bold",
      },
    },
    { selector: 'node[kind = "client"]', style: { "background-color": "#4da6ff" } },
    {
      selector: 'node[kind = "client"][?unassociated]',
      style: { "background-color": "#8a93a8" },
    },
    {
      selector: "edge",
      style: {
        width: 2,
        "line-color": "#2d4654",
        "curve-style": "bezier",
        "target-arrow-shape": "none",
      },
    },
    {
      selector: ".faded",
      style: { opacity: 0.12, "text-opacity": 0.05, events: "no" },
    },
    {
      selector: ".highlight",
      style: { "border-color": "#34d399", "border-width": 4, "line-color": "#34d399" },
    },
    { selector: ".hidden-node", style: { display: "none" } },
    {
      selector: "node:selected",
      style: { "border-color": "#22d3ee", "border-width": 4 },
    },
  ],
});

let OFFENSIVE = false;
let currentLayout = "fcose";

function runLayout(name) {
  currentLayout = name || currentLayout;
  const opts =
    currentLayout === "fcose"
      ? { name: "fcose", animate: true, animationDuration: 600, nodeRepulsion: 8000,
          idealEdgeLength: 90, padding: 40 }
      : currentLayout === "concentric"
      ? { name: "concentric", concentric: (n) => n.degree(), levelWidth: () => 2, padding: 40 }
      : currentLayout === "breadthfirst"
      ? { name: "breadthfirst", directed: false, spacingFactor: 1.3, padding: 40 }
      : { name: currentLayout, padding: 40 };
  cy.layout(opts).run();
}

/* ----------------------------------------------------------------- render */
function renderGraph(payload) {
  const nodes = payload.elements.nodes.map((n) => {
    if (n.data.kind === "client") {
      n.data.unassociated = !payload.elements.edges.some(
        (e) => e.data.source === n.data.id || e.data.target === n.data.id
      );
    }
    return n;
  });
  cy.elements().remove();
  cy.add(nodes);
  cy.add(payload.elements.edges);
  runLayout();
  applyFilters();
  cy.fit(undefined, 50);
  document.getElementById("empty-state").classList.toggle("hidden", cy.nodes().length > 0);
  if (payload.summary) updateStats(payload.summary);
  populateFilterOptions();
}

function updateStats(s) {
  document.getElementById("stat-aps").textContent = s.access_points ?? 0;
  document.getElementById("stat-clients").textContent = s.clients ?? 0;
  document.getElementById("stat-assoc").textContent = s.associated_clients ?? 0;
  document.getElementById("stat-hidden").textContent = s.hidden_aps ?? 0;
}

function populateFilterOptions() {
  const encs = new Set();
  const chans = new Set();
  cy.nodes('[kind = "ap"]').forEach((n) => {
    if (n.data("privacy")) encs.add(n.data("privacy"));
    if (n.data("channel")) chans.add(n.data("channel"));
  });
  fillSelect("filter-enc", [...encs].sort());
  fillSelect(
    "filter-chan",
    [...chans].sort((a, b) => Number(a) - Number(b))
  );
}

function fillSelect(id, values) {
  const sel = document.getElementById(id);
  const current = sel.value;
  sel.innerHTML = '<option value="">all</option>';
  values.forEach((v) => {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = v;
    sel.appendChild(o);
  });
  sel.value = current;
}

/* ----------------------------------------------------------------- filters */
function applyFilters() {
  const showAps = document.getElementById("filter-aps").checked;
  const showClients = document.getElementById("filter-clients").checked;
  const showUnassoc = document.getElementById("filter-unassoc").checked;
  const enc = document.getElementById("filter-enc").value;
  const chan = document.getElementById("filter-chan").value;

  cy.batch(() => {
    cy.nodes().forEach((n) => {
      const kind = n.data("kind");
      let show = true;
      if (kind === "ap") {
        if (!showAps) show = false;
        if (enc && n.data("privacy") !== enc) show = false;
        if (chan && String(n.data("channel")) !== chan) show = false;
      } else {
        if (!showClients) show = false;
        if (!showUnassoc && n.data("unassociated")) show = false;
      }
      n.toggleClass("hidden-node", !show);
    });
  });
}

/* ----------------------------------------------------------------- details */
function showDetails(info) {
  const body = document.getElementById("details-body");
  const isAp = info.kind === "ap";
  const rows = [];
  const row = (k, v) =>
    v !== null && v !== undefined && v !== ""
      ? rows.push(`<div class="detail-row"><span class="k">${k}</span><span class="v">${escapeHtml(v)}</span></div>`)
      : null;

  if (isAp) {
    row("ESSID", info.essid);
    row("BSSID", info.id);
    row("Channel", info.channel);
    row("Encryption", info.privacy);
    row("Cipher", info.cipher);
    row("Auth", info.authentication);
    row("Signal", info.power != null ? `${info.power} dBm` : null);
    row("Beacons", info.beacons);
    row("Data", info.data);
    row("Vendor", info.vendor);
    row("Clients", info.degree);
    row("First seen", info.first_seen);
    row("Last seen", info.last_seen);
  } else {
    row("MAC", info.id);
    row("Vendor", info.vendor);
    row("Associated to", info.associated_bssid);
    row("Signal", info.power != null ? `${info.power} dBm` : null);
    row("Packets", info.packets);
    row("First seen", info.first_seen);
    row("Last seen", info.last_seen);
  }

  let probes = "";
  if (info.probed_essids && info.probed_essids.length) {
    probes =
      `<h4>Probed ESSIDs</h4><ul class="probe-list">` +
      info.probed_essids.map((p) => `<li>${escapeHtml(p)}</li>`).join("") +
      `</ul>`;
  }

  const title = isAp ? info.essid || "&lt;Hidden&gt;" : info.id;
  const offBtn =
    OFFENSIVE && isAp
      ? `<button class="btn danger" id="op-deauth-btn">Deauth this AP…</button>`
      : "";

  body.innerHTML = `
    <span class="kind-badge ${info.kind}">${isAp ? "Access Point" : "Client"}</span>
    <h3>${escapeHtml(title)}</h3>
    ${rows.join("")}
    ${probes}
    <div class="actions">
      <button class="btn" id="neighbors-btn">Highlight neighbors</button>
      ${offBtn}
    </div>`;

  document.getElementById("details").classList.remove("hidden");
  document.getElementById("neighbors-btn").onclick = () => highlightNeighbors(info.id);
  const deauthBtn = document.getElementById("op-deauth-btn");
  if (deauthBtn) deauthBtn.onclick = () => openDeauthModal(info);
}

function closeDetails() {
  document.getElementById("details").classList.add("hidden");
}

/* -------------------------------------------------------------- highlight */
function highlightNeighbors(id) {
  const node = cy.getElementById(id);
  if (node.empty()) return;
  const hood = node.closedNeighborhood();
  cy.elements().addClass("faded");
  hood.removeClass("faded").addClass("highlight");
  setTimeout(() => cy.elements().removeClass("highlight"), 1500);
}

function focusNode(id) {
  const node = cy.getElementById(id);
  if (node.empty()) return;
  cy.animate({ center: { eles: node }, zoom: 1.6 }, { duration: 400 });
  node.select();
  node.addClass("highlight");
  setTimeout(() => node.removeClass("highlight"), 1200);
}

/* ----------------------------------------------------------- context menu */
cy.cxtmenu({
  selector: "node",
  menuRadius: 80,
  fillColor: "rgba(16, 28, 39, 0.95)",
  activeFillColor: "rgba(52, 211, 153, 0.85)",
  commands: (ele) => {
    const id = ele.id();
    const isAp = ele.data("kind") === "ap";
    const cmds = [
      { content: "Details", select: () => openNode(id) },
      { content: "Neighbors", select: () => highlightNeighbors(id) },
      { content: "Isolate", select: () => isolate(id) },
      { content: "Copy ID", select: () => copyText(id) },
    ];
    if (OFFENSIVE && isAp) {
      cmds.push({
        content: "Deauth",
        select: () => API.node(id).then(openDeauthModal),
        fillColor: "rgba(255, 93, 108, 0.85)",
      });
    }
    return cmds;
  },
});

function isolate(id) {
  const node = cy.getElementById(id);
  const keep = node.closedNeighborhood();
  cy.batch(() => {
    cy.elements().addClass("faded");
    keep.removeClass("faded");
  });
}

/* ------------------------------------------------------------------ search */
const searchInput = document.getElementById("search-input");
const searchResults = document.getElementById("search-results");
let searchTimer = null;

searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  const q = searchInput.value.trim();
  if (!q) return hideSearch();
  searchTimer = setTimeout(async () => {
    try {
      const { results } = await API.search(q);
      renderSearch(results);
    } catch (e) {
      /* ignore transient search errors */
    }
  }, 180);
});

function renderSearch(results) {
  if (!results.length) return hideSearch();
  searchResults.innerHTML = results
    .slice(0, 30)
    .map(
      (r) =>
        `<li data-id="${escapeHtml(r.id)}"><span>${escapeHtml(r.label)}</span><span class="kind">${r.kind}</span></li>`
    )
    .join("");
  searchResults.classList.remove("hidden");
  searchResults.querySelectorAll("li").forEach((li) => {
    li.onclick = () => {
      const id = li.getAttribute("data-id");
      hideSearch();
      searchInput.value = "";
      focusNode(id);
      openNode(id);
    };
  });
}

function hideSearch() {
  searchResults.classList.add("hidden");
}
document.addEventListener("click", (e) => {
  if (!e.target.closest(".search")) hideSearch();
});

/* ------------------------------------------------------------- operations */
let pendingOp = null;

function openDeauthModal(info) {
  pendingOp = info;
  document.getElementById("op-title").textContent = "Deauthentication";
  document.getElementById("op-body").innerHTML = `
    <p>Target AP <strong>${escapeHtml(info.essid || info.id)}</strong> (${escapeHtml(info.id)})</p>
    <label>Monitor interface</label>
    <input id="op-iface" placeholder="wlan0mon" value="wlan0mon"/>
    <label>Deauth bursts (1–64)</label>
    <input id="op-count" type="number" min="1" max="64" value="5"/>
    <label><input type="checkbox" id="op-dry"/> Dry run (build command only)</label>`;
  document.getElementById("op-modal").classList.remove("hidden");
}

document.getElementById("op-cancel").onclick = () => {
  document.getElementById("op-modal").classList.add("hidden");
  pendingOp = null;
};

document.getElementById("op-confirm").onclick = async () => {
  if (!pendingOp) return;
  const payload = {
    interface: document.getElementById("op-iface").value.trim(),
    bssid: pendingOp.id,
    count: Number(document.getElementById("op-count").value) || 5,
    acknowledged: true,
    dry_run: document.getElementById("op-dry").checked,
  };
  try {
    const res = await API.deauth(payload);
    toast(`Deauth ${res.status}: ${res.command.join(" ")}`, "ok");
  } catch (e) {
    toast(e.message, "error");
  } finally {
    document.getElementById("op-modal").classList.add("hidden");
    pendingOp = null;
  }
};

/* --------------------------------------------------------------- wiring up */
async function openNode(id) {
  try {
    const info = await API.node(id);
    showDetails(info);
  } catch (e) {
    toast(e.message, "error");
  }
}

cy.on("tap", "node", (evt) => openNode(evt.target.id()));
cy.on("tap", (evt) => {
  if (evt.target === cy) cy.elements().removeClass("faded");
});

document.getElementById("file-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    toast("Parsing capture…");
    const payload = await API.import(file);
    renderGraph(payload);
    toast(`Loaded ${payload.summary.access_points} APs / ${payload.summary.clients} clients`, "ok");
  } catch (err) {
    toast(err.message, "error");
  } finally {
    e.target.value = "";
  }
});

document.getElementById("enrich-btn").onclick = async () => {
  try {
    const payload = await API.enrich();
    const summary = (await API.graph()).summary;
    renderGraph({ ...payload, summary });
    toast(`Resolved ${payload.resolved} vendors`, "ok");
  } catch (e) {
    toast(e.message, "error");
  }
};

document.getElementById("reset-btn").onclick = () => {
  cy.elements().removeClass("faded highlight");
  cy.nodes().removeClass("hidden-node");
  document.querySelectorAll(".filter input").forEach((c) => (c.checked = true));
  document.getElementById("filter-enc").value = "";
  document.getElementById("filter-chan").value = "";
  cy.fit(undefined, 50);
};

document.getElementById("details-close").onclick = closeDetails;
document.getElementById("layout-select").onchange = (e) => runLayout(e.target.value);
["filter-aps", "filter-clients", "filter-unassoc", "filter-enc", "filter-chan"].forEach(
  (id) => document.getElementById(id).addEventListener("change", applyFilters)
);

/* ------------------------------------------------------------------ utils */
function copyText(text) {
  navigator.clipboard?.writeText(text).then(
    () => toast("Copied to clipboard", "ok"),
    () => toast(text)
  );
}

let toastTimer = null;
function toast(msg, kind) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = "toast" + (kind ? " " + kind : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), 3500);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}

/* ------------------------------------------------------------------ start */
(async function init() {
  try {
    const cfg = await API.config();
    OFFENSIVE = !!cfg.offensive_enabled;
  } catch (e) {
    /* default OFFENSIVE = false */
  }
  try {
    const payload = await API.graph();
    if (payload.elements.nodes.length) renderGraph(payload);
  } catch (e) {
    /* nothing loaded yet */
  }
})();
