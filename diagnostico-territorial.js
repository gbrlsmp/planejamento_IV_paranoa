"use strict";
(() => {
  const folder="dados-mapas/fitopolis-2026/", pending=new Map(), arrayBuffers=new Map();
  const number=(v,d=2)=>v==null || !Number.isFinite(v)?"Sem estimativa":v.toLocaleString("pt-BR",{maximumFractionDigits:d});
  const pause=()=>new Promise(resolve=>setTimeout(resolve,0));
  async function cached(key,producer) {
    if (!pending.has(key)) pending.set(key,producer().catch(e=>{pending.delete(key);throw e;}));
    return pending.get(key);
  }
  async function bytes(path) {
    const response=await fetch(path);if (!response.ok)throw new Error("Arquivo indisponível: "+path);
    let buffer=await response.arrayBuffer();const head=new Uint8Array(buffer,0,Math.min(2,buffer.byteLength));
    if (head[0]===31 && head[1]===139) buffer=await new Response(new Blob([buffer]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer();
    return buffer;
  }
  function array(kind,record,type=Float64Array) {
    const key=folder+kind+"/"+record.file;
    if(arrayBuffers.has(key)){const item=arrayBuffers.get(key);arrayBuffers.delete(key);arrayBuffers.set(key,item);return item;}
    const task=(async()=>{const buffer=await bytes(key+"?v="+record.sha256.slice(0,16));if (buffer.byteLength!==record.count*type.BYTES_PER_ELEMENT)throw new Error("Tamanho de dados divergente.");return new type(buffer);})().catch(e=>{arrayBuffers.delete(key);throw e;});
    arrayBuffers.set(key,task);while(arrayBuffers.size>12)arrayBuffers.delete(arrayBuffers.keys().next().value);return task;
  }
  function ids(kind,info) {
    return cached(kind+":ids",()=>new Promise((resolve,reject)=>{
      const img=new Image();img.onload=()=>{try {const canvas=document.createElement("canvas");canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;const ctx=canvas.getContext("2d",{willReadFrequently:true});ctx.drawImage(img,0,0);resolve({width:canvas.width,height:canvas.height,data:ctx.getImageData(0,0,canvas.width,canvas.height).data});}catch(e){reject(e);}};
      img.onerror=()=>reject(new Error("Não foi possível carregar a malha de visualização."));img.src=folder+kind+"/"+info.image.file+"?v="+info.image.sha256.slice(0,16);
    }));
  }
  function json(kind,path) { return cached(kind+":"+path,()=>loadData(folder+kind+"/"+path)); }
  function label(field) {
    return ({area_m2:"Área da unidade (m²)",edif_ocupada_m2:"Área ocupada (m²)",edif_dominio_m2:"Área do domínio de edificações (m²)",inundacao_valid_m2:"Área com estimativa TR5 (m²)",inundada_m2:"Área inundada (m²)",inundada_pct_valida:"Proporção inundada da área válida (%)",profundidade_media_inundada_m:"Profundidade média na parcela inundada (m)",inundacao_max:"Profundidade máxima válida (m)",setor_pct_unidade:"Parcela da unidade no setor selecionado (%)",renda_reais:"Rendimento contextual (R$, 2022)"})[field] || (field.endsWith("_min")?"Mínimo":field.endsWith("_max")?"Máximo":field.endsWith("_stdev")?"Desvio padrão":field);
  }
  function initialize(root) {
    root.innerHTML=`<div class="fitopolis-tools"><label>Unidade de análise<select data-unit><option value="hexagonos">Hexágonos · 30 m entre faces</option><option value="fragmentos">Fragmentos · 46.876 unidades</option></select></label><label>Indicador<select data-field></select></label><label>Consultar ID ou chave q:r<input data-search placeholder="Ex.: 125 ou q:r"></label><button type="button" data-find>Localizar</button><button type="button" data-fit>Bacia inteira</button><button type="button" data-download>Baixar seleção (CSV)</button></div><div class="fitopolis-legend" data-legend></div><div class="fitopolis-summary" data-summary></div><div class="fitopolis-map" role="region" aria-label="Diagnóstico territorial por hexágonos e fragmentos"></div><p class="fitopolis-status" data-status role="status" aria-live="polite">Abra esta seção para carregar o mapa.</p><p class="climate-note">Os resultados das unidades permanecem integrais ao selecionar RAs. Os resumos usam a parcela inserida no recorte. Cinza indica valor ausente; zero é um valor válido. As cores são contínuas e comparáveis entre RAs. <a href="docs/metodologia-diagnostico-fitopolis.md">Métodos e limites</a>.</p>`;
    const $=s=>root.querySelector(s),unit=$("[data-unit]"),field=$("[data-field]"),status=$("[data-status]");
    $("[data-find]").disabled=true;$("[data-download]").disabled=true;
    const sourceLabel=document.createElement("label");sourceLabel.textContent="Camada de origem / identificação";
    const sourceSelect=document.createElement("select");sourceSelect.append(new Option("Nenhuma", ""));
    for(const [key,title] of [["uso","Uso e cobertura"],["momentos","Momentos da Água"],["pre","PRE"],["iv","Elementos da IV"],["tipologias","Tipologias de AVU"],["origem:inund_max","Profundidade TR5 · origem"],["origem:edif_pct","Edificações · origem"],["origem:renda_sm","Renda por setor · origem"]])sourceSelect.append(new Option(title,key));
    sourceLabel.append(sourceSelect);$(".fitopolis-tools").append(sourceLabel);
    let sourceLayer,sourceToken=0;
    let manifest,base,map,overview,outline,canvas,ctx,current,token=0,drawRequest=0,started=false,starting=false;
    let overviewUrl=null;
    const colorCache=new Map();
    function schedule() { if (!drawRequest) drawRequest=requestAnimationFrame(()=>{drawRequest=0;drawDetail();}); }
    function drawDetail() {
      if (!current || !map)return;
      const began=performance.now();let drawn=0;
      const detailed=current.kind==="hexagonos" && map.getZoom()>=14;
      canvas.hidden=!detailed;
      if (!detailed) {if (overview && !map.hasLayer(overview)) overview.addTo(map);return;}
      overview?.remove();
      const size=map.getSize(),dpr=Math.min(devicePixelRatio||1,2),origin=map.containerPointToLayerPoint([0,0]);
      canvas.width=Math.ceil(size.x*dpr);canvas.height=Math.ceil(size.y*dpr);canvas.style.width=size.x+"px";canvas.style.height=size.y+"px";L.DomUtil.setPosition(canvas,origin);ctx.setTransform(dpr,0,0,dpr,0,0);
      // A cartographic basin clip also trims partial cells in overview/detail.
      ctx.beginPath();
      for (const f of base.bacia.features || [base.bacia]) {
        const polys=f.geometry.type==="Polygon"?[f.geometry.coordinates]:f.geometry.coordinates;
        for (const rings of polys)for (const ring of rings) {ring.forEach(([lng,lat],i)=>{const p=map.latLngToContainerPoint([lat,lng]);if (i)ctx.lineTo(p.x,p.y);else ctx.moveTo(p.x,p.y);});ctx.closePath();}
      }
      ctx.clip("evenodd");
      const b=map.getBounds(),corners=[b.getNorthWest(),b.getNorthEast(),b.getSouthWest(),b.getSouthEast()].map(p=>FitopolisDados.utmForward(p.lng,p.lat));
      const minx=Math.min(...corners.map(p=>p[0]))-60,maxx=Math.max(...corners.map(p=>p[0]))+60,miny=Math.min(...corners.map(p=>p[1]))-60,maxy=Math.max(...corners.map(p=>p[1]))+60;
      const q0=Math.floor(minx/(1.5*FitopolisDados.side)),q1=Math.ceil(maxx/(1.5*FitopolisDados.side)),ax=current.axial;
      colorCache.clear();
      for (let q=q0;q<=q1;q++) {
        const r0=Math.floor(miny/30-q/2),r1=Math.ceil(maxy/30-q/2);
        let low=0,high=ax.length/2;
        while(low<high){const mid=(low+high)>>>1;if(ax[2*mid]<q || (ax[2*mid]===q && ax[2*mid+1]<r0))low=mid+1;else high=mid;}
        for(let i=low;i<ax.length/2 && ax[2*i]===q && ax[2*i+1]<=r1;i++) {
          const r=ax[2*i+1],center=FitopolisDados.center(q,r),value=current.values[i];
          const bucket=Number.isFinite(value)?Math.round(255*Math.max(0,Math.min(1,(value-current.config.range[0])/(current.config.range[1]-current.config.range[0]||1)))):-1;
          if (!colorCache.has(bucket)) colorCache.set(bucket,"rgba("+FitopolisDados.color(value,current.config.range,current.config.colors).join(",")+")");
          ctx.fillStyle=colorCache.get(bucket);ctx.beginPath();
          for(let k=0;k<6;k++){const angle=k*Math.PI/3,[lng,lat]=FitopolisDados.utmInverse(center[0]+FitopolisDados.side*Math.cos(angle),center[1]+FitopolisDados.side*Math.sin(angle)),p=map.latLngToContainerPoint([lat,lng]);if(k)ctx.lineTo(p.x,p.y);else ctx.moveTo(p.x,p.y);}
          ctx.closePath();ctx.fill();if(map.getZoom()>=16){ctx.strokeStyle="#354e4166";ctx.lineWidth=.5;ctx.stroke();}
          drawn++;
        }
      }
      root.dataset.drawMs=(performance.now()-began).toFixed(2);root.dataset.drawnUnits=String(drawn);
    }
    async function update() {
      if(!map || !manifest)return;
      const began=performance.now();$("[data-find]").disabled=true;$("[data-download]").disabled=true;
      const generation=++token,kind=unit.value,key=field.value,info=manifest.units[kind],config=manifest.indicators[key];
      status.textContent="Carregando o indicador…";outline?.remove();
      try {
        const [values,pixels,axial,coverage,summaries]=await Promise.all([array(kind,info.arrays[key]),ids(kind,info),kind==="hexagonos"?array(kind,info.axial,Int32Array):null,config.coverage?array(kind,info.arrays[config.coverage]):null,json(kind,info.summaries)]);
        if(generation!==token)return;
        current={kind,key,info,config,values,pixels,axial,coverage,summaries};
        const image=document.createElement("canvas");image.width=pixels.width;image.height=pixels.height;const bytesOut=new Uint8ClampedArray(pixels.data.length);
        // Lookup colors once per unit, then color pixels without per-pixel parsing.
        const lut=new Uint8ClampedArray((values.length+1)*4);
        for(let i=0;i<values.length;i++){lut.set(FitopolisDados.color(values[i],config.range,config.colors),(i+1)*4);if(i && i%50000===0){await pause();if(generation!==token)return;}}
        for(let i=0;i<bytesOut.length;i+=4){const id=pixels.data[i]*65536+pixels.data[i+1]*256+pixels.data[i+2],offset=id*4;bytesOut[i]=lut[offset];bytesOut[i+1]=lut[offset+1];bytesOut[i+2]=lut[offset+2];bytesOut[i+3]=lut[offset+3];if(i && i%4000000===0){await pause();if(generation!==token)return;}}
        image.getContext("2d").putImageData(new ImageData(bytesOut,image.width,image.height),0,0);
        const blob=await new Promise(resolve=>image.toBlob(resolve,"image/png"));if(generation!==token)return;
        overview?.remove();if(overviewUrl)URL.revokeObjectURL(overviewUrl);overviewUrl=URL.createObjectURL(blob);
        const b=info.image.bounds,crs=L.CRS.EPSG3857;
        overview=L.imageOverlay(overviewUrl,[crs.unproject(L.point(b[0],b[1])),crs.unproject(L.point(b[2],b[3]))],{className:"mapa-classe",opacity:1,alt:config.label}).addTo(map);
        const legend=$("[data-legend]");legend.replaceChildren();const title=document.createElement("strong");title.textContent=config.label+(config.unit?" ("+config.unit+")":"");
        const ramp=document.createElement("div");ramp.className="fitopolis-ramp";ramp.style.background="linear-gradient(to right,"+config.colors.join(",")+")";
        const range=document.createElement("div");range.className="fitopolis-range";for(const v of config.range){const span=document.createElement("span");span.textContent=number(v,3);range.append(span);}
        const note=document.createElement("p");note.textContent=config.note;legend.append(title,ramp,range,note);
        status.textContent=`${number(info.count,0)} ${kind==='hexagonos'?'hexágonos':'fragmentos'} · clique para consultar. No panorama, IDs de 20 m podem omitir unidades pequenas; a busca abrange todos os IDs.`;
        await summary();schedule();root.dataset.updateMs=(performance.now()-began).toFixed(2);root.dataset.heapBytes=String(performance.memory?.usedJSHeapSize || '');root.dataset.transferBytes=String(performance.getEntriesByType('resource').filter(r=>r.name.includes('fitopolis-2026')).reduce((sum,r)=>sum+r.transferSize,0));$("[data-find]").disabled=false;$("[data-download]").disabled=false;
      }catch(e){if(generation===token)status.textContent=e.message+" Troque o indicador para tentar novamente.";}
    }
    async function selectionAreas(kind) {
      const ras=FitopolisTerritorio.selected(),info=manifest.units[kind];
      if(!ras.length)return null;
      const rows=await Promise.all(ras.filter(ra=>info.ras[ra]).map(ra=>json(kind,info.ras[ra].file)));
      const totals=new Map();for(const row of rows)for(let i=0;i<row.indices.length;i++)totals.set(row.indices[i],(totals.get(row.indices[i])||0)+row.areas[i]);
      return totals;
    }
    async function summary() {
      if(!current)return;
      const began=performance.now();
      const captured=current,ras=FitopolisTerritorio.selected(),combined=FitopolisDados.combine(current.summaries[current.key],ras),areas=await selectionAreas(current.kind);
      if(captured!==current)return;
      const node=$("[data-summary]");node.replaceChildren();
      for(const text of [`${number((areas?areas.size:current.info.count),0)} unidades que intersectam o recorte`,`Área das unidades no recorte: ${number(combined.area/10000)} ha`,`Cobertura válida proporcional: ${number(combined.coverage)}%`]){const p=document.createElement("p");p.textContent=text;node.append(p);}
      const note=document.createElement("p");note.textContent="Área válida no recorte estimada pela proporção válida integral de cada unidade. A seleção de RAs não recalcula seus indicadores.";node.append(note);
      if(ras.length>0){
        const wrap=document.createElement("div");wrap.className="table-scroll";wrap.style.width="100%";
        const table=document.createElement("table");table.className="indicator-table";
        const head=document.createElement("thead"),tr=document.createElement("tr");
        for(const title of ["RA","Área no recorte (ha)","Cobertura proporcional (%)","Mínimo das unidades","Máximo das unidades"]){const th=document.createElement("th");th.textContent=title;tr.append(th);}head.append(tr);table.append(head);
        const body=document.createElement("tbody");
        for(const ra of ras){const row=captured.summaries[captured.key][ra];if(!row)continue;const line=document.createElement("tr");for(const value of [regionNames[ra]||ra,number(row.area_m2/10000),number(100*(row.coverage_m2??row.valid_m2)/row.area_m2),number(row.min,4),number(row.max,4)]){const td=document.createElement("td");td.textContent=value;line.append(td);}body.append(line);}table.append(body);wrap.append(table);node.append(wrap);
      }
      root.dataset.summaryMs=(performance.now()-began).toFixed(2);
    }
    async function popup(index,latlng) {
      if(!current || index<0 || index>=current.values.length)return;
      const c=current,info=c.info,fields=["area_m2",...c.config.details];
      const arrays=await Promise.all(fields.map(f=>array(c.kind,info.arrays[f])));if(c!==current)return;
      const box=document.createElement("div");box.className="fitopolis-popup";const title=document.createElement("strong");title.textContent=(c.kind==="hexagonos"?"Hexágono ":"Fragmento ")+(index+1)+(c.axial?` · ${c.axial[index*2]}:${c.axial[index*2+1]}`:"");box.append(title);
      const values=document.createElement("dl");
      function line(name,value){const dt=document.createElement("dt"),dd=document.createElement("dd");dt.textContent=name;dd.textContent=value;values.append(dt,dd);}
      const notApplicable=c.key==="profundidade_media_inundada_m" && !Number.isFinite(c.values[index]) && c.coverage[index]>0;
      line(c.config.label,notApplicable?"Não se aplica: sem parcela inundada":number(c.values[index],4)+(Number.isFinite(c.values[index]) && c.config.unit?" "+c.config.unit:""));
      if(sourceLayer){const value=sourceLayer.classAt(L.CRS.EPSG3857.project(latlng));line("Camada de origem / identificação",value||"Sem classe neste local");}
      line("Cobertura válida",c.coverage?number(c.coverage[index])+"%":Number.isFinite(c.values[index])?"Disponível":"Sem dado disponível");
      fields.forEach((f,j)=>line(label(f),f==="inundada_m2" && c.coverage?.[index]===0?"Sem estimativa":f==="profundidade_media_inundada_m" && !Number.isFinite(arrays[j][index]) && c.coverage?.[index]>0?"Não se aplica: sem parcela inundada":number(arrays[j][index],4)));
      if(c.key==="renda_sm") {
        if(c.kind==="fragmentos"){const context=await json(c.kind,info.context);line("Setor censitário",context[index].setor_codigo||"Sem setor");line("Situação da renda",context[index].renda_status);}
        else {const codes=await json(c.kind,"renda-contexto.json.gz");line("Setor censitário",codes.setor_codigo[index]||"Sem setor");line("Situação da renda",codes.renda_status[index]);}
      }
      box.append(values);const note=document.createElement("p");note.textContent="Valores da unidade integral; os recortes de RA alteram a área resumida, não o indicador.";box.append(note);
      L.popup().setLatLng(latlng).setContent(box).openOn(map);
      if(c.kind==="fragmentos") {
        const batch=String(Math.floor(index/256)).padStart(3,"0"),data=await loadData(`dados-mapas/clima/diagnostico-2026/fragmentos-${batch}.geojson.gz`);
        if(c!==current)return;const feature=data.features.find(f=>f.properties.id_frag===index+1);
        outline?.remove();if(feature)outline=L.geoJSON(feature,{interactive:false,style:{color:"#273f2e",weight:2,fill:false}}).addTo(map);
      }
    }
    async function find() {
      if(!current)return;
      try{
        const text=$("[data-search]").value.trim();let index=Number(text)-1,latlng;
        if(current.kind==="hexagonos"){
          if(text.includes(":")){const [q,r]=text.split(":").map(Number);index=FitopolisDados.axialIndex(current.axial,q,r);}
          if(!Number.isInteger(index) || index<0 || index>=current.values.length)throw new Error("ID ou chave não localizado.");
          const [lng,lat]=FitopolisDados.utmInverse(...FitopolisDados.center(current.axial[2*index],current.axial[2*index+1]));latlng=L.latLng(lat,lng);
        }else{
          if(!Number.isInteger(index) || index<0 || index>=current.values.length)throw new Error("ID não localizado.");
          const centers=await array(current.kind,current.info.centers);latlng=L.CRS.EPSG3857.unproject(L.point(centers[2*index],centers[2*index+1]));
        }
        if(!map._fitopolisTerritory.contains(latlng)){
          const areas=await selectionAreas(current.kind);
          if(!areas?.has(index)){status.textContent="A unidade está fora das RAs selecionadas. Selecione a bacia inteira para localizá-la.";return;}
          for(const ra of FitopolisTerritorio.selected()){
            const record=current.info.ras[ra];if(!record)continue;const data=await json(current.kind,record.file);
            if(data.anchors?.[index]){latlng=L.latLng(...data.anchors[index]);break;}
          }
        }
        map.setView(latlng,Math.max(map.getZoom(),16),{animate:false});await popup(index,latlng);
      }catch(e){status.textContent=e.message;}
    }
    async function download() {
      if(!current)return;
      const captured=current;$("[data-download]").disabled=true;status.textContent="Preparando CSV da seleção…";
      try{
        const areas=await selectionAreas(captured.kind),unitArea=await array(captured.kind,captured.info.arrays.area_m2),parts=["\uFEFFid_unidade,chave_hex,indicador,valor,situacao_valor,cobertura_valida_pct,area_unidade_m2,area_no_recorte_m2\r\n"];
        let lines=[];
        for(let i=0;i<captured.values.length;i++){
          if(areas && !areas.has(i))continue;
          const key=captured.axial?captured.axial[2*i]+":"+captured.axial[2*i+1]:"",value=captured.values[i],coverage=captured.coverage?captured.coverage[i]:Number.isFinite(value)?100:"";
          lines.push(FitopolisDados.csvRecord(i+1,key,captured.key,value,coverage,unitArea[i],areas?areas.get(i):unitArea[i]));
          if(lines.length===10000){parts.push(lines.join(""));lines=[];await pause();}
        }
        parts.push(lines.join(""));const blob=new Blob(parts,{type:"text/csv;charset=utf-8"}),url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=`fitopolis-${captured.kind}-${captured.key}.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status.textContent="CSV preparado com os valores integrais e a área inserida no recorte.";
      }catch(e){status.textContent=e.message;}finally{$("[data-download]").disabled=false;}
    }
    async function start() {
      if(started || starting || !root.offsetWidth)return;
      starting=true;
      try{
        [manifest,base]=await Promise.all([loadData(folder+"manifesto.json"),loadData("mapa-base.json.gz")]);
        for(const [key,c] of Object.entries(manifest.indicators)){const option=document.createElement("option");option.value=key;option.textContent=c.label;field.append(option);}
        const params=new URLSearchParams(location.search),aliases={temp_dia:"t_dia_mean",temp_noite:"t_noite_mean",inund_max:"inundada_pct_valida",momentos:"momentos_pct_fonte",pre:"pre_pct_alto"};
        const requested=root.dataset.indicator || params.get("indicador") || params.get("tema") || "t_dia_mean";field.value=manifest.indicators[requested]?requested:aliases[requested]||"t_dia_mean";
        map=L.map($(".fitopolis-map"),{preferCanvas:true,scrollWheelZoom:false,zoomAnimation:false});const bounds=addMapBase(map,base);map.fitBounds(bounds,{padding:[12,12]});
        const sourcePane=map.createPane("fitopolis-fontes");sourcePane.style.zIndex="415";sourcePane.style.pointerEvents="none";
        sourceSelect.addEventListener("change",async()=>{
          const generation=++sourceToken;sourceLayer?.overlay.remove();sourceLayer=null;const key=sourceSelect.value;if(!key)return;
          try{
            const origin=key.startsWith("origem:"),id=origin?key.slice(7):key,catalog=await loadData(origin?"dados-mapas/contexto-riscos.json":"dados-mapas/catalogo.json");
            if(generation!==sourceToken)return;const config=catalog[id];if(!config)throw new Error("Camada de origem indisponível.");
            sourceLayer=createMapImage((origin?"dados-mapas/contexto/":"dados-mapas/")+id+".png",config,"fitopolis-fontes",.75);sourceLayer.overlay.addTo(map);
            sourceLayer.overlay.on("error",()=>{sourceLayer?.overlay.remove();sourceLayer=null;sourceSelect.value="";status.textContent="Falha ao carregar a camada de origem; selecione novamente para tentar.";});
            status.textContent="Sobreposição: "+config.title+". Clique para consultar a classe de origem junto com o indicador da unidade.";
          }catch(e){status.textContent=e.message;}
        });
        if(typeof addSatellite==="function" && document.getElementById("mostrar-satelite"))addSatellite(map);
        canvas=document.createElement("canvas");map.getPane("overlayPane").append(canvas);ctx=canvas.getContext("2d");
        map.on("moveend zoomend resize",schedule);
        map.on("click",e=>{
          if(!current || !map._fitopolisTerritory.contains(e.latlng) || !FitopolisTerritorio.inGeometry([e.latlng.lng,e.latlng.lat],base.bacia.features?.[0]?.geometry || base.bacia.geometry))return;
          let index=-1;
          if(current.kind==="hexagonos"){const [q,r]=FitopolisDados.axialAt(...FitopolisDados.utmForward(e.latlng.lng,e.latlng.lat));index=FitopolisDados.axialIndex(current.axial,q,r);}
          else{const b=current.info.image.bounds,p=L.CRS.EPSG3857.project(e.latlng),x=Math.floor((p.x-b[0])/(b[2]-b[0])*current.pixels.width),y=Math.floor((b[3]-p.y)/(b[3]-b[1])*current.pixels.height);if(x>=0 && y>=0 && x<current.pixels.width && y<current.pixels.height){const n=(y*current.pixels.width+x)*4,a=current.pixels.data;index=a[n]*65536+a[n+1]*256+a[n+2]-1;}}
          popup(index,e.latlng).catch(e=>{status.textContent=e.message;});
        });
        unit.addEventListener("change",update);field.addEventListener("change",update);$("[data-find]").addEventListener("click",find);$("[data-search]").addEventListener("keydown",e=>{if(e.key==="Enter")find();});$("[data-download]").addEventListener("click",download);
        $("[data-fit]").addEventListener("click",()=>FitopolisTerritorio.choose([]));
        window.addEventListener("fitopolis:territorio",()=>summary().catch(e=>{status.textContent=e.message;}));
        started=true;await update();
      }catch(e){status.textContent=e.message+" Reabra a seção para tentar novamente.";}finally{starting=false;}
    }
    new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting))start();},{rootMargin:"100px"}).observe(root);
    document.addEventListener("toggle",e=>{if(e.target.open && e.target.contains(root)){start();setTimeout(()=>map?.invalidateSize(),0);} },true);
    document.addEventListener("click",e=>{if(e.target.closest("[data-report-tabs]"))requestAnimationFrame(()=>{start();map?.invalidateSize();});});
    start();
  }
  document.querySelectorAll("[data-fitopolis]").forEach(initialize);
})();
