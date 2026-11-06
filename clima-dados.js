"use strict";

// Both map views read this one catalogue; no parallel thresholds or palettes.
const ClimateData = (() => {
  let pending;
  const load = () => pending ??= loadData("dados-mapas/clima/catalogo.json");
  function find(catalog, field) {
    for (const [indicator, config] of Object.entries(catalog.indicators)) {
      for (const [scenario, record] of Object.entries(config.scenarios)) {
        if (record.field === field) return { indicator, config, scenario, record };
      }
    }
    return null;
  }
  function color(value, config) {
    if (value === null || !Number.isFinite(value)) return "#a9afb4";
    const [low, high] = config.range;
    // Same 255-colour quantization as the canonical raster images.
    const position = Math.round(254 * Math.max(0, Math.min(1, (value - low) / (high - low)))) / 254 * (config.colors.length - 1);
    const index = Math.min(config.colors.length - 2, Math.floor(position));
    const fraction = position - index;
    const rgb = [1, 3, 5].map(offset => Math.round(
      parseInt(config.colors[index].slice(offset, offset + 2), 16) * (1 - fraction) +
      parseInt(config.colors[index + 1].slice(offset, offset + 2), 16) * fraction));
    return "#" + rgb.map(value => value.toString(16).padStart(2, "0")).join("");
  }
  function format(value, config) {
    return value.toLocaleString("pt-BR", { minimumFractionDigits: config.decimals, maximumFractionDigits: config.decimals }) + (config.unit ? " " + config.unit : "");
  }
  function entries(config, record) {
    const list = config.labels_numeric.map((label, index) => [
      label + " · " + format(record.cuts[index], config) + " a " + format(record.cuts[index + 1], config), config.colors[index],
    ]);
    return config.labels_numeric[0] === "base" ? list : list.reverse();
  }
  function verify(catalog, data) {
    if (catalog.revision !== data.climate_revision) throw new Error("Arquivos climáticos de revisões diferentes; atualize a página.");
  }
  return { load, find, color, format, entries, verify };
})();
