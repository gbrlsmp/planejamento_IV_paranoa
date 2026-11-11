"use strict";

(() => {
  const directory = "dados-mapas/identificacao/fitofisionomia/";
  let manifestPromise;
  let imageRevision = "";
  let statsPromise;
  const manifest = () => manifestPromise ??= loadData(directory + "manifesto.json")
    .then(config => {
      imageRevision = config.revision || "";
      const gif = document.querySelector('.fit-gif img');
      if (gif && imageRevision) gif.src = directory + "refinamento.gif?v=" + imageRevision;
      return config;
    })
    .catch(error => { manifestPromise = null; throw error; });
  const stats = () => statsPromise ??= loadData(directory + "exploracoes_adicionais.json")
    .catch(error => { statsPromise = null; throw error; });
  const number = new Intl.NumberFormat("pt-BR");

  function bounds(rect) {
    const [left, bottom, right, top] = rect;
    return L.latLngBounds(L.CRS.EPSG3857.unproject(L.point(left, bottom)),
                          L.CRS.EPSG3857.unproject(L.point(right, top)));
  }
  function makeMap(container, extent) {
    const map = L.map(container, { scrollWheelZoom: false, minZoom: 8, maxZoom: 18,
                                   zoomAnimation: false });
    L.control.scale({ imperial: false }).addTo(map);
    const view = bounds(extent);
    map.fitBounds(view, { padding: [12, 12], animate: false });
    map.setMaxBounds(view.pad(.5));
    setTimeout(() => map.invalidateSize(), 100);
    return { map, view };
  }
  function image(file, extent, opacity, alt) {
    const url = directory + file + (imageRevision ? "?v=" + imageRevision : "");
    return L.imageOverlay(url, bounds(extent), { opacity, alt, interactive: false });
  }
  function legend(container, items) {
    container.replaceChildren();
    for (const item of items) {
      const li = document.createElement("li");
      const swatch = document.createElement("span");
      swatch.className = "fit-swatch";
      swatch.style.backgroundColor = item.color;
      li.append(swatch, document.createTextNode(`${item.name} (${item.code})`));
      container.append(li);
    }
  }
  function cell(row, value, header = false) {
    const element = document.createElement(header ? "th" : "td");
    element.textContent = value;
    if (header) element.scope = "row";
    row.append(element);
  }
  function quartiles(values) { return values.map(value => value.toFixed(4).replace(".", ",")).join(" / "); }

  async function extraExploration(root) {
    const info = await stats();
    const codes = { florestal: 3, savanica: 4, campestre: 12, pastagem: 15, campo_alagado: 11 };
    const groups = root.querySelector("[data-extra-summary]");
    const comparison = root.querySelector("[data-extra-camp-past]");
    const check = root.querySelector("[data-extra-check]");
    for (const group of info.grupos) {
      const tr = document.createElement("tr");
      cell(tr, `${group.nome} (${codes[group.id]})`, true); cell(tr, number.format(group.n));
      for (const key of ["seca", "chuva", "delta"]) cell(tr, quartiles(group[key]));
      groups.append(tr);
    }
    for (const slice of info.campestre_pastagem) {
      for (const [key, name] of [["campestre", "Formação campestre (12)"], ["pastagem", "Pastagem (15)"]]) {
        const tr = document.createElement("tr");
        cell(tr, `${slice.seca[0].toFixed(4)}–${slice.seca[1].toFixed(4)}`.replaceAll(".", ","), true);
        cell(tr, name); cell(tr, number.format(slice.classes[key].n));
        cell(tr, quartiles(slice.classes[key].chuva));
        comparison.append(tr);
      }
    }
    for (const group of info.checagem) {
      const tr = document.createElement("tr");
      cell(tr, `${group.nome} (${codes[group.id]})`, true); cell(tr, number.format(group.n));
      for (const key of ["3", "4", "12", "100"]) cell(tr, number.format(group.contagens[key]));
      check.append(tr);
    }
  }

  async function classification(root) {
    const status = root.querySelector("[data-fit-status]");
    try {
      const config = await manifest();
      const stage = makeMap(root.querySelector("[data-stage-map]"), config.overview_bounds);
      stage.map.attributionControl.addAttribution("PlanetScope 2026 · classificação proxy");
      const select = root.querySelector("[data-stage-select]");
      const stageLegend = root.querySelector("[data-stage-legend]");
      let stageImage;
      function updateStage() {
        stageImage?.remove();
        const item = config.stages.find(entry => String(entry.version) === select.value);
        stageImage = image(item.image, config.overview_bounds, 1, item.name).addTo(stage.map);
        legend(stageLegend, item.legend ?? config.classes);
      }
      select.addEventListener("change", updateStage);
      root.querySelector("[data-stage-fit]").addEventListener("click", () => stage.map.fitBounds(stage.view));
      updateStage();
      status.textContent = "Mapa das quatro etapas carregado.";
    } catch (error) { status.textContent = "Falha ao carregar as etapas: " + error.message; }
  }

  async function finalMap(root) {
    const status = root.querySelector("[data-final-status]");
    try {
      const config = await manifest();
      const final = makeMap(root.querySelector("[data-final-map]"), config.overview_bounds);
      final.map.attributionControl.addAttribution("PlanetScope 2026 · proxy 3 m · ZEE-DF · MapBiomas");
      addSatellite(final.map);
      const slider = root.querySelector("[data-final-opacity]");
      const output = root.querySelector("[data-final-opacity-value]");
      const overview = image(config.stages.at(-1).image, config.overview_bounds, .85,
                             "Classificação proxy final, raster 04").addTo(final.map);
      const active = new Map();
      function refresh() {
        const opacity = 1 - Number(slider.value) / 100;
        output.value = slider.value + "%";
        overview.setOpacity(opacity);
        const detailed = final.map.getZoom() >= config.detail_min_zoom;
        overview.getElement()?.classList.toggle("fit-hide-overview", detailed);
        if (detailed) {
          const visible = final.map.getBounds().pad(.15);
          for (const block of config.blocks) {
            const blockBounds = bounds(block.bounds);
            if (!visible.intersects(blockBounds)) continue;
            if (!active.has(block.file)) {
              active.set(block.file, image(block.file, block.bounds, opacity,
                                           "Bloco de 3 m da classificação").addTo(final.map));
            }
          }
        }
        for (const [file, layer] of active) {
          const block = config.blocks.find(item => item.file === file);
          if (!detailed || !final.map.getBounds().pad(.2).intersects(bounds(block.bounds))) {
            layer.remove(); active.delete(file);
          } else layer.setOpacity(opacity);
        }
      }
      final.map.on("moveend zoomend", refresh);
      overview.on("load", refresh);
      slider.addEventListener("input", refresh);
      root.querySelector("[data-final-fit]").addEventListener("click", () => final.map.fitBounds(final.view));
      legend(root.querySelector("[data-fit-legend]"), config.classes);
      refresh();
      status.textContent = "Mapa final carregado. Aproxime para ver os blocos de 3 m.";
    } catch (error) { status.textContent = "Falha ao carregar o mapa final: " + error.message; }
  }

  async function context(root) {
    const status = root.querySelector("[data-context-status]");
    try {
      const config = await manifest();
      const { map, view } = makeMap(root.querySelector("[data-context-map]"), config.overview_bounds);
      map.attributionControl.addAttribution("ZEE-DF · PlanetScope 2026");
      const z = image(config.context.image, config.overview_bounds, .8, "Contexto ZEE-DF").addTo(map);
      const final = image(config.stages.at(-1).image, config.overview_bounds, 1,
                          "Classificação proxy final, raster 04");
      final.addTo(map); final.bringToBack(); final.remove();
      const check = root.querySelector("[data-context-final]");
      check.addEventListener("change", () => {
        if (check.checked) { final.addTo(map); final.bringToBack(); }
        else final.remove();
      });
      const slider = root.querySelector("[data-context-opacity]");
      slider.addEventListener("input", () => {
        z.setOpacity(Number(slider.value) / 100);
        root.querySelector("[data-context-opacity-value]").value = slider.value + "%";
      });
      root.querySelector("[data-context-fit]").addEventListener("click", () => map.fitBounds(view));
      legend(root.querySelector("[data-context-legend]"), config.context.legend);
      status.textContent = "Mapa do ZEE-DF carregado.";
    } catch (error) { status.textContent = "Falha ao carregar o contexto: " + error.message; }
  }

  for (const [selector, handler] of [
    ["[data-extra-ndvi]", extraExploration],
    ["[data-fitofisionomia-results]", classification],
    ["[data-context-results]", context],
  ]) {
    const root = document.querySelector(selector);
    if (!root) continue;
    const details = root.closest("details");
    let started = false;
    if (!details) { handler(root).catch(console.error); continue; }
    details.addEventListener("toggle", () => {
      if (details.open && !started) { started = true; handler(root).catch(console.error); }
    });
  }
  const finalRoot = document.querySelector("[data-final-result]");
  if (finalRoot) {
    const start = () => finalMap(finalRoot).catch(console.error);
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { observer.disconnect(); start(); }
    }, { rootMargin: "500px" });
    observer.observe(finalRoot);
  }
})();
