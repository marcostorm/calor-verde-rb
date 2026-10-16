"""Diff estruturado entre duas rodadas do pipeline.

Uso:
  python scripts/compare_runs.py <dir_antigo> <dir_novo>

Cada diretório precisa ter:
  - resumo.json
  - ranking.csv
  - unidades_prioridade.geojson (opcional, só pra bin de cor)

Imprime:
  - deltas nas métricas da cidade (lst, perda, cobertura)
  - top-5 que entrou/saiu do ranking
  - top-10 maiores saltos de índice (pra cima e pra baixo)
  - mudanças de bin de cor por setor
  - interpolação: originais que viraram interpolados e vice-versa
"""
import argparse
import csv
import json
import os
import sys
from pathlib import Path


BINS_PRI = [10, 25, 40, 55, 70, 85]  # bate com viewer.html


def bin_of(v, bins):
    if v is None:
        return "cinza"
    for i, b in enumerate(bins):
        if v < b:
            return f"bin{i}"
    return f"bin{len(bins)}"


def load(dir_path):
    d = Path(dir_path)
    with open(d / "resumo.json") as f:
        resumo = json.load(f)
    rows = {}
    with open(d / "ranking.csv") as f:
        for r in csv.DictReader(f):
            rows[r["nome"]] = r
    return resumo, rows


def to_float(v):
    if v is None or v == "" or v == "nan":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def pct_delta(old, new):
    if old in (None, 0) or new is None:
        return None
    return 100 * (new - old) / abs(old)


def fmt(v, d=2):
    return "—" if v is None else f"{v:.{d}f}"


def diff_metricas(r_old, r_new):
    print("\n═══ Métricas da cidade ═══")
    keys = [
        ("lst_media_cidade", "°C"),
        ("lst_p75_cidade", "°C"),
        ("perda_total_ha", "ha"),
    ]
    for k, unit in keys:
        a = to_float(r_old.get(k))
        b = to_float(r_new.get(k))
        delta = None if (a is None or b is None) else b - a
        pct = pct_delta(a, b)
        p = "" if pct is None else f" ({pct:+.1f}%)"
        print(f"  {k:25s}  {fmt(a)} → {fmt(b)} {unit}  Δ={fmt(delta,2)}{p}")


def diff_top5(r_old, r_new):
    print("\n═══ Top-5 do ranking ═══")
    old = {t["nome"] for t in r_old.get("top5_prioridade", [])}
    new = {t["nome"] for t in r_new.get("top5_prioridade", [])}
    saiu = old - new
    entrou = new - old
    permaneceu = old & new
    print(f"  permaneceu: {len(permaneceu)}  entrou: {len(entrou)}  saiu: {len(saiu)}")
    if entrou:
        print(f"  entrou no top-5: {sorted(entrou)}")
    if saiu:
        print(f"  saiu do top-5:   {sorted(saiu)}")


def diff_saltos(rows_old, rows_new, n=10, min_delta=0.5):
    print(f"\n═══ Maiores saltos de índice (|Δ| ≥ {min_delta}) ═══")
    deltas = []
    for nome, new in rows_new.items():
        old = rows_old.get(nome)
        if not old:
            continue
        a = to_float(old.get("indice_prioridade"))
        b = to_float(new.get("indice_prioridade"))
        if a is None or b is None:
            continue
        if abs(b - a) < min_delta:
            continue
        deltas.append((b - a, nome, a, b))
    if not deltas:
        print("  (nenhum salto relevante)")
        return
    deltas.sort()
    quedas = [d for d in deltas if d[0] < 0][:n]
    altas = [d for d in deltas if d[0] > 0][-n:]
    if quedas:
        print(f"  Maiores quedas ({len(quedas)}):")
        for d, nome, a, b in quedas:
            print(f"    {nome}  {a:.2f} → {b:.2f}  Δ={d:+.2f}")
    if altas:
        print(f"  Maiores altas ({len(altas)}):")
        for d, nome, a, b in reversed(altas):
            print(f"    {nome}  {a:.2f} → {b:.2f}  Δ={d:+.2f}")


def diff_bins(rows_old, rows_new):
    print("\n═══ Mudança de bin de cor ═══")
    mudou = 0
    comparados = 0
    transicoes = {}
    for nome, new in rows_new.items():
        old = rows_old.get(nome)
        if not old:
            continue
        comparados += 1
        a_bin = bin_of(to_float(old.get("indice_prioridade")), BINS_PRI)
        b_bin = bin_of(to_float(new.get("indice_prioridade")), BINS_PRI)
        if a_bin != b_bin:
            mudou += 1
            key = f"{a_bin}→{b_bin}"
            transicoes[key] = transicoes.get(key, 0) + 1
    pct = 100 * mudou / max(comparados, 1)
    print(f"  {mudou} de {comparados} setores mudaram de bin ({pct:.1f}%)")
    if transicoes:
        top = sorted(transicoes.items(), key=lambda x: -x[1])[:6]
        print(f"  transições mais comuns: {', '.join(f'{k}×{v}' for k,v in top)}")


def diff_interpolacao(rows_old, rows_new):
    print("\n═══ Interpolação ═══")
    def is_true(v):
        return v in (True, "True", "true", "1")
    o_int = {n for n, r in rows_old.items() if is_true(r.get("interpolado"))}
    n_int = {n for n, r in rows_new.items() if is_true(r.get("interpolado"))}
    virou_interp = n_int - o_int
    deixou_interp = o_int - n_int
    print(f"  antes: {len(o_int)} interpolados  |  agora: {len(n_int)} interpolados")
    if virou_interp:
        print(f"  viraram interpolados: {len(virou_interp)}")
    if deixou_interp:
        print(f"  deixaram de ser interpolados: {len(deixou_interp)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("old", help="diretório da rodada antiga (ex. snapshots/2026-08)")
    ap.add_argument("new", help="diretório da rodada nova (ex. data/out)")
    args = ap.parse_args()

    for d in (args.old, args.new):
        if not os.path.isdir(d):
            sys.exit(f"diretório inexistente: {d}")

    r_old, rows_old = load(args.old)
    r_new, rows_new = load(args.new)

    print(f"OLD = {args.old}  ({len(rows_old)} setores)")
    print(f"NEW = {args.new}  ({len(rows_new)} setores)")

    diff_metricas(r_old, r_new)
    diff_top5(r_old, r_new)
    diff_saltos(rows_old, rows_new)
    diff_bins(rows_old, rows_new)
    diff_interpolacao(rows_old, rows_new)


if __name__ == "__main__":
    main()
