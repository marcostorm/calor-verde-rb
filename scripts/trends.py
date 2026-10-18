"""Série temporal de LST por setor a partir dos snapshots.

Lê `snapshots/<chave>/ranking.csv` e produz `data/out/trends/setor_lst.csv`
com uma coluna de LST por período. Marca setores cuja variação total está
acima da média da cidade + 1σ da cidade.

Granularidade:
    annual   (default): varre snapshots/YYYY/ranking.csv
    monthly:            varre snapshots/YYYY-MM/ranking.csv

Uso:
    python scripts/trends.py                              # anual, snapshots/ e data/out/
    python scripts/trends.py --granularidade monthly      # mensal
    python scripts/trends.py --snapshots dir --out dir
    python scripts/trends.py --col lst_percentile_90      # (default: lst_mean)

Com só 1 período disponível, roda e avisa — o CSV sai com só uma coluna.
"""
import argparse
import logging
import os
import re
import sys

import pandas as pd

logger = logging.getLogger("trends")

ANNUAL_RE = re.compile(r"^\d{4}$")
MONTHLY_RE = re.compile(r"^\d{4}-\d{2}$")


def discover_snapshots(snapshots_dir, granularidade):
    """Retorna {chave: path_ranking} pra subpastas que casam o padrão da granularidade.

    annual  → chave 'YYYY'    (ex.: '2025', '2026')
    monthly → chave 'YYYY-MM' (ex.: '2026-07', '2026-08')
    """
    regex = ANNUAL_RE if granularidade == "annual" else MONTHLY_RE
    found = {}
    for entry in sorted(os.listdir(snapshots_dir)):
        if not regex.match(entry):
            continue
        p = os.path.join(snapshots_dir, entry, "ranking.csv")
        if os.path.exists(p):
            found[entry] = p
    return found


def load_period(path, col):
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
    periods = sorted(found)  # strings ordenam lexicograficamente (YYYY ou YYYY-MM)
    first = periods[0]
    base = load_period(found[first], col).rename(columns={col: first})
    if "bairro" not in base.columns:
        base["bairro"] = None
    out = base[["nome", "bairro", first]].copy()
    for p in periods[1:]:
        df = load_period(found[p], col).rename(columns={col: p})
        if "bairro" in df.columns and out["bairro"].isna().all():
            out["bairro"] = df.set_index("nome")["bairro"].reindex(out["nome"]).values
        out = out.merge(df[["nome", p]], on="nome", how="outer")
    return out, periods


def mark_outliers(series, periods, granularidade):
    """Marca setores com delta_total acima de média_cidade + 1σ_cidade."""
    period_cols = list(periods)
    delta_label = "delta_anual_media" if granularidade == "annual" else "delta_mensal_media"
    if len(periods) < 2:
        series["delta_total"] = None
        series[delta_label] = None
        series["alerta"] = False
        return series, delta_label
    values = series[period_cols]
    series["delta_total"] = (values[period_cols[-1]] - values[period_cols[0]]).round(2)
    series[delta_label] = (series["delta_total"] / (len(periods) - 1)).round(2)
    valid = series["delta_total"].dropna()
    mean = float(valid.mean())
    sigma = float(valid.std(ddof=0))
    cutoff = mean + sigma
    series["alerta"] = series["delta_total"].apply(
        lambda d: bool(d is not None and not pd.isna(d) and d > cutoff)
    )
    logger.info("variação da cidade: média=%.2f°C, σ=%.2f°C, corte=%.2f°C",
                mean, sigma, cutoff)
    return series, delta_label


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshots", default="snapshots",
                    help="diretório com subpastas de snapshot contendo ranking.csv")
    ap.add_argument("--out", default="data/out/trends",
                    help="diretório onde gravar setor_lst.csv")
    ap.add_argument("--col", default="lst_mean",
                    help="coluna do ranking.csv a seguir no tempo (default: lst_mean)")
    ap.add_argument("--granularidade", choices=["annual", "monthly"], default="annual",
                    help="varre YYYY/ (annual) ou YYYY-MM/ (monthly)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)

    found = discover_snapshots(args.snapshots, args.granularidade)
    if not found:
        padrao = "YYYY" if args.granularidade == "annual" else "YYYY-MM"
        sys.exit(f"nenhum snapshot {padrao}/ranking.csv em {args.snapshots}/")
    logger.info("snapshots %s encontrados: %s", args.granularidade, sorted(found))

    series, periods = build_series(found, args.col)
    series, delta_label = mark_outliers(series, periods, args.granularidade)

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, "setor_lst.csv")
    cols_order = ["nome", "bairro"] + list(periods)
    if len(periods) >= 2:
        cols_order += ["delta_total", delta_label, "alerta"]
    series[cols_order].to_csv(path, index=False)
    logger.info("escrito: %s (%d setores, %d períodos)", path, len(series), len(periods))

    if len(periods) < 2:
        unidade = "ano" if args.granularidade == "annual" else "mês"
        logger.warning("só %d %s disponível — tendências precisam de ≥2 períodos",
                       len(periods), unidade)
    else:
        n_alerta = int(series["alerta"].sum())
        logger.info("setores em alerta (esquentando acima do normal): %d", n_alerta)


if __name__ == "__main__":
    main()
