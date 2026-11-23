"""Entrada atual do diagnóstico integrado do Sistema Fitópolis.

Usa a base de 46.876 fragmentos (id_frag), a malha de 30 m e os rasters
vigentes. Preserva os resultados hidrológicos; não executa modelos.

Execute pelo ambiente isolado do QGIS:
    ./scripts/fitopolis_ambiente.ps1 scripts/01_Diagnostico_RISCOS.py

As implementações anteriores permanecem no histórico Git.
"""
from gerar_diagnostico_fitopolis import main

if __name__ == '__main__':
    main()