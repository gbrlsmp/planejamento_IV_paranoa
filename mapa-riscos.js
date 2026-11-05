"use strict";

const select = document.getElementById("indicador");
const fit = document.getElementById("enquadrar");
const mapStatus = document.getElementById("map-status");
const legendTitle = document.getElementById("legend-title");
const legendNote = document.getElementById("legend-note");
const legendItems = document.getElementById("legend-items");
const missingColor = "#a9afb4";
const numberFormat = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });

const heatClasses = ["base", "boa", "média", "ruim", "muito ruim"];
const heatColors = ["#fff1b9", "#fbc87c", "#f58f4c", "#df4a35", "#981e31"];
const waterColors = ["#d8eaf7", "#8cc4e5", "#3b8abe", "#155687"];
const incomeClasses = ["até 1 SM", ">1 a 3 SM", ">3 a 6 SM", ">6 a 9 SM", ">9 SM"];
const mapGroups = [
  ["Clima e calor", [
    { id: "icu", label: "Ilha de calor urbano", classes: ["não", "sim"], colors: ["#c8e4da", "#d34536"] },
    { id: "temp_dia", label: "Temperatura de dia", value: "temp_dia", category: "td_classe", unit: "°C", classes: heatClasses, colors: heatColors },
    { id: "temp_noite", label: "Temperatura à noite", value: "temp_noite", category: "tn_classe", unit: "°C", classes: heatClasses, colors: heatColors },
    { id: "temp_media", label: "Temperatura média", value: "temp_media", category: "tm_classe", unit: "°C", classes: heatClasses, colors: heatColors },
    { id: "hm_dia", label: "Mitigação térmica de dia", value: "hm_dia", continuous: true },
    { id: "hm_noite", label: "Mitigação térmica à noite", value: "hm_noite", continuous: true },
    { id: "hm_media", label: "Mitigação térmica média", value: "hm_media", continuous: true },
    { id: "umid_pct", label: "Umidade relativa", value: "umid_pct", category: "umid_cls", unit: "%", classes: ["muito baixo", "médio baixo", "médio", "alto"], colors: waterColors },
  ]],
  ["Inundação e ocupação", [
    { id: "inund_max", label: "Inundação · TR de 5 anos", value: "inund_max", category: "inund_cls", classes: ["muito baixa", "baixa", "média", "alta"], colors: waterColors },
    { id: "edif_pct", label: "Pressão de edificações", value: "edif_pct", category: "edif_cls", unit: "%", classes: ["inexistente", "baixa", "média", "alta"], colors: ["#dfe5e1", "#f7d497", "#ed9452", "#aa3e31"] },
  ]],
  ["Contexto territorial", [
    { id: "renda_sm", label: "Contexto de renda", value: "renda_sm", category: "renda_cls", unit: "SM", classes: incomeClasses, colors: ["#f1e9f7", "#d4bfe5", "#ae86c7", "#8151a4", "#502b77"] },
  ]],
];

const indicators = new Map(mapGroups.flatMap(([, list]) => list.map(item => [item.id, item])));
let active = null;
let fieldIndex, data, colors;

function readField(values, key) {
  return values[fieldIndex[key]] ?? null;
}

function formatValue(value, unit = "") {
  if (value === null) return "Sem dados";
  const formatted = typeof value === "number" ? numberFormat.format(value) : value;
  return unit ? formatted + " " + unit : formatted;
}

function categoryKey(item) {
  return item.category ?? item.id;
}

function legendEntries(item) {
  return item.classes.map((label, i) => [label, item.colors[i]]);
}

function gradient(value, range) {
  if (value === null || !range) return missingColor;
  const [min, max] = range;
  const position = max === min ? 0.5 : Math.max(0, Math.min(1, (value - min) / (max - min)));
  return "hsl(164 52% " + (91 - position * 65) + "%)";
}

function decodeRing(encoded) {
  const points = [];
  let cursor = 0, x = 0, y = 0;
  function readDelta() {
    let bits = 0, shift = 0, unit;
    do {
      if (cursor >= encoded.length || shift > 30) throw new Error("Geometria do mapa inválida");
      unit = encoded.charCodeAt(cursor++) - 63;
      if (unit < 0 || unit > 63) throw new Error("Geometria do mapa inválida");
      bits |= (unit & 31) << shift;
      shift += 5;
    } while (unit >= 32);
    return (bits & 1) ? -(bits >>> 1) - 1 : bits >>> 1;
  }
  while (cursor < encoded.length) {
    x += readDelta();
    y += readDelta();
    points.push([x / 1e5, y / 1e5]);
  }
  return points;
}

function appendLegendItems(entries) {
  const list = document.createElement("ul");
  for (const [label, color, outline] of entries) {
    const row = document.createElement("li");
    const swatch = document.createElement("span");
    swatch.className = "map-swatch";
    swatch.setAttribute("aria-hidden", "true");
    if (outline) {
      swatch.style.border = "2px solid " + color;
    } else {
      swatch.style.background = color;
    }
    row.append(swatch, document.createTextNode(label));
    list.append(row);
  }
  legendItems.append(list);
}

