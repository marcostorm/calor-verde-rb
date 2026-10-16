"""Integração end-to-end do analyze.py contra a fixture sintética.

Garante que o pipeline aceita entradas mínimas, gera os 3 outputs esperados,
e produz números dentro de ranges sensatos. Serve de rede de segurança pra
refatores no analyze.py e pra atualização de dependências.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def test_analyze_end_to_end(fixture_dir):
    env = os.environ.copy()
    env["CALOR_VERDE_DATA_DIR"] = fixture_dir["data_dir"]
    env["CALOR_VERDE_OUT_DIR"] = fixture_dir["out_dir"]

    cmd = [
        sys.executable, "analyze.py",
        "--unidades", fixture_dir["unidades"],
        "--sem-pois", "--sem-bairros", "--sem-interpolar",
        "--min-cobertura", "0.5",
    ]
    r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f"analyze.py falhou:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"

    out = Path(fixture_dir["out_dir"])
    ranking = out / "ranking.csv"
    geojson = out / "unidades_prioridade.geojson"
    resumo = out / "resumo.json"
    for p in (ranking, geojson, resumo):
        assert p.exists(), f"saída esperada não existe: {p}"

    df = pd.read_csv(ranking)
    assert len(df) == fixture_dir["n_setores"], (
        f"ranking tem {len(df)} linhas, esperava {fixture_dir['n_setores']}"
    )
    assert "indice_prioridade" in df.columns
    assert "lst_mean" in df.columns
    assert df["indice_prioridade"].between(0, 100).all()

    with resumo.open() as f:
        meta = json.load(f)
    assert "lst_media_cidade" in meta
    assert 25.0 <= meta["lst_media_cidade"] <= 45.0, (
        f"lst_media_cidade fora do range sensato: {meta['lst_media_cidade']}"
    )

    with geojson.open() as f:
        gj = json.load(f)
    assert gj.get("type") == "FeatureCollection"
    assert len(gj["features"]) == fixture_dir["n_setores"]


def test_read_raster_returns_float32(fixture_dir):
    """Anti-regressão do bug OOM: read_raster precisa devolver float32.
    Reverter pra float64 explode a RAM em rasters reais (ver commit ec5c364)."""
    import importlib

    sys.path.insert(0, str(ROOT))
    try:
        analyze = importlib.import_module("analyze")
        importlib.reload(analyze)
        lst_path = os.path.join(fixture_dir["data_dir"], "lst_2026.tif")
        arr, _, _ = analyze.read_raster(lst_path)
        assert arr.dtype.name == "float32", (
            f"read_raster devolveu {arr.dtype}; precisa ser float32 (ver ec5c364)"
        )
    finally:
        if str(ROOT) in sys.path:
            sys.path.remove(str(ROOT))
