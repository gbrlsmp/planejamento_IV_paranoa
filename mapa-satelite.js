"use strict";

function addGoogleSatellite(map) {
  const toggle = document.getElementById("mostrar-satelite");
  const status = document.getElementById("satelite-status");
  const key = document.querySelector('meta[name="google-maps-key"]').content.trim();
  if (!key) {
    status.textContent = "A camada de satélite aguarda a configuração da chave do Google Maps.";
    return;
  }

  const container = map.getContainer();
  const mapPane = map.getPane("mapPane");
  const satellite = L.DomUtil.create("div", "google-satellite");
  const vectorViewport = L.DomUtil.create("div", "map-vector-viewport");
  satellite.hidden = true;
  container.prepend(satellite, vectorViewport);
  vectorViewport.append(mapPane);
  let googleMap, mapsLibrary;

  function setVisible(visible) {
    satellite.hidden = !visible;
    container.classList.toggle("satellite-active", visible);
  }

  function hideWithError(message) {
    toggle.checked = false;
    setVisible(false);
    status.textContent = message;
  }

  function loadMaps() {
    if (!mapsLibrary) {
      mapsLibrary = new Promise((resolve, reject) => {
        const script = document.createElement("script");
        window.loadParanoaSatellite = () => resolve(window.google.maps);
        window.gm_authFailure = () => {
          reject(new Error("Falha de autenticação"));
          toggle.disabled = true;
          hideWithError("O Google Maps recusou a chave de acesso ao satélite.");
        };
        const params = new URLSearchParams({
          key, loading: "async", callback: "loadParanoaSatellite",
          language: "pt-BR", region: "BR", auth_referrer_policy: "origin",
        });
        script.src = "https://maps.googleapis.com/maps/api/js?" + params;
        script.async = true;
        script.onerror = () => {
          script.remove();
          mapsLibrary = undefined;
          reject(new Error("Google Maps indisponível"));
        };
        document.head.append(script);
      });
    }
    return mapsLibrary;
  }

  function camera() {
    const { lat, lng } = map.getCenter();
    return { center: { lat, lng }, zoom: map.getZoom() };
  }

  function syncCamera() {
    if (googleMap && !satellite.hidden) googleMap.moveCamera(camera());
  }

  async function updateSatellite() {
    if (!toggle.checked) {
      setVisible(false);
      status.textContent = "";
      return;
    }

    status.textContent = "Carregando imagem de satélite…";
    try {
      const maps = await loadMaps();
      if (!toggle.checked) return;
      setVisible(true);
      if (!googleMap) {
        googleMap = new maps.Map(satellite, {
          ...camera(),
          mapTypeId: "satellite",
          tilt: 0,
          disableDefaultUI: true,
          gestureHandling: "none",
          keyboardShortcuts: false,
          clickableIcons: false,
        });
      } else {
        syncCamera();
      }
      status.textContent = "";
    } catch {
      if (toggle.checked) hideWithError("Não foi possível carregar o satélite. Tente novamente.");
    }
  }

  map.on("move resize", syncCamera);
  toggle.addEventListener("change", updateSatellite);
  toggle.checked = false;
  toggle.disabled = false;
}
