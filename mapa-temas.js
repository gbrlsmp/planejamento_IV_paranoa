"use strict";

const reportMapThemes = {
  "ras": [
    "identificacao.html",
    "regioes-administrativas",
    "Bacia e regiões administrativas"
  ],
  "rede": [
    "identificacao.html",
    "leitura-da-rede",
    "Leitura da rede"
  ],
  "uso": [
    "identificacao.html",
    "uso-solo",
    "Uso e cobertura do solo"
  ],
  "tipologias": [
    "identificacao.html",
    "tipologias",
    "Tipologias de AVU e de IV"
  ],
  "metricas": [
    "identificacao.html",
    "metricas-forma",
    "Métricas de forma"
  ],
  "momentos": [
    "condicionantes.html",
    "momentos-da-agua",
    "Momentos da água"
  ],
  "pre": [
    "condicionantes.html",
    "potencial-recuperacao",
    "Potencial de recuperação ecológica"
  ],
  "rodovias": [
    "ecologia.html",
    "fragmentos-rodovias",
    "Fragmentos afetados por rodovias"
  ],
  "trampolins": [
    "ecologia.html",
    "trampolins-ecologicos",
    "Trampolins ecológicos"
  ],
  "fauna": [
    "ecologia.html",
    "animais-estudados",
    "Animais estudados"
  ]
};

function configureThemeView() {
  const id = new URLSearchParams(location.search).get("tema");
  const theme = Object.hasOwn(reportMapThemes, id) ? reportMapThemes[id] : null;
  const view = { id: theme ? id : null };
  if (!theme) return view;

  const [page, anchor, title] = theme;
  document.title = title + " | Mapa interativo";
  document.getElementById("titulo-atlas").textContent = title;
  document.getElementById("metodologia-do-tema").href = page + "#" + anchor;
  document.getElementById("mapa-do-tema").href = "mapa.html?tema=" + id;
  document.getElementById("vistas-do-tema").hidden = false;
  document.getElementById("indicadores-do-atlas").hidden = true;
  document.getElementById("fonte-riscos-atlas").hidden = true;
  return view;
}

async function addThemeLayers(map, view) {
  const controls = document.getElementById("camadas-tematicas");
  const note = document.getElementById("contexto-atlas");
  const sources = document.getElementById("fontes-atlas");
  const legends = document.getElementById("legendas-tematicas");
  const catalog = await loadData("dados-mapas/catalogo.json");
  const choices = view.id ? Object.entries(catalog).filter(([id]) => id === view.id) : Object.entries(catalog);
  if (!choices.length) {
    controls.hidden = true;
    note.textContent = view.id === "ras"
      ? "Ative as RAs para consultar os limites e os códigos da base cartográfica."
      : "A camada temática está pendente. O mapa mostra o recorte da bacia.";
    return;
  }
  if (view.id) note.textContent = "Ative a camada e clique no mapa para consultar a classe no ponto selecionado.";

  const thematicPane = map.createPane("temas");
  thematicPane.style.zIndex = "350";
  thematicPane.style.pointerEvents = "none";
  const layers = [];

  for (const [id, layer] of choices) {
    const control = document.createElement("label");
    control.className = "map-toggle";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = id === view.id;
    control.append(input, document.createTextNode(layer.title));
    controls.append(control);

    const source = document.createElement("li");
    const sourceLink = document.createElement("a");
    const [page, anchor] = reportMapThemes[id];
    sourceLink.href = page + "#" + anchor;
    sourceLink.textContent = layer.title;
    source.append(sourceLink);
    sources.append(source);

    const legend = document.createElement("section");
    const heading = document.createElement("h4");
    heading.textContent = layer.title;
    const list = document.createElement("ul");
    const colors = new Map();
    for (const [, label, color] of layer.classes) {
      const row = document.createElement("li");
      const swatch = document.createElement("span");
      swatch.className = "map-swatch";
      swatch.style.background = color;
      swatch.setAttribute("aria-hidden", "true");
      row.append(swatch, document.createTextNode(label));
      list.append(row);
      const code = Number.parseInt(color.slice(1), 16);
      colors.set(code, label);
    }
    legend.append(heading, list);
    legends.append(legend);

    const [west, south, east, north] = layer.bounds;
    const project = L.CRS.EPSG3857;
    const bounds = [
      project.unproject(L.point(west, south)),
      project.unproject(L.point(east, north)),
    ];
    const overlay = L.imageOverlay("dados-mapas/" + id + ".png", bounds, {
      pane: "temas", opacity: 0.72, className: "mapa-classe", alt: layer.title,
    });
    const item = { layer, input, overlay, colors, canvas: null, loaded: false };
    layers.push(item);
    overlay.on("load", () => { item.loaded = true; });
    overlay.on("error", () => {
      input.checked = false;
      input.disabled = true;
      note.textContent = "Camada indisponível: " + layer.title + ".";
      toggle();
    });
    function toggle() {
      legend.hidden = !input.checked;
      if (input.checked) {
        overlay.addTo(map);
      } else {
        overlay.remove();
      }
    }
    input.addEventListener("change", toggle);
    toggle();
  }
  controls.disabled = false;

  map.on("click", ({ latlng }) => {
    const point = L.CRS.EPSG3857.project(latlng);
    const panel = document.createElement("div");
    for (const item of layers) {
      if (!item.input.checked || !item.loaded) continue;
      const [west, south, east, north] = item.layer.bounds;
      if (point.x < west || point.x >= east || point.y <= south || point.y > north) continue;
      if (!item.canvas) {
        const img = item.overlay.getElement();
        const canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth;
        canvas.height = img.naturalHeight;
        item.canvas = canvas.getContext("2d", { willReadFrequently: true });
        item.canvas.drawImage(img, 0, 0);
      }
      const ctx = item.canvas;
      const x = Math.floor((point.x - west) / (east - west) * ctx.canvas.width);
      const y = Math.floor((north - point.y) / (north - south) * ctx.canvas.height);
      const [r, g, b, alpha] = ctx.getImageData(x, y, 1, 1).data;
      const label = alpha ? item.colors.get((r << 16) | (g << 8) | b) : null;
      if (label) {
        const line = document.createElement("p");
        line.textContent = item.layer.title + " · " + label;
        panel.append(line);
      }
    }
    if (panel.childElementCount) L.popup().setLatLng(latlng).setContent(panel).openOn(map);
  });
}
