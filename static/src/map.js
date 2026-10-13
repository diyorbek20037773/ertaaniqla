// Directory map (D-083): the 14 regions drawn from static/geo/uz-regions.json (no third-party
// request for the shapes), coloured by the number of institutions; a click on a region filters
// the list and zooms in, where every district shows its number of institutions at its centre (the
// Ministry list has no coordinates); a click on a district filters the list to it. Countries
// around Uzbekistan are faded, the base map is grey so the regions stand out.
// Reads <script type="application/json" id="map-data"> (CSP-safe) and re-reads it after every HTMX
// swap of the results. Loaded only on the directory page (static/dist/map.js).
import L from "leaflet";

const TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION = "&copy; OpenStreetMap contributors · geoBoundaries";
const UZ_BOUNDS = [[37.1, 55.9], [45.6, 73.2]];
const RAMP = ["#f7e4ea", "#f0c6d6", "#e29cbc", "#c86b95", "#a34f72"]; // blush → mauve
const SELECTED = "#b8336a";

let map = null;
let regionsLayer = null;
let districtsLayer = null;
let pointsLayer = null;
let geo = null;
let geoPromise = null;
let data = { regions: {}, districts: [], points: [], selected: {} };

function readData() {
  const node = document.getElementById("map-data");
  if (!node) return data;
  try {
    const parsed = JSON.parse(node.textContent || "{}");
    return Array.isArray(parsed) ? { regions: {}, districts: [], points: parsed, selected: {} } : parsed;
  } catch (e) {
    return data;
  }
}

