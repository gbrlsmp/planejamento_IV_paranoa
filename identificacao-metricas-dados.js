"use strict";

// Consulta e mapa compartilham os mesmos CSVs e a mesma promessa de carregamento.
const loadMakurhiniMetrics = (() => {
  const folder = "dados-mapas/identificacao/metricas/";
  let dataset;

  async function loadMetrics() {
    if (!dataset) {
      dataset = (async () => {
        const manifest = await loadData(folder + "manifesto.json");
        const scenarios = await Promise.all(manifest.cenarios.map(async scenario => {
          const response = await fetch(folder + scenario.fragmentos.arquivo + "?v=" + scenario.fragmentos.sha256,
            { cache: "no-cache" });
          if (!response.ok) throw new Error("CSV indisponível");
          // Estes CSVs do R têm cabeçalho entre aspas e somente campos numéricos.
          const lines = (await response.text()).trim().split(/\r?\n/);
          const headers = lines.shift().split(",").map(value => value.replace(/^"|"$/g, ""));
          const fields = manifest.indicadores.map(info => headers.indexOf(info.campo));
          const idColumn = headers.indexOf("IdTemp");
          if (idColumn < 0 || fields.some(index => index < 0)) throw new Error("Colunas inesperadas");
          const records = new Map();
          lines.forEach(line => {
            const values = line.split(",").map(value => Number(value.replace(/^"|"$/g, "")));
            const id = values[idColumn];
            if (values.length !== headers.length || values.some(value => !Number.isFinite(value)) ||
                !Number.isInteger(id) || records.has(id)) throw new Error("Registro inválido");
            records.set(id, fields.map(index => values[index]));
          });
          if (records.size !== manifest.fragmentos) throw new Error("Tabela incompleta");
          return { borda: scenario.borda_m, records };
        }));
        if (scenarios.length !== 2 || scenarios[0].borda !== 45 || scenarios[1].borda !== 90) {
          throw new Error("Cenários inesperados");
        }
        return { manifest, scenarios };
      })().catch(error => { dataset = null; throw error; });
    }
    return dataset;
  }

  return loadMetrics;
})();
