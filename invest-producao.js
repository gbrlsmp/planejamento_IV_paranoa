"use strict";

// Superfícies contínuas atuais. Não lê o catálogo ou os fragmentos históricos.
(() => {
  const root = document.querySelector("[data-invest-explorer]");
  if (!root) return;
  const folder = "dados-mapas/clima/urban-cooling-2026/";
  const indicator = root.querySelector("[data-invest-indicator]");
  const period = root.querySelector("[data-invest-period]");
  const scale = root.querySelector("[data-invest-scale]");
  const compare = root.querySelector("[data-invest-compare]");
  const comparison = root.querySelector("[data-invest-comparison]");
  const status = root.querySelector("[data-invest-status]");
  const retry = root.querySelector("[data-invest-retry]");
  const maps = [];
  const cache = new Map();
  let metadata, base, pending, generation = 0, syncing = false, started = false;
  const number = (value, digits = 2) => value.toLocaleString("pt-BR", { maximumFractionDigits: digits, minimumFractionDigits: digits });

  function ensure() {
    return pending ??= Promise.all([loadData(folder + "manifesto.json"), loadData("mapa-base.json.gz")])
      .then(([m, b]) => { metadata = m; base = b; })
      .catch(error => { pending = null; throw error; });
  }

  async function imageValues(record) {
    if (!cache.has(record.file)) {
      const operation = new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => {
          try {
            const canvas = document.createElement("canvas");
            canvas.width = image.naturalWidth; canvas.height = image.naturalHeight;
            const context = canvas.getContext("2d", { willReadFrequently: true });
            context.drawImage(image, 0, 0);
            resolve({ width: canvas.width, height: canvas.height, bytes: context.getImageData(0, 0, canvas.width, canvas.height).data });
          } catch (error) { reject(error); }
        };
        image.onerror = () => reject(new Error("Não foi possível carregar os valores do mapa."));
        image.src = folder + record.file + "?v=" + record.sha256.slice(0, 16);
      }).catch(error => { cache.delete(record.file); throw error; });
      cache.set(record.file, operation);
      // A comparação precisa de duas imagens; cenários anteriores são liberados.
      while (cache.size > 2) cache.delete(cache.keys().next().value);
    }
    return cache.get(record.file);
  }

  const { valueAt, colorTable } = InvestRaster;

  function coloredImage(values, config, limits) {
    const lut = colorTable(config, limits);
    const pixels = new Uint8ClampedArray(values.width * values.height * 4);
    for (let p = 0; p < pixels.length; p += 4) {
      const code = values.bytes[p] * 256 + values.bytes[p + 1];
      pixels[p] = lut[code * 4]; pixels[p + 1] = lut[code * 4 + 1];
      pixels[p + 2] = lut[code * 4 + 2]; pixels[p + 3] = lut[code * 4 + 3];
    }
    const canvas = document.createElement("canvas");
    canvas.width = values.width; canvas.height = values.height;
    canvas.getContext("2d").putImageData(new ImageData(pixels, values.width, values.height), 0, 0);
    return canvas.toDataURL("image/png");
  }

  function createMap(index) {
    if (maps[index]) return maps[index];
    const canvas = root.querySelectorAll("[data-invest-map]")[index];
    const map = L.map(canvas, { scrollWheelZoom: false, zoomSnap: .25, zoomDelta: .5 });
    const bounds = addMapBase(map, base, false);
    // Água fica sob a superfície climática; não pode esconder seus resultados.
    map.getPane("cartografia").style.zIndex = "340";
    map.createPane("invest-superficie").style.zIndex = "350";
    map.createPane("invest-limite").style.zIndex = "420";
    map.getPane("invest-limite").style.pointerEvents = "none";
    L.geoJSON(base.bacia, { pane: "invest-limite", interactive: false, style: { fill: false, color: "#344f40", weight: 1.2 } }).addTo(map);
    L.control.scale({ imperial: false }).addTo(map);
    map.attributionControl.addAttribution("InVEST 3.20.2 · seca 2026 · base IPE-DF");
    map.fitBounds(bounds, { padding: [14, 14] });
    const controller = { map, bounds, overlay: null, values: null, config: null, period: null };
    maps[index] = controller;
    map.on("moveend", () => {
      if (!compare.checked || syncing || !maps[1 - index]) return;
      const other = maps[1 - index].map, center = map.getCenter();
      if (other.getCenter().equals(center, 1e-8) && other.getZoom() === map.getZoom()) return;
      syncing = true; other.setView(center, map.getZoom(), { animate: false }); syncing = false;
    });
    map.on("click", event => {
      if (!controller.values) return;
      const point = L.CRS.EPSG3857.project(event.latlng), box = metadata.bounds;
      const content = document.createElement("div");
      const title = document.createElement("strong"); title.textContent = controller.config.label; content.append(title);
      const line = document.createElement("p");
      const value = valueAt(controller.values, box, point, controller.config);
      line.textContent = value === null ? "Sem dados neste local." : `${controller.period === "dia" ? "Dia" : "Noite"}: ${number(value, controller.config.unit ? 2 : 3)} ${controller.config.unit}`;
      content.append(line);
      const note = document.createElement("small"); note.textContent = "Célula de visualização de 20 m, agregada por média. Estimativa do modelo."; content.append(note);
      L.popup().setLatLng(event.latlng).setContent(content).openOn(map);
    });
    return controller;
  }

  async function render(index, scenario, config, limits, ticket) {
    const values = await imageValues(config.scenarios[scenario]);
    if (ticket !== generation || !root.offsetWidth) return;
    const controller = createMap(index);
    const image = coloredImage(values, config, limits);
    if (controller.overlay) controller.overlay.remove();
    const box = metadata.bounds;
    const bounds = L.latLngBounds(L.CRS.EPSG3857.unproject(L.point(box[0], box[1])), L.CRS.EPSG3857.unproject(L.point(box[2], box[3])));
    controller.overlay = L.imageOverlay(image, bounds, { pane: "invest-superficie", opacity: 1 }).addTo(controller.map);
    Object.assign(controller, { values, config, period: scenario });
    controller.map.closePopup();
  }

  async function update() {
    if (!root.offsetWidth) return;
    const ticket = ++generation;
    status.textContent = "Carregando a superfície climática…"; retry.hidden = true;
    try {
      await ensure();
      if (ticket !== generation) return;
      const config = metadata.indicators[indicator.value];
      if (compare.checked) { scale.value = "common"; period.value = "dia"; }
      scale.disabled = compare.checked; period.disabled = compare.checked;
      comparison.hidden = !compare.checked;
      root.querySelector(".invest-map-grid").classList.toggle("is-comparing", compare.checked);
      root.querySelector("[data-invest-map-title]").textContent = period.value === "dia" ? "Dia" : "Noite";
      const stats = config.scenarios[period.value].native_stats;
      const limits = scale.value === "common" ? config.range : [stats.min, stats.max];
      await render(0, period.value, config, limits, ticket);
      if (compare.checked) await render(1, "noite", config, limits, ticket);
      if (ticket !== generation) return;
      const legend = root.querySelector("[data-invest-legend]"); legend.replaceChildren();
      const heading = document.createElement("strong"); heading.textContent = config.label + (config.unit ? " (" + config.unit + ")" : " · adimensional");
      const bar = document.createElement("div"); bar.className = "invest-legend-bar"; bar.style.background = `linear-gradient(to right, ${config.colors.join(",")})`;
      const labels = document.createElement("div"); labels.className = "invest-legend-labels";
      for (const value of limits) { const label = document.createElement("span"); label.textContent = number(value, config.unit ? 2 : 3); labels.append(label); }
      const note = document.createElement("p"); note.className = "climate-note";
      note.textContent = scale.value === "common" ? "Escala comum aos dois cenários. As cores representam valores contínuos, sem classificação de risco." : "Contraste ampliado com os limites deste cenário. As cores não devem ser comparadas diretamente com outro cenário nessa escala.";
      legend.append(heading, bar, labels, note);
      requestAnimationFrame(() => {
        maps.forEach(c => c.map.invalidateSize());
        if (compare.checked && maps[1]) maps[1].map.setView(maps[0].map.getCenter(), maps[0].map.getZoom(), { animate: false });
      });
      status.textContent = "Mapa disponível. Clique para consultar o valor; use os controles para alternar o indicador e o cenário.";
    } catch (error) {
      if (ticket !== generation) return;
      status.textContent = "Não foi possível carregar o mapa: " + error.message; retry.hidden = false;
    }
  }

  [indicator, period, scale, compare].forEach(control => control.addEventListener("change", update));
  retry.addEventListener("click", update);
  root.querySelector("[data-invest-fit]").addEventListener("click", () => maps.forEach(c => c.map.fitBounds(c.bounds, { padding: [14, 14] })));
  const observer = new IntersectionObserver(entries => {
    if (!started && entries.some(entry => entry.isIntersecting)) { started = true; update(); }
  }, { rootMargin: "150px" });
  observer.observe(root);
  window.addEventListener("hashchange", () => { if (root.offsetWidth && started) requestAnimationFrame(() => maps.forEach(c => c.map.invalidateSize())); });
  document.addEventListener("click", event => {
    if (!event.target.closest("[data-report-tabs]")) return;
    requestAnimationFrame(() => {
      if (!root.offsetWidth || !started) return;
      if (!maps[0]?.overlay) update();
      else maps.forEach(c => c.map.invalidateSize());
    });
  });
})();