function escapeHtml(text) {
  return String(text || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function loadGeo(url) {
  if (!geoPromise) geoPromise = fetch(url, { credentials: "same-origin" }).then((r) => r.json()).then((json) => (geo = json));
  return geoPromise;
}

// the filter form drives the list (HTMX); the map only sets its fields
function applyFilter(region, district) {
  const form = document.querySelector(".filter-form");
  if (!form) return;
  const select = form.querySelector('select[name="region"]');
  const hidden = form.querySelector("[data-map-district]");
  if (select) select.value = region || "";
  if (hidden) hidden.value = district || "";
  if (typeof form.requestSubmit === "function") form.requestSubmit();
  else form.submit();
}

function colour(count, max) {
  if (!count) return "#ffffff";
  const step = Math.min(RAMP.length - 1, Math.floor((count / Math.max(max, 1)) * RAMP.length));
  return RAMP[step];
}

function regionStyle(code) {
  const counts = Object.values(data.regions || {}).map((r) => r.count || 0);
  const max = Math.max(1, ...counts);
  const selected = data.selected && data.selected.region;
  const info = (data.regions || {})[code] || {};
  const isSelected = selected === code;
  return {
    color: isSelected ? SELECTED : "#ffffff",
    weight: isSelected ? 3 : selected ? 1 : 1.5,
    fillColor: colour(info.count || 0, max),
    fillOpacity: !selected ? 0.8 : isSelected ? 0.45 : 0.15,
  };
}

function drawRegions() {
  if (!geo) return;
  if (regionsLayer) regionsLayer.remove();
  const shapes = geo.features.filter((f) => f.properties.code !== "UZ");
  regionsLayer = L.geoJSON({ type: "FeatureCollection", features: shapes }, {
    style: (feature) => regionStyle(feature.properties.code),
    onEachFeature: (feature, shape) => {
      const code = feature.properties.code;
      const info = (data.regions || {})[code] || {};
      shape.bindTooltip(`<strong>${escapeHtml(info.name)}</strong><br>${escapeHtml(info.label)}`, { sticky: true, className: "map-tip" });
      shape.on({
        mouseover: () => shape.setStyle({ weight: 3, color: SELECTED, fillOpacity: 0.9 }),
        mouseout: () => regionsLayer.resetStyle(shape),
        click: () => applyFilter(code === (data.selected && data.selected.region) && !data.selected.district ? "" : code, ""),
      });
    },
  }).addTo(map);
}

function drawMask() {
  // a world polygon with Uzbekistan cut out: the neighbours fade into the page colour
  const outline = geo.features.find((f) => f.properties.code === "UZ");
  if (!outline) return;
  const holes = [];
  outline.geometry.coordinates.forEach((poly) => holes.push(poly[0].map(([lng, lat]) => [lat, lng])));
  L.polygon([[[-89, -179], [-89, 179], [89, 179], [89, -179]], ...holes], {
    stroke: false, fillColor: "#faf7f5", fillOpacity: 0.72, interactive: false,
  }).addTo(map);
  L.geoJSON(outline, { style: { color: "#2b1a2e", weight: 1.5, fill: false }, interactive: false }).addTo(map);
}

function drawDistricts() {
  districtsLayer.clearLayers();
  const region = data.selected && data.selected.region;
  const chosen = data.selected && data.selected.district;
  (data.districts || [])
    .filter((d) => !region || d.region === region)
    .forEach((d) => {
      // smaller discs on phones, where a dense region (Fergana) has twenty districts side by side
      const narrow = map.getSize().x < 600;
      const size = Math.round(narrow ? Math.min(30, 18 + Math.sqrt(d.count) * 1.6) : Math.min(44, 22 + Math.sqrt(d.count) * 3));
      const icon = L.divIcon({
        className: "map-count" + (d.district === chosen ? " is-active" : ""),
        html: `<span>${d.count}</span>`,
        iconSize: [size, size],
      });
      const marker = L.marker([d.lat, d.lng], { icon, keyboard: true, title: `${d.name}: ${d.label}`, riseOnHover: true });
      marker.bindTooltip(`<strong>${escapeHtml(d.name)}</strong><br>${escapeHtml(d.label)}`, { direction: "top", offset: [0, -size / 2], className: "map-tip" });
      marker.on("click", () => applyFilter(d.region, d.district === chosen ? "" : d.district));
      marker.addTo(districtsLayer);
    });
  // the whole country shows the regions only; districts appear once a region is chosen
  if (region) districtsLayer.addTo(map);
  else districtsLayer.remove();
}

function drawPoints() {
  pointsLayer.clearLayers();
  (data.points || []).forEach((item) => {
    if (typeof item.lat !== "number" || typeof item.lng !== "number") return;
    L.circleMarker([item.lat, item.lng], { radius: 7, color: "#ffffff", weight: 2, fillColor: SELECTED, fillOpacity: 0.95 })
      .bindPopup(
        `<strong>${escapeHtml(item.name)}</strong><br>${escapeHtml(item.kind)}<br>${escapeHtml(item.address)}` +
          (item.phone ? `<br><a href="tel:${escapeHtml(item.phone)}">${escapeHtml(item.phone)}</a>` : "")
      )
      .addTo(pointsLayer);
  });
}

function fit() {
  const region = data.selected && data.selected.region;
  let target = null;
  if (region && regionsLayer) {
    regionsLayer.eachLayer((shape) => {
      if (shape.feature.properties.code === region) target = shape.getBounds();
    });
  }
  map.fitBounds(target || UZ_BOUNDS, { padding: [16, 16] });
}

async function render() {
  const container = document.getElementById("map");
  if (!container) return;
  data = readData();
  if (!map) {
    map = L.map(container, { scrollWheelZoom: false, zoomSnap: 0.25, minZoom: 5, maxZoom: 16, attributionControl: true });
    map.fitBounds(UZ_BOUNDS);
    L.tileLayer(TILES, { attribution: ATTRIBUTION, maxZoom: 18, className: "map-tiles" }).addTo(map);
    districtsLayer = L.layerGroup();
    pointsLayer = L.layerGroup().addTo(map);
    try {
      await loadGeo(container.dataset.geo);
      drawMask();
    } catch (e) {
      geo = null; // shapes missing: the list and the district numbers still work
    }
  }
  drawRegions();
  drawDistricts();
  drawPoints();
  if (pointsLayer) pointsLayer.bringToFront?.();
  fit();
  container.setAttribute("data-districts", String(districtsLayer.getLayers().length));
}

// typing a new region in the select starts over at region level
document.addEventListener("change", (event) => {
  if (event.target && event.target.matches('.filter-form select[name="region"]')) {
    const hidden = document.querySelector("[data-map-district]");
    if (hidden) hidden.value = "";
  }
});
document.addEventListener("DOMContentLoaded", render);
document.addEventListener("htmx:afterSwap", (event) => {
  if (event.target && event.target.id === "directory-results") render();
});
