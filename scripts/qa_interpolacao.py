"""Cross-validation da interpolação por buffer.

Mede o erro da interpolação simulando "ausência" de cobertura em setores que de fato
têm dado bom: retira do conjunto `ok`, pede ao `interpolate_by_buffer` pra estimar o
valor, e compara o estimado vs. o medido original.

Uso:
  python scripts/qa_interpolacao.py
  python scripts/qa_interpolacao.py --fracao 0.1 --seed 42 --buffer 3500

Reporta (em °C, salvo onde dito):
  - MAE (erro absoluto médio)
  - bias (média do erro assinado; positivo = interpolador superestima)
  - p50/p90 do erro absoluto
  - R² (coeficiente de determinação)
  - breakdown urbano/rural quando a camada tem SITUACAO
  - escreve data/out/qa_interpolacao.json
"""
import argparse
import json
import os
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import analyze  # noqa: E402
from analyze import (find, interpolate_by_buffer, interpolate_consciente_sit,  # noqa: E402
                     load_units, read_raster, zonal)
import config as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--unidades", default="data/setores_rb.gpkg")
    ap.add_argument("--min-cobertura", type=float, default=0.5)
    ap.add_argument("--fracao", type=float, default=0.1,
                    help="fração dos setores com dado bom usada como test set")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--buffer", type=float, default=3500,
                    help="buffer da interpolação (m) — bate com default do analyze")
    ap.add_argument("--min-pixels", type=int, default=50)
    ap.add_argument("--consciente", action="store_true",
                    help="usa interpolate_consciente_sit (restringe pixels do buffer "
                         "à mesma SITUACAO do setor-alvo)")
    ap.add_argument("--saida", default="data/out/qa_interpolacao.json")
    args = ap.parse_args()

    lst_tif = find("lst_*.tif")
    ndvi_now_tif = find(f"ndvi_{C.YEAR_NOW}.tif")
    ndvi_base_tif = find(f"ndvi_{C.YEAR_BASE}.tif")
    loss_tif = find("perda_*.tif")

    with rasterio.open(loss_tif) as src:
        crs = src.crs
    _, _, px_area = read_raster(loss_tif)
    _, _, lst_px = read_raster(lst_tif)

    gdf = load_units(args.unidades, None, crs)
    print(f"{len(gdf)} unidades carregadas (CRS {crs})")

    # zonal LST pra identificar setores "bons"
    z = zonal(gdf, lst_tif, ["mean", "percentile_90", "count"], "lst_")
    gdf = gpd.GeoDataFrame(pd.concat([gdf, z], axis=1), geometry="geometry", crs=crs)
    # as outras bandas precisam estar presentes pra interpolate_by_buffer rodar
    gdf = gpd.GeoDataFrame(pd.concat([
        gdf,
        zonal(gdf, ndvi_now_tif, ["mean"], "ndvi_atual_"),
        zonal(gdf, ndvi_base_tif, ["mean"], "ndvi_base_"),
        zonal(gdf, loss_tif, ["sum", "count"], "perda_"),
    ], axis=1), geometry="geometry", crs=crs)
    gdf["cobertura_calor"] = (gdf["lst_count"] * lst_px / gdf.geometry.area).clip(0, 1)
    gdf["ndvi_delta"] = gdf["ndvi_atual_mean"] - gdf["ndvi_base_mean"]
    gdf["perda_pct"] = 100 * gdf["perda_sum"] / gdf["perda_count"]

    bom = gdf[(gdf["cobertura_calor"] >= args.min_cobertura)
              & gdf["lst_mean"].notna()].copy()
    print(f"{len(bom)}/{len(gdf)} setores com cobertura >= {args.min_cobertura}")

    # Sorteio dos setores de teste
    rng = np.random.default_rng(args.seed)
    n_test = int(round(len(bom) * args.fracao))
    test_pos = rng.choice(bom.index.values, size=n_test, replace=False)
    print(f"test set: {n_test} setores (fração {args.fracao}, seed {args.seed})")

    # Captura truth ANTES da interpolação sobrescrever lst_mean
    truth = gdf.loc[test_pos, "lst_mean"].to_numpy()

    # Simular ausência: marca test set como ok=False, todo o resto como ok=True
    ok = np.ones(len(gdf), dtype=bool)
    ok[test_pos] = False
    # Também marca como False os setores que já não tinham cobertura boa (fidelidade
    # ao cenário real de produção; o interpolador vê o mesmo universo que vê de verdade)
    cob_boa = gdf["cobertura_calor"].to_numpy() >= args.min_cobertura
    ok = ok & cob_boa

    rasters = {"lst": lst_tif, "ndvi_now": ndvi_now_tif,
               "ndvi_base": ndvi_base_tif, "loss": loss_tif}
    if args.consciente:
        interp = interpolate_consciente_sit(gdf, ok, rasters,
                                            buffer_m=args.buffer,
                                            min_cobertura=args.min_cobertura,
                                            lst_px=lst_px, px_area=px_area,
                                            min_pixels=args.min_pixels)
    else:
        interp = interpolate_by_buffer(gdf, ok, rasters,
                                       buffer_m=args.buffer,
                                       min_cobertura=args.min_cobertura,
                                       lst_px=lst_px, px_area=px_area,
                                       min_pixels=args.min_pixels)

    pred = interp.loc[test_pos, "lst_mean"].to_numpy()
    interpolado = interp.loc[test_pos, "interpolado"].to_numpy()

    # Só compara onde o interpolador efetivamente aceitou
    mask = interpolado & ~np.isnan(pred) & ~np.isnan(truth)
    n_eff = int(mask.sum())
    n_recusados = n_test - n_eff
    err = pred[mask] - truth[mask]
    abserr = np.abs(err)

    def _r2(y_true, y_pred):
        ss_res = float(((y_pred - y_true) ** 2).sum())
        y_mean = float(y_true.mean())
        ss_tot = float(((y_true - y_mean) ** 2).sum())
        return 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    report = {
        "params": {
            "fracao": args.fracao, "seed": args.seed,
            "buffer_m": args.buffer, "min_cobertura": args.min_cobertura,
            "min_pixels": args.min_pixels,
            "modo": "consciente" if args.consciente else "ingenua",
        },
        "n_total": int(len(gdf)),
        "n_bons": int(len(bom)),
        "n_test": int(n_test),
        "n_aceitos_pelo_interp": n_eff,
        "n_recusados_pelo_interp": int(n_recusados),
        "mae_C": round(float(abserr.mean()), 3),
        "bias_C": round(float(err.mean()), 3),
        "abserr_p50_C": round(float(np.percentile(abserr, 50)), 3),
        "abserr_p90_C": round(float(np.percentile(abserr, 90)), 3),
        "abserr_max_C": round(float(abserr.max()), 3),
        "r2": round(_r2(truth[mask], pred[mask]), 3),
        "truth_media_C": round(float(truth[mask].mean()), 2),
        "pred_media_C": round(float(pred[mask].mean()), 2),
    }

    # Breakdown por SITUACAO se a camada tiver (string IBGE: 1 urbano, 4+ rural)
    if "SITUACAO" in gdf.columns:
        sit = gdf.loc[test_pos, "SITUACAO"].astype(str).to_numpy()[mask]
        por_sit = {}
        for s in np.unique(sit):
            m = sit == s
            por_sit[str(s)] = {
                "n": int(m.sum()),
                "mae_C": round(float(abserr[m].mean()), 3),
                "bias_C": round(float(err[m].mean()), 3),
            }
        report["por_situacao"] = por_sit

    os.makedirs(os.path.dirname(args.saida), exist_ok=True)
    with open(args.saida, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n→ {args.saida}")


if __name__ == "__main__":
    main()
