"use strict";

const basinColor = "#d2de7b";
const waterColor = "#acc6cb";

async function loadData(file) {
  const response = await fetch(file);
  if (!response.ok) throw new Error("Arquivo de dados indisponível");
  const bytes = await response.arrayBuffer();
  const header = new Uint8Array(bytes, 0, Math.min(bytes.byteLength, 2));
  if (header[0] === 31 && header[1] === 139) {
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    return new Response(stream).json();
  }
  return JSON.parse(new TextDecoder().decode(bytes));
}

function addMapBase(map, base, showRegions) {
  const pane = map.createPane("cartografia");
  pane.style.zIndex = "410";
  pane.style.pointerEvents = "none";
  const options = { pane: "cartografia", interactive: false, smoothFactor: 0 };

  L.geoJSON(base.agua, {
    ...options,
    style: { stroke: false, fillColor: waterColor, fillOpacity: 1 },
  }).addTo(map);
  const basin = L.geoJSON(base.bacia, {
    ...options,
    style: { fill: false, color: basinColor, weight: 3.78, lineJoin: "bevel" },
  }).addTo(map);

  if (!showRegions) return basin.getBounds();

  const regions = L.geoJSON(base.ras, {
    ...options,
    style: {
      fill: false, color: "#000", opacity: 0.6895, weight: 0.76,
      dashArray: "0.76 1.52", lineCap: "square", lineJoin: "bevel",
    },
  });
  const labels = base.ras.features.map(({ properties }) =>
    L.tooltip({ permanent: true, direction: "center", className: "ra-label", opacity: 1 })
      .setLatLng(L.GeoJSON.coordsToLatLng(properties.rotulo))
      .setContent(String(properties.ra_cira))
  );
  const regionOverlay = L.layerGroup([regions, ...labels]);

  function positionLabels() {
    if (!map.hasLayer(regionOverlay)) return;
    const visible = [];
    const viewport = map.getContainer().getBoundingClientRect();
    for (const label of labels) {
      const element = label.getElement();
      const box = element.getBoundingClientRect();
      const fits = box.left >= viewport.left && box.right <= viewport.right
        && box.top >= viewport.top && box.bottom <= viewport.bottom;
      const overlaps = visible.some(other => box.left < other.right && box.right > other.left
        && box.top < other.bottom && box.bottom > other.top);
      element.style.visibility = fits && !overlaps ? "" : "hidden";
      if (fits && !overlaps) visible.push(box);
    }
  }

  function toggleRegions() {
    if (showRegions.checked) {
      regionOverlay.addTo(map);
      basin.bringToFront();
      positionLabels();
    } else {
      regionOverlay.remove();
    }
  }
  map.on("moveend", positionLabels);
  showRegions.addEventListener("change", toggleRegions);
  showRegions.disabled = false;
  toggleRegions();
  return basin.getBounds();
}
