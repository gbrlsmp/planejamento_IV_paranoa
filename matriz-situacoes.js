"use strict";
const by=id=>document.getElementById(id);
const pastaMatriz = new URL("dados-mapas/matriz-situacoes/", document.baseURI);

async function obter(nome) {
 const resposta = await fetch(new URL(nome, pastaMatriz));
 if (!resposta.ok) throw new Error("Falha ao ler " + nome + " (HTTP " + resposta.status + ")");
 return resposta;
}

async function carregarCatalogo() {
 return (await obter("catalogo.json")).json();
}

async function descompactar(nome) {
 const bytes = await (await obter(nome)).arrayBuffer();
 const magic = new Uint8Array(bytes, 0, 2);
 if (magic[0] !== 31 || magic[1] !== 139) return bytes;
 const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream("gzip"));
 return new Response(stream).arrayBuffer();
}

async function lerObjetos(nome) {
 return JSON.parse(new TextDecoder().decode(await descompactar(nome + ".json.gz")));
}

function mostrarErro(erro) {
 by("comparar").textContent = "Não foi possível carregar a matriz.";
 by("detalhe").textContent = erro.message;
 const recarregar = document.createElement("button");
 recarregar.textContent = "Tentar novamente";
 recarregar.onclick = () => location.reload();
 by("comparar").append(" ", recarregar);
}

