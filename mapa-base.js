"use strict";

const basinColor = "#d2de7b";
const waterColor = "#acc6cb";
const regionNames = {
  "1": "Plano Piloto",
  "2": "Gama",
  "3": "Taguatinga",
  "4": "Brazlândia",
  "5": "Sobradinho",
  "7": "Paranoá",
  "8": "Núcleo Bandeirante",
  "10": "Guará",
  "11": "Cruzeiro",
  "12": "Samambaia",
  "13": "Santa Maria",
  "15": "Recanto das Emas",
  "16": "Lago Sul",
  "17": "Riacho Fundo",
  "18": "Lago Norte",
  "19": "Candangolândia",
  "20": "Águas Claras",
  "21": "Riacho Fundo II",
  "22": "Sudoeste/Octogonal",
  "23": "Varjão",
  "24": "Park Way",
  "25": "SCIA",
  "26": "Sobradinho II",
  "27": "Jardim Botânico",
  "28": "Itapoã",
  "29": "SIA",
  "30": "Vicente Pires",
  "33": "Arniqueira",
  "36": "26 de Setembro",
  "37": "Ponte Alta"
};

async function loadData(file) {
  const response = await fetch(file);
  if (!response.ok) throw new Error("Arquivo de dados indisponível");
  const bytes = await response.arrayBuffer();
  const header = new Uint8Array(bytes, 0, Math.min(bytes.byteLength, 2));
  if (header[0] === 31 && header[1] === 139) {
    const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
    return new Response(stream).json();
  }
  return JSON.parse(new TextDecoder().decode(bytes));
}

function addMapBase(map, base, showRegions) {
  const pane = map.createPane("cartografia");
  pane.style.zIndex = "410";
  pane.style.pointerEvents = "none";
  const options = { pane: "cartografia", interactive: false, smoothFactor: 0 };

  L.geoJSON(base.agua, {
    ...options,
    style: { stroke: false, fillColor: waterColor, fillOpacity: 1 },
  }).addTo(map);
  const basin = L.geoJSON(base.bacia, {
    ...options,
    style: { fill: false, color: basinColor, weight: 3.78, lineJoin: "bevel" },
  }).addTo(map);

  if (!showRegions) return basin.getBounds();

  const regions = L.geoJSON(base.ras, {
    ...options,
    style: {
      fill: false, color: "#000", opacity: 0.6895, weight: 0.76,
      dashArray: "0.76 1.52", lineCap: "square", lineJoin: "bevel",
    },
  });
  const features = [...base.ras.features].sort((a, b) => a.properties.ra_cira - b.properties.ra_cira);
  const anchors = features.map(({ properties }) => L.GeoJSON.coordsToLatLng(properties.rotulo));
  const labels = features.map(({ properties }, index) =>
    L.tooltip({ permanent: true, direction: "center", className: "ra-label", opacity: 1 })
      .setLatLng(anchors[index]).setContent(String(properties.ra_cira))
  );
  const leaders = anchors.map(anchor => L.polyline([anchor, anchor], {
    ...options, color: "#626262", weight: 1, opacity: 0.8,
  }));
  const regionOverlay = L.layerGroup([regions, ...leaders, ...labels]);
  const legend = document.getElementById("legenda-ras");
  if (legend) {
    const heading = document.createElement("h4");
    heading.textContent = "Regiões administrativas";
    const note = document.createElement("p");
    note.textContent = "Os números correspondem às RAs no mapa. Selecione uma RA para aproximar.";
    const list = document.createElement("ul");
    features.forEach(({ properties }, index) => {
      const row = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = properties.ra_cira + " · " + regionNames[properties.ra_cira];
      button.addEventListener("click", () => map.setView(anchors[index], Math.max(map.getZoom(), 12)));
      row.append(button);
      list.append(row);
    });
    legend.append(heading, note, list);
  }

  function positionLabels() {
    if (!map.hasLayer(regionOverlay)) return;
    const placed = [];
    const size = map.getSize();
    labels.forEach((label, index) => {
      const anchor = map.latLngToContainerPoint(anchors[index]);
      const element = label.getElement();
      if (anchor.x < 0 || anchor.y < 0 || anchor.x > size.x || anchor.y > size.y) {
        element.style.visibility = "hidden";
        leaders[index].setLatLngs([]);
        return;
      }
      const width = element.offsetWidth + 4;
      const height = element.offsetHeight + 4;
      let chosen;
      // Move close labels apart, retaining a line to their original position.
      for (let radius = 0; radius <= 180 && !chosen; radius += 18) {
        const steps = radius ? Math.ceil(2 * Math.PI * radius / 18) : 1;
        for (let step = 0; step < steps; step++) {
          const angle = step / steps * 2 * Math.PI;
          const x = anchor.x + Math.cos(angle) * radius;
          const y = anchor.y + Math.sin(angle) * radius;
          const box = { left: x - width / 2, right: x + width / 2, top: y - height / 2, bottom: y + height / 2 };
          if (box.left < 2 || box.top < 2 || box.right > size.x - 2 || box.bottom > size.y - 2) continue;
          if (placed.some(other => box.left < other.right && box.right > other.left && box.top < other.bottom && box.bottom > other.top)) continue;
          chosen = { x, y, box };
          break;
        }
      }
      element.style.visibility = "";
      const point = chosen ? L.point(chosen.x, chosen.y) : anchor;
      label.setLatLng(map.containerPointToLatLng(point));
      leaders[index].setLatLngs(point.distanceTo(anchor) > 5 ? [anchors[index], map.containerPointToLatLng(point)] : []);
      if (chosen) placed.push(chosen.box);
    });
  }

  function toggleRegions() {
    if (legend) legend.hidden = !showRegions.checked;
    if (showRegions.checked) {
      regionOverlay.addTo(map);
      basin.bringToFront();
      positionLabels();
    } else {
      regionOverlay.remove();
    }
  }
  map.on("moveend zoomend resize", positionLabels);
  showRegions.addEventListener("change", toggleRegions);
  showRegions.disabled = false;
  toggleRegions();
  return basin.getBounds();
}
