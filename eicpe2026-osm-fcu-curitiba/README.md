# Completude do OpenStreetMap e Favelas e Comunidades Urbanas em Curitiba

Material suplementar do resumo expandido **"Quem fica fora do mapa? Completude
de edificacoes no OpenStreetMap e Favelas e Comunidades Urbanas em Curitiba
(PR)"**, submetido ao II Encontro Internacional de Cartografia e Pensamento
Espacial (II EICPE), USP, 2026.

## A pergunta

A completude por area das edificacoes do OpenStreetMap difere entre celulas de
1 km2 com e sem Favelas e Comunidades Urbanas (FCU, IBGE 2022) em Curitiba?

## Como reproduzir

```bash
pip install -r requirements.txt
python scripts/00_baixar_fcu.py
python scripts/01_analise.py \
    --cells data/eicpe_cells_curitiba.parquet \
    --fcu   data/poligonos_FCUs_shp.zip \
    --out   outputs \
    --id-col id --osm-col osm_area --ref-col ref_area
```

As saidas ja calculadas estao em `outputs/`, para conferencia sem reexecutar.

## O que o script faz

1. Reprojeta tudo para EPSG:31982 e calcula `C = osm_area / ref_area` por celula.
   Celulas sem area de referencia sao excluidas; valores de `C > 1` sao mantidos
   nos testes e limitados a 1 apenas no mapa.
2. Corrige e dissolve os poligonos de FCU e os intersecta com as celulas,
   obtendo `fcu_share` = area de FCU na celula / area da celula.
3. Compara os grupos com e sem FCU em tres criterios de presenca (`f > 0`,
   `f >= 5%`, `f >= 10%`), por Mann-Whitney bilateral, com correlacao bisserial
   de postos como tamanho de efeito. `r > 0` indica completude MAIOR nas
   celulas com FCU.
4. Calcula a completude agregada por grupo e o Spearman entre `fcu_share` e `C`.
5. Opcionalmente, o I de Moran global de `C` (requer `esda` e `libpysal`).

## Resultado

Nao ha diferenca relevante entre os grupos. Nas 501 celulas analisadas, 181
interceptam ao menos um poligono de FCU; a mediana de `C` e 0,04 nas celulas com
FCU e 0,07 nas celulas sem, com `r = -0,03` (p = 0,622). O sinal nao se mantem
entre os criterios (`r = +0,05` com `f >= 10%`). Numeros completos em
`outputs/resultados.json`.

## Estrutura

```
data/      insumo por celula (ver data/README.md) e, apos o download, as FCU
scripts/   00_baixar_fcu.py, 01_analise.py
outputs/   resultados.json, resumo_resultados.txt, cells_fcu_completeness.csv,
           fig1_mapa.png, fig2_boxplot.png
```

## Licenca

Codigo sob licenca MIT (ver `LICENSE`). Os dados seguem as licencas das fontes
originais, listadas em `data/README.md`.
