"""Série temporal de LST por setor a partir dos snapshots anuais.

Lê `snapshots/<ano>/ranking.csv` (ou qualquer dir com subpastas numéricas de 4
dígitos contendo esse arquivo) e produz `data/out/trends/setor_lst.csv` com
uma coluna de LST média por ano. Marca setores cuja variação total está
acima da média da cidade + 1σ da cidade.

Uso:
    python scripts/trends.py                               # snapshots/ e data/out/
    python scripts/trends.py --snapshots dir --out dir
    python scripts/trends.py --col lst_mean                # (default) ou lst_percentile_90

Com só 1 ano disponível, roda e avisa — o CSV sai com só uma coluna.
"""
import argparse
import glob
import logging
import os
import re
import sys

import pandas as pd

logger = logging.getLogger("trends")

YEAR_RE = re.compile(r"^\d{4}$")


def discover_snapshots(snapshots_dir):
    """Retorna {ano: path_ranking} pra toda subpasta `YYYY/` com ranking.csv."""
    found = {}
    for entry in sorted(os.listdir(snapshots_dir)):
        if not YEAR_RE.match(entry):
            continue
        p = os.path.join(snapshots_dir, entry, "ranking.csv")
        if os.path.exists(p):
            found[int(entry)] = p
    return found


def load_year(path, col):
    df = pd.read_csv(path, dtype={"nome": str})
    cols = ["nome"]
    if "bairro" in df.columns:
        cols.append("bairro")
    if col not in df.columns:
        raise ValueError(f"coluna '{col}' não existe em {path}; disponíveis: {list(df.columns)}")
    cols.append(col)
    return df[cols].copy()


def build_series(found, col):
    """Faz merge por 'nome' (CD_SETOR) em um único DataFrame largo."""
    years = sorted(found)
    first_year = years[0]
    base = load_year(found[first_year], col).rename(columns={col: str(first_year)})
    if "bairro" not in base.columns:
        base["bairro"] = None
    out = base[["nome", "bairro", str(first_year)]].copy()
    for y in years[1:]:
        df = load_year(found[y], col).rename(columns={col: str(y)})
        if "bairro" in df.columns and out["bairro"].isna().all():
            out["bairro"] = df.set_index("nome")["bairro"].reindex(out["nome"]).values
        out = out.merge(df[["nome", str(y)]], on="nome", how="outer")
    return out, years


def mark_outliers(series, years):
    """Marca setores com delta_total acima de média_cidade + 1σ_cidade."""
    year_cols = [str(y) for y in years]
    if len(years) < 2:
        series["delta_total"] = None
        series["delta_anual_media"] = None
        series["alerta"] = False
        return series
    values = series[year_cols]
    series["delta_total"] = (values[year_cols[-1]] - values[year_cols[0]]).round(2)
    series["delta_anual_media"] = (series["delta_total"] / (len(years) - 1)).round(2)
    valid = series["delta_total"].dropna()
    mean = float(valid.mean())
    sigma = float(valid.std(ddof=0))
    cutoff = mean + sigma
    series["alerta"] = series["delta_total"].apply(
        lambda d: bool(d is not None and not pd.isna(d) and d > cutoff)
    )
    logger.info("variação da cidade: média=%.2f°C, σ=%.2f°C, corte=%.2f°C",
                mean, sigma, cutoff)
    return series


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", default="snapshots",
                    help="diretório com subpastas YYYY/ contendo ranking.csv")
    ap.add_argument("--out", default="data/out/trends",
                    help="diretório onde gravar setor_lst.csv")
    ap.add_argument("--col", default="lst_mean",
                    help="coluna do ranking.csv a seguir no tempo (default: lst_mean)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)

    found = discover_snapshots(args.snapshots)
    if not found:
        sys.exit(f"nenhum snapshot encontrado em {args.snapshots}/YYYY/ranking.csv")
    logger.info("snapshots encontrados: %s", sorted(found))

    series, years = build_series(found, args.col)
    series = mark_outliers(series, years)

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "setor_lst.csv")
    cols_order = ["nome", "bairro"] + [str(y) for y in years]
    if len(years) >= 2:
        cols_order += ["delta_total", "delta_anual_media", "alerta"]
    series[cols_order].to_csv(path, index=False)
    logger.info("escrito: %s (%d setores, %d anos)", path, len(series), len(years))

    if len(years) < 2:
        logger.warning("só %d ano disponível — tendências precisam de ≥2 anos", len(years))
    else:
        n_alerta = int(series["alerta"].sum())
        logger.info("setores em alerta (esquentando acima do normal): %d", n_alerta)


if __name__ == "__main__":
    main()
