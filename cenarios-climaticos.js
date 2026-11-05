"use strict";

(() => {
  const directory = "dados-mapas/clima/";
  const scenarios = { dia: "Dia · factors", noite: "Noite · intensity", media: "Média entre dia e noite" };
  const labels = ["Base", "Boa", "Média", "Ruim", "Muito ruim"];
  let sharedData;

  function data() {
    sharedData ??= Promise.all([
      loadData(directory + "catalogo.json"), loadData("mapa-base.json.gz"),
    ]).catch(error => { sharedData = null; throw error; });
    return sharedData;
  }

  function format(value, indicator, exact = false) {
    const digits = exact ? (indicator === "temperatura" ? 8 : 10) : (indicator === "temperatura" ? 1 : 4);
    return value.toLocaleString("pt-BR", { minimumFractionDigits: exact ? 0 : digits, maximumFractionDigits: digits });
  }

  function legend(root, config, scenario, indicator, mode) {
    const target = root.querySelector(".climate-legend-content");
    const title = root.querySelector(".climate-legend-title");
    const record = config.scenarios[scenario];
    const unit = indicator === "temperatura" ? " °C" : "";
    title.textContent = scenarios[scenario];
    target.replaceChildren();
    const note = document.createElement("p");
    if (mode === "continuo") {
      const bar = document.createElement("div");
      bar.className = "climate-ramp";
      bar.style.background = "linear-gradient(to right, " + config.colors.join(", ") + ")";
      bar.setAttribute("aria-hidden", "true");
      const range = document.createElement("p");
      range.className = "climate-range";
      config.range.forEach(value => {
        const span = document.createElement("span");
        span.textContent = format(value, indicator) + unit;
        range.append(span);
      });
      note.textContent = "Escala comum aos três cenários. A mesma cor representa o mesmo valor.";
      const observed = document.createElement("p");
      observed.textContent = "Neste cenário: " + format(record.minimum, indicator) + " a " + format(record.maximum, indicator) + unit + ".";
      target.append(bar, range, note, observed);
    } else {
      const list = document.createElement("ul");
      list.className = "climate-class-list";
      for (let display = 0; display < 5; display++) {
        const index = indicator === "hm" ? 4 - display : display;
        const row = document.createElement("li");
        const swatch = document.createElement("span");
        swatch.className = "climate-swatch";
        swatch.style.backgroundColor = config.colors[index];
        swatch.setAttribute("aria-hidden", "true");
        const text = document.createElement("span");
        const name = document.createElement("strong");
        name.textContent = labels[display];
        const values = document.createElement("span");
        values.textContent = format(record.cuts[index], indicator) + " a " + format(record.cuts[index + 1], indicator) + unit;
        values.title = (index === 0 ? "≥ " : "> ") + format(record.cuts[index], indicator, true) + " e ≤ " + format(record.cuts[index + 1], indicator, true) + unit;
        const area = document.createElement("span");
        const percentage = record.class_percent[index];
        area.className = "climate-area";
        area.textContent = percentage.toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + "% da área válida" + (record.class_counts[index] === 0 ? " · sem ocorrência" : "");
        text.append(name, values, area);
        row.append(swatch, text);
        list.append(row);
      }
      note.textContent = "Intervalos iguais deste cenário. Limites arredondados só na legenda; cortes com precisão original.";
      target.append(list, note);
    }
    const source = document.createElement("p");
    source.className = "climate-source";
    source.textContent = indicator === "hm"
      ? "HM é um índice: valores maiores indicam maior mitigação modelada. Base corresponde à maior mitigação."
      : "Base é a faixa mais fria; classes relativas ao estudo, sem limiares de conforto térmico.";
    target.append(source);
  }

  async function initialize(root) {
    if (root.dataset.initialized) return;
    root.dataset.initialized = "true";
    const indicator = root.dataset.climate;
    const scenarioSelect = root.querySelector(".climate-scenario");
    const modeSelect = root.querySelector(".climate-mode");
    const fit = root.querySelector(".climate-fit");
    const status = root.querySelector(".climate-status");
    const retry = root.querySelector(".climate-retry");
    const canvas = root.querySelector(".climate-map");
    status.textContent = "Carregando o mapa…";
    retry.hidden = true;
    let map;
    try {
      const [catalog, base] = await data();
      const config = catalog.indicators[indicator];
      const [left, bottom, right, top] = catalog.bounds_3857;
      const bounds = L.latLngBounds(
        L.CRS.EPSG3857.unproject(L.point(left, bottom)),
        L.CRS.EPSG3857.unproject(L.point(right, top)),
      );
      map = L.map(canvas, {
        zoomControl: false, scrollWheelZoom: false, minZoom: 8, maxZoom: 17,
        zoomSnap: 0.25, zoomDelta: 0.5,
        maxBounds: bounds.pad(0.35), maxBoundsViscosity: 0.8,
      });
      L.control.zoom({ zoomInTitle: "Aproximar", zoomOutTitle: "Afastar" }).addTo(map);
      L.control.scale({ imperial: false, maxWidth: 100 }).addTo(map);
      map.attributionControl.addAttribution('InVEST v6 · <a href="docs/cenarios-climaticos.md">Dados e método</a>');
      const boundaryPane = map.createPane("climate-boundary");
      boundaryPane.style.zIndex = "450";
      boundaryPane.style.pointerEvents = "none";
      const basin = L.geoJSON(base.bacia, { pane: "climate-boundary", interactive: false, style: { fill: false, color: "#354e41", weight: 1.5 } }).addTo(map);
      function fitBasin() { map.fitBounds(basin.getBounds(), { padding: [18, 18] }); }
      fit.addEventListener("click", fitBasin);
      fitBasin();
      const resize = new ResizeObserver(() => map.invalidateSize({ pan: false }));
      resize.observe(canvas);
      let overlay;
      let request = 0;

      function update() {
        const current = ++request;
        const scenario = scenarioSelect.value;
        const mode = modeSelect.value;
        const record = config.scenarios[scenario];
        const file = mode === "continuo" ? record.continuous : record.classes;
        const next = L.imageOverlay(directory + file, bounds, {
          opacity: 0, className: mode === "classes" ? "climate-pixels" : "",
          alt: (indicator === "temperatura" ? "Temperatura do ar" : "Mitigação térmica HM") + " · " + scenarios[scenario] + " · " + (mode === "classes" ? "cinco classes" : "degradê contínuo"),
        });
        status.textContent = "Carregando " + scenarios[scenario].toLocaleLowerCase("pt-BR") + "…";
        canvas.setAttribute("aria-busy", "true");
        retry.hidden = true;
        next.once("load", () => {
          if (current !== request) { next.remove(); return; }
          overlay?.remove();
          overlay = next;
          next.setOpacity(1);
          basin.bringToFront();
          legend(root, config, scenario, indicator, mode);
          root.querySelector(".climate-legend").hidden = false;
          canvas.setAttribute("aria-busy", "false");
          status.textContent = scenarios[scenario] + " · " + (mode === "classes" ? "cinco classes de igual amplitude" : "degradê em escala comum") + ".";
        });
        next.once("error", () => {
          next.remove();
          if (current !== request) return;
          overlay?.remove();
          root.querySelector(".climate-legend").hidden = true;
          canvas.setAttribute("aria-busy", "false");
          status.textContent = "A camada não pôde ser carregada. Tente novamente.";
          retry.hidden = false;
        });
        next.addTo(map);
      }

      scenarioSelect.addEventListener("change", update);
      modeSelect.addEventListener("change", update);
      retry.onclick = update;
      scenarioSelect.disabled = modeSelect.disabled = fit.disabled = false;
      update();
    } catch (error) {
      console.error("Mapa de cenários climáticos:", error);
      map?.remove();
      root.dataset.initialized = "";
      status.textContent = "O mapa não pôde ser iniciado. Tente novamente.";
      retry.hidden = false;
      retry.onclick = () => initialize(root);
    }
  }

  const roots = document.querySelectorAll("[data-climate]");
  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver(entries => {
      entries.filter(entry => entry.isIntersecting).forEach(entry => {
        observer.unobserve(entry.target);
        initialize(entry.target);
      });
    }, { rootMargin: "300px" });
    roots.forEach(root => observer.observe(root));
  } else {
    roots.forEach(initialize);
  }
})();
