#!/usr/bin/env python
"""
Completude por area das edificacoes do OpenStreetMap x Favelas e Comunidades
Urbanas (FCU, IBGE, Censo 2022), na grade estatistica de 1 km do IBGE.

Material suplementar do resumo expandido submetido ao II Encontro Internacional
de Cartografia e Pensamento Espacial (II EICPE), USP, 2026.

A medida e uma so: a razao de areas construidas
    C = area edificada no OSM / area edificada na referencia
por celula de 1 km2. O script nao calcula nem exporta nenhuma outra medida de
completude.

Uso:
    python scripts/01_analise.py \
        --cells data/eicpe_cells_curitiba.parquet \
        --fcu   data/poligonos_FCUs_shp.zip \
        --out   outputs \
        --id-col id --osm-col osm_area --ref-col ref_area

Entradas
  --cells : GeoParquet com uma linha por celula da grade (poligono).
  --fcu   : poligonos de FCU do IBGE (o .zip e lido direto).
Saidas (em --out)
  cells_fcu_completeness.csv, resultados.json, resumo_resultados.txt,
  fig1_mapa.png, fig2_boxplot.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

CRS_ANALYSIS = "EPSG:31982"  # SIRGAS 2000 / UTM 22S
THRESHOLDS = (0.0, 0.05, 0.10)  # FCU share of cell area (0.0 means "any overlap")


def read_any(path: str) -> gpd.GeoDataFrame:
    p = Path(path)
    if p.suffix.lower() == ".parquet":
        return gpd.read_parquet(p)
    if p.suffix.lower() == ".zip":
        return gpd.read_file(f"zip://{p.resolve()}")
    return gpd.read_file(p)


def fcu_share_per_cell(cells: gpd.GeoDataFrame, fcu: gpd.GeoDataFrame, id_col: str) -> pd.DataFrame:
    """Area of FCU polygons inside each cell and its share of the cell area."""
    fcu = fcu[["geometry"]].copy()
    fcu["geometry"] = fcu.geometry.make_valid()
    # dissolve so overlapping FCU polygons are not double counted
    fcu_union = gpd.GeoDataFrame(geometry=[fcu.union_all()], crs=fcu.crs)
    inter = gpd.overlay(cells[[id_col, "geometry"]], fcu_union, how="intersection", keep_geom_type=True)
    inter["fcu_area_m2"] = inter.geometry.area
    out = inter.groupby(id_col, as_index=False)["fcu_area_m2"].sum()
    res = cells[[id_col]].assign(cell_area_m2=cells.geometry.area).merge(out, on=id_col, how="left")
    res["fcu_area_m2"] = res["fcu_area_m2"].fillna(0.0)
    res["fcu_share"] = res["fcu_area_m2"] / res["cell_area_m2"]
    return res


def rank_biserial(x1: np.ndarray, x0: np.ndarray) -> tuple[float, float, float]:
    """Mann-Whitney U (two-sided) and rank-biserial r (positive => group 1 higher)."""
    u1, p = stats.mannwhitneyu(x1, x0, alternative="two-sided")
    r = 2.0 * u1 / (len(x1) * len(x0)) - 1.0
    return float(u1), float(p), float(r)


def describe(x: pd.Series) -> dict:
    return {
        "n": int(x.size),
        "mediana": float(np.median(x)),
        "q1": float(np.quantile(x, 0.25)),
        "q3": float(np.quantile(x, 0.75)),
        "media": float(np.mean(x)),
    }


def pooled(df: pd.DataFrame) -> float:
    """Aggregate completeness: sum(OSM area) / sum(reference area)."""
    if "osm_area" not in df or "ref_area" not in df:
        return float("nan")
    return float(df["osm_area"].sum() / df["ref_area"].sum())


def add_scalebar(ax, length_m: float = 5000):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    xs = x0 + 0.06 * (x1 - x0)
    ys = y0 + 0.05 * (y1 - y0)
    ax.plot([xs, xs + length_m], [ys, ys], color="black", lw=3)
    ax.text(xs + length_m / 2, ys + 0.015 * (y1 - y0), f"{length_m/1000:.0f} km", ha="center", fontsize=8)
    ax.annotate("N", xy=(0.93, 0.93), xytext=(0.93, 0.83), xycoords="axes fraction",
                ha="center", fontsize=10, fontweight="bold",
                arrowprops=dict(arrowstyle="-|>", color="black"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cells", required=True)
    ap.add_argument("--fcu", required=True)
    ap.add_argument("--out", default="outputs/eicpe")
    ap.add_argument("--id-col", default="id")
    ap.add_argument("--osm-col", default="osm_area", help="current OSM building area per cell")
    ap.add_argument("--ref-col", default="ref_area", help="reference (Google-Microsoft) building area per cell")
    ap.add_argument("--completeness-col", default=None, help="usar uma coluna de completude por area ja calculada")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log: list[str] = []

    cells = read_any(args.cells).to_crs(CRS_ANALYSIS)
    if cells[args.id_col].duplicated().any():
        raise ValueError(f"Duplicated ids in {args.id_col}")
    log.append(f"Celulas lidas: {len(cells)}")

    # ---------------- completeness (area ratio only) ----------------
    if args.completeness_col:
        cells["C"] = cells[args.completeness_col].astype(float)
        if args.ref_col in cells:
            cells["ref_area"] = cells[args.ref_col].astype(float)
        if args.osm_col in cells:
            cells["osm_area"] = cells[args.osm_col].astype(float)
    else:
        cells["osm_area"] = cells[args.osm_col].astype(float)
        cells["ref_area"] = cells[args.ref_col].astype(float)
        cells["C"] = np.where(cells["ref_area"] > 0, cells["osm_area"] / cells["ref_area"], np.nan)

    # ---------------- FCU overlay ----------------
    fcu = read_any(args.fcu).to_crs(CRS_ANALYSIS)
    fcu = fcu[fcu.intersects(cells.union_all())]
    log.append(f"Poligonos FCU que intersectam a area de estudo: {len(fcu)}")
    name_cols = [c for c in fcu.columns if "nm" in c.lower() or "nome" in c.lower()]
    if name_cols:
        log.append(f"Colunas de nome no arquivo FCU: {name_cols}")
    share = fcu_share_per_cell(cells, fcu, args.id_col)
    cells = cells.merge(share, on=args.id_col, how="left")

    valid = cells[np.isfinite(cells["C"])].copy()
    med_c = float(valid["C"].median())
    if not 0.001 <= med_c <= 5:
        print(f"ATENCAO: mediana de C = {med_c:.4g}. Confira se OSM e referencia estao na mesma unidade "
              f"(m2) - ex.: OBS_AREA_SCALE do pipeline.")
    n_excl = len(cells) - len(valid)
    log.append(f"Celulas sem referencia (ref_area<=0 ou nula), excluidas: {n_excl}")
    log.append(f"Celulas analisadas: {len(valid)}")
    log.append(f"Celulas com C>1 (OSM excede a referencia), mantidas: {int((valid['C'] > 1).sum())}")
    log.append(f"Celulas com alguma FCU: {int((valid['fcu_share'] > 0).sum())}")

    res: dict = {"n_celulas_total": len(cells), "n_sem_referencia": n_excl, "n_analisadas": len(valid),
                 "n_C_maior_1": int((valid["C"] > 1).sum()),
                 "n_fcu_poligonos_area": int(len(fcu)),
                 "area_fcu_total_km2": float(valid["fcu_area_m2"].sum() / 1e6),
                 "completude_agregada_total": pooled(valid),
                 "comparacoes": []}

    for t in THRESHOLDS:
        g1 = valid[valid["fcu_share"] > 0] if t == 0 else valid[valid["fcu_share"] >= t]
        g0 = valid[valid["fcu_share"] == 0]
        if len(g1) < 5 or len(g0) < 5:
            log.append(f"[limiar {t:.0%}] grupos pequenos demais (n1={len(g1)}, n0={len(g0)}); pulado")
            continue
        u, p, r = rank_biserial(g1["C"].to_numpy(), g0["C"].to_numpy())
        comp = {"limiar_fcu_share": t, "com_fcu": describe(g1["C"]), "sem_fcu": describe(g0["C"]),
                "agregada_com_fcu": pooled(g1), "agregada_sem_fcu": pooled(g0),
                "mann_whitney_U": u, "p_valor": p, "rank_biserial_r": r}
        res["comparacoes"].append(comp)
        log.append(
            f"[limiar {'>0' if t == 0 else f'>={t:.0%}'}] com FCU n={len(g1)} mediana C={comp['com_fcu']['mediana']:.3f} "
            f"(IQR {comp['com_fcu']['q1']:.3f}-{comp['com_fcu']['q3']:.3f}); sem FCU n={len(g0)} mediana C="
            f"{comp['sem_fcu']['mediana']:.3f} (IQR {comp['sem_fcu']['q1']:.3f}-{comp['sem_fcu']['q3']:.3f}); "
            f"agregada {comp['agregada_com_fcu']:.3f} vs {comp['agregada_sem_fcu']:.3f}; "
            f"U={u:.0f}, p={p:.4g}, r_rb={r:+.3f}"
        )

    rho, prho = stats.spearmanr(valid["fcu_share"], valid["C"])
    res["spearman_todas"] = {"rho": float(rho), "p": float(prho), "n": len(valid)}
    log.append(f"Spearman (fcu_share x C, todas as celulas): rho={rho:+.3f}, p={prho:.4g}, n={len(valid)}")
    sub = valid[valid["fcu_share"] > 0]
    if len(sub) >= 10:
        rho2, p2 = stats.spearmanr(sub["fcu_share"], sub["C"])
        res["spearman_so_fcu"] = {"rho": float(rho2), "p": float(p2), "n": len(sub)}
        log.append(f"Spearman (so celulas com FCU): rho={rho2:+.3f}, p={p2:.4g}, n={len(sub)}")

    # optional: global Moran's I of C (spatial dependence caveat)
    try:
        from esda.moran import Moran
        from libpysal.weights import Queen

        w = Queen.from_dataframe(valid, use_index=False)
        w.transform = "r"
        mi = Moran(valid["C"].to_numpy(), w, permutations=999)
        res["moran_C"] = {"I": float(mi.I), "p_sim": float(mi.p_sim)}
        log.append(f"Moran's I global de C (Queen): I={mi.I:.3f}, p_sim={mi.p_sim:.3f}")
    except Exception as e:  # esda/libpysal not installed or failure
        log.append(f"Moran's I nao calculado ({type(e).__name__}); instale esda+libpysal se quiser.")

    # ---------------- outputs ----------------
    cols = [args.id_col, "C", "fcu_area_m2", "fcu_share", "cell_area_m2"] + \
        [c for c in ("osm_area", "ref_area") if c in cells]
    cells[cols].to_csv(out / "cells_fcu_completeness.csv", index=False)
    (out / "resultados.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "resumo_resultados.txt").write_text("\n".join(log), encoding="utf-8")

    # Figure 1: completeness map with FCU outlines
    fig, ax = plt.subplots(figsize=(6.3, 7.0))
    cmap = plt.get_cmap("YlGnBu")
    plot_c = cells.assign(C_plot=cells["C"].clip(upper=1.0))
    plot_c[~np.isfinite(plot_c["C"])].plot(ax=ax, color="#d9d9d9", edgecolor="white", lw=0.2)
    plot_c[np.isfinite(plot_c["C"])].plot(ax=ax, column="C_plot", cmap=cmap, vmin=0, vmax=1,
                                          edgecolor="white", lw=0.2, legend=True,
                                          legend_kwds={"label": "Completude por área (C, limitada a 1)",
                                                       "shrink": 0.6})
    if len(fcu):
        fcu.boundary.plot(ax=ax, color="#d7301f", lw=0.6)
    ax.set_axis_off()
    add_scalebar(ax)
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    ax.legend(handles=[Line2D([0], [0], color="#d7301f", lw=1, label="Favelas e Comunidades Urbanas (IBGE, 2022)"),
                       Patch(color="#d9d9d9", label="Sem referência")],
              loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=2, fontsize=7, frameon=False)
    fig.tight_layout()
    fig.savefig(out / "fig1_mapa.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    # Figure 2: boxplot by group (any overlap)
    g1 = valid[valid["fcu_share"] > 0]["C"].clip(upper=1.0)
    g0 = valid[valid["fcu_share"] == 0]["C"].clip(upper=1.0)
    fig, ax = plt.subplots(figsize=(5.0, 4.0))
    ax.boxplot([g0, g1], tick_labels=[f"Sem FCU (n={len(g0)})", f"Com FCU (n={len(g1)})"],
               widths=0.5, showfliers=False)
    rng = np.random.default_rng(42)
    for i, g in enumerate([g0, g1], start=1):
        ax.scatter(rng.normal(i, 0.06, len(g)), g, s=6, alpha=0.4, color="#2b8cbe")
    ax.set_ylabel("Completude por área (C, limitada a 1)")
    ax.set_ylim(-0.02, 1.02)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "fig2_boxplot.png", dpi=300)
    plt.close(fig)

    print("\n".join(log))
    print(f"\nArquivos salvos em: {out.resolve()}")


if __name__ == "__main__":
    main()
