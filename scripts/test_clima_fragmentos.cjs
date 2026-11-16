"use strict";
const {test}=require("node:test"), assert=require("node:assert/strict"), vm=require("node:vm"), fs=require("node:fs"), path=require("node:path");
const Raster=require("../invest-raster.js");

function setup({fail=false}={}) {
  const state={fetches:[],renders:[],images:0};
  const rows=[{id_frag:1,cc_dia_mean:.8},{id_frag:2,cc_dia_mean:.1}];
  const metadata={count:2,bounds:[0,0,20,20],data_file:"fragmentos-dados.json.gz",data_sha256:"1234567890123456",ids_file:"id-fragmentos-20m.png",ids_sha256:"1234567890123456"};
  class MockImage {
    constructor(){this.naturalWidth=2;this.naturalHeight=2;state.images++;}
    set src(value){queueMicrotask(()=>this.onload());}
  }
  const context={Image:MockImage,Uint8ClampedArray,InvestRaster:Raster,ImageData:class{constructor(pixels){this.data=pixels;}},document:{querySelectorAll:()=>[],createElement:tag=>{
    if(tag==="canvas")return {getContext:()=>({drawImage(){},getImageData:()=>({data:Uint8ClampedArray.from([0,0,1,255,0,0,2,255,0,0,0,0,0,0,1,255])}),putImageData:data=>state.renders.push([...data.data])}),toDataURL:()=>"data:image/png;base64,test"};
    return {children:[],append(...nodes){this.children.push(...nodes);}};
  }},loadData:async file=>{
    state.fetches.push(file);
    if(fail){fail=false;throw new Error("falha simulada");}
    if(file.includes("manifesto"))return metadata;
    if(file.includes("fragmentos-dados"))return {rows};
    return {type:"FeatureCollection",features:rows.map(r=>({type:"Feature",properties:{id_frag:r.id_frag},geometry:{type:"Polygon",coordinates:[]}}))};
  },L:{geoJSON:feature=>({feature,addTo(){return this;}})}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../clima-fragmentos.js"),"utf8"),context);
  return {api:context.ClimateFragments,state};
}

test("IDs atuais decodificam 24 bits, bordas e ausência sem usar população histórica",async()=>{
  const h=setup();await h.api.ensure();await h.api.ensure();
  assert.equal(h.state.fetches.length,2);assert.equal(h.state.images,1);
  assert.equal(h.api.idAt({x:5,y:15}),1);assert.equal(h.api.idAt({x:15,y:15}),2);
  assert.equal(h.api.idAt({x:5,y:5}),null);assert.equal(h.api.idAt({x:20,y:15}),null);
  assert.equal(h.api.record(2).cc_dia_mean,.1);
});
test("cor por fragmento usa sua média e os mesmos cortes da legenda; exterior transparente",async()=>{
  const h=setup();await h.api.ensure();
  const config={class_breaks:{dia:[.25,.5,.75]},higher_is_better:true,colors:["#c4cc95","#2b5125"]};
  h.api.raster("cc","dia",config,[0,1],"classes");
  const pixels=h.state.renders[0];
  assert.deepEqual(pixels.slice(0,4),Raster.valueColor(.8,config,[0,1],"classes","dia"));
  assert.deepEqual(pixels.slice(4,8),Raster.valueColor(.1,config,[0,1],"classes","dia"));
  assert.deepEqual(pixels.slice(8,12),[0,0,0,0]);
});
test("contorno busca ID no lote correto e recupera falha de carregamento inicial",async()=>{
  const h=setup({fail:true});await assert.rejects(h.api.ensure(),/falha simulada/);
  await h.api.ensure();const outline=await h.api.outline({},2);
  assert.equal(outline.feature.properties.id_frag,2);
  await assert.rejects(h.api.outline({},3),/não localizado/);
  assert.equal(h.state.fetches.filter(f=>f.includes("fragmentos-000")).length,1);
});
