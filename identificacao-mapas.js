"use strict";

// Cada seção mantém seu próprio mapa, enquadramento e seleção de camadas.
(() => {
  let sharedData;
  let avuManifest;
  const avuFolder = "dados-mapas/identificacao/limites-avu/";

  function baseData() {
    if (!sharedData) {
      sharedData = Promise.all([loadData("mapa-base.json.gz"), loadData("dados-mapas/catalogo.json")])
        .catch(error => { sharedData = null; throw error; });
    }
    return sharedData;
  }

  function limitsManifest() {
    if (!avuManifest) {
      avuManifest = loadData(avuFolder + "manifesto.json")
        .catch(error => { avuManifest = null; throw error; });
    }
    return avuManifest;
  }

  function popupContent(title, rows) {
    const box = document.createElement("div");
    const heading = document.createElement("strong");
    heading.textContent = title;
    box.append(heading);
    rows.filter(Boolean).forEach(text => {
      const line = document.createElement("p");
      line.textContent = text;
      box.append(line);
    });
    return box;
  }

  document.querySelectorAll("[data-ident-map-theme]").forEach(root => {
    const theme = root.dataset.identMapTheme;
    const canvas = root.querySelector("[data-report-map]");
    const status = root.querySelector("[data-map-status]");
    const retry = root.querySelector("[data-map-retry]");
    const showImage = root.querySelector("[data-map-show]");
    const fit = root.querySelector("[data-map-fit]");
    const legend = root.querySelector("[data-map-legend]");
    let map;
    let initializing = false;
    let basinBounds;

    function errorMessage() {
      status.textContent = "Não foi possível carregar o mapa. Tente novamente.";
      retry.hidden = false;
    }

    async function addAvuLimits(image, ownerMap) {
      const group = root.querySelector("[data-avu-limits]");
      const message = root.querySelector("[data-avu-status]");
      try {
        const manifest = await limitsManifest();
        if (map !== ownerMap) return;
        group.replaceChildren();
        const heading = document.createElement("legend");
        heading.textContent = "Limites das AVUs e APPs";
        group.append(heading);
        manifest.camadas.forEach(info => {
          const label = document.createElement("label");
          const input = document.createElement("input");
          input.type = "checkbox";
          input.checked = info.visivel;
          input.dataset.avuLayer = info.id;
          const swatch = document.createElement("span");
          swatch.className = "ident-boundary-swatch";
          swatch.style.borderColor = info.cor;
          swatch.style.borderTopStyle = info.tracejado ? "dashed" : "solid";
          swatch.setAttribute("aria-hidden", "true");
          const text = document.createElement("span");
          text.textContent = info.nome + " (" + info.feicoes.toLocaleString("pt-BR") + ")";
          const state = document.createElement("small");
          state.setAttribute("role", "status");
          label.append(input, swatch, text, state);
          group.append(label);
          let layer;
          let pending;

          async function toggle() {
            if (!input.checked) {
              if (layer) layer.remove();
              return;
            }
            if (!layer && !pending) {
              state.textContent = "Carregando…";
              pending = loadData(avuFolder + info.arquivo + "?v=" + manifest.revisao)
                .then(data => {
                  layer = L.geoJSON(data, {
                    pane: "limites-avu", smoothFactor: 0, bubblingMouseEvents: false,
                    style: { fill: false, color: info.cor, weight: 1.8, opacity: 0.95,
                      dashArray: info.tracejado || null },
                    onEachFeature: (feature, polygon) => {
                      polygon.on("click", event => {
                        const properties = feature.properties;
                        const fragmentClass = showImage.checked
                          ? image.classAt(L.CRS.EPSG3857.project(event.latlng)) : null;
                        polygon.bindPopup(popupContent(properties.nome || info.nome, [
                          "Limite de referência: " + properties.categoria,
                          "Fonte: " + properties.fonte + " · feição " + properties.id_origem,
                          fragmentClass ? "Fragmento no local: " + fragmentClass : null,
                        ])).openPopup(event.latlng);
                      });
                    },
                  });
                });
            }
            try {
              if (pending) await pending;
              if (map !== ownerMap) return;
              state.textContent = "";
              if (input.checked) layer.addTo(ownerMap);
            } catch (error) {
              input.checked = false;
              state.textContent = "Falha ao carregar; marque para tentar novamente.";
            } finally {
              pending = null;
            }
          }
          input.addEventListener("change", toggle);
          if (input.checked) toggle();
        });
        message.textContent = "Contornos das fontes originais. Marque as categorias que deseja sobrepor aos fragmentos.";
      } catch (error) {
        if (map !== ownerMap) return;
        message.textContent = "Limites indisponíveis. Use Tentar novamente para recarregar o mapa.";
        retry.hidden = false;
      }
    }

    async function initialize() {
      if (initializing || map || canvas.clientWidth === 0) return;
      initializing = true;
      status.textContent = "Carregando mapa…";
      retry.hidden = true;
      try {
        const [base, catalog] = await baseData();
        if (!canvas.clientWidth) return;
        const layer = catalog[theme];
        map = L.map(canvas, { preferCanvas: true, scrollWheelZoom: false, zoomSnap: 0.25, zoomDelta: 0.5 });
        map.createPane("tema-relatorio").style.zIndex = "350";
        if (theme === "tipologias") map.createPane("limites-avu").style.zIndex = "430";
        basinBounds = addMapBase(map, base);
        L.control.scale({ imperial: false }).addTo(map);
        map.attributionControl.addAttribution("Base: IPE-DF");
        fit.disabled = false;
        fit.onclick = () => map.fitBounds(basinBounds, { padding: [16, 16] });
        if (theme === "metricas") {
          await createFragmentMetricsMap(root, map);
          fit.onclick();
          return;
        }
        const image = createMapImage("dados-mapas/" + theme + ".png?v=" + layer.revision,
          layer, "tema-relatorio", 1);
        image.overlay.on("load", () => {
          status.textContent = "Clique no mapa para consultar a classe representada.";
        });
        image.overlay.on("error", errorMessage);
        if (showImage.checked) image.overlay.addTo(map);
        showImage.disabled = false;
        fit.disabled = false;
        showImage.onchange = () => {
          map.closePopup();
          if (showImage.checked) image.overlay.addTo(map);
          else image.overlay.remove();
        };
        fit.onclick = () => map.fitBounds(basinBounds, { padding: [16, 16] });
        legend.replaceChildren();
        layer.classes.forEach(([, name, color]) => {
          const row = document.createElement("li");
          const swatch = document.createElement("span");
          swatch.className = "ident-class-swatch";
          swatch.style.backgroundColor = color;
          swatch.setAttribute("aria-hidden", "true");
          row.append(swatch, document.createTextNode(name));
          legend.append(row);
        });
        map.on("click", event => {
          const name = showImage.checked ? image.classAt(L.CRS.EPSG3857.project(event.latlng)) : null;
          if (name) L.popup().setLatLng(event.latlng)
            .setContent(popupContent(layer.title, [name])).openOn(map);
          else map.closePopup();
        });
        fit.onclick();
        if (theme === "tipologias") addAvuLimits(image, map);
      } catch (error) {
        if (map) { map.remove(); map = null; }
        errorMessage();
      } finally {
        initializing = false;
      }
    }

    retry.addEventListener("click", () => {
      if (map) { map.remove(); map = null; }
      initialize();
    });
    // Ao voltar a uma aba, atualiza as dimensões sem perder o enquadramento.
    new ResizeObserver(() => {
      if (canvas.clientWidth && map) map.invalidateSize({ pan: false });
    }).observe(canvas);
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) initialize();
    }, { rootMargin: "200px" });
    observer.observe(canvas);
  });
})();
