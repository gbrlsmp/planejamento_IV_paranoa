"use strict";

(() => {
  const root = document.querySelector('[data-inmet-explorer]');
  if (!root) return;
  const select = root.querySelector('[data-station]');
  const variable = root.querySelector('[data-variable]');
  const status = root.querySelector('[data-inmet-status]');
  const colors = { chuva: '#426e93', seca: '#b27736' };
  const names = { chuva: 'Chuva', seca: 'Seca' };
  const labels = { temp: 'Temperatura média diária (°C)', rh: 'Umidade relativa média diária (%)' };
  const config = { responsive: true, displaylogo: false, locale: 'pt-BR', modeBarButtonsToRemove: ['lasso2d', 'select2d'] };
  let data, stationMap, markers = [], starting = false, ready = false, stationBounds;
  const num = (v, d = 1) => v == null ? 'Sem dados' : v.toLocaleString('pt-BR', { maximumFractionDigits: d });
  function layout(title, x, y, extra = {}) {
    return { title: { text: title, font: { size: 16 } }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
      font: { family: 'system-ui, sans-serif', color: '#29372d', size: 12 }, margin: { t: 54, r: 35, b: 66, l: 62 },
      xaxis: { title: x, automargin: true, gridcolor: '#e4e8e0' }, yaxis: { title: y, automargin: true, gridcolor: '#e4e8e0' },
      legend: { orientation: 'h', y: -.25 }, hovermode: 'closest', ...extra };
  }
  function plot(id, traces, options) { return Plotly.react(root.querySelector(`[data-chart="${id}"]`), traces, options, config); }
  function sankey(s) {
    const narrow = root.clientWidth < 500;
    const tc = s.sankey_cuts.temp, rc = s.sankey_cuts.rh;
    const tlabels = [`T ≤ ${num(tc[0])} °C`, `${num(tc[0])} < T ≤ ${num(tc[1])} °C`, `T > ${num(tc[1])} °C`];
    const rlabels = [`UR ≤ ${num(rc[0])}%`, `${num(rc[0])} < UR ≤ ${num(rc[1])}%`, `UR > ${num(rc[1])}%`];
    const links = [];
    for (const season of ['chuva', 'seca']) for (let t = 0; t < 3; t++) {
      const subset = s.sankey_counts.filter(r => r.season === season && r.temp_bin === t);
      const total = subset.reduce((n, r) => n + r.n, 0);
      if (total) links.push({ source: season === 'chuva' ? 0 : 1, target: 2 + (season === 'chuva' ? 0 : 3) + t, value: total,
        color: season === 'chuva' ? 'rgba(66,110,147,.35)' : 'rgba(178,119,54,.35)',
        label: `${names[season]}: ${num(total, 0)} dias · ${num(100 * total / s.summary[season].joint_days)}% dos dias pareados válidos` });
      for (const r of subset) links.push({ source: 2 + (season === 'chuva' ? 0 : 3) + t, target: 8 + r.rh_bin, value: r.n,
        color: season === 'chuva' ? 'rgba(66,110,147,.25)' : 'rgba(178,119,54,.25)',
        label: `${names[season]}: ${num(r.n, 0)} dias · ${num(100 * r.n / s.summary[season].joint_days)}% dos dias pareados válidos` });
    }
    const fullLabels = ['Chuva', 'Seca', ...tlabels.map(t => `Chuva · ${t}`), ...tlabels.map(t => `Seca · ${t}`), ...rlabels];
    const compactLabels = ['Chuva', 'Seca', 'T menor', 'T interm.', 'T maior', 'T menor', 'T interm.', 'T maior', 'UR menor', 'UR interm.', 'UR maior'];
    return plot('sankey', [{ type: 'sankey', arrangement: 'snap', valueformat: '.0f', valuesuffix: ' dias',
      node: { label: narrow ? compactLabels : fullLabels, customdata: fullLabels, hovertemplate: '%{customdata}<extra></extra>',
        color: [colors.chuva, colors.seca, ...Array(3).fill(colors.chuva), ...Array(3).fill(colors.seca), ...Array(3).fill('#65775f')], pad: 22, thickness: 15, line: { width: 0 } },
      link: { source: links.map(r => r.source), target: links.map(r => r.target), value: links.map(r => r.value), color: links.map(r => r.color), customdata: links.map(r => r.label), hovertemplate: '%{customdata}<extra></extra>' }
    }], layout(narrow ? 'Combinações dos dias observados' : 'Período → temperatura → umidade', '', '', { margin: { t: 60, r: narrow ? 12 : 35, b: 20, l: narrow ? 12 : 35 } }));
  }
  async function update() {
    const s = data.stations.find(s => s.id === select.value), v = variable.value;
    if (!s) return;
    status.textContent = `${s.id} · ${s.name}. Chuva: ${s.summary.chuva[v].n} de 212 dias válidos; seca: ${s.summary.seca[v].n} de 153. Horário de Brasília.`;
    const summary = root.querySelector('[data-inmet-summary]');
    summary.replaceChildren();
    for (const season of ['chuva', 'seca']) {
      const row = document.createElement('tr');
      for (const text of [names[season], num(s.summary[season].temp.mean) + ' °C', num(s.summary[season].rh.mean) + '%', `${num(s.summary[season].rain.sum)} mm em ${s.summary[season].rain.n} dias completos`, `${s.summary[season].joint_days}/${s.summary[season].expected_days}`]) {
        const td = document.createElement('td'); td.textContent = text; row.append(td);
      }
      summary.append(row);
    }
    const time = [{ x: s.daily.map(r => r.date), y: s.daily.map(r => r.rain), type: 'bar', name: 'Chuva diária', marker: { color: 'rgba(66,110,147,.45)' }, yaxis: 'y2', hovertemplate: '%{x}<br>%{y:.1f} mm<extra>Chuva diária</extra>' }];
    for (const season of ['chuva', 'seca']) time.push({ x: s.daily.map(r => r.date), y: s.daily.map(r => r.season === season ? r[v] : null), type: 'scatter', mode: 'lines', name: names[season], connectgaps: false, line: { color: colors[season], width: 1.6 } });
    const temporal = plot('timeline', time, layout('Um ano de observações', 'Data', labels[v], { yaxis2: { title: 'Chuva (mm/dia)', overlaying: 'y', side: 'right', showgrid: false }, margin: { t: 55, r: 70, b: 65, l: 60 } }));
    const boxes = plot('distribution', ['chuva', 'seca'].map(season => ({ type: 'box', y: s.daily.filter(r => r.season === season && r[v] != null).map(r => r[v]), name: `${names[season]} · n=${s.summary[season][v].n}`, marker: { color: colors[season] }, boxpoints: 'outliers', boxmean: true })), layout('Valores típicos e variação entre os dias', 'Período', labels[v]));
    const profiles = [];
    for (const season of ['chuva', 'seca']) {
      const p = s.profiles.filter(p => p.variable === v && p.season === season);
      profiles.push({ type: 'scatter', mode: 'lines', x: p.map(r => r.hour), y: p.map(r => r.q25), line: { width: 0 }, showlegend: false, hoverinfo: 'skip', legendgroup: season });
      profiles.push({ type: 'scatter', mode: 'lines', x: p.map(r => r.hour), y: p.map(r => r.q75), fill: 'tonexty', fillcolor: season === 'chuva' ? 'rgba(66,110,147,.12)' : 'rgba(178,119,54,.12)', line: { width: 0 }, showlegend: false, hoverinfo: 'skip', legendgroup: season });
      profiles.push({ type: 'scatter', mode: 'lines+markers', x: p.map(r => r.hour), y: p.map(r => r.mean), customdata: p.map(r => r.n), name: names[season], line: { color: colors[season] }, marker: { size: 4 }, legendgroup: season, hovertemplate: '%{x} h<br>%{y:.1f}<br>%{customdata} leituras válidas<extra>%{fullData.name}</extra>' });
    }
    const profile = plot('profile', profiles, layout('Ciclo horário: média e faixa entre os quartis', 'Hora local (UTC−03)', v === 'temp' ? 'Temperatura (°C)' : 'Umidade relativa (%)', { xaxis: { title: 'Hora local (UTC−03)', dtick: 3, range: [0, 23] } }));
    const scatter = plot('scatter', ['chuva', 'seca'].map(season => {
      const p = s.daily.filter(r => r.season === season && r.joint_temp != null);
      return { type: 'scatter', mode: 'markers', x: p.map(r => r.joint_temp), y: p.map(r => r.joint_rh), text: p.map(r => r.date), name: names[season], marker: { color: colors[season], symbol: season === 'chuva' ? 'circle' : 'diamond', size: 6, opacity: .65 }, hovertemplate: '%{text}<br>%{x:.1f} °C · %{y:.1f}%<extra>%{fullData.name}</extra>' };
    }), layout('Temperatura e umidade no mesmo dia', 'Temperatura média dos pares horários (°C)', 'Umidade média dos pares horários (%)'));
    await Promise.all([temporal, boxes, profile, scatter, sankey(s)]);
    for (const item of markers) item.marker.setStyle({ radius: item.id === s.id ? 9 : 6, fillOpacity: item.id === s.id ? 1 : .45 });
    root.querySelector('[data-sankey-note]').textContent = `Faixas relativas calculadas pelos tercis dos dias pareados de ${s.id}, reunindo os dois períodos. Temperatura: ${num(s.sankey_cuts.temp[0], 2)} e ${num(s.sankey_cuts.temp[1], 2)} °C; umidade: ${num(s.sankey_cuts.rh[0], 2)} e ${num(s.sankey_cuts.rh[1], 2)}%. Os limites são iguais entre os períodos desta estação. Não são limiares de risco ou conforto.`;
  }
  async function start() {
    if (starting || ready || !root.offsetWidth) return;
    starting = true;
    try {
      const [observations, base] = await Promise.all([
        loadData('dados-mapas/clima/inmet-exploracao.json?v=20261115'), loadData('mapa-base.json.gz')
      ]);
      data = observations;
      if (!root.offsetWidth) return;
      select.replaceChildren();
      for (const s of data.stations) { const option = document.createElement('option'); option.value = s.id; option.textContent = `${s.id} · ${s.name}`; select.append(option); }
      select.value = 'A001'; select.disabled = false; variable.disabled = false;
      stationMap = L.map(root.querySelector('[data-stations-map]'), { scrollWheelZoom: false }).setView([-15.8, -47.8], 9);
      addMapBase(stationMap, base, false);
      stationBounds = data.stations.map(s => [s.latitude, s.longitude]);
      if (root.querySelector('[data-stations-map]').offsetWidth) stationMap.fitBounds(stationBounds, { padding: [25, 25] });
      L.control.scale({ imperial: false }).addTo(stationMap);
      // Local vector map: station locations remain available without third-party tiles.
      for (const s of data.stations) {
        const marker = L.circleMarker([s.latitude, s.longitude], { color: '#344f40', fillColor: '#637c5c', fillOpacity: .65, weight: 1, radius: 6 }).addTo(stationMap).bindTooltip(`${s.id} · ${s.name}`, { permanent: true, direction: 'top' });
        marker.on('click', () => { select.value = s.id; update(); }); markers.push({ id: s.id, marker });
      }
      select.addEventListener('change', update); variable.addEventListener('change', update);
      root.querySelector('details').addEventListener('toggle', () => requestAnimationFrame(() => {
        if (root.querySelector('[data-stations-map]').offsetWidth) { stationMap.invalidateSize(); stationMap.fitBounds(stationBounds, { padding: [25, 25] }); }
      }));
      await update();
      ready = true;
      document.addEventListener('click', e => { if (e.target.closest('[data-report-tabs]')) setTimeout(() => {
        if (!root.offsetWidth) return;
        if (root.querySelector('[data-stations-map]').offsetWidth) stationMap.invalidateSize();
        root.querySelectorAll('[data-chart]').forEach(el => { if (el.offsetWidth) Plotly.Plots.resize(el); });
      }, 80); });
      window.addEventListener('hashchange', () => setTimeout(() => {
        if (!root.offsetWidth) return;
        if (root.querySelector('[data-stations-map]').offsetWidth) stationMap.invalidateSize();
        root.querySelectorAll('[data-chart]').forEach(el => { if (el.offsetWidth) Plotly.Plots.resize(el); });
      }, 80));
      let resizeTimer;
      window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(() => { if (root.offsetWidth) update(); }, 200); });
    } catch (error) {
      if (stationMap) { stationMap.remove(); stationMap = null; markers = []; }
      status.textContent = 'Não foi possível carregar a exploração INMET: ' + error.message;
      const retry = document.createElement('button'); retry.type = 'button'; retry.textContent = 'Tentar novamente'; retry.onclick = () => location.reload(); status.append(' ', retry);
    } finally { starting = false; }
  }
  document.addEventListener('toggle', event => {
    if (event.target.tagName !== 'DETAILS' || !event.target.contains(root) || !event.target.open) return;
    if (!ready) start();
    else requestAnimationFrame(() => {
      if (root.querySelector('[data-stations-map]').offsetWidth) stationMap.invalidateSize();
      root.querySelectorAll('[data-chart]').forEach(el => { if (el.offsetWidth) Plotly.Plots.resize(el); });
    });
  }, true);
  start();
})();