async function iniciarMatriz(){
const data=await carregarCatalogo();
[data.fragmentos,data.avus]=await Promise.all([lerObjetos("fragmentos"),lerObjetos("avus")]);
const escapeText=t=>String(t??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt=(x,n=2)=>x.toLocaleString("pt-BR",{maximumFractionDigits:n,minimumFractionDigits:n});
const colors={calor:{"abaixo dos cortes":"#649b79","dia":"#e4af42","noite":"#6578ad","dia e noite":"#a13e42","indeterminado":"#858786"},
 tr5:{"zero na área válida":"#e6dfcc","positivo":"#257495","sem estimativa":"#8a827a"},
 uso:{campestre:"#aad064",savanica:"#62984a",florestal:"#245e44",alagado:"#358e91",agua:"#4e88ad",vegetacao_intraurbana:"#678e63",forracao:"#cacc82",impermeavel_solo_exposto:"#bd8960",edificacoes:"#995240",vias:"#58555f",mosaico:"#9989a6",indeterminado:"#bfc0bc"}};
const useNames={savanica:"Savânica",florestal:"Florestal",campestre:"Campestre",alagado:"Campo alagado",agua:"Água",vegetacao_intraurbana:"Vegetação intraurbana",forracao:"Forração",impermeavel_solo_exposto:"Impermeável / solo exposto",edificacoes:"Edificações",vias:"Vias pavimentadas",mosaico:"Mosaico",indeterminado:"Indeterminado"};
const label=x=>useNames[x]||x;
const groupById=new Map(data.grupos.map(g=>[g.grupo_id,g]));
const frById=new Map(data.fragmentos.map(f=>[f.id_frag,f]));
const avById=new Map(data.avus.map(a=>[a.id_avu,a]));
const territories=new Map(data.recortes.map(r=>[r.recorte,r.nome_recorte]));
let first,second,panos={},ready=false;
function table(headers,rows){return '<table><thead><tr>'+headers.map(h=>'<th>'+h+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(c=>'<td>'+c+'</td>').join('')+'</tr>').join('')+'</tbody></table>'}
function link(kind,id,text){return '<button type="button" class="action" data-kind="'+kind+'" data-id="'+id+'">'+escapeText(text)+'</button>'}
function condition(g){return escapeText(label(g.uso))+' · '+escapeText(g.calor)+' · TR5 '+escapeText(g.tr5)}
function hex(id){
 const i=first[id]; if(i===undefined||i<0)return "Hexágono fora dos dois recortes.";
 const ix=[i]; if(second.has(id))ix.push(second.get(id));
 const scoped=ix.filter(inScope);if(!scoped.length)return "Hexágono fora do recorte selecionado.";
 ix.splice(0,ix.length,...scoped);
 const area=ix.reduce((s,n)=>s+data.m2[n],0);
 let html='<h2>Hexágono '+id+'</h2><p>'+condition(groupById.get(data.grupo_id[i]))+'</p><p>'+ix.map(n=>escapeText(territories.get(data.recorte[n]))+' · '+fmt(data.m2[n])+' m²').join('<br>')+'</p>';
 html+=hexEvidence(ix,area);
 const iv=ix.reduce((sum,n)=>sum+data.iv_m2[n],0);
 const avus=ix.reduce((sum,n)=>sum+data.avu_uniao_m2[n],0);
 html+='<p>Área de fragmentos · '+fmt(iv)+' m². Área coberta pela união das AVUs · '+fmt(avus)+' m².</p>';
 for(const k of ["frag","avu"]){
  const found=new Map();
  for(const n of ix)for(let j=data[k+"_offset"][n];j<data[k+"_offset"][n+1];j++){
   const key=data[k+"_id"][j];found.set(key,(found.get(key)||0)+data[k+"_m2"][j]);}
  html+='<h3>'+(k==="frag"?"Fragmentos de IV":"AVUs")+'</h3>';
  if(k==="frag"&&found.size){
   const cats=new Map(); for(const [key,m] of found){const cat=frById.get(key).cat_iv, stats=cats.get(cat)||[0,0];stats[0]++;stats[1]+=m;cats.set(cat,stats)}
   html+=table(["Classe","Fragmentos","% da célula no recorte"],Array.from(cats,([c,[n,m]])=>[escapeText(c),n,fmt(100*m/area)]));
  }
  const rows=Array.from(found).sort((a,b)=>b[1]-a[1]).map(([key,m])=>{
   const obj=k==="frag"?frById.get(key):avById.get(key);
   return [link(k,key,k==="frag"?"Fragmento "+key:obj.nome||"AVU "+key),escapeText(k==="frag"?obj.cat_iv:obj.tipo),fmt(m),fmt(100*m/area)];});
  html+=rows.length?table(["Elemento","Classe / tipo","m²","%"],rows):'<p>Nenhuma interseção com área positiva.</p>';
 }
 return html;
}
function objectView(k,id){
 const fr=k==="frag", obj=(fr?frById:avById).get(id);
 if(!obj)return "Elemento ausente do cadastro do piloto.";
 let html='<h2>'+escapeText(fr?"Fragmento "+id:obj.nome||"AVU "+id)+'</h2><p>'+escapeText(fr?[obj.cat_iv,obj.form_pred,"Classe AVU do fragmento: "+obj.classe_avu].join(" · "):[obj.tipo,obj.subgrupo,obj.categoria].filter(Boolean).join(" · "))+'</p>';
 const sums=new Map(),familyAreas=Array(families.length).fill(0); let grand=0;
 for(let i=0;i<data.id_hex.length;i++)if(inScope(i))for(let j=data[k+"_offset"][i];j<data[k+"_offset"][i+1];j++)if(data[k+"_id"][j]===id){
  families.forEach((_,f)=>{if(data.fam[i]&(1<<f))familyAreas[f]+=data[k+"_m2"][j]});
  const key=data.recorte[i]*1000+data.grupo_id[i],m=data[k+"_m2"][j];sums.set(key,(sums.get(key)||0)+m);grand+=m;}
 if(!sums.size)return html+"<p>Sem parcela no recorte selecionado.</p>";
 const rows=Array.from(sums).sort((a,b)=>b[1]-a[1]).map(([key,m])=>[escapeText(territories.get(Math.floor(key/1000))),condition(groupById.get(key%1000)),fmt(m/10000,4),fmt(100*m/grand)]);
 return html+'<p>Área no recorte selecionado · '+fmt(grand/10000,4)+' ha</p>'+table(["Família presente nos hexágonos","ha do elemento"],families.map((f,i)=>[f.name,fmt(familyAreas[i]/10000,4)]))+'<small>Área do elemento em células da família. A projeção edificada exposta é medida separadamente.</small><div class="scroll">'+table(["Recorte","Combinação","ha","% do elemento no recorte"],rows)+'</div>';
}
function fields(){by("entrada").hidden=by("modo").value==="avu";by("nomes").hidden=by("modo").value!=="avu"}
function consult(k,id){
 if(!ready)return; by("modo").value=k; fields();
 if(k==="avu")by("nomes").value=id;else by("numero").value=id;
 by("detalhe").innerHTML=k==="hex"?hex(id):objectView(k,id);
}
// A máscara de cada família e os totais territoriais vêm do cruzamento espacial.
const ecologia = "Sustentar a diversidade das formações e a continuidade da infraestrutura verde.";
const agua = "Restabelecer espaço para a água e reduzir a exposição à inundação na escala da bacia.";
const termica = "Melhorar as condições térmicas dos percursos e lugares de permanência.";
const acesso = "Ampliar o acesso cotidiano aos benefícios da IV onde a oferta é menor.";
const families = [
 {name:"Formações nativas abaixo dos cortes de calor", rule:"Predomínio florestal, savânico, campestre ou de campo alagado e temperatura do ar abaixo dos cortes de calor nos dois períodos.", main:ecologia, extra:"Considerar a função hídrica onde os Momentos da Água indicarem sua relevância.", scale:"Fragmento, entorno e rede da bacia.", color:"#246648"},
 {name:"Calor diurno e noturno em terra", rule:"Cobertura terrestre identificada, incluindo mosaicos, e temperatura acima do corte da bacia nos dois períodos.", main:termica, extra:acesso, scale:"Tecido urbano e espaços de uso cotidiano. Conferir ocupação, CC e HM antes de indicar uma intervenção.", color:"#98432f"},
 {name:"Calor em um único período em terra", rule:"Cobertura terrestre identificada e calor acima do corte apenas de dia ou apenas à noite. O mapa de calor distingue os dois períodos.", main:termica, extra:"Verificar acesso à sombra nos percursos diurnos e a configuração do entorno nos casos noturnos.", scale:"Lugar de permanência, percurso e entorno construído.", color:"#a96622"},
 {name:"Inundação em cobertura vegetada", rule:"Cobertura vegetal predominante, incluindo vegetação intraurbana e forração, com profundidade TR5 positiva em alguma parcela do hexágono.", main:agua, extra:ecologia, scale:"Trecho de drenagem e bacia contribuinte. Conferir se há fonte, condução ou acomodação.", color:"#227b82"},
 {name:"Inundação com edificações expostas", rule:"Interseção espacial de área positiva entre projeções edificadas e a inundação modelada no TR5, dentro do recorte. Contatos apenas de borda ficam de fora.", main:agua, extra:"Considerar a diretriz térmica nos lugares que também apresentam calor elevado.", scale:"Edificação e seu entorno para localizar exposição, bacia para investigar intervenções.", color:"#704b88"}
];
const cuts = [4,1,2,3];
let selectedFamily = 0;
let selectedCut = 4;
let catalog = null;
const inScope = i => selectedCut === 4 ? data.recorte[i] < 3 : data.recorte[i] === selectedCut;
const currentMap = () => panos[selectedCut === 3 ? "30" : "1"];
const ha = m => fmt(m/10000, m>0 && m<100 ? 4 : 2);
const percent = (m,total) => total ? fmt(100*m/total,m>0 && m/total<.0001 ? 4 : 2)+"%" : "Sem estimativa";
function pixelIndex(value){
 if(!value)return -1;
 const id=value & 0x7fffff, primary=first[id];
 if(primary===undefined || primary<0)return -1;
 if(second.has(id)){
  const target=(value & 0x800000)?1:2;
  return data.recorte[primary]===target?primary:second.get(id);
 }
 return primary;
}
function buildComparison(){
 const rows=families.map((family,index)=>{
  const cells=cuts.map(c=>{
   const s=data.stats[index][c];
   return '<td><button class="pick" data-family="'+index+'" data-cut="'+c+'" aria-label="'+family.name+', '+territories.get(c)+', '+ha(s.m2)+' hectares" aria-pressed="'+(index===selectedFamily&&c===selectedCut)+'"><strong>'+ha(s.m2)+' ha</strong><span>'+percent(s.m2,s.total)+'</span></button></td>';
  }).join("");
  return '<tr><th scope="row">'+family.name+'</th>'+cells+'</tr>';
 }).join("");
 by("comparar").innerHTML='<table><thead><tr><th rowspan="2" scope="col">Família em revisão</th><th colspan="3" scope="colgroup">Plano Piloto na bacia</th><th rowspan="2" scope="col">Vicente Pires</th></tr><tr><th>Total</th><th>Dentro do Parque Nacional</th><th>Fora do Parque Nacional</th></tr></thead><tbody>'+rows+'</tbody></table>';
}
by("comparar").addEventListener("click",event=>{
 const b=event.target.closest("button[data-family]");
 if(b)selectFamily(Number(b.dataset.family),Number(b.dataset.cut));
});
function selectFamily(index,cut,resetTheme=true){
 if(!ready)return;
 selectedFamily=index;selectedCut=cut;
 by("ra").value=String(cut);
 if(resetTheme)by("tema").value="familia";
 const f=families[index],s=data.stats[index][cut];
 buildComparison();
 let text='<h3>'+f.name+'</h3><p>'+f.rule+'</p><p><strong>'+ha(s.m2)+' ha de hexágonos no recorte</strong> · '+percent(s.m2,s.total)+' do recorte.</p>';
 if(index===3)text+='<p>A vegetação predominante e a parcela inundada ocorrem na mesma célula. A mancha inundada pode alcançar mais de uma cobertura dentro dela.</p>';
 if(index===4)text+='<p><strong>'+ha(s.footprint)+' ha de projeção edificada exposta</strong> dentro das parcelas classificadas.</p>';
 by("ficha").innerHTML=text+'<details><summary>Diretrizes, escala e cobertura</summary><p><strong>Principal</strong> · '+f.main+'</p><p><strong>Complementar</strong> · '+f.extra+'</p><p><strong>Escala</strong> · '+f.scale+'</p><p>Área indeterminada para esta família · '+ha(s.unknown)+' ha. Entre as parcelas classificadas na família, '+percent(s.stable,s.m2)+' mantiveram a combinação original em todos os testes de sensibilidade.</p></details>';
 draw(); renderCriteria();
 if(s.example!==null)consult("hex",s.example);
 else by("detalhe").textContent="Nenhuma parcela identificada nesta família e neste recorte. Selecione um hexágono no mapa para consultá-lo.";
}
function toRGBA(hexcode){
 const n=parseInt(hexcode.slice(1),16);
 return (0xff000000 | ((n & 255)<<16) | (n & 0xff00) | (n>>>16))>>>0;
}
function draw(){
 const p=currentMap();if(!p)return;
 const theme=by("tema").value;
 const missing="#be9c63",other="#d4dcd4",outside="#ffffff", f=families[selectedFamily];
 const palette=theme==="familia"?{[f.name]:f.color,"Outras áreas analisadas":other,"Evidência insuficiente":missing}:colors[theme];
 const rowColors=new Uint32Array(data.id_hex.length);
 const mask=1<<selectedFamily;
 const pos=toRGBA(f.color), neutral=toRGBA(other), unknown=toRGBA(missing), off=toRGBA(outside);
 const groupColors=theme==="familia"?{}:Object.fromEntries(data.grupos.map(g=>[g.grupo_id,toRGBA(palette[g[theme]])]));
 for(let i=0;i<rowColors.length;i++){
  if(!inScope(i)){rowColors[i]=off;continue}
  if(theme!=="familia"){rowColors[i]=groupColors[data.grupo_id[i]];continue}
  rowColors[i]=(data.fam[i]&mask)?pos:(data.inc[i]&mask)?unknown:neutral;
 }
 const canvas=by("mapa");canvas.width=p.width;canvas.height=p.height;
 const ctx=canvas.getContext("2d"),image=ctx.createImageData(p.width,p.height),pixels=new Uint32Array(image.data.buffer);
 for(let j=0;j<p.ids.length;j++){
  const i=pixelIndex(p.ids[j]);pixels[j]=i<0?off:rowColors[i];
 }
 ctx.putImageData(image,0,0);
 by("legenda").innerHTML=Object.entries({...palette,"Fora do recorte":outside}).map(([k,c])=>'<span><i class="dot" style="background:'+c+'"></i>'+escapeText(label(k))+'</span>').join("");
}
function hexEvidence(ix,area){
 const i=ix[0];
 const seen=families.filter((_,f)=>ix.some(n=>data.fam[n]&(1<<f)));
 const gap=families.filter((_,f)=>ix.some(n=>data.inc[n]&(1<<f)));
 const land=ix.reduce((a,n)=>a+data.edif_tr5_positivo_m2[n],0);
 let body='<p><b>Famílias presentes</b> · '+(seen.map(f=>f.name).join(" / ")||"Nenhuma das cinco propostas")+'</p>';
 if(seen.length)body+='<p><b>Diretrizes principais</b> · '+[...new Set(seen.map(f=>f.main))].join(" ")+'</p>';
 if(gap.length)body+='<p>Evidência insuficiente · '+gap.map(f=>f.name).join(" / ")+'</p>';
 const metric=(key,digit=2)=>Number.isFinite(data[key][i])?fmt(data[key][i],digit):"Sem estimativa";
 const metrics=[
 ["ΔT relativo à A001 · dia / noite (°C)",metric("delta_dia")+" / "+metric("delta_noite")],
 ["CC · dia / noite",metric("cc_dia_mean",3)+" / "+metric("cc_noite_mean",3)],
 ["HM · dia / noite",metric("hm_dia_mean",3)+" / "+metric("hm_noite_mean",3)],
 ["Landsat · seca / chuva (°C de superfície)",metric("lst_seca_mean")+" / "+metric("lst_chuva_mean")],
 ["TR5 · cobertura válida (%)",metric("inundacao_coverage_pct")],
 ["Área inundada na parcela válida (%)",metric("inundada_pct_valida")],
 ["Profundidade média na parcela positiva (m)",data.inundada_pct_valida[i]===0?"Não se aplica":metric("profundidade_media_inundada_m")],
 ["Projeção edificada sobre inundação no recorte (m²)",fmt(land)],
 ["Projeção edificada sem estimativa TR5 no recorte (m²)",fmt(ix.reduce((a,n)=>a+data.edif_sem_estimativa_m2[n],0))],
 ["Edificações na célula (%)",metric("edif_pct")],["Renda do setor (SM de 2022)",metric("renda_sm")],
 ["Momentos da Água · fonte / condução / acomodação (%)",["momentos_pct_fonte","momentos_pct_conducao","momentos_pct_acomodacao"].map(k=>metric(k)).join(" / ")],
 ["PRE · alto / muito alto / cobertura válida (%)",["pre_pct_alto","pre_pct_muito_alto","pre_coverage_pct"].map(k=>metric(k)).join(" / ")],
 ["Combinação original estável nos testes",data.stability[i]?"Sim":"Sensível"]
 ];
 return body+'<details><summary>Indicadores e cobertura do hexágono</summary>'+table(["Indicador","Valor"],metrics)+'<small>Indicadores da unidade integral. Áreas de interseção usam a parcela no recorte. A renda caracteriza o setor de maior sobreposição.</small></details>';
}
function renderCriteria(){
 if(!catalog){
  catalog={};
  for(const c of cuts)catalog[c]=new Map();
  for(let i=0;i<data.id_hex.length;i++){
   const code=data.recorte[i],g=data.grupo_id[i],area=data.m2[i];
   for(const c of code===3?[3]:[code,4]){
    const stats=catalog[c].get(g)||[0,0,...families.map(()=>0)];
    stats[0]+=area;
    if(data.stability[i])stats[1]+=area;
    for(let f=0;f<families.length;f++)if(data.fam[i]&(1<<f))stats[2+f]+=area;
    catalog[c].set(g,stats);
   }
  }
 }
 const rows=data.grupos.map(g=>{
  const totals=catalog[selectedCut].get(g.grupo_id);
  const area=totals?.[0]||0;
  return [g.grupo_id,condition(g),ha(area),ha(totals?.[2+selectedFamily]||0),area?percent(totals[1],area):"—"];
 });
 const sens=data.sensitivity.map(r=>[r.ra===1?"Plano Piloto":"Vicente Pires",escapeText(r.variacao),fmt(r.area_sensivel_ha),fmt(r.pct_ra)]);
 const method=[
  "As cinco famílias são propostas para o livro. Cada percentual da tabela comparativa usa a área integral do recorte. As parcelas dentro e fora do Parque Nacional seguem seu limite cartográfico. As famílias podem se sobrepor ou deixar outras situações para discussão.",
  "O calor relativo usa a média da bacia mais um desvio-padrão na seca: 26,3293 °C de dia e 20,0557 °C à noite. O ΔT usa as referências de 24,2654 e 19,7144 °C da A001. A predominância exige mais de 50% da célula. TR5 positivo indica profundidade maior que zero em alguma parcela válida.",
  "A evidência insuficiente depende dos dados necessários à família. Um contato positivo estabelece presença com cobertura parcial. Sem contato positivo, a parcela edificada descoberta pelo TR5 mantém a condição indeterminada. As tabelas usam áreas de interseção; o mapa usa pixels para navegação."
 ];
 const catalogTable=table(["ID","Cobertura · calor · TR5","ha no recorte","ha na família selecionada","Área estável da combinação"],rows);
 const sensitivityTable=table(["RA","Variação","Área sensível (ha)","% da RA"],sens);
 by("criterios").innerHTML=method.map(p=>"<p>"+p+"</p>").join("")
  +"<h3>Combinações do piloto · "+escapeText(territories.get(selectedCut))+"</h3><p>Família selecionada · "+families[selectedFamily].name+"</p>"
  +'<div class="scroll">'+catalogTable+"</div><h3>Sensibilidade da combinação original por RA</h3>"
  +"<p>Variaram o corte de calor, a predominância da cobertura e o tratamento de pequenas parcelas com inundação positiva. Uma mudança da combinação original pode ocorrer mesmo quando a parcela continua na mesma família.</p>"+sensitivityTable;
}
async function init(){
 const metrics=Object.fromEntries(data.metrics.map(k=>[k,Float64Array]));
 const tipos=Object.entries({...metrics,fam:Uint8Array,inc:Uint8Array,stability:Uint8Array,id_hex:Uint32Array,recorte:Uint8Array,grupo_id:Uint8Array,m2:Float64Array,iv_m2:Float64Array,avu_uniao_m2:Float64Array,frag_offset:Uint32Array,avu_offset:Uint32Array,frag_id:Uint32Array,avu_id:Uint32Array,frag_m2:Float64Array,avu_m2:Float64Array});
 for(let pos=0;pos<tipos.length;pos+=6){
  await Promise.all(tipos.slice(pos,pos+6).map(async ([field,T])=>{
   data[field]=new T(await descompactar(field+".bin.gz"));
  }));
 }
 let maxId=0;for(const id of data.id_hex)maxId=Math.max(maxId,id);
 first=new Int32Array(maxId+1).fill(-1);second=new Map();
 for(let i=0;i<data.id_hex.length;i++){const id=data.id_hex[i];if(first[id]===-1)first[id]=i;else second.set(id,i)}
 for(const [code,url] of Object.entries(data.panos)){
  const img=new Image();img.src=new URL(url,pastaMatriz).href;await img.decode();const c=document.createElement("canvas");c.width=img.width;c.height=img.height;
  const ctx=c.getContext("2d");ctx.drawImage(img,0,0);const pix=ctx.getImageData(0,0,c.width,c.height).data,ids=new Uint32Array(c.width*c.height);
  for(let i=0;i<ids.length;i++)ids[i]=pix[i*4]+256*pix[i*4+1]+65536*pix[i*4+2];panos[code]={ids,width:c.width,height:c.height};
 }
 const active=new Set(data.avu_id);
 for(const a of data.avus.filter(a=>active.has(a.id_avu)).sort((x,y)=>(x.nome||"").localeCompare(y.nome||""))){
 const opt=new Option((a.nome||a.tipo)+" · "+a.id_avu,a.id_avu);by("nomes").add(opt);}
 ready=true;selectFamily(0,4);
}
by("busca").onsubmit=e=>{e.preventDefault();const k=by("modo").value;consult(k,Number(by(k==="avu"?"nomes":"numero").value))};
by("modo").onchange=fields;by("ra").onchange=()=>selectFamily(selectedFamily,Number(by("ra").value),false);by("tema").onchange=draw;
by("detalhe").onclick=e=>{const b=e.target.closest("button[data-kind]");if(b)consult(b.dataset.kind,Number(b.dataset.id))};
by("mapa").onclick=e=>{if(!ready)return;const p=currentMap(),r=e.target.getBoundingClientRect();const x=Math.floor((e.clientX-r.left)*p.width/r.width),y=Math.floor((e.clientY-r.top)*p.height/r.height);const i=pixelIndex(p.ids[y*p.width+x]);if(i>=0&&inScope(i))consult("hex",data.id_hex[i])};
await init();
}
iniciarMatriz().catch(mostrarErro);
