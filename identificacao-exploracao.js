"use strict";

(() => {
  let pending;
  function data() {
    pending ??= Promise.all([
      loadData("dados-mapas/identificacao/referencias.json"),
      loadData("dados-mapas/identificacao/exploracao.json"),
      loadData("mapa-base.json.gz"),
    ]).then(([references, exploration, base]) => {
      if (!references.revisao || references.revisao !== exploration.revisao) {
        throw new Error("Os arquivos de referências e NDVI pertencem a execuções diferentes.");
      }
      return { references, exploration, base };
    }).catch(error => { pending = null; throw error; });
    return pending;
  }
  const format = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
  const titles = { mapbiomas: "MapBiomas", zee: "ZEE de cobertura vegetal", intersecao: "Interseção entre classes equivalentes" };

  async function referenceMap(root) {
    if (root.dataset.loading) return;
    root.dataset.loading = "true";
    const status = root.querySelector(".ident-status");
    const retry = root.querySelector("[data-reference-retry]");
    let map;
    retry.hidden = true;
    status.textContent = "Carregando as referências…";
    try {
      const { references: config, base } = await data();
      const body = root.querySelector("[data-reference-areas]");
      body.replaceChildren();
      for (const area of config.areas) {
        const row = document.createElement("tr");
        const title = document.createElement("th");
        title.scope = "row";
        title.textContent = `${area.nome} (${area.mapbiomas_codigo})`;
        row.append(title);
        for (const key of ["mapbiomas_ha", "zee_ha", "intersecao_ha"]) {
          const cell = document.createElement("td");
          cell.textContent = format.format(area[key]);
          row.append(cell);
        }
        body.append(row);
      }
      const container = root.querySelector("[data-reference-map]");
      map = L.map(container, { scrollWheelZoom: false, zoomAnimation: false, minZoom: 8, maxZoom: 18 });
      L.control.scale({ imperial: false }).addTo(map);
      map.attributionControl.addAttribution("MapBiomas · ZEE-DF · IPE-DF");
      const basin = L.geoJSON(base.bacia, { interactive: false, style: { fill: false, color: "#354e41", weight: 1.6 } });
      const limits = basin.getBounds();
      const fit = () => map.fitBounds(limits, { padding: [16, 16], animate: false });
      map.setMaxBounds(limits.pad(.5));
      const [left, bottom, right, top] = config.bounds_3857;
      const bounds = L.latLngBounds(L.CRS.EPSG3857.unproject(L.point(left, bottom)), L.CRS.EPSG3857.unproject(L.point(right, top)));
      const select = root.querySelector("[data-reference-layer]");
      const opacity = root.querySelector("[data-reference-opacity]");
      let currentImage, currentCanvas, currentKey, sequence = 0;

      async function update() {
        const request = ++sequence;
        const key = select.value;
        const item = config.camadas[key];
        map.closePopup();
        currentImage?.remove();
        currentCanvas = null;
        root.querySelector("[data-reference-legend]").replaceChildren();
        status.textContent = "Carregando " + titles[key] + "…";
        retry.hidden = true;
        container.setAttribute("aria-busy", "true");
        const overlay = L.imageOverlay(item.imagem + "?v=" + config.revisao, bounds, { opacity: Number(opacity.value), alt: titles[key] });
        overlay.once("load", () => {
          if (request !== sequence) { overlay.remove(); return; }
          currentImage = overlay;
          currentKey = key;
          const image = overlay.getElement();
          currentCanvas = document.createElement("canvas");
          currentCanvas.width = image.naturalWidth;
          currentCanvas.height = image.naturalHeight;
          currentCanvas.getContext("2d").drawImage(image, 0, 0);
          const legend = root.querySelector("[data-reference-legend]");
          for (const entry of item.legenda) {
            const row = document.createElement("li");
            const swatch = document.createElement("span");
            swatch.className = "ident-swatch";
            swatch.style.backgroundColor = entry.cor;
            swatch.setAttribute("aria-hidden", "true");
            const code = key === "mapbiomas" ? entry.codigo
              : key === "intersecao" ? config.areas.find(area => area.nome === entry.nome)?.mapbiomas_codigo
              : null;
            row.append(swatch, document.createTextNode(entry.nome + (code == null ? "" : ` (${code})`)));
            legend.append(row);
          }
          status.textContent = titles[key] + " · representação de 20 m. Clique para consultar.";
          container.setAttribute("aria-busy", "false");
        });
        overlay.once("error", () => {
          overlay.remove();
          if (request !== sequence) return;
          status.textContent = "Não foi possível carregar a imagem. Tente novamente.";
          retry.hidden = false;
          container.setAttribute("aria-busy", "false");
        });
        overlay.addTo(map);
        basin.bringToFront();
      }
      select.addEventListener("change", update);
      opacity.addEventListener("input", () => currentImage?.setOpacity(Number(opacity.value)));
      root.querySelector("[data-reference-fit]").addEventListener("click", fit);
      retry.onclick = update;
      map.on("click", event => {
        if (!currentCanvas) return;
        const point = L.CRS.EPSG3857.project(event.latlng);
        const x = Math.floor((point.x - left) / (right - left) * currentCanvas.width);
        const y = Math.floor((top - point.y) / (top - bottom) * currentCanvas.height);
        if (x < 0 || y < 0 || x >= currentCanvas.width || y >= currentCanvas.height) return;
        const rgba = currentCanvas.getContext("2d").getImageData(x, y, 1, 1).data;
        const color = "#" + [...rgba.slice(0, 3)].map(v => v.toString(16).padStart(2, "0")).join("");
        const entry = rgba[3] ? config.camadas[currentKey].legenda.find(e => e.cor.toLowerCase() === color) : null;
        const content = document.createElement("div");
        const label = document.createElement("strong");
        label.textContent = titles[currentKey];
        const text = document.createElement("p");
        text.textContent = entry?.nome ?? (currentKey === "intersecao" ? "Sem interseção equivalente representada nesta célula." : "Sem classe representada nesta célula.");
        content.append(label, text);
        if (currentKey === "intersecao" && entry?.nome === "Campo alagado e área pantanosa") {
          const note = document.createElement("p");
          note.textContent = config.nota_areas_umidas;
          content.append(note);
        }
        const note = document.createElement("small");
        note.textContent = "Consulta da representação reduzida; não substitui a geometria integral.";
        content.append(note);
        L.popup().setLatLng(event.latlng).setContent(content).openOn(map);
      });
      basin.addTo(map);
      fit();
      const resize = new ResizeObserver(() => map.invalidateSize({ pan: false }));
      resize.observe(container);
      update();
    } catch (error) {
      map?.remove();
      status.textContent = "As referências não puderam ser carregadas. " + error.message;
      root.dataset.loading = "";
      retry.hidden = false;
      retry.onclick = () => referenceMap(root);
    }
  }

  function chart(canvas, square = false) {
    const width = Math.max(240, canvas.clientWidth);
    const height = canvas.clientHeight;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);
    ctx.fillStyle = "#fff";
    ctx.fillRect(0, 0, width, height);
    let plotWidth = width - 72, plotHeight = height - 58;
    if (square) plotWidth = plotHeight = Math.min(plotWidth, plotHeight);
    const left = square ? (width - plotWidth) / 2 : 52;
    return { ctx, width, height, left, top: 12, plotWidth, plotHeight };
  }
  function axes(c, ymax, yLabel) {
    const { ctx, left, top, plotWidth: w, plotHeight: h } = c;
    const x = v => left + (v + 1) / 2 * w;
    const y = v => top + h - v / ymax * h;
    ctx.font = "12px system-ui, sans-serif";
    ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const tick = ymax * i / 4;
      ctx.strokeStyle = "#e5e8e2";
      ctx.beginPath(); ctx.moveTo(left, y(tick)); ctx.lineTo(left + w, y(tick)); ctx.stroke();
      ctx.fillStyle = "#4c5751";
      ctx.textAlign = "right";
      ctx.fillText(tick.toLocaleString("pt-BR", { maximumFractionDigits: 1 }), left - 7, y(tick) + 4);
    }
    for (const tick of [-1, -.5, 0, .5, 1]) {
      ctx.textAlign = "center";
      ctx.fillStyle = "#4c5751";
      ctx.fillText(tick.toLocaleString("pt-BR"), x(tick), top + h + 20);
    }
    ctx.strokeStyle = "#536458";
    ctx.beginPath(); ctx.moveTo(left, top); ctx.lineTo(left, top + h); ctx.lineTo(left + w, top + h); ctx.stroke();
    ctx.textAlign = "center";
    ctx.fillStyle = "#34483b";
    ctx.fillText("NDVI", left + w / 2, top + h + 42);
    ctx.save(); ctx.translate(left - 39, top + h / 2); ctx.rotate(-Math.PI / 2); ctx.fillText(yLabel, 0, 0); ctx.restore();
    return { x, y };
  }

  function appendSvg(parent, tag, attributes, label) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
    if (label) element.textContent = label;
    parent.append(element);
    return element;
  }

  function drawSankey(root, active, bins) {
    root.hidden = !active.length;
    if (root.hidden) return;

    // Os limites coincidem com bordas dos histogramas, para preservar as contagens.
    const limits = [-1, .2, .35, .45, .55, .65, .75, 1];
    const edges = limits.map(limit => bins.findIndex(bin => Math.abs(bin - limit) < 1e-8));
    if (edges.includes(-1)) throw new Error("Os intervalos do histograma são incompatíveis com o Sankey.");
    const labels = limits.slice(1).map((upper, index) => {
      const lower = limits[index];
      return format.format(lower) + " a " + (upper === 1 ? "" : "<") + format.format(upper);
    });
    const sum = values => values.reduce((total, value) => total + value, 0);
    const percent = (count, group) => 100 * count / group.n_pares_validos;
    const points = new Intl.NumberFormat("pt-BR");
    const groups = active.map(group => ({
      ...group,
      bands: labels.map((label, i) => {
        const count = season => sum(group.histogramas[season].slice(edges[i], edges[i + 1]));
        return { label, seca: count("seca"), chuva: count("chuva") };
      }),
    }));

    const svg = root.querySelector("svg");
    const body = root.querySelector("tbody");
    svg.replaceChildren();
    body.replaceChildren();
    for (const group of groups) {
      for (const band of group.bands) {
        const row = body.insertRow();
        const name = document.createElement("th");
        name.scope = "row";
        name.textContent = group.nome;
        row.append(name);
        for (const value of [band.label, format.format(percent(band.seca, group)), points.format(band.seca),
          format.format(percent(band.chuva, group)), points.format(band.chuva)]) {
          row.insertCell().textContent = value;
        }
      }
    }

    const width = 690;
    const scale = .55;
    const gap = 12;
    const bar = 9;
    const groupHeight = 100 * scale;
    const middleLeft = 264, middleRight = 426;
    let bandsHeight = 0;
    const rows = labels.map((label, i) => {
      const total = season => scale * sum(groups.map(group => percent(group.bands[i][season], group)));
      const seca = total("seca"), chuva = total("chuva");
      const height = Math.max(20, seca, chuva);
      const row = { label, seca, chuva, height, y: bandsHeight };
      bandsHeight += height + gap;
      return row;
    });
    bandsHeight -= gap;
    const groupsHeight = groups.length * (groupHeight + gap) - gap;
    const plotHeight = Math.max(bandsHeight, groupsHeight);
    const groupTop = 44 + (plotHeight - groupsHeight) / 2;
    const bandTop = 44 + (plotHeight - bandsHeight) / 2;
    svg.setAttribute("viewBox", `0 0 ${width} ${Math.ceil(plotHeight + 62)}`);

    const headings = { class: "ident-sankey-heading", y: 24 };
    appendSvg(svg, "text", { ...headings, x: 12 }, "Seca · 30/07/2026");
    appendSvg(svg, "text", { ...headings, x: width / 2, "text-anchor": "middle" }, "Grupos de referência");
    appendSvg(svg, "text", { ...headings, x: width - 12, "text-anchor": "end" }, "Chuva · 17/01/2026");

    for (const [season, date, isDry, x] of [["seca", "Seca", true, 108], ["chuva", "Chuva", false, 573]]) {
      const offsets = rows.map(row => bandTop + row.y + (row.height - row[season]) / 2);
      for (const [groupIndex, group] of groups.entries()) {
        let groupY = groupTop + groupIndex * (groupHeight + gap);
        for (const [i, band] of group.bands.entries()) {
          const count = band[season];
          if (!count) continue;
          const share = percent(count, group);
          const thickness = scale * share;
          const [x1, x2] = isDry ? [x + bar, middleLeft] : [middleRight, x];
          const [y1, y2] = isDry ? [offsets[i], groupY] : [groupY, offsets[i]];
          const mid = (x1 + x2) / 2;
          const d = `M ${x1} ${y1} C ${mid} ${y1}, ${mid} ${y2}, ${x2} ${y2}
            v ${thickness} C ${mid} ${y2 + thickness}, ${mid} ${y1 + thickness}, ${x1} ${y1 + thickness} Z`;
          const ribbon = appendSvg(svg, "path", { d, fill: group.cor, class: "ident-sankey-ribbon" });
          appendSvg(ribbon, "title", {}, `${date} · ${group.nome} · NDVI ${band.label} · ${format.format(share)}% · ${points.format(count)} pontos`);
          groupY += thickness;
          offsets[i] += thickness;
        }
      }
      for (const row of rows) {
        const center = bandTop + row.y + row.height / 2;
        if (row[season]) appendSvg(svg, "rect", { x, y: center - row[season] / 2, width: bar, height: row[season], opacity: .75 });
        appendSvg(svg, "text", { x: isDry ? x - 8 : x + bar + 8, y: center, "dominant-baseline": "middle",
          "text-anchor": isDry ? "end" : "start" }, row.label);
      }
    }

    for (const [index, group] of groups.entries()) {
      const y = groupTop + index * (groupHeight + gap);
      const box = { x: middleLeft, y, width: middleRight - middleLeft, height: groupHeight };
      appendSvg(svg, "rect", { ...box, fill: group.cor, "fill-opacity": .14, stroke: group.cor, rx: 4 });
      const label = document.createElement("div");
      label.className = "ident-sankey-group";
      label.textContent = group.nome;
      appendSvg(svg, "foreignObject", box).append(label);
    }
  }

  async function ndviCharts(root) {
    if (root.dataset.loading) return;
    root.dataset.loading = "true";
    const status = root.querySelector(".ident-status");
    const retry = root.querySelector("[data-ndvi-retry]");
    retry.hidden = true;
    status.textContent = "Carregando os gráficos…";
    try {
      const { exploration: report } = await data();
      const codes = { campestre: 12, savanica: 4, florestal: 3, campo_alagado: 11, pastagem: 15 };
      for (const [key, group] of Object.entries(report.grupos)) {
        if (key === "pastagem") group.nome = `Pastagem (${codes[key]}) — comparação`;
        else if (!group.nome.endsWith(`(${codes[key]})`)) group.nome += ` (${codes[key]})`;
      }
      const groups = Object.entries(report.grupos);
      const controls = root.querySelector("[data-ndvi-groups]");
      controls.replaceChildren();
      for (const [key, group] of groups) {
        const label = document.createElement("label");
        const input = document.createElement("input");
        input.type = "checkbox"; input.value = key; input.checked = group.n_pares_validos > 0;
        input.disabled = group.n_pares_validos === 0;
        const swatch = document.createElement("span");
        swatch.className = "ident-swatch"; swatch.style.backgroundColor = group.cor; swatch.setAttribute("aria-hidden", "true");
        label.append(input, swatch, document.createTextNode(group.nome + (group.n_pares_validos ? "" : " — sem pares válidos")));
        controls.append(label);
      }
      const dry = root.querySelector("[data-ndvi-dry]");
      const rain = root.querySelector("[data-ndvi-rain]");
      const scatter = root.querySelector("[data-ndvi-scatter]");
      const sankey = root.querySelector("[data-ndvi-sankey]");
      const selectedGroups = () => [...controls.querySelectorAll("input:checked")].map(input => report.grupos[input.value]);

      function draw() {
        const active = selectedGroups();
        let ymax = 1;
        for (const group of active) {
          for (const season of ["seca", "chuva"]) {
            ymax = Math.max(ymax, ...group.histogramas[season].map(n => 100 * n / group.n_pares_validos));
          }
        }
        ymax = Math.ceil(ymax / 5) * 5;
        for (const [canvas, season] of [[dry, "seca"], [rain, "chuva"]]) {
          const c = chart(canvas);
          const { ctx } = c;
          const { x, y } = axes(c, ymax, "Pares do grupo (%)");
          for (const group of active) {
            ctx.strokeStyle = group.cor;
            ctx.lineWidth = 2;
            ctx.beginPath();
            group.histogramas[season].forEach((n, i) => {
              const value = 100 * n / group.n_pares_validos;
              const a = x(report.amostragem.bins[i]);
              const b = x(report.amostragem.bins[i + 1]);
              if (i === 0) ctx.moveTo(a, y(value)); else ctx.lineTo(a, y(value));
              ctx.lineTo(b, y(value));
            });
            ctx.stroke();
          }
        }
        const c = chart(scatter, true);
        const { ctx, left, top, plotWidth: w, plotHeight: h } = c;
        const x = v => left + (v + 1) / 2 * w;
        const y = v => top + (1 - v) / 2 * h;
        ctx.font = "12px system-ui, sans-serif";
        for (const v of [-1, -.5, 0, .5, 1]) {
          ctx.strokeStyle = "#e5e8e2"; ctx.lineWidth = 1;
          ctx.beginPath(); ctx.moveTo(x(v), top); ctx.lineTo(x(v), top + h); ctx.moveTo(left, y(v)); ctx.lineTo(left + w, y(v)); ctx.stroke();
          ctx.fillStyle = "#4c5751"; ctx.textAlign = "center"; ctx.fillText(v.toLocaleString("pt-BR"), x(v), top + h + 20);
          ctx.textAlign = "right"; ctx.fillText(v.toLocaleString("pt-BR"), left - 7, y(v) + 4);
        }
        ctx.strokeStyle = "#7d8980"; ctx.setLineDash([4, 4]);
        ctx.beginPath(); ctx.moveTo(x(-1), y(-1)); ctx.lineTo(x(1), y(1)); ctx.stroke(); ctx.setLineDash([]);
        ctx.save(); ctx.beginPath(); ctx.rect(left, top, w, h); ctx.clip();
        // Intercalar grupos reduz o encobrimento sistemático pelo último grupo.
        const count = Math.max(0, ...active.map(g => g.pontos_grafico.length));
        ctx.globalAlpha = .35;
        for (let i = 0; i < count; i++) for (const group of active) {
          const point = group.pontos_grafico[i];
          if (!point) continue;
          ctx.fillStyle = group.cor; ctx.beginPath(); ctx.arc(x(point[0]), y(point[1]), 1.6, 0, Math.PI * 2); ctx.fill();
        }
        ctx.restore();
        ctx.strokeStyle = "#536458"; ctx.strokeRect(left, top, w, h);
        ctx.fillStyle = "#34483b"; ctx.textAlign = "center";
        ctx.fillText("NDVI da seca", left + w / 2, top + h + 43);
        ctx.save(); ctx.translate(left - 39, top + h / 2); ctx.rotate(-Math.PI / 2); ctx.fillText("NDVI da chuva", 0, 0); ctx.restore();
        status.textContent = active.length ? "Gráficos da nova execução · marque os grupos que deseja comparar." : "Selecione pelo menos um grupo para comparar.";
      }
      function update() {
        draw();
        drawSankey(sankey, selectedGroups(), report.amostragem.bins);
      }
      update();
      controls.addEventListener("change", update);
      const resize = new ResizeObserver(draw);
      for (const canvas of [dry, rain, scatter]) resize.observe(canvas);
    } catch (error) {
      status.textContent = "Os gráficos não puderam ser carregados. " + error.message;
      root.dataset.loading = "";
      retry.hidden = false;
      retry.onclick = () => ndviCharts(root);
    }
  }

  for (const [selector, initialize] of [["[data-reference-results]", referenceMap], ["[data-ndvi-results]", ndviCharts]]) {
    for (const root of document.querySelectorAll(selector)) {
      const details = root.closest("details");
      const observer = new IntersectionObserver(entries => {
        if (details.open && entries.some(entry => entry.isIntersecting)) initialize(root);
      }, { rootMargin: "200px" });
      observer.observe(root);
      details.addEventListener("toggle", () => {
        if (details.open) initialize(root);
      });
    }
  }
})();
