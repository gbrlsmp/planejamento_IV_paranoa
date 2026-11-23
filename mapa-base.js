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

const mapDataCache = new Map();
async function loadData(file) {
  if (!mapDataCache.has(file)) mapDataCache.set(file, readMapData(file).catch(error => { mapDataCache.delete(file); throw error; }));
  return mapDataCache.get(file);
}
async function readMapData(file) {
  const response = await fetch(file, { cache: "no-cache" });
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
  const background = map.getPane("cartografia-fundo") || map.createPane("cartografia-fundo");
  background.style.zIndex = "330"; background.style.pointerEvents = "none";

  L.geoJSON(base.agua, {
    ...options,
    pane: "cartografia-fundo",
    style: { stroke: false, fillColor: waterColor, fillOpacity: 1 },
  }).addTo(map);
  const basin = L.geoJSON(base.bacia, {
    ...options,
    style: { fill: false, color: basinColor, weight: 3.78, lineJoin: "bevel" },
  }).addTo(map);

  if (typeof FitopolisTerritorio !== "undefined") FitopolisTerritorio.attach(map, base);
  return basin.getBounds();
}
