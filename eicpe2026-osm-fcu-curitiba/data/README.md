# Dados

## `eicpe_cells_curitiba.parquet`

As **502 celulas** de 1 km x 1 km da Grade Estatistica do IBGE que recobrem o
municipio de Curitiba (PR). EPSG:31982 (SIRGAS 2000 / UTM 22S).

| coluna | conteudo | unidade |
|---|---|---|
| `id` | identificador da celula | — |
| `osm_area` | area total de edificacoes do OSM na celula, em 2026-02-01 | m2 |
| `ref_area` | area total de edificacoes na referencia Google-Microsoft (VIDA) | m2 |
| `geometry` | poligono da celula | — |

**Proveniencia.** `osm_area` vem da serie mensal de area edificada do OSM obtida
pela API ohsome (filtro `building=* and building!=no and (geometry:polygon or
geometry:other)`), tomada no ultimo instante da serie, 1 de fevereiro de 2026.
`ref_area` vem da camada combinada Google-Microsoft Open Buildings distribuida
pela VIDA, em versao anterior a incorporacao da camada do OSM — essa escolha
evita que a referencia incorpore o proprio sinal avaliado.

**O que NAO e redistribuido:** os poligonos brutos de edificacao, nem do OSM nem
da referencia. Apenas o agregado por celula das duas areas, que e o insumo
efetivamente usado. Uma das 502 celulas nao tem area de referencia e e excluida
da analise pelo proprio script.

## `poligonos_FCUs_shp.zip`

Nao esta no repositorio. Rode `python scripts/00_baixar_fcu.py` para obte-lo do
servidor do IBGE.

## Licencas

| fonte | licenca |
|---|---|
| OpenStreetMap | ODbL 1.0 — (c) colaboradores do OpenStreetMap |
| Google Open Buildings | CC BY 4.0 |
| Microsoft GlobalMLBuildingFootprints | ODbL |
| IBGE (grade estatistica, FCU) | termos de dados abertos do IBGE, com atribuicao |
