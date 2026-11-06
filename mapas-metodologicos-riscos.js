"use strict";

(() => {
  let shared;
  function data() {
    shared ??= Promise.all([
      loadData("dados-mapas/metodologia-riscos.json"), loadData("mapa-base.json.gz"),
    ]).catch(error => { shared = null; throw error; });
    return shared;
  }
  function number(value) {
    return value.toLocaleString("pt-BR", { maximumFractionDigits: 2 });
  }
  function legend(root, config, view, mode) {
    const item = config[view];
    const content = root.querySelector(".climate-legend-content");
    root.querySelector(".climate-legend-title").textContent = item.title +
      (view === "source" && item.continuous && config.unit ? " (" + config.unit + ")" : "");
    content.replaceChildren();
    const note = document.createElement("p");
    if (mode === "continuo") {
      const bar = document.createElement("div");
      bar.className = "climate-ramp";
      bar.style.background = "linear-gradient(to right, " + config.colors.join(", ") + ")";
      bar.setAttribute("aria-hidden", "true");
      const range = document.createElement("p");
      range.className = "climate-range";
      for (const value of item.continuous.range) {
        const label = document.createElement("span");
        label.textContent = number(value) + (config.unit ? " " + config.unit : "");
        range.append(label);
      }
      note.textContent = view === "source"
        ? "A cor representa o valor da camada de entrada, antes do resumo por fragmento."
        : "A cor representa o valor numérico registrado em cada fragmento.";
      content.append(bar, range);
    } else {
      const list = document.createElement("ul");
      list.className = "climate-class-list";
      for (const [, label, color] of item.classes.entries) {
        const row = document.createElement("li");
        const swatch = document.createElement("span");
        swatch.className = "climate-swatch";
        swatch.style.backgroundColor = color;
        swatch.setAttribute("aria-hidden", "true");
        row.append(swatch, document.createTextNode(label));
        list.append(row);
      }
      content.append(list);
      note.textContent = view === "source" && item.continuous
        ? "Faixas cartográficas da entrada. Para as classes do diagnóstico, escolha Resultado por fragmento."
        : item.note;
    }
    content.append(note);
    if (view === "fragments" && mode === "continuo") {
      const missing = document.createElement("p");
      missing.textContent = "Cinza: fragmento sem dado válido. Áreas externas aos fragmentos são transparentes.";
      content.append(missing);
    } else if (view === "source") {
      const coverage = document.createElement("p");
      coverage.className = "climate-source";
      coverage.textContent = "A imagem mostra a cobertura da camada de entrada; o limite escuro identifica a bacia.";
      content.append(coverage);
    }
  }

  async function initialize(root) {
    if (root.dataset.initialized) return;
    root.dataset.initialized = "true";
    const key = root.dataset.riskMap;
    const view = root.querySelector(".risk-view");
    const mode = root.querySelector(".risk-mode");
    const modeLabel = root.querySelector(".risk-mode-label");
    const fit = root.querySelector(".climate-fit");
    const status = root.querySelector(".climate-status");
    const retry = root.querySelector(".climate-retry");
    const container = root.querySelector(".climate-map");
    const fullMap = root.querySelector(".risk-full-map");
    let map, image, current = 0;
    retry.hidden = true;
    status.textContent = "Carregando o mapa…";
    try {
      const [catalog, base] = await data();
      const config = catalog.indicators[key];
      map = L.map(container, {
        zoomControl: false, scrollWheelZoom: false,
        zoomAnimation: false,
        minZoom: 8, maxZoom: 18, zoomSnap: 0.25, zoomDelta: 0.5,
      });
      L.control.zoom({ zoomInTitle: "Aproximar", zoomOutTitle: "Afastar" }).addTo(map);
      L.control.scale({ imperial: false, maxWidth: 100 }).addTo(map);
      map.attributionControl.addAttribution('<a href="docs/mapas-metodologicos-riscos.md">Dados e método</a>');
      const pane = map.createPane("limite-metodologico");
      pane.style.zIndex = "450";
      pane.style.pointerEvents = "none";
      const basin = L.geoJSON(base.bacia, {
        pane: "limite-metodologico", interactive: false,
        style: { fill: false, color: "#354e41", weight: 1.5 },
      }).addTo(map);
      const limits = basin.getBounds();
      map.setMaxBounds(limits.pad(0.5));
      const fitBasin = () => map.fitBounds(limits, { padding: [18, 18], animate: false });
      fit.addEventListener("click", fitBasin);
      fitBasin();
      const resize = new ResizeObserver(() => map.invalidateSize({ pan: false }));
      resize.observe(container);

      function update() {
        const request = ++current;
        const selectedView = view.value;
        const item = config[selectedView];
        fullMap.href = "mapa.html?indicador=" + key + "&visualizacao=" + (selectedView === "source" ? "contexto" : "fragmentos");
        modeLabel.hidden = !item.continuous;
        if (!item.continuous) mode.value = "classes";
        mode.querySelector('[value="classes"]').textContent = selectedView === "source" && item.continuous
          ? "Faixas cartográficas" : "Classes do diagnóstico";
        const selectedMode = mode.value;
        const layer = selectedMode === "continuo" ? item.continuous : item.classes;
        const [left, bottom, right, top] = layer.bounds;
        const bounds = L.latLngBounds(
          L.CRS.EPSG3857.unproject(L.point(left, bottom)),
          L.CRS.EPSG3857.unproject(L.point(right, top)),
        );
        const next = L.imageOverlay(layer.image, bounds, {
          opacity: 0, className: selectedMode === "classes" ? "climate-pixels" : "",
          alt: item.title + " · " + (selectedMode === "continuo" ? "degradê" : "classes"),
        });
        status.textContent = "Carregando " + (selectedView === "source" ? "a camada de entrada" : "o resultado por fragmento") + "…";
        retry.hidden = true;
        container.setAttribute("aria-busy", "true");
        map.closePopup();
        next.once("load", () => {
          if (request !== current) { next.remove(); return; }
          image?.remove();
          image = next;
          image.setOpacity(1);
          legend(root, config, selectedView, selectedMode);
          root.querySelector(".climate-legend").hidden = false;
          container.setAttribute("aria-busy", "false");
          status.textContent = (selectedView === "source" ? "Camada de entrada" : "Resultado por fragmento") +
            " · " + (selectedMode === "continuo" ? "degradê contínuo" : "classes") + ".";
        });
        next.once("error", () => {
          next.remove();
          if (request !== current) return;
          image?.remove();
          root.querySelector(".climate-legend").hidden = true;
          container.setAttribute("aria-busy", "false");
          status.textContent = "A camada não pôde ser carregada. Tente novamente.";
          retry.hidden = false;
        });
        next.addTo(map);
      }
      view.addEventListener("change", update);
      mode.addEventListener("change", update);
      retry.onclick = update;
      view.disabled = mode.disabled = fit.disabled = false;
      update();
    } catch (error) {
      map?.remove();
      root.dataset.initialized = "";
      console.error("Mapa metodológico de Riscos:", error);
      status.textContent = "O mapa não pôde ser iniciado. Tente novamente.";
      retry.hidden = false;
      retry.onclick = () => initialize(root);
    }
  }
  const roots = document.querySelectorAll("[data-risk-map]");
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        observer.unobserve(entry.target);
        initialize(entry.target);
      }
    }, { rootMargin: "300px" });
    roots.forEach(root => observer.observe(root));
  } else {
    roots.forEach(initialize);
  }
})();
