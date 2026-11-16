"use strict";

// A base atual é independente do catálogo de fragmentos do diagnóstico histórico.
globalThis.ClimateFragments = (() => {
  const folder = "dados-mapas/clima/diagnostico-2026/";
  let pending, metadata, rows, records, ids;
  const outlines = new Map();
  const number = (n, digits = 2) => n == null ? "Sem dados" : n.toLocaleString("pt-BR", { maximumFractionDigits: digits });
  function image(path) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        try {
          const canvas = document.createElement("canvas"); canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
          const context = canvas.getContext("2d", { willReadFrequently: true });context.drawImage(img, 0, 0);
          resolve({ width: canvas.width, height: canvas.height, bytes: context.getImageData(0, 0, canvas.width, canvas.height).data });
        } catch (e) { reject(e); }
      };
      img.onerror = () => reject(new Error("Não foi possível carregar os identificadores dos fragmentos."));img.src = path;
    });
  }
  function ensure() {
    return pending ??= loadData(folder + "manifesto.json").then(async m => {
      const [data, pixels] = await Promise.all([loadData(folder + m.data_file + "?v=" + m.data_sha256.slice(0, 16)), image(folder + m.ids_file + "?v=" + m.ids_sha256.slice(0, 16))]);
      if (data.rows.length !== m.count) throw new Error("Contagem de fragmentos divergente.");
      metadata = m;rows = data.rows;records = new Map(rows.map(r => [r.id_frag, r]));ids = pixels;
      return { metadata, rows, records, ids };
    }).catch(e => { pending = null;throw e; });
  }
  function idAt(point) {
    const b = metadata.bounds, x = Math.floor((point.x - b[0]) / (b[2] - b[0]) * ids.width), y = Math.floor((b[3] - point.y) / (b[3] - b[1]) * ids.height);
    if (x < 0 || y < 0 || x >= ids.width || y >= ids.height) return null;
    const p = (y * ids.width + x) * 4;
    return ids.bytes[p] * 65536 + ids.bytes[p + 1] * 256 + ids.bytes[p + 2] || null;
  }
  function raster(key, scenario, config, limits, mode) {
    const lut = new Uint8ClampedArray((metadata.count + 1) * 4);
    for (const row of rows) lut.set(InvestRaster.valueColor(row[`${key}_${scenario}_mean`], config, limits, mode, scenario), row.id_frag * 4);
    const pixels = new Uint8ClampedArray(ids.bytes.length);
    for (let p = 0; p < pixels.length; p += 4) {
      const id = ids.bytes[p] * 65536 + ids.bytes[p + 1] * 256 + ids.bytes[p + 2];
      const offset = id * 4;pixels[p] = lut[offset];pixels[p + 1] = lut[offset + 1];pixels[p + 2] = lut[offset + 2];pixels[p + 3] = lut[offset + 3];
    }
    const canvas = document.createElement("canvas");canvas.width = ids.width;canvas.height = ids.height;
    canvas.getContext("2d").putImageData(new ImageData(pixels, ids.width, ids.height), 0, 0);
    return { image: canvas.toDataURL("image/png"), bounds: metadata.bounds };
  }
  function popup(row, key, scenario, config) {
    const node = document.createElement("div");
    const title = document.createElement("strong");title.textContent = `Fragmento ${row.id_frag} · ${row.cat_iv || row.form_pred}`;node.append(title);
    const p = document.createElement("p");p.textContent = `${row.form_pred} · área: ${number(row.area_m2 / 10000, 4)} ha · ${row.classe_avu}`;node.append(p);
    const values = document.createElement("p");values.textContent = `${config.label}: média ${number(row[`${key}_${scenario}_mean`], 3)} ${config.unit}; mínimo ${number(row[`${key}_${scenario}_min`], 3)}; máximo ${number(row[`${key}_${scenario}_max`], 3)}; desvio padrão ${number(row[`${key}_${scenario}_sd`], 3)}.`;node.append(values);
    const quality = document.createElement("p");quality.textContent = `Classe relativa: ${row[`${key}_${scenario}_classe`]}. Cobertura válida: ${number(key === "lst" ? row[`lst_${scenario}_coverage_pct`] : row.cobertura_percentual)}%.`;node.append(quality);
    const note = document.createElement("small");note.textContent = "Estatísticas da geometria integral. O contorno exibido é simplificado; as cores de 20 m podem omitir fragmentos pequenos. Consulte qualquer ID na tabela.";node.append(note);
    return node;
  }
  async function outline(map, id) {
    const batch = String(Math.floor((id - 1) / 256)).padStart(3, "0");
    if (!outlines.has(batch)) outlines.set(batch, loadData(folder + `fragmentos-${batch}.geojson.gz`).catch(e => { outlines.delete(batch);throw e; }));
    const data = await outlines.get(batch), feature = data.features.find(f => f.properties.id_frag === id);
    if (!feature) throw new Error("Contorno do fragmento não localizado.");
    const layer = L.geoJSON(feature, { style: { color: "#2b5125", weight: 3, fill: false }, interactive: false }).addTo(map);
    return layer;
  }
  function initializeTable(root) {
    const input = root.querySelector("[data-fragment-search]"), body = root.querySelector("tbody"), status = root.querySelector("[data-fragment-table-status]");
    const previous = root.querySelector("[data-fragment-previous]"), next = root.querySelector("[data-fragment-next]");
    let page = 0, filtered = [], started = false;
    function render() {
      const term = input.value.trim().toLocaleLowerCase("pt-BR");
      filtered = rows.filter(r => `${r.id_frag} ${r.cat_iv} ${r.form_pred} ${r.classe_avu}`.toLocaleLowerCase("pt-BR").includes(term));
      const pages = Math.max(1, Math.ceil(filtered.length / 40));page = Math.min(page, pages - 1);body.replaceChildren();
      for (const row of filtered.slice(page * 40, page * 40 + 40)) {
        const tr = document.createElement("tr");
        const id = document.createElement("td"), button = document.createElement("button");button.type = "button";button.dataset.fragmentId = row.id_frag;button.textContent = String(row.id_frag);button.title = "Localizar fragmento no mapa do diagnóstico";id.append(button);tr.append(id);
        for (const value of [row.cat_iv + " · " + row.form_pred, number(row.area_m2 / 10000, 4), number(row.cc_dia_mean, 3), number(row.hm_dia_mean, 3), number(row.t_dia_mean), row.t_dia_classe, number(row.t_noite_mean), row.t_noite_classe, number(row.lst_seca_mean), number(row.lst_chuva_mean)]) {
          const td = document.createElement("td");td.textContent = value;tr.append(td);
        }
        body.append(tr);
      }
      previous.disabled = page === 0;next.disabled = page + 1 >= pages;
      status.textContent = `${number(filtered.length, 0)} fragmentos · página ${page + 1} de ${pages}. Clique no ID para localizar no mapa. CSV inclui os 46.876 registros e todas as estatísticas/classes.`;
    }
    input.addEventListener("input", () => { page = 0;if (started) render(); });
    previous.addEventListener("click", () => { page--;render(); });next.addEventListener("click", () => { page++;render(); });
    body.addEventListener("click", e => {
      const button = e.target.closest("[data-fragment-id]");if (!button) return;
      const target = root.querySelector("[data-fragment-target]").value;
      document.dispatchEvent(new CustomEvent("climate-fragment-select", { detail: { id: Number(button.dataset.fragmentId), target } }));
    });
    const start = async () => {
      if (started || !root.offsetWidth) return;
      try { await ensure();started = true;render(); } catch (e) { status.textContent = e.message; }
    };
    new IntersectionObserver(entries => { if (entries.some(e => e.isIntersecting)) start(); }, { rootMargin: "100px" }).observe(root);
    document.addEventListener("toggle", e => { if (e.target.open && e.target.contains(root)) start(); }, true);
    document.addEventListener("click", e => { if (e.target.closest("[data-report-tabs]")) requestAnimationFrame(start); });
  }
  document.querySelectorAll("[data-fragment-table]").forEach(initializeTable);
  return { ensure, idAt, raster, popup, outline, record: id => records.get(id) };
})();
