"use strict";

// Codificação compartilhada por cor e consulta; zero é sempre ausência.
(() => {
  function decode(code, config) {
    return config.range[0] + (code - 1) / 65534 * (config.range[1] - config.range[0]);
  }
  function valueAt(values, bounds, point, config) {
    const x = Math.floor((point.x - bounds[0]) / (bounds[2] - bounds[0]) * values.width);
    const y = Math.floor((bounds[3] - point.y) / (bounds[3] - bounds[1]) * values.height);
    if (x < 0 || y < 0 || x >= values.width || y >= values.height) return null;
    const offset = (y * values.width + x) * 4;
    const code = values.bytes[offset] * 256 + values.bytes[offset + 1];
    return code ? decode(code, config) : null;
  }
  const classLabels = ["Ruim", "Médio", "Bom", "Muito bom"];
  const classColors = ["#8d554e", "#d0a55f", "#86a58f", "#2b5125"];
  function classIndex(value, config, scenario) {
    if (value === null || !Number.isFinite(value)) return null;
    const cuts = config.class_breaks[scenario];
    const bin = cuts.reduce((n, cut) => n + Number(value >= cut), 0);
    return config.higher_is_better ? bin : 3 - bin;
  }
  function rgb(color) { return [1, 3, 5].map(i => parseInt(color.slice(i, i + 2), 16)); }
  function valueColor(value, config, limits, mode = "continuous", scenario) {
    if (value === null || !Number.isFinite(value)) return [0, 0, 0, 0];
    if (mode === "classes") return [...rgb(classColors[classIndex(value, config, scenario)]), 255];
    const anchors = config.colors.map(rgb);
    const span = limits[1] - limits[0];
    const position = (span > 0 ? Math.max(0, Math.min(1, (value - limits[0]) / span)) : .5) * (anchors.length - 1);
    const low = Math.min(anchors.length - 2, Math.floor(position)), part = position - low;
    return [...anchors[low].map((v, c) => Math.round(v * (1 - part) + anchors[low + 1][c] * part)), 255];
  }
  function colorTable(config, limits, mode = "continuous", scenario) {
    const anchors = config.colors.map(color => [1, 3, 5].map(offset => parseInt(color.slice(offset, offset + 2), 16)));
    const lut = new Uint8ClampedArray(65536 * 4);
    for (let code = 1; code < 65536; code++) {
      if (mode === "classes") {
        lut.set(valueColor(decode(code, config), config, limits, mode, scenario), code * 4);
        continue;
      }
      const span = limits[1] - limits[0];
      const position = (span > 0 ? Math.max(0, Math.min(1, (decode(code, config) - limits[0]) / span)) : .5) * (anchors.length - 1);
      const low = Math.min(anchors.length - 2, Math.floor(position)), part = position - low;
      for (let c = 0; c < 3; c++) lut[code * 4 + c] = Math.round(anchors[low][c] * (1 - part) + anchors[low + 1][c] * part);
      lut[code * 4 + 3] = 255;
    }
    return lut;
  }
  const api = { decode, valueAt, colorTable, valueColor, classIndex, classLabels, classColors };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else globalThis.InvestRaster = api;
})();
