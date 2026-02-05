/* global L */

const ui = {
  app: document.getElementById("app"),

  themeBtn: document.getElementById("btn-theme"),
  locateBtn: document.getElementById("btn-locate"),
  clearBtn: document.getElementById("btn-clear"),
  exportBtn: document.getElementById("btn-export"),

  nearbyBtn: document.getElementById("btn-nearby"),
  searchBtn: document.getElementById("btn-search"),
  towersBtn: document.getElementById("btn-towers"),
  celltowerBtn: document.getElementById("btn-celltower"),

  lat: document.getElementById("lat"),
  lon: document.getElementById("lon"),
  mode: document.getElementById("mode"),
  searchType: document.getElementById("searchType"),
  searchQuery: document.getElementById("searchQuery"),

  filterText: document.getElementById("filterText"),
  chips: [...document.querySelectorAll("[data-chip]")],

  results: document.getElementById("results"),
  statusText: document.getElementById("statusText"),
  providersText: document.getElementById("providersText"),

  savedName: document.getElementById("savedName"),
  savedList: document.getElementById("savedList"),
  saveBtn: document.getElementById("btn-save-location"),

  toast: document.getElementById("toast"),
  toastTitle: document.getElementById("toastTitle"),
  toastBody: document.getElementById("toastBody"),
  toastClose: document.getElementById("toastClose"),

  drawer: document.getElementById("drawer"),
  drawerBackdrop: document.getElementById("drawerBackdrop"),
  drawerTitle: document.getElementById("drawerTitle"),
  drawerJson: document.getElementById("drawerJson"),
  drawerClose: document.getElementById("drawerClose"),
  drawerCopy: document.getElementById("drawerCopy"),
};

const state = {
  lastExport: null,
  devices: [],
  towers: [],
  selected: null,
  filters: {
    text: "",
    types: new Set(),
  },
};

function setStatus(text) {
  ui.statusText.textContent = text;
}

let toastTimer = null;
function showToast(kind, title, body) {
  ui.toast.dataset.kind = kind;
  ui.toastTitle.textContent = title;
  ui.toastBody.textContent = body ?? "";
  ui.toast.classList.add("show");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => ui.toast.classList.remove("show"), 5000);
}

ui.toastClose.addEventListener("click", () => ui.toast.classList.remove("show"));

function safeText(x) {
  if (x === null || x === undefined) return "";
  return String(x);
}

function parseLatLon() {
  const lat = Number.parseFloat(ui.lat.value);
  const lon = Number.parseFloat(ui.lon.value);
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
    throw new Error("Latitude/Longitude must be valid numbers.");
  }
  return { lat, lon };
}

function colorFor(type) {
  const t = (type || "").toLowerCase();
  if (t.includes("cell")) return "#fbbf24";
  if (t.includes("bluetooth")) return "#a78bfa";
  if (t.includes("camera")) return "#fb7185";
  if (t.includes("iot")) return "#34d399";
  if (t.includes("tv")) return "#38bdf8";
  if (t.includes("headphone")) return "#f472b6";
  if (t.includes("car")) return "#22c55e";
  return "#60a5fa";
}

