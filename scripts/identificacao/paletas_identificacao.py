"""Paletas da identificação: dois QML da pesquisa e cores derivadas para o ZEE."""

from pathlib import Path
import xml.etree.ElementTree as ET


def qml_colors(path: Path) -> dict[int, str]:
    root = ET.parse(path).getroot()
    entries = root.findall(".//rasterrenderer/colorPalette/paletteEntry")
    colors = {int(entry.attrib["value"]): entry.attrib["color"].lower()
              for entry in entries}
    if not colors:
        raise ValueError(f"QML sem entradas de paleta: {path}")
    return colors


# Classes semelhantes seguem a família cromática do QML MapBiomas: verdes
# para vegetação, azuis para água, terras para campos e cinzas para urbano.
# Variações deixam as categorias distintas no mapa de cobertura do ZEE-DF.
ZEE_COLORS = {
    "Agricultura Intensiva": "#78b679",
    "Agricultura intensiva - Pivo-de-irrigação": "#a3cc8c",
    "Estradas Não-Pavimentadas": "#baa38d",
    "Estradas Pavimentadas": "#888888",
    "Ferrovia e Metrô": "#5f6662",
    "Formação Campestre": "#d0a55f",
    "Formação Florestal": "#4b6a40",
    "Formação Savânica": "#86a58f",
    "Hortifruticultura": "#a7d18b",
    "Lagoas de Estabilização": "#80b0b8",
    "Pecuária": "#915558",
    "Reflorestamento": "#d5d69e",
    "Represas, Lagos, Lagoas e Rios": "#acc6cb",
    "Uso Rural Diversificado": "#b6b787",
    "Área Degradada": "#c9ae94",
    "Área Urbana com Infraestrutura": "#b4b4b4",
    "Área Urbana sem Infraestrutura": "#e2e2e2",
    "Área Verde Intra Urbana": "#658966",
    "Área em Processo de Parcelamento Urbano": "#d3c8bc",
    "Áreas úmidas: Parque Cerrado (ou Murundum), Palmeirais e Veredas": "#496a6e",
}

# A ausência de Cerrado nativo é uma categoria separada dos três níveis de risco.
RISK_COLORS = {
    2: ("Ausência de Cerrado nativo", "#b2b5a8"),
    3: ("Risco médio", "#d0a55f"),
    4: ("Risco alto", "#b47e4f"),
    5: ("Risco muito alto", "#8d554e"),
}
