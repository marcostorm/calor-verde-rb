"""Integração do scripts/trends.py: lê snapshots multi-ano e flagga setores
que esquentam acima da média da cidade + 1σ."""
import os
import sys

import pandas as pd

_SCRIPTS = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, os.path.abspath(_SCRIPTS))

import trends  # noqa: E402


def _make_snapshot(year_dir, rows):
    os.makedirs(year_dir, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(year_dir, "ranking.csv"), index=False)


def test_trends_two_years_flags_hot_outlier(tmp_path):
    snaps = tmp_path / "snapshots"
    out = tmp_path / "trends_out"
    # 10 setores: 9 esquentam ~0.5°C; 1 esquenta 4°C (deve ir pro alerta)
    base_2025 = [
        {"rank": i + 1, "nome": f"S{i:03d}", "bairro": f"B{i}", "lst_mean": 32.0 + i * 0.2}
        for i in range(10)
    ]
    _2026 = []
    for i, r in enumerate(base_2025):
        delta = 4.0 if i == 7 else 0.5
        _2026.append({**r, "lst_mean": r["lst_mean"] + delta})
    _make_snapshot(snaps / "2025", base_2025)
    _make_snapshot(snaps / "2026", _2026)

    trends.main([
        "--snapshots", str(snaps),
        "--out", str(out),
        "--col", "lst_mean",
    ])

    csv = out / "setor_lst.csv"
    assert csv.exists()
    df = pd.read_csv(csv, dtype={"nome": str})
    assert list(df.columns) == ["nome", "bairro", "2025", "2026",
                                 "delta_total", "delta_anual_media", "alerta"]
    assert len(df) == 10

    hot = df[df["nome"] == "S007"].iloc[0]
    assert hot["alerta"] == True
    assert abs(hot["delta_total"] - 4.0) < 1e-6

    tame = df[df["nome"] == "S000"].iloc[0]
    assert tame["alerta"] == False
    assert abs(tame["delta_total"] - 0.5) < 1e-6


def test_trends_single_year_runs_without_delta(tmp_path):
    """Com só 1 ano, trends.py não deve quebrar: escreve CSV com só a coluna
    do ano e omite delta_total/alerta."""
    snaps = tmp_path / "snapshots"
    out = tmp_path / "trends_out"
    _make_snapshot(snaps / "2026", [
        {"rank": 1, "nome": "S000", "bairro": "B0", "lst_mean": 34.5},
        {"rank": 2, "nome": "S001", "bairro": "B1", "lst_mean": 36.0},
    ])

    trends.main([
        "--snapshots", str(snaps),
        "--out", str(out),
    ])

    df = pd.read_csv(out / "setor_lst.csv", dtype={"nome": str})
    assert list(df.columns) == ["nome", "bairro", "2026"]
    assert len(df) == 2
    assert "delta_total" not in df.columns


def test_trends_errors_when_no_snapshots(tmp_path):
    """Dir vazio → sys.exit explícito (não gera CSV silenciosamente vazio)."""
    snaps = tmp_path / "snapshots"
    snaps.mkdir()
    out = tmp_path / "trends_out"
    with __import__("pytest").raises(SystemExit):
        trends.main([
            "--snapshots", str(snaps),
            "--out", str(out),
        ])
