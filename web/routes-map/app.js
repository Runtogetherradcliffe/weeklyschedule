/* global L */
const INDEX_URL = "../../routes/index.json";

const map = L.map('map');
const osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
}).addTo(map);

// default view
map.setView([53.6, -2.32], 12);

const routeLayer = L.geoJSON(null, {
  style: function () {
    return { weight: 4 };
  }
}).addTo(map);

const state = {
  routes: [],
  filtered: [],
};

const els = {
  list: document.getElementById("route-list"),
  search: document.getElementById("search"),
  count: document.getElementById("count"),
  run: document.getElementById("filter-run"),
  ride: document.getElementById("filter-ride"),
  meta: document.getElementById("route-meta"),
};

function fmtKm(km) {
  return `${(km || 0).toFixed(2)} km`;
}

function renderList() {
  els.list.innerHTML = "";
  state.filtered.forEach(r => {
    const li = document.createElement("li");
    li.innerHTML = `
      <div class="title">${r.name}</div>
      <div class="meta">
        <span class="badge">${r.type || "route"}</span>
        <span class="badge">${fmtKm(r.distance_km)}</span>
        ${r.elev_gain_m ? `<span class="badge">${Math.round(r.elev_gain_m)} m ↑</span>` : ""}
      </div>
    `;
    li.addEventListener("click", () => showRoute(r));
    els.list.appendChild(li);
  });
  els.count.textContent = state.filtered.length;
}

function applyFilters() {
  const q = (els.search.value || "").toLowerCase();
  const showRun = els.run.checked;
  const showRide = els.ride.checked;

  state.filtered = state.routes.filter(r => {
    const byType = (r.type === "run" && showRun) || (r.type === "ride" && showRide) || (!r.type && (showRun || showRide));
    const byText = r.name.toLowerCase().includes(q);
    return byType && byText;
  });
  renderList();
}

async function loadIndex() {
  const res = await fetch(INDEX_URL, { cache: "no-cache" });
  if (!res.ok) {
    throw new Error(`Failed to load ${INDEX_URL}: ${res.status}`);
  }
  const data = await res.json();
  state.routes = data.routes || [];
  state.filtered = state.routes.slice();
  renderList();
}

async function showRoute(r) {
  routeLayer.clearLayers();
  const res = await fetch(`../../${r.file}`, { cache: "no-cache" });
  if (!res.ok) {
    alert("Could not load route GeoJSON.");
    return;
  }
  const gj = await res.json();
  const layer = L.geoJSON(gj, { style: { weight: 5 } }).addTo(routeLayer);
  try {
    const bounds = layer.getBounds();
    if (bounds && bounds.isValid()) map.fitBounds(bounds, { padding: [20, 20] });
  } catch (e) {}

  // Meta card
  els.meta.classList.remove("hidden");
  els.meta.innerHTML = `
    <div><strong>${r.name}</strong></div>
    <div style="margin-top:6px;color:#6b7280;font-size:13px;">
      Type: ${r.type || "n/a"} · Distance: ${fmtKm(r.distance_km)} ${r.elev_gain_m ? `· Elev gain: ${Math.round(r.elev_gain_m)} m` : ""}
    </div>
    <div style="margin-top:6px;font-size:12px;color:#9ca3af;">
      Updated: ${r.updated_at ? new Date(r.updated_at).toLocaleString() : "unknown"}
    </div>
  `;
}

els.search.addEventListener("input", applyFilters);
els.run.addEventListener("change", applyFilters);
els.ride.addEventListener("change", applyFilters);

loadIndex().catch(err => {
  console.error(err);
  els.list.innerHTML = `<li>Failed to load index.json. Ensure routes/index.json exists.</li>`;
});
