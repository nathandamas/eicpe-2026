# -*- coding: utf-8 -*-
"""Baixa os poligonos de Favelas e Comunidades Urbanas (IBGE, Censo 2022).

O arquivo nao e redistribuido neste repositorio: e dado do IBGE, de acesso
aberto, e baixa-lo garante que a versao usada seja a vigente na fonte oficial.
"""
import urllib.request
from pathlib import Path

URL = ("https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
       "Favelas_e_comunidades_urbanas_Resultados_do_universo/"
       "arquivos_vetoriais/poligonos_FCUs_shp.zip")
DEST = Path(__file__).resolve().parent.parent / "data" / "poligonos_FCUs_shp.zip"

if DEST.exists() and DEST.stat().st_size > 10_000:
    print("ja existe: %s (%.1f MB)" % (DEST.name, DEST.stat().st_size / 1e6))
else:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "eicpe2026/1.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(DEST, "wb") as f:
        f.write(r.read())
    print("gravado: %s (%.1f MB)" % (DEST.name, DEST.stat().st_size / 1e6))
