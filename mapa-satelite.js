"use strict";

function addSatellite(map) {
  const toggle = document.getElementById("mostrar-satelite");
  const status = document.getElementById("satelite-status");
  const satellite = L.tileLayer(
    "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2025_3857/default/g/{z}/{y}/{x}.jpg",
    {
      maxNativeZoom: 14, maxZoom: 19, noWrap: true,
      attribution: '<a href="https://maps.eox.at">EOX::Maps</a> · <a href="https://cloudless.eox.at">Sentinel-2 cloudless 2025</a> © EOX, contém dados Copernicus Sentinel modificados (2025), <a href="https://creativecommons.org/licenses/by-nc-sa/4.0/">CC BY-NC-SA 4.0</a>',
    }
  );
  let loaded = 0, failed = 0;
  satellite.on("loading", () => {
    loaded = 0;
    failed = 0;
    if (toggle.checked) status.textContent = "Carregando imagem de satélite…";
  });
  satellite.on("tileload", () => { loaded++; });
  satellite.on("tileerror", () => { failed++; });
  satellite.on("load", () => {
    if (!toggle.checked) return;
    if (!loaded && failed) {
      toggle.checked = false;
      satellite.remove();
      status.textContent = "Não foi possível carregar o satélite. Tente ativar novamente.";
    } else {
      status.textContent = failed
        ? "Algumas imagens não carregaram. Desative e ative o satélite para tentar novamente."
        : "Sentinel-2 cloudless 2025 · resolução de 10 m · uso não comercial.";
    }
  });
  toggle.addEventListener("change", () => {
    if (toggle.checked) {
      status.textContent = "Carregando imagem de satélite…";
      satellite.addTo(map);
    } else {
      satellite.remove();
      status.textContent = "";
    }
  });
  toggle.checked = false;
  toggle.disabled = false;
}
