"""Prepara apenas faixas cartográficas de Perimeter, PARA e FRAC.

Partição ótima em quatro intervalos contíguos, minimizando a soma dos desvios
quadráticos ponderados por Area. Usa todos os fragmentos, sem amostragem.
Não calcula métricas científicas nem grava nas fontes.
"""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

FIELDS = ('Perimeter', 'PARA', 'FRAC')


def weighted_breaks(values, weights, classes=4):
    values, weights = np.asarray(values, dtype=float), np.asarray(weights, dtype=float)
    if (values.ndim != 1 or values.shape != weights.shape or len(values) == 0 or
            not np.all(np.isfinite(values)) or not np.all(np.isfinite(weights)) or
            np.any(weights <= 0) or classes < 1):
        raise ValueError('Valores finitos e pesos positivos são necessários')
    unique, inverse = np.unique(values, return_inverse=True)
    classes = min(classes, len(unique))
    if classes == 1:
        return []
    grouped = np.bincount(inverse, weights=weights)
    # A normalização afim preserva a partição ótima e reduz cancelamento.
    x = (unique-unique[0])/(unique[-1]-unique[0])
    w = np.r_[0, np.cumsum(grouped)]
    s = np.r_[0, np.cumsum(grouped*x)]
    q = np.r_[0, np.cumsum(grouped*x*x)]
    n = len(unique)
    previous = np.full(n+1, np.inf)
    previous[0] = 0
    back = np.zeros((classes+1, n+1), dtype=int)
    for k in range(1, classes+1):
        current = np.full(n+1, np.inf)
        for end in range(k, n+1):
            starts = np.arange(k-1, end)
            variance = np.maximum(0, q[end]-q[starts] - (s[end]-s[starts])**2/(w[end]-w[starts]))
            costs = previous[starts]+variance
            best = int(np.argmin(costs))
            current[end] = costs[best]
            back[k, end] = starts[best]
        previous = current
    limits, end = [], n
    for k in range(classes, 1, -1):
        end = back[k, end]
        limits.append(float(unique[end-1]))
    return sorted(limits)


def prepare(repo):
    folder = repo/'dados-mapas/identificacao/metricas'
    manifest = json.loads((folder/'manifesto.json').read_text(encoding='utf-8'))
    datasets, sources = [], []
    for scenario in manifest['cenarios']:
        info = scenario['fragmentos']
        payload = (folder/info['arquivo']).read_bytes()
        assert sha256(payload).hexdigest() == info['sha256']
        rows = list(csv.DictReader(payload.decode('utf-8-sig').splitlines()))
        assert [int(r['IdTemp']) for r in rows] == list(range(1, manifest['fragmentos']+1))
        datasets.append(np.array([[float(row[f]) for f in ('Area', *FIELDS)] for row in rows]))
        sources.append({'arquivo': info['arquivo'], 'sha256': info['sha256']})
    assert np.array_equal(*datasets), 'As faixas comuns exigem os mesmos valores nos cenários'
    data = datasets[0]
    weights = data[:, 0]
    result = {'schema': 1, 'metodo': 'Partição ótima de variância intra-classe ponderada pela área',
        'peso': 'Area em m² de todos os fragmentos; valores iguais nunca são separados.',
        'classes': 4, 'fragmentos': len(data), 'fontes': sources, 'indicadores': {}}
    for index, field in enumerate(FIELDS, 1):
        values = data[:, index]
        edges = weighted_breaks(values, weights)
        labels = np.searchsorted(edges, values, side='left')
        count = np.bincount(labels, minlength=4)
        area = np.bincount(labels, weights=weights, minlength=4)
        assert np.all(count > 0) and len(edges) == 3
        result['indicadores'][field] = {'limites_superiores': edges,
            'minimo': float(values.min()), 'maximo': float(values.max()),
            'fragmentos_por_classe': count.tolist(), 'area_ha_por_classe': (area/10000).tolist(),
            'area_percentual_por_classe': (100*area/weights.sum()).tolist()}
    result['revisao'] = sha256(json.dumps(result, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    output = args.repo/'dados-mapas/identificacao/metricas-mapa/faixas.json'
    result = prepare(args.repo)
    if args.check:
        assert json.loads(output.read_text(encoding='utf-8')) == result
        print('OK: faixas reproduzidas, cobertura de todos os valores e fontes originais conferidas.')
    else:
        with output.open('x', encoding='utf-8') as handle:
            handle.write(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps(result['indicadores'], ensure_ascii=False))
