"use strict";

async function initializeIdentificationMap() {
  const status = document.getElementById("map-status");
  const showRegions = document.getElementById("mostrar-ras");
  try {
    const base = await loadData("mapa-base.json.gz");
    const container = document.getElementById("mapa");
    const map = L.map(container, { scrollWheelZoom: false, minZoom: 8, maxZoom: 19, zoomSnap: 0.5 });
    map.setView([-15.8, -47.85], 11);
    L.control.scale({ imperial: false }).addTo(map);
    const bounds = addMapBase(map, base, showRegions);
    let framed = false;
    const resize = new ResizeObserver(() => {
      if (!container.clientWidth || !container.clientHeight) return;

      map.invalidateSize({ animate: false });
      if (!framed) {
        map.fitBounds(bounds, { padding: [18, 18], animate: false });
        framed = true;
      }
    });
    resize.observe(container);
    status.textContent = "Limite da bacia, massas d’água e regiões administrativas.";
  } catch (error) {
    console.error(error);
    status.textContent = "O mapa não pôde ser carregado. Os códigos e nomes estão na lista abaixo.";
  }
}

initializeIdentificationMap();
