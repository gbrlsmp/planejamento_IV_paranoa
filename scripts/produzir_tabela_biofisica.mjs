import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const [climateRoot, moduleRoot] = process.argv.slice(2);
if (!climateRoot || !moduleRoot) throw new Error('Uso: node produzir_tabela_biofisica.mjs PASTA_CLIMA MODULOS_RUNTIME');
const req=createRequire(pathToFileURL(path.join(moduleRoot,'../package.json')));
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(req.resolve('@oai/artifact-tool',{paths:[moduleRoot]})).href);
const old=JSON.parse(await fs.readFile(path.join(climateRoot,'11_Intensidade_combinada_500m_2026-11-15/RESULTADO_COMBINACAO.json'),'utf8'));
const source=JSON.parse(await fs.readFile(path.join(climateRoot,'08_Scripts_e_verificacoes/Atualizacao_2026-11-15/TABELAS_JSON.json'),'utf8'));
const folder=path.join(climateRoot,'03_Tabelas/Biofisica');
const previewFolder=path.join(climateRoot,'07_Mapas_e_figuras/Tabela_biofisica');await fs.mkdir(previewFolder,{recursive:true});
const wb=Workbook.create();
const complete=wb.worksheets.add('Completa');const day=wb.worksheets.add('Diurna');const method=wb.worksheets.add('Método');
for(const sh of [complete,day,method]){
 sh.showGridLines=false;sh.getRange('A1:H38').format.font={name:'Arial',size:10,color:'#29372d'};
 sh.getRange('A1:H38').format.verticalAlignment='center';sh.getRange('A1:H38').format.rowHeight=24;
 sh.getRange('A:A').format.columnWidth=40;sh.getRange('B:B').format.columnWidth=12;sh.getRange('C:F').format.columnWidth=15;sh.getRange('G:G').format.columnWidth=22;
 sh.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:'#29372d'};
}
function header(sh,range){sh.getRange(range).format={fill:'#344f40',font:{name:'Arial',size:10,color:'#FFFFFF',bold:true},horizontalAlignment:'center',rowHeight:32};}
complete.getRange('A2').values=[['Tabela biofísica completa']];complete.getRange('A3').values=[['Cobertura auxiliar: vias 104 e edificações 1031–1033.']];
complete.getRange('A5:G17').values=source.complete;header(complete,'A5:G5');complete.getRange('A6:A17').format.wrapText=true;
complete.getRange('B6:B17').setNumberFormat('0');complete.getRange('C6:C17').setNumberFormat('0.0000000');complete.getRange('D6:D17').setNumberFormat('0');complete.getRange('E6:G17').setNumberFormat('0.000000');
day.getRange('A2').values=[['Tabela diurna da cobertura de dez classes']];day.getRange('A3').values=[['Inclui vias pavimentadas 104 e mantém edificações 103.']];
day.getRange('A5:F15').values=source.day;header(day,'A5:F5');day.getRange('A6:A15').format.wrapText=true;
day.getRange('B6:B15').setNumberFormat('0');day.getRange('C6:C15').setNumberFormat('0.0000000');day.getRange('D6:D15').setNumberFormat('0');day.getRange('E6:F15').setNumberFormat('0.000000');
method.getRange('A2').values=[['Intensidade construída e fontes']];method.getRange('A4').values=[['D = ocupação horizontal; V = mínimo(H500 / 31,5; 1); I = média 50/50 de D e V.']];
method.getRange('A6:B8').values=[['Referência vertical (m)',31.5],['Peso horizontal',.5],['Peso vertical',.5]];
method.getRange('A10:F13').values=[['Subclasse','Código','D médio','V médio','building_intensity','Faixa de I'],...old.classes.slice(0,3).map((c,i)=>[['Baixa','Média','Alta'][i],c.lucode,c.D_medio,c.V_medio,null,['>0–0,25','>0,25–0,50','>0,50–1'][i]])];header(method,'A10:F10');
for(let i=0;i<3;i++){
 method.getRange(`E${11+i}`).formulas=[[`=$B$7*C${11+i}+$B$8*D${11+i}`]];
 complete.getRange(`G${15+i}`).formulas=[[`='Método'!E${11+i}`]];
}
method.getRange('C11:E13').setNumberFormat('0.0000000000');method.getRange('A:A').format.columnWidth=28;method.getRange('B:B').format.columnWidth=13;method.getRange('C:F').format.columnWidth=22;
const notes=[
 ['Faixas','Baixa até 0,25; média >0,25–0,50; alta >0,50–1. As amplitudes são diferentes.'],
 ['Coeficientes','Média de I nos pixels 103 com altura regional disponível, por grupo.'],
 ['Alturas parciais','Média com dados aproveitáveis; sem mínimo adicional de cobertura regional.'],
 ['Preenchimento','6,445500373840332 m em 5,1174 ha; D local preservado; flag 9.'],
 ['Aplicação das fórmulas','Resumem os grupos existentes. Alterar pesos ou cortes exige reclassificar os rasters.'],
 ['Referência vertical','31,5 m é o P99 das medianas individuais de alturas; V limitado a 1.'],
 ['Adaptação','D/V combinados não medem a razão literal entre área de pavimentos e implantação.'],
 ['Fontes de Kc/albedo','Hu, Wang e Li (2023), Tabela 1. https://doi.org/10.3390/land12050963'],
 ['Shade','Ribeiro e Walter (2008), discussão de copas; valores são hipóteses da pesquisa.'],
 ['Savânica','Mistura 50% árvores + 50% herbáceas para Kc e albedo; shade 0,50.'],
 ['Classe 102','Média 50/50 de built-up e bare/sparse de Hu, sem frações locais medidas.'],
 ['Vias pavimentadas','Referência built-up de Hu; Kc 0,327539, albedo 0,208190; demais campos zero.'],
 ['Noite','BI zero nas classes não edificadas produz CC inicial 1; limitação do modelo.'],
 ['Alturas','Open Buildings 2023, cobertura 2026; fonte efetiva ~4 m, alinhamento de 3 m.'],
 ['Pesos diurnos','Padrão InVEST: sombra 0,60; albedo 0,20; evapotranspiração 0,20.'],
 ['Estado','Escolhas aprovadas; sem calibração local e sem nova execução do InVEST.']
];
notes.forEach(([label,text],i)=>{const n=16+i;method.getRange(`A${n}`).values=[[label]];method.getRange(`B${n}:F${n}`).merge();method.getRange(`B${n}`).values=[[text]];method.getRange(`B${n}:F${n}`).format.wrapText=true;method.getRange(`A${n}:F${n}`).format.rowHeight=34;});
complete.getRange('A20').values=[['Parâmetros por referência; não são calibração local. Critérios na aba Método.']];
day.getRange('A18').values=[['Usar esta tabela com a cobertura que mantém a classe 103.']];
wb.recalculate();
const actual=complete.getRange('G15:G17').values.flat();for(let i=0;i<3;i++)if(Math.abs(actual[i]-old.classes[i].building_intensity)>1e-12)throw new Error('Coeficiente divergente.');
const err=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},maxChars:1500});console.log(err.ndjson);
const book=await SpreadsheetFile.exportXlsx(wb);await book.save(path.join(folder,'tabela_biofisica_atual.xlsx'));
for(const [name,range] of [['Completa','A1:G21'],['Diurna','A1:F19'],['Método','A1:F32']]){
 const blob=await wb.render({sheetName:name,range,scale:1.4,format:'png'});await fs.writeFile(path.join(previewFolder,name==='Método'?'metodo.png':name.toLowerCase()+'.png'),new Uint8Array(await blob.arrayBuffer()));
}
console.log(JSON.stringify({rows:source.complete.length-1,coefficients:actual,output:path.join(folder,'tabela_biofisica_atual.xlsx')}));
