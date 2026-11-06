"""Gera figura e nota de leitura a partir da exploração, sem ler/alterar fontes."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('resultados', type=Path)
    out = p.parse_args().resultados
    report = json.loads((out/'resultados.json').read_text(encoding='utf-8'))
    samples = np.load(out/'amostras.npz')
    labels = {'campestre': 'Campestre', 'savanica': 'Savânica', 'florestal': 'Florestal'}
    colors = {'campestre': '#b87c13', 'savanica': '#498050', 'florestal': '#285572'}
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 2, figsize=(13, 11))
    fig.subplots_adjust(top=.86, bottom=.20, hspace=.40, wspace=.22)
    fig.suptitle('NDVI nas áreas de concordância entre MapBiomas e ZEE',
                 x=.08, y=.97, ha='left', fontsize=18, fontweight='bold')
    fig.text(.08, .925, 'PlanetScope · janeiro e julho de 2026 · referências locais · análise exploratória',
             fontsize=11, color='#444444')
    bins = np.linspace(-1, 1, 81)
    titles = {'seca': 'Seca · 30 de julho', 'chuva': 'Chuva · 17 de janeiro',
              'media_sazonal': 'Média das duas datas · não é média anual'}
    for ax, var in zip(axes.flat, titles):
        for key, label in labels.items():
            values = samples[key+'__'+var]
            ax.hist(values, bins=bins, density=True, histtype='step', linewidth=1.8,
                    color=colors[key], label=label)
        ax.set_title(titles[var], loc='left', fontsize=12, fontweight='bold')
        ax.set_xlim(-1, 1)
        ax.set_xlabel('NDVI')
        ax.set_ylabel('Densidade da distribuição')
        ax.grid(axis='y', color='#dddddd', alpha=.7)
    ax = axes[1, 1]
    rng = np.random.default_rng(20261106)
    for key, label in labels.items():
        dry, wet = samples[key+'__seca'], samples[key+'__chuva']
        ix = rng.choice(len(dry), min(3000, len(dry)), replace=False)
        ax.scatter(dry[ix], wet[ix], s=4, color=colors[key], alpha=.22, rasterized=True)
    ax.plot([-1, 1], [-1, 1], color='#888888', linewidth=.8, linestyle='--')
    ax.set(xlim=(-1, 1), ylim=(-1, 1), xlabel='NDVI da seca', ylabel='NDVI da chuva')
    ax.set_title('As duas datas preservadas separadamente', loc='left', fontsize=12, fontweight='bold')
    handles = [plt.Line2D([0], [0], color=colors[k], linewidth=2,
               label=f"{v} (n={len(samples[k+'__seca']):,})".replace(',', '.')) for k, v in labels.items()]
    fig.legend(handles=handles, loc='upper left', bbox_to_anchor=(.07, .915), ncol=3, frameon=False)
    spacing = report['amostragem']['espacamento_m']
    fig.text(.08, .045, f'Amostra sistemática com espaçamento de {spacing} m, selecionando pixels originais de 3 m.\n'
             'Mesmos pontos válidos nas duas datas. Sem máscara UDM2 e sem validação independente.\n'
             'Curvas sobrepostas indicam confusão possível; não representam acurácia de classificação.',
             fontsize=9, color='#555555', va='bottom')
    fig.savefig(out/'comparacao_ndvi.png', dpi=180, facecolor='white')
    plt.close(fig)

    def fmt(x):
        return f'{x:.3f}'.replace('.', ',')
    lines = [
        '# Exploração inicial da identificação da vegetação', '',
        'Esta análise compara o NDVI de janeiro e julho de 2026 em áreas onde as cópias locais '
        'do MapBiomas e do ZEE concordam nas formações campestre, savânica e florestal. '
        'Não estabelece cortes finais e não aplica critérios de inclusão na rede de infraestrutura verde.', '',
        '## Resultados descritivos', '',
        '| Formação | Pares válidos | Média seca | Média chuva | Média das datas | DP da média das datas |',
        '| --- | ---: | ---: | ---: | ---: | ---: |',
    ]
    for key, label in labels.items():
        group = report['grupos'][key]
        s = group['estatisticas_pareadas']
        count = f"{group['n_pares_validos']:,}".replace(',', '.')
        lines.append(f"| {label} | {count} | {fmt(s['seca']['media'])} | "
                     f"{fmt(s['chuva']['media'])} | {fmt(s['media_sazonal']['media'])} | "
                     f"{fmt(s['media_sazonal']['desvio_padrao_populacional'])} |")
    lines += ['', 'Médias e desvios descrevem as amostras de referência. Não são limites de classificação. '
              'Os grupos têm tamanhos distintos, e os pontos não representam observações independentes.', '',
              '## Como a análise foi feita', '',
              '1. Conferência de projeção, resolução, bandas e alinhamento das duas imagens.',
              '2. Seleção sistemática dos centros de pixels originais, com espaçamento de '
              f'{spacing} m. Isso reduz a leitura para exploração; não muda a resolução das imagens de origem.',
              '3. Cálculo de NDVI a partir das bandas Red e NIR originais, desativando o uso automático '
              'de pirâmides de visualização. Pontos verificados diretamente nas fontes.',
              '4. Consulta das classes do MapBiomas por vizinho mais próximo e das classes do ZEE '
              'nos mesmos centros. A concordância é feita nos pontos amostrais, sem gerar '
              'uma nova interseção vetorial integral.',
              '5. Comparação pareada: apenas pontos válidos nas duas datas para cada grupo.',
              '6. Resumos, distribuições e sobreposições descritivas. Pastagem e ausência de '
              'remanescentes são mantidas como grupos de comparação, sem excluir dados.', '',
              '## Limitações', '']
    lines += ['- '+x+'.' for x in report['limitacoes']]
    lines += ['', 'As fontes desta primeira exploração são cópias locais. Nenhum novo download do '
              'SISDIA ou do MapBiomas foi realizado. O ano está identificado no nome do arquivo '
              'local do MapBiomas, mas sua coleção não é comprovada pelos metadados do raster.', '',
              '## Apresentação futura no site', '',
              'Destino definido pela autora: Identificação → Uso do solo. Seguir a organização '
              'de Riscos socioambientais: introdução, tabela geral antes dos quadros, produção '
              'do indicador, procedimento completo em expansor fechado por padrão e mapas '
              'carregados sob demanda. Distinguir produção da cobertura vegetal da aplicação '
              'posterior ao diagnóstico e à rede de infraestrutura verde. O site não foi alterado.', '',
              '## Arquivos', '',
              '- `resultados.json`: método, limitações, resumos, cruzamentos e SHA-256 das fontes.',
              '- `estatisticas.csv`: valores descritivos de todos os grupos.',
              '- `amostras.npz`: valores pareados por grupo e variável.',
              '- `comparacao_ndvi.png`: distribuições e relação entre as duas datas.', '',
              'Para reproduzir, executar `analisar_vegetacao.py --base PASTA_DADOS --out PASTA_SAIDA` '
              'com Python/GDAL do QGIS, depois `apresentar_resultados.py PASTA_SAIDA` com '
              'Python, NumPy e Matplotlib. Os scripts ficam na pasta imediatamente acima dos resultados.', '']
    (out/'LEITURA.md').write_text('\n'.join(lines), encoding='utf-8')
    print(out/'comparacao_ndvi.png')


if __name__ == '__main__':
    main()
