"use strict";

function createMapImage(path, layer, pane, opacity) {
  const [west, south, east, north] = layer.bounds;
  const crs = L.CRS.EPSG3857;
  const bounds = [crs.unproject(L.point(west, south)), crs.unproject(L.point(east, north))];
  const overlay = L.imageOverlay(path, bounds, {
    pane, opacity, className: "mapa-classe", alt: layer.title,
  });
  const colors = new Map(layer.classes.map(([, label, color]) =>
    [Number.parseInt(color.slice(1), 16), label]));
  let ctx;
  let loaded = false;
  overlay.on("load", () => { loaded = true; });

  function classAt(point) {
    if (!loaded || point.x < west || point.x >= east || point.y <= south || point.y > north) return null;
    if (!ctx) {
      const img = overlay.getElement();
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth;
      canvas.height = img.naturalHeight;
      ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (!ctx) return null;
      ctx.drawImage(img, 0, 0);
    }
    const x = Math.floor((point.x - west) / (east - west) * ctx.canvas.width);
    const y = Math.floor((north - point.y) / (north - south) * ctx.canvas.height);
    const [r, g, b, alpha] = ctx.getImageData(x, y, 1, 1).data;
    return alpha ? colors.get((r << 16) | (g << 8) | b) ?? null : null;
  }
  return { overlay, classAt };
}