function markerIcon(type) {
  const c = colorFor(type);
  return L.divIcon({
    className: "",
    html: `<div class="marker-dot" style="background:${c}"></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

async function fetchJson(url, params) {
  const qs = new URLSearchParams(params ?? {});
  const full = qs.toString() ? `${url}?${qs}` : url;
  const res = await fetch(full);
  const ct = res.headers.get("content-type") || "";
  const isJson = ct.includes("application/json");
  const data = isJson ? await res.json() : await res.text();
  const reqId = res.headers.get("x-request-id") || "";
  if (!res.ok) {
    const msg =
      (isJson && data && (data.error || data.message)) ||
      (typeof data === "string" ? data.slice(0, 180) : "Request failed");
    const suffix = reqId ? `\n\nRequest ID: ${reqId}` : "";
    throw new Error(`${msg}${suffix}`);
  }
  return { data, reqId };
}

function setBusy(isBusy) {
  const buttons = [ui.nearbyBtn, ui.searchBtn, ui.towersBtn, ui.celltowerBtn];
  for (const b of buttons) b.disabled = isBusy;
}

// Map
const map = L.map("map", { zoomControl: true }).setView([51.505, -0.09], 13);
L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

const cluster = L.markerClusterGroup({ showCoverageOnHover: false, maxClusterRadius: 44 });
cluster.addTo(map);

const towersLayer = L.layerGroup().addTo(map);
const focusLayer = L.layerGroup().addTo(map);

function clearAll() {
  cluster.clearLayers();
  towersLayer.clearLayers();
  focusLayer.clearLayers();
  state.devices = [];
  state.towers = [];
  state.selected = null;
  state.lastExport = null;
  ui.results.innerHTML = "";
  setStatus("Cleared");
}

function addDeviceMarkers(devices) {
  for (const d of devices) {
    const lat = Number(d.lat);
    const lon = Number(d.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    const type = safeText(d.type || "");
    const title =
      safeText(d.ssid) || safeText(d.bssid) || safeText(d.ip) || safeText(d.cell_id) || "Device";

    const m = L.marker([lat, lon], { icon: markerIcon(type) });
    m.on("click", () => openDrawer(title, d));
    const parts = [];
    parts.push(`<b>${title}</b>`);
    if (d.vendor) parts.push(`<div>Vendor: ${safeText(d.vendor)}</div>`);
    if (d.signal !== undefined) parts.push(`<div>Signal: ${safeText(d.signal)}</div>`);
    if (d.timestamp) parts.push(`<div>Time: ${safeText(d.timestamp)}</div>`);
    if (d.info) parts.push(`<div>${safeText(d.info)}</div>`);
    if (type) parts.push(`<div>Type: ${type}</div>`);
    m.bindPopup(parts.join(""));
    cluster.addLayer(m);
  }
}

function addTowerMarkers(towers) {
  for (const t of towers) {
    const lat = Number(t.lat);
    const lon = Number(t.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    const m = L.circleMarker([lat, lon], {
      radius: 6,
      color: "#fbbf24",
      weight: 2,
      fillColor: "#fbbf24",
      fillOpacity: 0.55,
    });
    const id = safeText(t.id || "");
    m.on("click", () => openDrawer(`Tower ${id || ""}`.trim(), t));
    m.bindPopup(`<b>Cell tower</b><div>ID: ${id}</div>`);
    m.addTo(towersLayer);
  }
}

function focusLatLon(lat, lon) {
  focusLayer.clearLayers();
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
  const m = L.circleMarker([lat, lon], {
    radius: 7,
    color: "#60a5fa",
    weight: 2,
    fillColor: "#60a5fa",
    fillOpacity: 0.3,
  });
  m.addTo(focusLayer);
}

map.on("click", (e) => {
  ui.lat.value = e.latlng.lat.toFixed(6);
  ui.lon.value = e.latlng.lng.toFixed(6);
  focusLatLon(e.latlng.lat, e.latlng.lng);
  showToast("ok", "Coordinates set", `${ui.lat.value}, ${ui.lon.value}`);
});

// Drawer
function openDrawer(title, obj) {
  state.selected = obj;
  ui.drawerTitle.textContent = title || "Details";
  ui.drawerJson.textContent = JSON.stringify(obj, null, 2);
  ui.drawer.classList.add("open");
}

function closeDrawer() {
  ui.drawer.classList.remove("open");
}

ui.drawerClose.addEventListener("click", closeDrawer);
ui.drawerBackdrop.addEventListener("click", closeDrawer);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeDrawer();
});

ui.drawerCopy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(ui.drawerJson.textContent || "");
    showToast("ok", "Copied", "JSON copied to clipboard.");
  } catch {
    showToast("warn", "Copy failed", "Clipboard permission denied.");
  }
});

// Filtering
function matchesFilters(item) {
  const t = safeText(item.type || "").toLowerCase();
  if (state.filters.types.size) {
    let ok = false;
    for (const want of state.filters.types) {
      if (t.includes(want)) ok = true;
    }
    if (!ok) return false;
  }

  const q = state.filters.text.trim().toLowerCase();
  if (!q) return true;
  const blob = JSON.stringify(item).toLowerCase();
  return blob.includes(q);
}

function renderResults(items, kind) {
  ui.results.innerHTML = "";
  const filtered = items.filter(matchesFilters);

  if (!filtered.length) {
    ui.results.innerHTML =
      '<div class="item"><div class="k"><span class="tag">Empty</span><b>No results</b></div><div class="hint">Try adjusting filters or changing the query.</div></div>';
    return;
  }

  for (const item of filtered) {
    const lat = Number(item.lat);
    const lon = Number(item.lon);
    const t = safeText(item.type || kind);
    const name = safeText(item.ssid || item.bssid || item.ip || item.id || item.cell_id || "Unknown");
    const vendor = safeText(item.vendor || item.org || item.radio || "");
    const meta =
      safeText(item.timestamp) ||
      safeText(item.lastupdt) ||
      safeText(item.info) ||
      safeText(item.signal ?? "");

    const el = document.createElement("div");
    el.className = "item";
    el.innerHTML = `
      <div class="k">
        <span class="tag">${t || "device"}</span>
        <b>${name}</b>
      </div>
      <div class="hint">${vendor}${vendor && meta ? " • " : ""}${meta}</div>
      <div class="hint">${Number.isFinite(lat) && Number.isFinite(lon) ? `${lat.toFixed(6)}, ${lon.toFixed(6)}` : ""}</div>
    `;
    el.addEventListener("click", () => {
      openDrawer(name, item);
      if (Number.isFinite(lat) && Number.isFinite(lon)) map.setView([lat, lon], Math.max(16, map.getZoom()));
    });
    ui.results.appendChild(el);
  }
}

ui.filterText.addEventListener("input", () => {
  state.filters.text = ui.filterText.value;
  const combined = [...state.devices, ...state.towers];
  renderResults(combined, "result");
});

for (const chip of ui.chips) {
  chip.addEventListener("click", () => {
    const key = chip.dataset.chip;
    const pressed = chip.getAttribute("aria-pressed") === "true";
    chip.setAttribute("aria-pressed", pressed ? "false" : "true");
    if (pressed) state.filters.types.delete(key);
    else state.filters.types.add(key);
    const combined = [...state.devices, ...state.towers];
    renderResults(combined, "result");
  });
  chip.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      chip.click();
    }
  });
}

// Saved locations
const LS_KEY = "wt.savedLocations.v1";

function loadSaved() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    const items = raw ? JSON.parse(raw) : [];
    return Array.isArray(items) ? items : [];
  } catch {
    return [];
  }
}

function saveSaved(items) {
  localStorage.setItem(LS_KEY, JSON.stringify(items.slice(0, 50)));
}

function renderSaved() {
  const items = loadSaved();
  ui.savedList.innerHTML = "";
  if (!items.length) {
    ui.savedList.innerHTML = '<div class="hint">No saved locations yet.</div>';
    return;
  }

  for (const loc of items) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "ghost";
    b.style.textAlign = "left";
    b.textContent = `${safeText(loc.name)} • ${Number(loc.lat).toFixed(4)}, ${Number(loc.lon).toFixed(4)}`;
    b.addEventListener("click", () => {
      ui.lat.value = Number(loc.lat).toFixed(6);
      ui.lon.value = Number(loc.lon).toFixed(6);
      focusLatLon(Number(loc.lat), Number(loc.lon));
      map.setView([Number(loc.lat), Number(loc.lon)], 15);
      showToast("ok", "Location loaded", safeText(loc.name));
    });

    const del = document.createElement("button");
    del.type = "button";
    del.textContent = "Delete";
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      const next = items.filter((x) => x.id !== loc.id);
      saveSaved(next);
      renderSaved();
    });

    const row = document.createElement("div");
    row.style.display = "grid";
    row.style.gridTemplateColumns = "1fr auto";
    row.style.gap = "8px";
    row.style.marginTop = "8px";
    row.appendChild(b);
    row.appendChild(del);
    ui.savedList.appendChild(row);
  }
}

ui.saveBtn.addEventListener("click", () => {
  try {
    const { lat, lon } = parseLatLon();
    const name = ui.savedName.value.trim() || `Location ${new Date().toLocaleString()}`;
    const items = loadSaved();
    const id = (crypto && crypto.randomUUID && crypto.randomUUID()) || String(Date.now());
    const loc = { id, name, lat, lon };
    items.unshift(loc);
    saveSaved(items);
    ui.savedName.value = "";
    renderSaved();
    showToast("ok", "Saved", name);
  } catch (e) {
    showToast("bad", "Save failed", safeText(e.message || e));
  }
});

// Theme
const savedTheme = localStorage.getItem("wt.theme");
if (savedTheme === "dark" || savedTheme === "light") ui.app.dataset.theme = savedTheme;

ui.themeBtn.addEventListener("click", () => {
  const current = ui.app.dataset.theme || "dark";
  const next = current === "dark" ? "light" : "dark";
  ui.app.dataset.theme = next;
  localStorage.setItem("wt.theme", next);
});

// Actions
ui.clearBtn.addEventListener("click", clearAll);

ui.exportBtn.addEventListener("click", () => {
  if (!state.lastExport) {
    showToast("warn", "Nothing to export", "Run a query first.");
    return;
  }
  const blob = new Blob([JSON.stringify(state.lastExport, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "wiretapper-results.json";
  a.click();
  URL.revokeObjectURL(url);
});

ui.locateBtn.addEventListener("click", () => {
  if (!navigator.geolocation) {
    showToast("bad", "Geolocation unavailable", "Your browser does not support geolocation.");
    return;
  }
  setStatus("Locating…");
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      ui.lat.value = pos.coords.latitude.toFixed(6);
      ui.lon.value = pos.coords.longitude.toFixed(6);
      focusLatLon(pos.coords.latitude, pos.coords.longitude);
      map.setView([pos.coords.latitude, pos.coords.longitude], 15);
      setStatus("Location set");
    },
    (err) => {
      setStatus("Ready");
      showToast("bad", "Location error", safeText(err.message));
    },
    { enableHighAccuracy: true, timeout: 8000 },
  );
});

async function refreshProviders() {
  try {
    const { data } = await fetchJson("/api/status");
    const p = data.providers || {};
    const bits = [];
    bits.push(`Wigle: ${p.wigle ? "✓" : "—"}`);
    bits.push(`OpenCellID: ${p.opencellid ? "✓" : "—"}`);
    bits.push(`Shodan: ${p.shodan ? "✓" : "—"}`);
    ui.providersText.textContent = bits.join(" • ");
  } catch {
    ui.providersText.textContent = "Unavailable";
  }
}

ui.nearbyBtn.addEventListener("click", async () => {
  try {
    const { lat, lon } = parseLatLon();
    clearAll();
    focusLatLon(lat, lon);
    setBusy(true);
    setStatus("Querying nearby…");
    const { data } = await fetchJson("/nearby", { lat, lon, mode: ui.mode.value });
    const devices = data.devices || [];
    state.devices = devices;
    state.lastExport = data;
    addDeviceMarkers(devices);
    renderResults(devices, ui.mode.value);
    setStatus(`Nearby: ${devices.length} device(s)${data.meta && data.meta.cached ? " (cached)" : ""}`);
    if (devices.length) map.setView([lat, lon], Math.max(14, map.getZoom()));
  } catch (e) {
    setStatus("Ready");
    showToast("bad", "Nearby failed", safeText(e.message || e));
  } finally {
    setBusy(false);
  }
});

ui.searchBtn.addEventListener("click", async () => {
  try {
    const type = ui.searchType.value;
    const query = ui.searchQuery.value.trim();
    if (!query) throw new Error("Search query is required.");
    clearAll();
    setBusy(true);
    setStatus("Searching…");
    const { data } = await fetchJson("/searchzz", { type, query });
    const devices = data.devices || [];
    state.devices = devices;
    state.lastExport = data;
    addDeviceMarkers(devices);
    renderResults(devices, type);
    setStatus(`Search: ${devices.length} result(s)`);
    if (devices.length) {
      const first = devices.find((d) => Number.isFinite(Number(d.lat)) && Number.isFinite(Number(d.lon)));
      if (first) map.setView([Number(first.lat), Number(first.lon)], 15);
    }
  } catch (e) {
    setStatus("Ready");
    showToast("bad", "Search failed", safeText(e.message || e));
  } finally {
    setBusy(false);
  }
});

ui.towersBtn.addEventListener("click", async () => {
  try {
    const { lat, lon } = parseLatLon();
    towersLayer.clearLayers();
    focusLatLon(lat, lon);
    setBusy(true);
    setStatus("Fetching towers…");
    const { data } = await fetchJson("/api/geo/towers", { lat, lon });
    state.towers = Array.isArray(data) ? data : [];
    state.lastExport = data;
    addTowerMarkers(state.towers);
    renderResults(state.towers, "cell_tower");
    setStatus(`Towers: ${state.towers.length}`);
  } catch (e) {
    setStatus("Ready");
    showToast("bad", "Towers failed", safeText(e.message || e));
  } finally {
    setBusy(false);
  }
});

ui.celltowerBtn.addEventListener("click", async () => {
  try {
    const { lat, lon } = parseLatLon();
    towersLayer.clearLayers();
    focusLatLon(lat, lon);
    setBusy(true);
    setStatus("Fetching GeoJSON towers…");
    const { data } = await fetchJson("/api/geo/celltower", { lat, lon });
    state.towers = Array.isArray(data) ? data : [];
    state.lastExport = data;
    addTowerMarkers(state.towers);
    renderResults(state.towers, "cell_tower");
    setStatus(`GeoJSON towers: ${state.towers.length}`);
  } catch (e) {
    setStatus("Ready");
    showToast("bad", "Celltower failed", safeText(e.message || e));
  } finally {
    setBusy(false);
  }
});

// Init
renderSaved();
refreshProviders();
showToast("ok", "Tip", "Click the map to set coordinates. Use filters to narrow results, and save locations.");
