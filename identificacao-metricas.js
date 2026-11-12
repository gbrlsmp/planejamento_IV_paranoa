"use strict";

(() => {
  const root = document.querySelector("[data-makurhini]");
  if (!root) return;
  const form = root.querySelector("form");
  const input = root.querySelector("[name=fragmento]");
  const button = form.querySelector("button");
  const status = root.querySelector("[data-metric-status]");
  const result = root.querySelector("[data-metric-result]");
  const title = root.querySelector("[data-metric-title]");
  const tbody = root.querySelector("tbody");
  const format = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 4, maximumFractionDigits: 4 });

  form.addEventListener("submit", async event => {
    event.preventDefault();
    const id = Number(input.value);
    result.hidden = true;
    if (!Number.isInteger(id) || id < 1) {
      status.textContent = "Informe um ID de fragmento válido.";
      return;
    }
    button.disabled = true;
    form.setAttribute("aria-busy", "true");
    status.textContent = "Carregando as métricas dos dois cenários…";
    try {
      const { manifest, scenarios } = await loadMakurhiniMetrics();
      if (scenarios.some(scenario => !scenario.records.has(id))) {
        status.textContent = "ID não encontrado. Use um número de 1 a " + manifest.fragmentos.toLocaleString("pt-BR") + ".";
        return;
      }
      title.textContent = "Métricas do fragmento " + id;
      tbody.replaceChildren();
      manifest.indicadores.forEach((info, index) => {
        const row = document.createElement("tr");
        const name = document.createElement("th");
        name.scope = "row";
        name.textContent = info.nome + " (" + info.campo + ")";
        const unit = document.createElement("td");
        unit.textContent = info.unidade;
        row.append(name, unit);
        scenarios.forEach(scenario => {
          const value = document.createElement("td");
          value.textContent = format.format(scenario.records.get(id)[index]);
          row.append(value);
        });
        tbody.append(row);
      });
      result.hidden = false;
      status.textContent = "Fragmento " + id + ": valores originais dos cenários de 45 m e 90 m, apresentados com quatro casas decimais.";
    } catch (error) {
      status.textContent = "Não foi possível carregar a consulta. Tente novamente ou acesse os CSVs abaixo.";
    } finally {
      button.disabled = false;
      form.removeAttribute("aria-busy");
    }
  });
})();
