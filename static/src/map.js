// Directory map (spec §4.3 Institution: Leaflet + OpenStreetMap tiles, fallback to list).
// Loaded only on the directory page (static/dist/map.js) to keep main.js under budget.
// Reads institutions from <script type="application/json" id="map-data"> (CSP-safe, no
// inline JS) and re-reads it after every HTMX swap of the results.
import L from "leaflet";

const TILES = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION = "&copy; OpenStreetMap contributors";
const UZBEKISTAN_CENTER = [41.3, 64.5];
const COLOURS = { women: "#b8336a", children: "#8a5a00", both: "#2b2b2b" };

let map = null;
let layer = null;

function readData() {
  const node = document.getElementById("map-data");
  if (!node) return [];
  try {
    return JSON.parse(node.textContent || "[]");
  } catch (e) {
    return [];
  }
}

function escapeHtml(text) {
  return String(text || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function render() {
  const container = document.getElementById("map");
  if (!container) return;
  const items = readData().filter((i) => typeof i.lat === "number" && typeof i.lng === "number");
  if (!map) {
    map = L.map(container, { scrollWheelZoom: false }).setView(UZBEKISTAN_CENTER, 6);
    L.tileLayer(TILES, { attribution: ATTRIBUTION, maxZoom: 18 }).addTo(map);
    layer = L.layerGroup().addTo(map);
  }
  layer.clearLayers();
  const bounds = [];
  items.forEach((item) => {
    const marker = L.circleMarker([item.lat, item.lng], {
      radius: 9,
      color: COLOURS[item.sections] || COLOURS.both,
      fillColor: COLOURS[item.sections] || COLOURS.both,
      fillOpacity: 0.85,
      weight: 2,
    });
    marker.bindPopup(
      `<strong>${escapeHtml(item.name)}</strong><br>${escapeHtml(item.kind)}<br>${escapeHtml(item.address)}` +
        (item.phone ? `<br><a href="tel:${escapeHtml(item.phone)}">${escapeHtml(item.phone)}</a>` : "") +
        (item.free ? `<br>${escapeHtml(item.free_label)}` : "")
    );
    marker.addTo(layer);
    bounds.push([item.lat, item.lng]);
  });
  if (bounds.length) {
    map.fitBounds(bounds, { padding: [24, 24], maxZoom: 13 });
  } else {
    map.setView(UZBEKISTAN_CENTER, 6);
  }
  container.setAttribute("data-markers", String(bounds.length));
}

document.addEventListener("DOMContentLoaded", render);
document.addEventListener("htmx:afterSwap", (event) => {
  if (event.target && event.target.id === "directory-results") render();
});
