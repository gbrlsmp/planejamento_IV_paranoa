"use strict";

// A mesma seleção recorta as camadas em todos os mapas da página.
// As geometrias web são cartográficas; áreas de resumo vêm das interseções locais.
const FitopolisTerritorio = (() => {
  const controllers = new Set();
  let selected = [];
  const key = "fitopolis-ras-v1";
  try { selected = JSON.parse(sessionStorage.getItem(key) || "[]"); } catch { selected = []; }
  if (!Array.isArray(selected)) selected = [];
  selected = selected.map(String);
  let serial = 0;
  function inRing(point, ring) {
    let inside = false;
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const a = ring[i], b = ring[j];
      if ((a[1] > point[1]) !== (b[1] > point[1]) && point[0] < (b[0] - a[0]) * (point[1] - a[1]) / (b[1] - a[1]) + a[0]) inside = !inside;
    }
    return inside;
  }
  function inGeometry(point, geometry) {
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    return polygons.some(rings => inRing(point, rings[0]) && !rings.slice(1).some(r => inRing(point, r)));
  }
  function choose(values) {
    selected = [...new Set(values.map(String))];
    try { sessionStorage.setItem(key, JSON.stringify(selected)); } catch { /* Storage is optional. */ }
    for (const controller of controllers) controller.update(true);
    window.dispatchEvent(new CustomEvent("fitopolis:territorio", { detail: { ras: [...selected] } }));
  }
  function attach(map, base) {
    if (map._fitopolisTerritory) return map._fitopolisTerritory;
    const features = base.ras.features.filter(f => f.geometry && f.properties.ra_cira != null);
    const available = new Set(features.map(f => String(f.properties.ra_cira)));
    selected = selected.filter(id => available.has(id));
    const ns = "http://www.w3.org/2000/svg", svg = document.createElementNS(ns, "svg");
    svg.setAttribute("width", "0"); svg.setAttribute("height", "0");
    svg.style.position = "absolute"; svg.setAttribute("aria-hidden", "true");
    const defs = document.createElementNS(ns, "defs"), clip = document.createElementNS(ns, "clipPath");
    clip.id = "fitopolis-recorte-" + (++serial);clip.setAttribute("clipPathUnits", "userSpaceOnUse");
    defs.append(clip);svg.append(defs);map.getContainer().append(svg);
    const Control = L.Control.extend({
      onAdd() {
        const box = L.DomUtil.create("details", "fitopolis-territorio leaflet-bar");
        const summary = document.createElement("summary");summary.textContent = "Bacia inteira · selecionar RAs";box.append(summary);
        const list = document.createElement("div");list.className = "fitopolis-ra-list";
        const all = document.createElement("button");all.type = "button";all.textContent = "Todas as RAs / bacia inteira";
        all.addEventListener("click", () => choose([]));list.append(all);
        const checks = new Map();
        for (const f of [...features].sort((a, b) => String(a.properties.ra_nome || regionNames[a.properties.ra_cira]).localeCompare(String(b.properties.ra_nome || regionNames[b.properties.ra_cira]), "pt-BR"))) {
          const label = document.createElement("label"), input = document.createElement("input");
          input.type = "checkbox";input.value = String(f.properties.ra_cira);checks.set(input.value, input);
          input.addEventListener("change", () => choose([...checks].filter(([, c]) => c.checked).map(([id]) => id)));
          label.append(input, document.createTextNode(f.properties.ra_nome || regionNames[input.value] || "RA " + input.value));list.append(label);
        }
        box.append(list);L.DomEvent.disableClickPropagation(box);L.DomEvent.disableScrollPropagation(box);
        this.summary = summary;this.checks = checks;return box;
      }
    });
    const control = new Control({ position: "topright" }).addTo(map);
    const boundaryPane=map.getPane("fitopolis-limites") || map.createPane("fitopolis-limites");boundaryPane.style.zIndex="490";boundaryPane.style.pointerEvents="none";
    const boundaries = L.geoJSON(base.ras, { pane:"fitopolis-limites", interactive: false, style: { color: "#425747", weight: .8, dashArray: "3 4", fill: false } }).addTo(map);
    function update(fit = false) {
      const active = features.filter(f => selected.includes(String(f.properties.ra_cira)));
      control.summary.textContent = active.length ? `${active.length} RA${active.length > 1 ? "s" : ""} selecionada${active.length > 1 ? "s" : ""}` : "Bacia inteira · selecionar RAs";
      for (const [id, input] of control.checks) input.checked = selected.includes(id);
      clip.replaceChildren();
      for (const feature of active) {
        const polygons = feature.geometry.type === "Polygon" ? [feature.geometry.coordinates] : feature.geometry.coordinates;
        for (const rings of polygons) {
          const path = document.createElementNS(ns, "path");path.setAttribute("clip-rule", "evenodd");
          path.setAttribute("d", rings.map(ring => ring.map(([lng, lat], i) => { const p = map.latLngToLayerPoint([lat, lng]);return `${i ? "L" : "M"}${p.x},${p.y}`; }).join(" ") + " Z").join(" "));
          clip.append(path);
        }
      }
      for (const [name, pane] of Object.entries(map.getPanes())) {
        if (["mapPane", "tilePane", "popupPane", "tooltipPane"].includes(name)) continue;
        pane.style.clipPath = active.length ? `url(#${clip.id})` : "";
      }
      boundaries.setStyle(f => ({ weight: selected.includes(String(f.properties.ra_cira)) ? 2 : .8 }));
      if (fit && active.length) map.fitBounds(L.geoJSON({ type: "FeatureCollection", features: active }).getBounds(), { padding: [16, 16], animate: false });
      else if (fit) map.fitBounds(L.geoJSON(base.bacia).getBounds(), { padding: [16, 16], animate: false });
    }
    const controller = { update, contains: latlng => !selected.length || features.some(f => selected.includes(String(f.properties.ra_cira)) && inGeometry([latlng.lng, latlng.lat], f.geometry)) };
    map._fitopolisTerritory = controller;controllers.add(controller);
    map.on("moveend zoomend resize layeradd", () => { if (map._loaded) update(); });
    map.on("popupopen", e => { if (!controller.contains(e.popup.getLatLng())) map.closePopup(e.popup); });
    map.on("unload", () => { controllers.delete(controller);svg.remove(); });
    map.whenReady(() => update());return controller;
  }
  if (typeof L !== "undefined" && L.Map?.addInitHook) L.Map.addInitHook(function () {
    this.whenReady(() => loadData("mapa-base.json.gz").then(base => attach(this, base)).catch(() => {
      const status = this.getContainer().parentElement?.querySelector('[role="status"]');
      if (status) status.textContent = "Não foi possível carregar a seleção territorial. Recarregue a página para tentar novamente.";
    }));
  });
  return { attach, choose, selected: () => [...selected], inGeometry };
})();
if (typeof module !== "undefined") module.exports = FitopolisTerritorio;
