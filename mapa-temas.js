"use strict";

const reportMapThemes = {
  "condicionantes": ["condicionantes.html", "condicionantes", "Mapa dos indicadores de Condicionantes", ["momentos", "pre"]],
  "ecologia": ["ecologia.html", "ecologia", "Mapa dos indicadores de Ecologia", []],
  "ras": [
    "mapa.html?tema=ras",
    "",
    "Bacia e regiões administrativas"
  ],
  "rede": [
    "mapa.html?tema=rede",
    "",
    "Leitura da rede"
  ],
  "uso": [
    "identificacao.html",
    "uso-solo",
    "Uso e cobertura do solo"
  ],
  "iv": ["identificacao.html", "elementos-iv", "Elementos da infraestrutura verde"],
  "tipologias": [
    "identificacao.html",
    "tipologias",
    "Tipologias de AVU"
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

  const [page, anchor, title, members = [id]] = theme;
  view.members = members;
  document.title = title + " | Mapa interativo";
  const heading = document.getElementById("titulo-atlas");
  heading.textContent = title;
  const topics = document.getElementById("diagnostico-atlas");
  const topic = topics.querySelector('a[href="' + page + '"]');
  if (topic) {
    topics.hidden = false;
    topic.setAttribute("aria-current", "location");
    const subheading = document.createElement("h3");
    subheading.id = heading.id;
    subheading.textContent = title;
    heading.replaceWith(subheading);
    document.querySelector('.main-tabs a[href="mapa.html"]').removeAttribute("aria-current");
    document.querySelector('.main-tabs a[href="diagnostico.html"]').setAttribute("aria-current", "location");
  }
  document.getElementById("metodologia-do-tema").href = page + "#" + anchor;
  const mapLink = document.getElementById("mapa-do-tema");
  mapLink.href = "mapa.html?tema=" + id;
  if (theme.length > 3) mapLink.textContent = "Mapa dos indicadores";
  document.getElementById("vistas-do-tema").hidden = ["ras", "rede"].includes(id);
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
  const choices = Object.entries(catalog).filter(([id]) => !view.id || view.members.includes(id));
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
    input.checked = id === view.members?.[0];
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
    for (const [, label, color] of layer.classes) {
      const row = document.createElement("li");
      const swatch = document.createElement("span");
      swatch.className = "map-swatch";
      swatch.style.background = color;
      swatch.setAttribute("aria-hidden", "true");
      row.append(swatch, document.createTextNode(label));
      list.append(row);
    }
    legend.append(heading, list);
    legends.append(legend);

    const url = "dados-mapas/" + id + ".png" + (layer.revision ? "?v=" + layer.revision : "");
    const { overlay, classAt } = createMapImage(url, layer, "temas", 0.72);
    layers.push({ layer, input, classAt });
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
    if (document.getElementById("leitura-indicador")?.value === "contexto" &&
        document.getElementById("indicador").value) return;
    const point = L.CRS.EPSG3857.project(latlng);
    const panel = document.createElement("div");
    for (const item of layers) {
      if (!item.input.checked) continue;
      const label = item.classAt(point);
      if (label) {
        const line = document.createElement("p");
        line.textContent = item.layer.title + " · " + label;
        panel.append(line);
      }
    }
    if (panel.childElementCount) L.popup().setLatLng(latlng).setContent(panel).openOn(map);
  });
}