function showLegend() {
  legendItems.replaceChildren();
  if (!active) {
    legendTitle.textContent = "Base cartográfica";
    legendNote.textContent = document.getElementById("camadas-tematicas") ? "" : "Selecione um indicador para colorir os fragmentos.";
    appendLegendItems([["Limite da bacia", basinColor, true], ["Massa d’água", waterColor]]);
    return;
  }
  const entries = active.continuous ? [] : legendEntries(active);
  colors = new Map(entries);
  legendTitle.textContent = active.label;
  if (active.continuous) {
    legendNote.textContent = "Índice médio na faixa externa de cinco metros. A cor representa o valor numérico.";
    const range = data.ranges[active.value];
    if (range) {
      const ramp = document.createElement("div");
      ramp.className = "map-ramp";
      ramp.style.background = "linear-gradient(90deg," + gradient(range[0], range) + "," + gradient(range[1], range) + ")";
      const labels = document.createElement("div");
      labels.className = "map-range";
      for (const value of range) {
        const label = document.createElement("span");
        label.textContent = formatValue(value);
        labels.append(label);
      }
      legendItems.append(ramp, labels);
    }
  } else {
    legendNote.textContent = "Classes registradas no diagnóstico por fragmento.";
  }
  appendLegendItems([...entries, ["Sem dados", missingColor]]);
}

function popupContent(values) {
  const panel = document.createElement("div");
  panel.className = "fragment-popup";
  const title = document.createElement("strong");
  title.textContent = "Fragmento " + readField(values, "patch_id");
  panel.append(title);
  function add(text) {
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    panel.append(paragraph);
  }
  const measure = active.value ? readField(values, active.value) : readField(values, categoryKey(active));
  add(active.label + " · " + formatValue(measure, active.unit));
  if (active.category) add("Classe · " + formatValue(readField(values, active.category)));
  if (active.id === "inund_max") add("Profundidade média · " + formatValue(readField(values, "inund_med")));
  if (active.id === "edif_pct") add("Presença de edificações · " + formatValue(readField(values, "edif")));
  return panel;
}

async function initializeMap() {
  const map = L.map("mapa", { scrollWheelZoom: false, minZoom: 8, maxZoom: 19, zoomAnimation: false });
  if (getComputedStyle(map.getContainer()).overflow !== "hidden") {
    map.remove();
    throw new Error("A folha de estilos do Leaflet não carregou");
  }
  map.setView([-15.8, -47.85], 11);
  L.control.scale({ imperial: false }).addTo(map);
  const isAtlas = document.getElementById("camadas-tematicas") !== null;
  const view = isAtlas ? configureThemeView() : null;
  const base = await loadData("mapa-base.json.gz");
  const regions = isAtlas ? document.getElementById("mostrar-ras") : null;
  if (regions) regions.checked = view.id === "ras";
  const basinBounds = addMapBase(map, base, regions);
  const fitBasin = () => map.fitBounds(basinBounds, { padding: [18, 18], animate: false });
  fitBasin();
  fit.addEventListener("click", fitBasin);
  fit.disabled = false;
  addGoogleSatellite(map);
  if (view) {
    addThemeLayers(map, view).catch(error => {
      console.error(error);
      document.getElementById("contexto-atlas").textContent = "As camadas temáticas não puderam ser carregadas.";
    });
    mapStatus.textContent = "Base cartográfica carregada.";
    if (view.id) {
      showLegend();
      return;
    }
  }
  data = await loadData("mapa-dados.json.gz");
  if (data.encoding !== "polyline-xy-5" || !Array.isArray(data.fields) || !Array.isArray(data.rows) || !data.rows.length) {
    throw new Error("Dados do mapa inválidos");
  }
  fieldIndex = Object.fromEntries(data.fields.map((field, i) => [field, i]));
  showLegend();
  const style = feature => {
    if (!active) return { stroke: false, fill: false };
    const values = feature.properties.values;
    const color = active.continuous
      ? gradient(readField(values, active.value), data.ranges[active.value])
      : colors.get(readField(values, categoryKey(active))) ?? missingColor;
    return { stroke: false, fill: true, fillColor: color, fillOpacity: 0.8 };
  };
  const fragmentPane = map.createPane("fragmentos");
  fragmentPane.hidden = !active;
  const fragments = L.geoJSON(null, {
    renderer: L.canvas({ pane: "fragmentos", padding: 0.1 }),
    bubblingMouseEvents: !isAtlas,
    style,
  }).addTo(map);
  fragments.on("click", event => {
    const values = event.layer?.feature?.properties?.values;
    if (values) L.popup().setLatLng(event.latlng).setContent(popupContent(values)).openOn(map);
  });
  for (const [label, list] of mapGroups) {
    const group = document.createElement("optgroup");
    group.label = label;
    for (const item of list) group.append(new Option(item.label, item.id));
    select.append(group);
  }
  const total = data.rows.length;
  for (let offset = 0; offset < total; offset += 500) {
    fragments.addData(data.rows.slice(offset, offset + 500).map(([polygons, values]) => ({
      type: "Feature",
      properties: { values },
      geometry: { type: "MultiPolygon", coordinates: polygons.map(poly => poly.map(decodeRing)) },
    })));
    if (offset % 2500 === 0) mapStatus.textContent = "Preparando o mapa · " + Math.floor(offset / total * 100) + "%";
    await new Promise(resolve => setTimeout(resolve, 0));
  }
  data.rows = [];
  function selectIndicator() {
    active = indicators.get(select.value) ?? null;
    showLegend();
    map.closePopup();
    fragmentPane.hidden = !active;
    if (active) fragments.setStyle(style);
  }
  select.addEventListener("change", selectIndicator);
  if (select.value) selectIndicator();
  select.disabled = false;
  mapStatus.textContent = numberFormat.format(total) + " fragmentos disponíveis";
}

initializeMap().catch(error => {
  console.error(error);
  mapStatus.textContent = "O mapa não pôde ser carregado. Recarregue a página para tentar de novo.";
});
