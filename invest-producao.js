"use strict";

// Produção e diagnóstico compartilham cor, consulta e controles.
(() => {
  function initialize(root) {
    const options = root.dataset || {}, folder = options.folder || "dados-mapas/clima/urban-cooling-2026/";
    const find = selector => root.querySelector(selector);
    const indicator = find("[data-invest-indicator]"), period = find("[data-invest-period]"), scale = find("[data-invest-scale]");
    const mode = find("[data-invest-mode]"), view = find("[data-invest-view]"), zones = find("[data-invest-zones]");
    const references = find("[data-invest-references]");
    const compare = find("[data-invest-compare]"), comparison = find("[data-invest-comparison]");
    const status = find("[data-invest-status]"), retry = find("[data-invest-retry]");
    const maps = [], cache = new Map(), zoneCache = new Map();
    let metadata, base, pending, zoneMetadata, generation = 0, selectionGeneration = 0, syncing = false, started = false;
    const number = (value, digits = 2) => value.toLocaleString("pt-BR", { maximumFractionDigits: digits, minimumFractionDigits: digits });
    const isFragments = () => view?.value === "fragments";
    const representation = () => mode?.value === "classes" ? "classes" : "continuous";
    function ensure() {
      return pending ??= Promise.all([loadData(folder + "manifesto.json"), loadData("mapa-base.json.gz")])
        .then(([m, b]) => { metadata = m;base = b; }).catch(error => { pending = null;throw error; });
    }
    async function imageValues(record) {
      if (!cache.has(record.file)) {
        const operation = new Promise((resolve, reject) => {
          const image = new Image();
          image.onload = () => {
            try {
              const canvas = document.createElement("canvas");canvas.width = image.naturalWidth;canvas.height = image.naturalHeight;
              const context = canvas.getContext("2d", { willReadFrequently: true });context.drawImage(image, 0, 0);
              resolve({ width: canvas.width, height: canvas.height, bytes: context.getImageData(0, 0, canvas.width, canvas.height).data });
            } catch (error) { reject(error); }
          };
          image.onerror = () => reject(new Error("Não foi possível carregar os valores do mapa."));
          image.src = folder + record.file + "?v=" + record.sha256.slice(0, 16);
        }).catch(error => { cache.delete(record.file);throw error; });
        cache.set(record.file, operation);while (cache.size > 4) cache.delete(cache.keys().next().value);
      }
      return cache.get(record.file);
    }
    function coloredImage(values, config, limits, scenario) {
      const lut = InvestRaster.colorTable(config, limits, representation(), scenario), pixels = new Uint8ClampedArray(values.bytes.length);
      for (let p = 0; p < pixels.length; p += 4) {
        const offset = (values.bytes[p] * 256 + values.bytes[p + 1]) * 4;
        pixels[p] = lut[offset];pixels[p + 1] = lut[offset + 1];pixels[p + 2] = lut[offset + 2];pixels[p + 3] = lut[offset + 3];
      }
      const canvas = document.createElement("canvas");canvas.width = values.width;canvas.height = values.height;
      canvas.getContext("2d").putImageData(new ImageData(pixels, values.width, values.height), 0, 0);
      return canvas.toDataURL("image/png");
    }
    function popup(controller, latlng) {
      const point = L.CRS.EPSG3857.project(latlng);
      if (controller.fragments) {
        const id = ClimateFragments.idAt(point);if (!id) return;
        L.popup().setLatLng(latlng).setContent(ClimateFragments.popup(ClimateFragments.record(id), controller.key, controller.period, controller.config)).openOn(controller.map);return;
      }
      if (!controller.values) return;
      const content = document.createElement("div"), title = document.createElement("strong");title.textContent = controller.config.label;content.append(title);
      const value = InvestRaster.valueAt(controller.values, metadata.bounds, point, controller.config), line = document.createElement("p");
      line.textContent = value === null ? "Sem dados neste local." : `${metadata.periods?.[controller.period] || (controller.period === "dia" ? "Dia" : "Noite")}: ${number(value, controller.config.unit ? 2 : 3)} ${controller.config.unit}`;content.append(line);
      if (value !== null && representation() === "classes") {
        const label = document.createElement("p");label.textContent = "Classe relativa: " + InvestRaster.classLabels[InvestRaster.classIndex(value, controller.config, controller.period)];content.append(label);
      }
      if (controller.counts && value !== null) {
        const box = metadata.bounds, x = Math.floor((point.x - box[0]) / (box[2] - box[0]) * controller.counts.width), y = Math.floor((box[3] - point.y) / (box[3] - box[1]) * controller.counts.height);
        const count = controller.counts.bytes[(y * controller.counts.width + x) * 4], p = document.createElement("p");
        p.textContent = count === 255 ? "Contagem indisponível nesta célula." : `${count} de ${controller.config.scenarios[controller.period].count_max} observações válidas no pixel de apoio mais próximo.`;content.append(p);
      }
      const note = document.createElement("small");note.textContent = indicator.value === "lst" ? "Superfície nas passagens diurnas Landsat; grade de 30 m, térmico efetivo de 100 m. Não é temperatura do ar." : "Célula de visualização de 20 m, agregada por média. Estimativa do modelo.";content.append(note);
      L.popup().setLatLng(latlng).setContent(content).openOn(controller.map);
    }
    function createMap(index) {
      if (maps[index]) return maps[index];
      const map = L.map(root.querySelectorAll("[data-invest-map]")[index], { scrollWheelZoom: false, zoomSnap: .25, zoomDelta: .5 });
      const bounds = addMapBase(map, base, false);map.getPane("cartografia").style.zIndex = "340";
      map.createPane("invest-superficie").style.zIndex = "350";map.createPane("invest-limite").style.zIndex = "420";map.getPane("invest-limite").style.pointerEvents = "none";
      L.geoJSON(base.bacia, { pane: "invest-limite", interactive: false, style: { fill: false, color: "#344f40", weight: 1.2 } }).addTo(map);
      L.control.scale({ imperial: false }).addTo(map);map.attributionControl.addAttribution(indicator.value === "lst" ? "Landsat 8/9 · USGS · passagens diurnas" : "InVEST 3.20.2 · seca 2026 · referência A001");map.fitBounds(bounds, { padding: [14, 14] });
      const controller = { map, bounds, overlay: null, values: null, config: null, period: null, fragments: false };maps[index] = controller;
      map.on("moveend", () => {
        if (!compare.checked || syncing || !maps[1 - index]) return;
        const other = maps[1 - index].map, center = map.getCenter();
        if (other.getCenter().equals(center, 1e-8) && other.getZoom() === map.getZoom()) return;
        syncing = true;other.setView(center, map.getZoom(), { animate: false });syncing = false;
      });map.on("click", e => popup(controller, e.latlng));return controller;
    }
    async function render(index, scenario, config, limits, ticket) {
      const fragments = isFragments();let values, display, counts;
      if (fragments) { await ClimateFragments.ensure();display = ClimateFragments.raster(indicator.value, scenario, config, limits, representation()); }
      else {
        values = await imageValues(config.scenarios[scenario]);display = { image: coloredImage(values, config, limits, scenario), bounds: metadata.bounds };
        const record = config.scenarios[scenario];if (record.count_file) counts = await imageValues({ file: record.count_file, sha256: record.count_sha256 });
      }
      if (ticket !== generation || !root.offsetWidth) return;
      const controller = createMap(index), box = display.bounds;
      const bounds = L.latLngBounds(L.CRS.EPSG3857.unproject(L.point(box[0], box[1])), L.CRS.EPSG3857.unproject(L.point(box[2], box[3])));
      controller.overlay?.remove();controller.outline?.remove();controller.zoneLayer?.remove();controller.referenceLayer?.remove();
      controller.overlay = L.imageOverlay(display.image, bounds, { pane: "invest-superficie", opacity: 1, className: representation() === "classes" || fragments ? "climate-pixels" : "" }).addTo(controller.map);
      Object.assign(controller, { values, config, key: indicator.value, period: scenario, fragments, counts });controller.map.closePopup();
      if (references?.checked && metadata.reference_areas_file) {
        const data = await loadData(folder + metadata.reference_areas_file + "?v=" + metadata.reference_areas_sha256.slice(0, 16));
        if (ticket !== generation) return;
        controller.referenceLayer = L.geoJSON(data, { bubblingMouseEvents: false, style: feature => ({ color: feature.properties.area_id === "vicente_pires" ? "#8d554e" : "#2b5125", weight: 2, fillOpacity: .06 }), onEachFeature(feature, layer) {
          const p = document.createElement("p");p.textContent = (feature.properties.tipo === "entorno_500m" ? feature.properties.area_id + " — " : "") + feature.properties.nome + (feature.properties.tipo === "entorno_500m" ? ": entorno comparativo de 500 m, sem equivalência a raio de representatividade meteorológica." : ": área usada no contraste superficial UHI.");layer.bindPopup(p);
        } }).addTo(controller.map);
      }
      if (zones?.checked) {
        const { metadata: diagnostic } = await ClimateFragments.ensure(), record = diagnostic.zones[scenario];
        zoneMetadata = diagnostic;
        if (!zoneCache.has(scenario)) zoneCache.set(scenario, loadData("dados-mapas/clima/diagnostico-2026/" + record.file + "?v=" + record.sha256.slice(0, 16)).catch(e => { zoneCache.delete(scenario);throw e; }));
        const data = await zoneCache.get(scenario);if (ticket !== generation) return;
        controller.zoneLayer = L.geoJSON(data, { bubblingMouseEvents: false, style: { color: "#8d554e", weight: 2, fillOpacity: .08 }, onEachFeature(feature, layer) {
          const p = document.createElement("p");p.textContent = `Zona relativamente quente ${feature.properties.id_zona}: ${number(feature.properties.area_ha)} ha; T > ${number(feature.properties.limiar_C, 3)} °C. Critério: média + 1 desvio padrão, área mínima 2 ha.`;layer.bindPopup(p);
        } }).addTo(controller.map);
      }
    }
    function legend(config, limits, periods) {
      const node = find("[data-invest-legend]");node.replaceChildren();
      const heading = document.createElement("strong");heading.textContent = config.label + (config.unit ? " (" + config.unit + ")" : " · adimensional");node.append(heading);
      if (representation() === "classes") {
        const list = document.createElement("ul");list.className = "climate-class-list";
        InvestRaster.classLabels.forEach((label, i) => {
          const row = document.createElement("li"), swatch = document.createElement("span");swatch.className = "climate-swatch";swatch.style.backgroundColor = InvestRaster.classColors[i];
          const text = document.createElement("span");
          const bin = config.higher_is_better ? i : 3 - i;
          const uniquePeriods = periods.length > 1 && JSON.stringify(config.class_breaks[periods[0]]) === JSON.stringify(config.class_breaks[periods[1]]) ? [periods[0]] : periods;
          text.textContent = label + " · " + uniquePeriods.map(p => {
            const cuts = config.class_breaks[p], interval = bin === 0 ? `< ${number(cuts[0], 3)}` : bin === 3 ? `≥ ${number(cuts[2], 3)}` : `≥ ${number(cuts[bin - 1], 3)} e < ${number(cuts[bin], 3)}`;
            return (uniquePeriods.length > 1 ? (metadata.periods?.[p] || p) + ": " : "") + interval + (config.unit ? " " + config.unit : "");
          }).join("; ");row.append(swatch, text);list.append(row);
        });node.append(list);
        const cuts = document.createElement("p");cuts.className = "climate-note";
        cuts.textContent = periods.map(p => `${metadata.periods?.[p] || p}: cortes ${config.class_breaks[p].map(v => number(v, 3)).join(" / ")}${config.unit ? " " + config.unit : ""}`).join(" · ");node.append(cuts);
      } else {
        const bar = document.createElement("div");bar.className = "invest-legend-bar";bar.style.background = `linear-gradient(to right, ${config.colors.join(",")})`;
        const labels = document.createElement("div");labels.className = "invest-legend-labels";
        for (const value of limits) { const span = document.createElement("span");span.textContent = number(value, config.unit ? 2 : 3);labels.append(span); }node.append(bar, labels);
      }
      const note = document.createElement("p");note.className = "climate-note";
      note.textContent = representation() === "classes" ? config.class_method : (scale.value === "common" ? "Escala comum aos dois cenários. As cores representam valores contínuos, sem classificação de risco." : "Contraste ampliado com os limites deste cenário. As cores não devem ser comparadas diretamente com outro cenário nessa escala.");node.append(note);
      if (isFragments()) { const p = document.createElement("p");p.textContent = "Média de cada fragmento. Fora dos fragmentos e sem dados: transparente. IDs pequenos podem não aparecer em 20 m; consulte todos na tabela.";node.append(p); }
      if (zones?.checked && zoneMetadata) {
        const p = document.createElement("p");p.className = "climate-zone-legend";
        p.textContent = "Contorno das zonas relativamente quentes: " + periods.map(s => `${metadata.periods?.[s] || s}: T > ${number(zoneMetadata.zones[s].threshold_C, 3)} °C`).join("; ") + ". Média + 1 desvio padrão; área mínima 2 ha. O critério é diferente das quatro classes térmicas.";node.append(p);
      }
    }
    async function update() {
      if (!root.offsetWidth) return;
      const ticket = ++generation;status.textContent = "Carregando a superfície climática…";retry.hidden = true;
      try {
        await ensure();if (ticket !== generation) return;
        const config = metadata.indicators[indicator.value], keys = Object.keys(config.scenarios), selected = compare.checked ? keys[0] : period.value;
        if (compare.checked) { scale.value = "common";period.value = keys[0]; }
        scale.disabled = compare.checked || representation() === "classes";period.disabled = compare.checked;comparison.hidden = !compare.checked;
        find(".invest-map-grid").classList.toggle("is-comparing", compare.checked);find("[data-invest-map-title]").textContent = metadata.periods?.[selected] || (selected === "dia" ? "Dia" : "Noite");
        const stats = config.scenarios[selected].native_stats, limits = scale.value === "common" || representation() === "classes" ? config.range : [stats.min, stats.max];
        await render(0, selected, config, limits, ticket);if (compare.checked) await render(1, keys[1], config, limits, ticket);
        if (ticket !== generation) return;legend(config, limits, compare.checked ? keys : [selected]);
        requestAnimationFrame(() => { maps.forEach(c => c.map.invalidateSize());if (compare.checked && maps[1]) maps[1].map.setView(maps[0].map.getCenter(), maps[0].map.getZoom(), { animate: false }); });
        status.textContent = isFragments() ? "Mapa disponível: médias por fragmento. Clique para consultar ou localize um ID na tabela do diagnóstico." : "Mapa disponível. Clique para consultar o valor; use os controles para alternar o indicador e o cenário.";
      } catch (error) { if (ticket === generation) { status.textContent = "Não foi possível carregar o mapa: " + error.message;retry.hidden = false; } }
    }
    [indicator, period, scale, compare, mode, view, zones, references].filter(Boolean).forEach(c => c.addEventListener("change", () => { selectionGeneration++;update(); }));retry.addEventListener("click", update);
    find("[data-invest-fit]").addEventListener("click", () => maps.forEach(c => c.map.fitBounds(c.bounds, { padding: [14, 14] })));
    new IntersectionObserver(entries => { if (!started && entries.some(e => e.isIntersecting) && root.offsetWidth) { started = true;update(); } }, { rootMargin: "150px" }).observe(root);
    document.addEventListener("toggle", e => { if (e.target.open && e.target.contains(root) && root.offsetWidth) { started = true;update(); } }, true);
    window.addEventListener("hashchange", () => { if (root.offsetWidth && started) requestAnimationFrame(() => maps.forEach(c => c.map.invalidateSize())); });
    document.addEventListener("click", e => {
      if (!e.target.closest("[data-report-tabs]")) return;
      requestAnimationFrame(() => { if (!root.offsetWidth) return;started = true;if (!maps[0]?.overlay) update();else maps.forEach(c => c.map.invalidateSize()); });
    });
    document.addEventListener("climate-fragment-select", async event => {
      if (options.explorerId !== event.detail.target || !view) return;
      const selectionTicket = ++selectionGeneration;
      try {
        for (let detail = root.closest("details"); detail;detail = detail.parentElement?.closest("details")) detail.open = true;
        view.value = "fragments";await update();const controller = maps[0];if (!controller || selectionTicket !== selectionGeneration) return;
        const { records } = await ClimateFragments.ensure(), row = records.get(event.detail.id);if (!row) return;
        const layer = await ClimateFragments.outline(controller.map, row.id_frag);
        if (selectionTicket !== selectionGeneration) { layer.remove();return; }
        controller.outline?.remove();controller.outline = layer;
        controller.map.fitBounds(layer.getBounds(), { padding: [30, 30], maxZoom: 17 });
        L.popup().setLatLng(row.center).setContent(ClimateFragments.popup(row, indicator.value, period.value, metadata.indicators[indicator.value])).openOn(controller.map);root.scrollIntoView({ behavior: "smooth", block: "start" });
      } catch (e) { if (selectionTicket === selectionGeneration) status.textContent = "Não foi possível localizar o fragmento: " + e.message; }
    });
  }
  const roots = document.querySelectorAll ? document.querySelectorAll("[data-invest-explorer]") : [document.querySelector("[data-invest-explorer]")].filter(Boolean);roots.forEach(initialize);
})();
