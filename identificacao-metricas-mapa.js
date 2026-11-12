"use strict";

// As cores são uma representação dos valores originais, sem novos cálculos de métricas.
async function createFragmentMetricsMap(root, map) {
  const folder = "dados-mapas/identificacao/metricas-mapa/";
  const metric = root.querySelector("[data-map-metric]");
  const scenario = root.querySelector("[data-map-scenario]");
  const show = root.querySelector("[data-map-show]");
  const status = root.querySelector("[data-map-status]");
  const legend = root.querySelector("[data-map-legend]");
  const heading = root.querySelector("[data-map-legend-title]");
  const note = root.querySelector("[data-map-metric-note]");
  const [{ manifest, scenarios }, spatial] = await Promise.all([
    loadMakurhiniMetrics(), loadData(folder + "manifesto.json"),
  ]);
  const img = new Image();
  await new Promise((resolve, reject) => {
    img.onload = resolve;
    img.onerror = () => reject(new Error("IDs indisponíveis"));
    img.src = folder + spatial.arquivo + "?v=" + spatial.revisao;
  });
  if (img.naturalWidth !== spatial.largura || img.naturalHeight !== spatial.altura) {
    throw new Error("Dimensões inesperadas");
  }
  const canvas = document.createElement("canvas");
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) throw new Error("Canvas indisponível");
  ctx.drawImage(img, 0, 0);
  const original = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  const ids = new Uint16Array(canvas.width * canvas.height);
  for (let i = 0; i < ids.length; i++) {
    ids[i] = original[i*4]*256 + original[i*4+1];
    if (ids[i] && scenarios.some(s => !s.records.has(ids[i]))) throw new Error("ID sem métricas");
  }
  const [west, south, east, north] = spatial.bounds;
  const crs = L.CRS.EPSG3857;
  const bounds = [crs.unproject(L.point(west, south)), crs.unproject(L.point(east, north))];
  let overlay;
  let current;
  const palette = ["#c4cc95", "#86a58f", "#4b6a40", "#2b5125"];
  const number = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  const exact = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 12 });
  const dependent = new Set(["CA", "CAPercent", "EdgePercent"]);
  metric.replaceChildren();
  manifest.indicadores.forEach(info => {
    const option = document.createElement("option");
    option.value = info.campo;
    option.textContent = info.nome + " (" + info.campo + ")";
    metric.append(option);
  });

  function redraw() {
    map.closePopup();
    const index = manifest.indicadores.findIndex(info => info.campo === metric.value);
    const info = manifest.indicadores[index];
    const records = scenarios.find(s => s.borda === Number(scenario.value)).records;
    const isArea = info.campo === "Area" || info.campo === "CA";
    const isPercent = info.unidade === "%";
    const hasZero = dependent.has(info.campo);
    let edges;
    let scale;
    if (isArea) {
      edges = [10000, 100000, 1000000];
      scale = "Faixas de área; legenda em hectares.";
    } else if (isPercent) {
      edges = [25, 50, 75];
      scale = "Faixas fixas de percentual.";
    } else {
      const sorted = Array.from(records.values(), row => row[index]).sort((a, b) => a-b);
      const maximum = sorted[sorted.length-1];
      edges = [...new Set([.25, .5, .75].map(q => sorted[Math.ceil(q*sorted.length)-1]))]
        .filter(value => value < maximum);
      scale = "Faixas pelos quartis dos 46.876 fragmentos; não são critérios de classificação da IV.";
    }
    const colors = hasZero ? ["#e1e1e1", ...palette] : palette;
    function category(value) {
      if (hasZero && value === 0) return 0;
      const position = edges.findIndex(edge => value <= edge);
      return (position < 0 ? edges.length : position) + (hasZero ? 1 : 0);
    }
    const lookup = new Uint8Array(manifest.fragmentos+1);
    records.forEach((row, id) => { lookup[id] = category(row[index]); });
    const rgb = colors.map(color => color.slice(1).match(/../g).map(part => parseInt(part, 16)));
    const pixels = ctx.createImageData(canvas.width, canvas.height);
    for (let i = 0; i < ids.length; i++) {
      if (!ids[i]) continue;
      const color = rgb[lookup[ids[i]]];
      const p = i*4;
      pixels.data[p] = color[0];
      pixels.data[p+1] = color[1];
      pixels.data[p+2] = color[2];
      pixels.data[p+3] = 255;
    }
    ctx.putImageData(pixels, 0, 0);
    const url = canvas.toDataURL("image/png");
    if (!overlay) {
      overlay = L.imageOverlay(url, bounds, { pane: "tema-relatorio", opacity: 1, className: "mapa-classe" });
    } else overlay.setUrl(url);
    if (show.checked) overlay.addTo(map);
    const display = value => exact.format(isArea ? value/10000 : value);
    const unit = isArea ? "ha" : info.unidade === "adimensional" ? "" : info.unidade;
    const labels = edges.map((edge, i) =>
      (i ? "Acima de " + display(edges[i-1]) + " até " : hasZero ? "Acima de 0 até " : "Até ") + display(edge));
    labels.push(edges.length ? "Acima de " + display(edges[edges.length-1]) : "Todos os valores");
    if (hasZero) labels.unshift("0");
    heading.textContent = info.nome + (dependent.has(info.campo) ? " · borda de " + scenario.value + " m" : "");
    legend.replaceChildren();
    labels.forEach((label, i) => {
      const row = document.createElement("li");
      const swatch = document.createElement("span");
      swatch.className = "ident-class-swatch";
      swatch.style.backgroundColor = colors[i];
      swatch.setAttribute("aria-hidden", "true");
      row.append(swatch, document.createTextNode(label + (unit ? " " + unit : "")));
      legend.append(row);
    });
    scenario.disabled = !dependent.has(info.campo);
    note.textContent = scale + (scenario.disabled ? " Esta métrica é igual nos cenários de 45 m e 90 m." :
      " Cenário de borda de " + scenario.value + " m.") +
      (info.campo === "CA" ? " As cores indicam a área de núcleo atribuída ao fragmento inteiro; não delimitam o núcleo." : "") +
      (info.campo === "PARA" ? " PARA = Area / Perimeter, conforme a execução adotada." : "");
    current = { info, records, index };
    status.textContent = "Clique em um fragmento para consultar seu ID e o valor da métrica selecionada.";
  }
  metric.disabled = false;
  metric.value = "Area";
  metric.onchange = redraw;
  scenario.onchange = redraw;
  show.disabled = false;
  show.onchange = () => {
    map.closePopup();
    if (show.checked) overlay.addTo(map);
    else overlay.remove();
  };
  map.on("click", event => {
    const point = crs.project(event.latlng);
    if (!show.checked || point.x < west || point.x >= east || point.y <= south || point.y > north) {
      map.closePopup(); return;
    }
    const x = Math.floor((point.x-west)/(east-west)*canvas.width);
    const y = Math.floor((north-point.y)/(north-south)*canvas.height);
    const id = ids[y*canvas.width+x];
    if (!id) { map.closePopup(); return; }
    const content = document.createElement("div");
    const title = document.createElement("strong");
    title.textContent = "Fragmento " + id;
    const value = document.createElement("p");
    value.textContent = current.info.nome + ": " + number.format(current.records.get(id)[current.index]) +
      (current.info.unidade === "adimensional" ? "" : " " + current.info.unidade);
    const detail = document.createElement("p");
    detail.textContent = dependent.has(current.info.campo) ? "Borda de " + scenario.value + " m." : "Mesmo valor em 45 m e 90 m.";
    content.append(title, value, detail);
    L.popup().setLatLng(event.latlng).setContent(content).openOn(map);
  });
  redraw();
}
