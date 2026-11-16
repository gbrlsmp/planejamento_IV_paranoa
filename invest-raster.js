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
  function colorTable(config, limits) {
    const anchors = config.colors.map(color => [1, 3, 5].map(offset => parseInt(color.slice(offset, offset + 2), 16)));
    const lut = new Uint8ClampedArray(65536 * 4);
    for (let code = 1; code < 65536; code++) {
      const position = Math.max(0, Math.min(1, (decode(code, config) - limits[0]) / (limits[1] - limits[0]))) * (anchors.length - 1);
      const low = Math.min(anchors.length - 2, Math.floor(position)), part = position - low;
      for (let c = 0; c < 3; c++) lut[code * 4 + c] = Math.round(anchors[low][c] * (1 - part) + anchors[low + 1][c] * part);
      lut[code * 4 + 3] = 255;
    }
    return lut;
  }
  const api = { decode, valueAt, colorTable };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else globalThis.InvestRaster = api;
})();
