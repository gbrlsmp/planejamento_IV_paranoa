import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const [root,moduleRoot,outputDir]=process.argv.slice(2);
if(!root||!moduleRoot||!outputDir)throw new Error('Uso: node atualizar_tabela_biofisica_102_104.mjs PASTA_CLIMA MODULOS_RUNTIME PASTA_SAIDA');
const req=createRequire(pathToFileURL(path.join(moduleRoot,'../package.json')));
const {FileBlob,SpreadsheetFile,Workbook}=await import(pathToFileURL(req.resolve('@oai/artifact-tool',{paths:[moduleRoot]})).href);
const run=root+'/06_Execucoes_InVEST/Seca_2026_A001_102_104_2026-11-16';
const input=root+'/03_Tabelas/Biofisica/tabela_biofisica_atual.xlsx';
const output=path.join(outputDir,'tabela_biofisica_atual.xlsx');
await fs.mkdir(outputDir,{recursive:true});
const csvBook=await Workbook.fromCSV((await fs.readFile(run+'/01_Entradas/tab_biofisica_102_104_regional.csv','utf8')).replace(/^\uFEFF/,''),{sheetName:'Dados'});
const [csvFields,...csvRows]=csvBook.worksheets.getItem('Dados').getUsedRange().values;
const rows=csvRows.filter(row=>row[0]!=null).map(row=>Object.fromEntries(csvFields.map((key,i)=>[key,row[i]])));
assert.equal(rows.length,18);
const proof=JSON.parse(await fs.readFile(run+'/05_Verificacoes/PROVA_DIURNA_E_PARAMETRIZACAO.json','utf8'));
const wb=await SpreadsheetFile.importXlsx(await FileBlob.load(input));
const sh=wb.worksheets.getItem('Completa'),method=wb.worksheets.getItem('Método');
const beforeDiurna=wb.worksheets.getItem('Diurna').getRange('A1:H38').values;
const beforeMethod=method.getRange('A1:F31').values;
const beforeFormulas=method.getRange('E11:E13').formulas;
await fs.mkdir(run+'/09_Registros_vigentes_anteriores',{recursive:true});
try{await fs.copyFile(input,run+'/09_Registros_vigentes_anteriores/tabela_biofisica_atual.xlsx',fs.constants.COPYFILE_EXCL);}catch(e){if(e.code!=='EEXIST')throw e;}
sh.getRange('A26:G26').copyFrom(sh.getRange('A20:G20'),'all');
for(let r=18;r<=23;r++)sh.getRange(`A${r}:G${r}`).copyFrom(sh.getRange('A16:G16'),'all');
sh.getRange('A6:G25').clear({applyTo:'contents'});
sh.getRange('A3').values=[['Cobertura auxiliar: 18 códigos. Intensidade regional em 102/104; edificações 1031–1033 preservadas.']];
const fields=['classe','lucode','kc','green_area','shade','albedo','building_intensity'];
sh.getRange('A6:G23').values=rows.map(r=>fields.map(k=>k==='classe'?r[k]:Number(r[k])));
for(let i=0;i<rows.length;i++){
  const code=Number(rows[i].lucode),row=i+6;
  if(code>=1031&&code<=1033)sh.getRange(`G${row}`).formulas=[[`='Método'!E${11+code-1031}`]];
  else if(proof.classes.some(r=>r.lucode===code)){
    const j=proof.classes.findIndex(r=>r.lucode===code);
    sh.getRange(`G${row}`).formulas=[[`='Método'!B${35+j}`]];
  }
}
sh.getRange('A13:A23').format.wrapText=true;
sh.getRange('A13:G23').format.rowHeight=46;
method.getRange('B17').values=[['103: média de I disponível por grupo. 102/104: média disponível por superfície/faixa, excluindo preenchidos.']];
method.getRange('B19').values=[['H mediana 6,445500373840332 m: 103 = 5,1174 ha; 102/104 = 435,6081 ha; D preservado, flag 9.']];
method.getRange('B27').values=[['Kc/albedo de built-up; shade e green_area zero; BI regional nas subclasses 1040–1043.']];
method.getRange('B28').values=[['CC = 1 − BI. Alto CC em pavimento/edifício não prova resfriamento ativo. HM pode receber influência verde.']];
method.getRange('B31').values=[['Revisão noturna 102/104. Dia A001 preservado por equivalência integral; sem calibração térmica local.']];
method.getRange('A34:F34').copyFrom(method.getRange('A10:F10'),'all');
method.getRange('A34:F34').values=[['Código','Intensidade (BI)','Pixels com suporte','Pixels preenchidos','Faixa do índice I','Superfície']];
method.getRange('A34:F34').format.wrapText=true;
method.getRange('A34:F34').format.rowHeight=38;
for(let i=0;i<8;i++)method.getRange(`A${35+i}:F${35+i}`).copyFrom(method.getRange('A11:F11'),'all');
method.getRange('A35:F42').values=proof.classes.map(r=>[r.lucode,r.building_intensity,r.known_n,r.fallback_n,['D500 = 0','0 < I ≤ 0,25','0,25 < I ≤ 0,50','I > 0,50'][r.level],r.base===102?'Impermeável/solo exposto':'Vias pavimentadas']);
method.getRange('A35:A42').setNumberFormat('0');
method.getRange('B35:B42').setNumberFormat('0.0000000');
method.getRange('C35:D42').setNumberFormat('#,##0');
method.getRange('E35:F42').setNumberFormat('@');
method.getRange('E35:F42').format.wrapText=true;
method.getRange('E35:E42').format.horizontalAlignment='center';
method.getRange('A35:F42').format.rowHeight=34;
method.getRange('A44').values=[['Zero e lacunas']];
method.getRange('B44').values=[['D500 zero mantém BI zero. Lacunas com D positivo usam H mediana só para classificar; não estimam médias.']];
method.getRange('A45').values=[['Reprodução']];
method.getRange('B45').values=[['corrigir_intensidade_noturna.py; PROVA_DIURNA_E_PARAMETRIZACAO.json na rodada 102/104.']];
wb.recalculate();
assert.deepEqual(wb.worksheets.getItem('Diurna').getRange('A1:H38').values,beforeDiurna);
assert.deepEqual(method.getRange('E11:E13').formulas,beforeFormulas);
for(let r=0;r<31;r++)for(let c=0;c<6;c++){
  if(c===1&&[16,18,26,27,30].includes(r))continue;
  assert.equal(method.getRange('A1:F31').values[r][c],beforeMethod[r][c]);
}
const matrix=sh.getRange('A6:G23').values;
for(let r=0;r<rows.length;r++)for(let c=0;c<fields.length;c++){
  const expected=c?Number(rows[r][fields[c]]):rows[r].classe;
  if(c)assert.ok(Math.abs(matrix[r][c]-expected)<1e-14);else assert.equal(matrix[r][c],expected);
}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:20},maxChars:1500})).ndjson);
for(const [sheetName,range,file] of [['Completa','A1:G26','bio-after.png'],['Método','A34:F45','bio-method-after.png']]){
  const blob=await wb.render({sheetName,range,scale:1.3,format:'png'});
  await fs.writeFile(path.join(outputDir,file),new Uint8Array(await blob.arrayBuffer()));
}
const xlsx=await SpreadsheetFile.exportXlsx(wb);await xlsx.save(output);
const reopened=await SpreadsheetFile.importXlsx(await FileBlob.load(output));
assert.deepEqual(reopened.worksheets.getItem('Diurna').getRange('A1:H38').values,beforeDiurna);
const saved=reopened.worksheets.getItem('Completa').getRange('A6:G23').values;
for(let r=0;r<rows.length;r++)for(let c=1;c<7;c++)assert.ok(Math.abs(saved[r][c]-Number(rows[r][fields[c]]))<1e-14);
console.log(JSON.stringify({output,classes:18,day_unchanged:true,source_103_formulas_preserved:true,csv_values_verified:true}));
