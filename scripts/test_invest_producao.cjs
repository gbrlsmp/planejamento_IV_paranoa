"use strict";
const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs"), path = require("node:path"), vm = require("node:vm");
const Raster = require("../invest-raster.js");
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, "../dados-mapas/clima/urban-cooling-2026/manifesto.json")));
const settle = async () => { for (let i = 0; i < 8; i++) await new Promise(resolve => setImmediate(resolve)); };

class Element {
  constructor() { this.children = []; this.handlers = {}; this.value = ""; this.checked = false; this.hidden = false; this.offsetWidth = 800; this.style = {}; this.classList = { toggle() {} }; }
  addEventListener(name, handler) { this.handlers[name] = handler; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  remove() { this.removed = true; }
  dispatch(name) { this.handlers[name]?.({ target: this }); }
}

function harness({ failImage = false, hidden = false, delayed = false } = {}) {
  const elements = new Map();
  const element = selector => { if (!elements.has(selector)) elements.set(selector, new Element()); return elements.get(selector); };
  const root = element("root");root.offsetWidth = hidden ? 0 : 800;
  root.querySelector = element;root.querySelectorAll = () => [element("canvas0"),element("canvas1")];
  element("[data-invest-indicator]").value="t";element("[data-invest-period]").value="dia";element("[data-invest-scale]").value="common";
  const state = { fetches: [], images: [], maps: [], documentHandlers: {}, intersections: [], popups: [] };
  const center = (x=0,y=0) => ({x,y,equals(other) { return this.x===other.x && this.y===other.y; }});
  class MapStub {
    constructor() { this.panes={};this.center=center();this.zoom=10;this.events={};this.attributionControl={addAttribution(){}};state.maps.push(this); }
    createPane(name) { return this.panes[name]={style:{}}; } getPane(name){return this.panes[name];}
    fitBounds(){return this;} getCenter(){return this.center;} getZoom(){return this.zoom;}
    setView(c,z){this.center=center(c.x,c.y);this.zoom=z;this.events.moveend?.();return this;}
    on(name,handler){this.events[name]=handler;return this;} invalidateSize(){return this;} closePopup(){return this;}
  }
  const document = { querySelector: () => root, addEventListener: (name,fn) => {state.documentHandlers[name]=fn;}, createElement: tag => {
    const node=new Element();
    if(tag==="canvas") {node.getContext=()=>({drawImage(){},getImageData(){return {data:Uint8ClampedArray.from([128,0,0,255,0,0,0,0,255,255,0,255,0,1,0,255])};},putImageData(){}});node.toDataURL=()=>"data:image/png;base64,test";}
    return node;
  }};
  const L={map:()=>new MapStub(),geoJSON:()=>({addTo(){}}),control:{scale:()=>({addTo(){}})},latLngBounds:(a,b)=>[a,b],point:(x,y)=>({x,y}),CRS:{EPSG3857:{project:p=>p,unproject:p=>p}},imageOverlay:()=>({addTo(){return this;},remove(){}}),popup:()=>({setLatLng(){return this;},setContent(content){state.popups.push(content);return this;},openOn(){return this;}})};
  class MockImage {
    constructor(){this.naturalWidth=2;this.naturalHeight=2;state.images.push(this);}
    set src(value){this.url=value;if(!delayed)queueMicrotask(()=>{if(failImage){failImage=false;this.onerror();}else this.onload();});}
  }
  const context={document,L,InvestRaster:Raster,Image:MockImage,ImageData:class{},Uint8ClampedArray,console,requestAnimationFrame:fn=>fn(),window:{addEventListener(){}},IntersectionObserver:class{constructor(fn){state.intersections.push(fn);}observe(){}},loadData:async file=>{state.fetches.push(file);return file.includes("manifesto")?manifest:{};},addMapBase:map=>{map.createPane("cartografia");return [];}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../invest-producao.js"),"utf8"),context);
  return {state,root,element,enter(){state.intersections[0]([{isIntersecting:true}]);}};
}

test("decodificação e consulta preservam zero como ausência e limites espaciais",()=>{
  const config={range:[10,20]};assert.equal(Raster.decode(1,config),10);assert.equal(Raster.decode(65535,config),20);
  const values={width:2,height:1,bytes:Uint8Array.from([255,255,0,255,0,0,0,0])};
  assert.equal(Raster.valueAt(values,[0,0,20,10],{x:1,y:5},config),20);
  assert.equal(Raster.valueAt(values,[0,0,20,10],{x:15,y:5},config),null);
  assert.equal(Raster.valueAt(values,[0,0,20,10],{x:-1,y:5},config),null);
  assert.equal(Raster.valueAt(values,[0,0,20,10],{x:20,y:5},config),null);
});
test("paleta é contínua e mantém as cores das extremidades e a transparência",()=>{
  for(const config of Object.values(manifest.indicators)){
    const lut=Raster.colorTable(config,config.range);assert.deepEqual([...lut.slice(0,4)],[0,0,0,0]);
    for(const [code,color] of [[1,config.colors[0]],[65535,config.colors.at(-1)]])assert.deepEqual([...lut.slice(code*4,code*4+3)],[1,3,5].map(i=>parseInt(color.slice(i,i+2),16)));
    const middle=32768;const varied=Raster.colorTable(config,[config.range[0],Raster.decode(middle,config)]);
    assert.notDeepEqual([...varied.slice(middle*4,middle*4+3)],[...lut.slice(middle*4,middle*4+3)]);
  }
});
test("carrega ao entrar na seção, compara cenários e mantém escala comum",async()=>{
  const h=harness();assert.equal(h.state.fetches.length,0);h.enter();await settle();
  assert.equal(h.state.maps.length,1);assert.match(h.element("[data-invest-status]").textContent,/Mapa disponível/);
  assert.equal(h.state.maps[0].getPane("cartografia").style.zIndex,"340");
  const compare=h.element("[data-invest-compare]");compare.checked=true;compare.dispatch("change");await settle();
  assert.equal(h.state.maps.length,2);assert.equal(h.element("[data-invest-period]").disabled,true);assert.equal(h.element("[data-invest-scale]").disabled,true);
  assert.equal(h.element("[data-invest-scale]").value,"common");assert.equal(h.element("[data-invest-comparison]").hidden,false);
  h.state.maps[0].setView({x:5,y:6},12);assert.equal(h.state.maps[1].getZoom(),12);assert.equal(h.state.maps[1].getCenter().x,5);
  compare.checked=false;compare.dispatch("change");await settle();assert.equal(h.element("[data-invest-scale]").disabled,false);
  const metric=h.element("[data-invest-indicator]");metric.value="cc";metric.dispatch("change");await settle();
  assert.match(h.element("[data-invest-legend]").children[0].textContent,/Capacidade/);
  const scale=h.element("[data-invest-scale]");scale.value="scenario";scale.dispatch("change");await settle();
  assert.match(h.element("[data-invest-legend]").children.at(-1).textContent,/não devem ser comparadas/);
});
test("consulta usa o valor decodificado, inclusive ao ampliar contraste",async()=>{
  const h=harness();h.element("[data-invest-indicator]").value="cc";h.element("[data-invest-period]").value="noite";h.element("[data-invest-scale]").value="scenario";
  h.enter();await settle();const box=manifest.bounds;
  h.state.maps[0].events.click({latlng:{x:box[0]+(box[2]-box[0])*.25,y:box[3]-(box[3]-box[1])*.25}});
  assert.match(h.state.popups[0].children[1].textContent,/Noite: 0,500/);
});
test("falha de imagem permite tentar novamente sem mapa duplicado",async()=>{
  const h=harness({failImage:true});h.enter();await settle();assert.equal(h.element("[data-invest-retry]").hidden,false);
  h.element("[data-invest-retry]").dispatch("click");await settle();assert.equal(h.state.maps.length,1);assert.match(h.element("[data-invest-status]").textContent,/Mapa disponível/);
});
test("troca rápida de indicador não exibe resposta antiga",async()=>{
  const h=harness({delayed:true});h.enter();await settle();
  h.element("[data-invest-indicator]").value="hm";h.element("[data-invest-indicator]").dispatch("change");await settle();
  h.state.images[1].onload();await settle();h.state.images[0].onload();await settle();
  assert.equal(h.state.maps.length,1);assert.match(h.element("[data-invest-legend]").children[0].textContent,/Mitigação/);
});
test("retorna à aba Clima após iniciar a seção escondida",async()=>{
  const h=harness({hidden:true});h.enter();await settle();assert.equal(h.state.fetches.length,0);
  h.root.offsetWidth=800;h.state.documentHandlers.click({target:{closest:()=>({})}});await settle();
  assert.equal(h.state.maps.length,1);assert.match(h.element("[data-invest-status]").textContent,/Mapa disponível/);
});

test("INMET recolhido não carrega gráficos; abrir a etapa inicializa uma vez",async()=>{
  const elements=new Map();
  const element=key=>{if(!elements.has(key))elements.set(key,new Element());return elements.get(key);};
  const root=element("root");root.offsetWidth=0;root.clientWidth=800;root.querySelector=element;
  root.querySelectorAll=()=>["timeline","distribution","profile","scatter","sankey"].map(key=>element(`[data-chart="${key}"]`));
  element("[data-variable]").value="temp";element("[data-stations-map]").offsetWidth=0;
  const data=JSON.parse(fs.readFileSync(path.join(__dirname,"../dados-mapas/clima/inmet-exploracao.json")));
  const state={fetches:0,plots:[],mapCount:0,fitCount:0,handlers:{}};
  let releaseBase, holdBase=true;
  const map={setView(){return this;},fitBounds(){state.fitCount++;return this;},invalidateSize(){},remove(){}};
  const marker=()=>({addTo(){return this;},bindTooltip(){return this;},on(){return this;},setStyle(){}});
  const context={document:{querySelector:()=>root,createElement:()=>new Element(),addEventListener:(name,fn)=>{state.handlers[name]=fn;}},window:{addEventListener(){}},requestAnimationFrame:fn=>fn(),setTimeout:fn=>fn(),clearTimeout(){},location:{reload(){}},loadData:async file=>{state.fetches++;return file.includes("inmet")?data:(holdBase?new Promise(resolve=>{releaseBase=resolve;}):{});},addMapBase(){},L:{map:()=>{state.mapCount++;return map;},circleMarker:marker,control:{scale:()=>({addTo(){}})}},Plotly:{react:async(node,traces)=>{state.plots.push({node,traces});},Plots:{resize(){}}},console};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../clima-exploracao.js"),"utf8"),context);
  assert.equal(state.fetches,0);assert.equal(state.plots.length,0);
  root.offsetWidth=800;const outer={tagName:"DETAILS",open:true,contains:node=>node===root};
  state.handlers.toggle({target:outer});await settle();assert.equal(state.fetches,2);
  root.offsetWidth=0;holdBase=false;releaseBase({});await settle();assert.equal(state.mapCount,0);assert.equal(state.plots.length,0);
  root.offsetWidth=800;state.handlers.toggle({target:outer});await settle();assert.equal(state.fetches,4);assert.equal(state.plots.length,5);assert.equal(state.mapCount,1);
  assert.match(element("[data-inmet-status]").textContent,/A001/);assert.equal(element("[data-inmet-summary]").children.length,2);
  state.handlers.toggle({target:outer});await settle();assert.equal(state.fetches,4);assert.equal(state.mapCount,1);
  element("[data-stations-map]").offsetWidth=800;element("details").dispatch("toggle");assert.equal(state.fitCount,1);
});
