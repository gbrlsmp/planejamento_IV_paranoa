"use strict";

const seletorRa = document.getElementById("indicador-ra");
const statusRa = document.getElementById("status-ra");
const formatoRa = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });

function valorRa(valor, unidade = "") {
  if (valor == null) return "—";
  const numero = formatoRa.format(valor);
  return unidade === "R$" ? "R$ " + numero : numero + (unidade ? " " + unidade : "");
}

function adicionarCelula(linha, valor, tipo = "td", escopo) {
  const celula = document.createElement(tipo);
  if (escopo) celula.scope = escopo;
  celula.textContent = valor;
  linha.append(celula);
}

function renderizarRas(dados) {
  const pos = seletorRa.selectedIndex;
  const indicador = dados.indicadores[pos];
  const colunas = [
    "Região Administrativa", "RA inteiramente dentro da bacia",
    "Fragmentos", "Área de fragmentos (ha)", "Área com dado válido (%)",
  ];
  if (indicador.numerico) colunas.push("Média ponderada", "Mínimo", "Máximo");
  colunas.push(...indicador.classes.map(classe => classe + " (%)"));
  const cabecalho = document.createElement("tr");
  for (const coluna of colunas) adicionarCelula(cabecalho, coluna, "th", "col");
  document.getElementById("colunas-ra").replaceChildren(cabecalho);

  const corpo = document.createDocumentFragment();
  for (const ra of dados.regioes) {
    const linha = document.createElement("tr");
    const resumo = ra.indicadores[pos];
    adicionarCelula(linha, ra.codigo + " · " + ra.nome, "th", "row");
    adicionarCelula(linha, ra.inteira ? "Sim" : "Não");
    for (const valor of [ra.fragmentos, ra.area_ha, resumo.cobertura]) {
      adicionarCelula(linha, valorRa(valor));
    }
    if (indicador.numerico) {
      for (const valor of [resumo.media, resumo.minimo, resumo.maximo]) {
        adicionarCelula(linha, valorRa(valor, indicador.unidade));
      }
    }
    for (const percentual of resumo.classes ?? []) adicionarCelula(linha, valorRa(percentual));
    corpo.append(linha);
  }
  document.getElementById("linhas-ra").replaceChildren(corpo);
  statusRa.textContent = dados.regioes.length + " RAs · " + indicador.titulo;
}

async function iniciarRas() {
  const resposta = await fetch("dados-mapas/riscos-por-ra.json");
  if (!resposta.ok) throw new Error("Resumo territorial indisponível.");
  const dados = await resposta.json();
  dados.regioes.sort((a, b) => a.nome.localeCompare(b.nome, "pt-BR"));
  for (const indicador of dados.indicadores) {
    seletorRa.add(new Option(indicador.titulo, indicador.id));
  }
  seletorRa.disabled = false;
  const mapIndicator = document.getElementById("indicador");
  function syncFromMap() {
    if (dados.indicadores.some(item => item.id === mapIndicator.value)) {
      seletorRa.value = mapIndicator.value;
      renderizarRas(dados);
    }
  }
  mapIndicator.addEventListener("change", syncFromMap);
  seletorRa.addEventListener("change", () => {
    renderizarRas(dados);
    if (Array.from(mapIndicator.options).some(option => option.value === seletorRa.value)) {
      mapIndicator.value = seletorRa.value;
      mapIndicator.dispatchEvent(new Event("change"));
    }
  });
  syncFromMap();
  renderizarRas(dados);
  document.getElementById("resultados-ra").hidden = false;
}

const raTheme = new URLSearchParams(location.search).get("tema");
if (typeof reportMapThemes !== "undefined" && Object.hasOwn(reportMapThemes, raTheme)) {
  document.getElementById("riscos-por-ra").hidden = true;
} else {
  iniciarRas().catch(erro => {
    console.error(erro);
    statusRa.textContent = "A tabela por RA não pôde ser carregada.";
  });
}
