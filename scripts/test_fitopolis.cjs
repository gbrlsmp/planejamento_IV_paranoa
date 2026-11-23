"use strict";
const {test}=require("node:test"),assert=require("node:assert/strict");
const D=require("../fitopolis-dados.js"),T=require("../fitopolis-territorio.js");

test("posição axial preserva IDs e localiza células vizinhas na bacia",()=>{
  const rows=[];
  for(let q=6500;q<6508;q++)for(let r=272500;r<272508;r++)rows.push(q,r);
  const a=new Int32Array(rows);
  for(let i=0;i<a.length/2;i++){
    const q=a[2*i],r=a[2*i+1],center=D.center(q,r);
    assert.deepEqual(D.axialAt(...center),[q,r]);
    assert.equal(D.axialIndex(a,q,r),i);
    assert.deepEqual(D.axialAt(center[0]+3,center[1]+3),[q,r]);
  }
  assert.equal(D.axialIndex(a,6500,272499),-1);
  assert.equal(D.axialIndex(a,6508,272500),-1);
});

test("projeção cartográfica concorda com GDAL e mantém precisão subcentimétrica",()=>{
  const fixtures=require("../dados-mapas/fitopolis-2026/projecao-verificada.json");
  for(const p of fixtures){
    const [x,y]=D.utmForward(...p.lonlat),[lng,lat]=D.utmInverse(...p.utm);
    assert.ok(Math.hypot(x-p.utm[0],y-p.utm[1])<.01);
    assert.ok(Math.hypot((lng-p.lonlat[0])*107000,(lat-p.lonlat[1])*111000)<.01);
  }
});

test("zero numérico recebe cor, NaN continua ausência e as extremidades são fixas",()=>{
  const colors=["#ffffff","#000000"];
  assert.deepEqual(D.color(0,[0,100],colors),[255,255,255,255]);
  assert.deepEqual(D.color(100,[0,100],colors),[0,0,0,255]);
  assert.deepEqual(D.color(NaN,[0,100],colors),[169,175,180,255]);
});

test("união de RAs não duplica resumos e preserva cobertura sem parcela inundada",()=>{
  const summaries={1:{area_m2:100,coverage_m2:100,valid_m2:0,weighted_sum:0},2:{area_m2:50,coverage_m2:40,valid_m2:40,weighted_sum:80},bacia:{area_m2:150,coverage_m2:140,valid_m2:40,weighted_sum:80}};
  const r=D.combine(summaries,["1","2","1"]);
  assert.equal(r.area,150);assert.equal(r.mean,2);assert.equal(r.coverage,100*140/150);
  assert.deepEqual(D.combine(summaries,[]),r);
  assert.equal(D.combine(summaries,["1"]).mean,null);
  assert.equal(D.combine(summaries,["1"]).coverage,100);
});

test("recorte territorial respeita vazios e polígonos separados",()=>{
  const outer=[[0,0],[10,0],[10,10],[0,10],[0,0]],hole=[[3,3],[7,3],[7,7],[3,7],[3,3]];
  const geometry={type:"MultiPolygon",coordinates:[[outer,hole],[[[20,20],[21,20],[21,21],[20,21],[20,20]]]]};
  assert.equal(T.inGeometry([1,1],geometry),true);
  assert.equal(T.inGeometry([5,5],geometry),false);
  assert.equal(T.inGeometry([20.5,20.5],geometry),true);
  assert.equal(T.inGeometry([15,15],geometry),false);
});

test("CSV distingue zero, lacuna e média não aplicável e preserva área parcial",()=>{
  assert.equal(D.csvRecord(1,'2:3','inundada_pct_valida',0,100,779,12),'1,2:3,inundada_pct_valida,0,disponivel,100,779,12\r\n');
  assert.ok(D.csvRecord(2,'','inundada_pct_valida',NaN,0,9,3).includes(',,sem_estimativa,0,9,3'));
  assert.ok(D.csvRecord(3,'','profundidade_media_inundada_m',NaN,100,9,3).includes(',,sem_parcela_inundada,100,9,3'));
});
