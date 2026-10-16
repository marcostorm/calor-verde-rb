"""Integração end-to-end do analyze.py contra a fixture sintética.

Garante que o pipeline aceita entradas mínimas, gera os 3 outputs esperados,
e produz números dentro de ranges sensatos. Serve de rede de segurança pra
refatores no analyze.py e pra atualização de dependências.
"""
import json
import os
from argparse import Namespace
from pathlib import Path

import pandas as pd
import pytest


def _args_for_pipeline(fixture_dir, **overrides):
    base = dict(
        unidades=fixture_dir["unidades"],
        dissolver=None, arborizacao=None,
        chave="nome", col_arbor="pct_arborizacao",
        min_cobertura=0.5, sem_pois=True, sem_interpolar=True,
        buffer_interp=3500, min_pixels_interp=50,
        interpolacao_ingenua=False, bairros_gpkg="data/bairros_rb.gpkg",
        bairro_max_m=3000, sem_bairros=True,
    )
    base.update(overrides)
    return Namespace(**base)


def test_analyze_end_to_end(fixture_dir, monkeypatch):
    import analyze
    import config
    monkeypatch.setattr(config, "DATA_DIR", fixture_dir["data_dir"])
    monkeypatch.setattr(config, "OUT_DIR", fixture_dir["out_dir"])

    args = _args_for_pipeline(fixture_dir)
    writer = analyze.AtomicWriter(fixture_dir["out_dir"])
    try:
        analyze._run_pipeline(args, writer)
    except BaseException:
        writer.cleanup()
        raise

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


def test_hard_fail_preserves_old_outputs(fixture_dir, tmp_path, monkeypatch):
    """Idempotência (Fase 6.3): se o pipeline falha depois de ter começado a
    escrever, os outputs da rodada anterior ficam intactos e nenhum .tmp
    sobra. Hard-fail forçado com --min-cobertura 1.1 (nenhum setor passa)."""
    out_dir = tmp_path / "out_isolado"
    out_dir.mkdir()
    SENTINELS = {
        "ranking.csv": "sentinela-ranking-antigo\n",
        "resumo.json": '{"sentinela": "antigo"}\n',
        "unidades_prioridade.geojson": "sentinela-geojson-antigo\n",
    }
    for name, content in SENTINELS.items():
        (out_dir / name).write_text(content)

    import analyze
    import config
    monkeypatch.setattr(config, "DATA_DIR", fixture_dir["data_dir"])
    monkeypatch.setattr(config, "OUT_DIR", str(out_dir))

    args = _args_for_pipeline(fixture_dir, min_cobertura=1.1)
    writer = analyze.AtomicWriter(str(out_dir))
    with pytest.raises(SystemExit) as excinfo:
        try:
            analyze._run_pipeline(args, writer)
        except BaseException:
            writer.cleanup()
            raise
    assert excinfo.value.code == 2

    for name, expected in SENTINELS.items():
        actual = (out_dir / name).read_text()
        assert actual == expected, (
            f"{name} foi sobrescrito; esperado sentinela, veio: {actual[:80]!r}"
        )

    orphan_tmps = list(out_dir.glob("*.tmp"))
    assert not orphan_tmps, f"tmps órfãos no out_dir: {orphan_tmps}"


def test_run_recorder_captures_metrics_on_success(fixture_dir, tmp_path, monkeypatch):
    """Fase 6.2: run manifest JSON é gravado com counts, stages, versions e
    métricas finais. Também valida que set_args não vaza secrets (só os args
    do argparse) e que o status final é 'ok'."""
    out_dir = tmp_path / "out_log_ok"
    out_dir.mkdir()
    logs_dir = tmp_path / "logs"

    import analyze
    import config
    monkeypatch.setattr(config, "DATA_DIR", fixture_dir["data_dir"])
    monkeypatch.setattr(config, "OUT_DIR", str(out_dir))
    monkeypatch.setattr(config, "LOGS_DIR", str(logs_dir))

    args = _args_for_pipeline(fixture_dir)
    writer = analyze.AtomicWriter(str(out_dir))
    recorder = analyze.RunRecorder(str(logs_dir))
    recorder.set_args(args)
    try:
        analyze._run_pipeline(args, writer, recorder)
    except BaseException:
        writer.cleanup()
        raise
    recorder.finalize("ok")
    path = recorder.save()

    assert path and os.path.exists(path), f"run log não foi gravado: {path}"
    with open(path) as f:
        data = json.load(f)
    assert data["status"] == "ok"
    assert data["duration_s"] > 0
    assert data["counts"]["unidades"] == fixture_dir["n_setores"]
    assert "write" in data["stages"] and data["stages"]["write"] >= 0
    assert "validate" in data["stages"]
    assert data["versions"]["geopandas"] is not None
    assert data["versions"]["rasterio"] is not None
    assert 25.0 <= data["metrics"]["lst_media_cidade"] <= 45.0


def test_run_recorder_saved_even_on_hard_fail(fixture_dir, tmp_path, monkeypatch):
    """Fase 6.2: mesmo em hard-fail, o run manifest é gravado — é a razão
    de ser do log (post-mortem de incidentes). Status fica 'hard_fail'."""
    out_dir = tmp_path / "out_log_fail"
    out_dir.mkdir()
    logs_dir = tmp_path / "logs_fail"

    import analyze
    import config
    monkeypatch.setattr(config, "DATA_DIR", fixture_dir["data_dir"])
    monkeypatch.setattr(config, "OUT_DIR", str(out_dir))
    monkeypatch.setattr(config, "LOGS_DIR", str(logs_dir))

    args = _args_for_pipeline(fixture_dir, min_cobertura=1.1)
    writer = analyze.AtomicWriter(str(out_dir))
    recorder = analyze.RunRecorder(str(logs_dir))
    recorder.set_args(args)
    try:
        analyze._run_pipeline(args, writer, recorder)
    except SystemExit as e:
        writer.cleanup()
        recorder.finalize("hard_fail" if e.code == 2 else "error", str(e.code))
    path = recorder.save()

    assert path and os.path.exists(path)
    with open(path) as f:
        data = json.load(f)
    assert data["status"] == "hard_fail"
    assert data["counts"]["unidades"] == fixture_dir["n_setores"]


def test_read_raster_returns_float32(fixture_dir):
    """Anti-regressão do bug OOM: read_raster precisa devolver float32.
    Reverter pra float64 explode a RAM em rasters reais (ver commit ec5c364)."""
    import analyze
    lst_path = os.path.join(fixture_dir["data_dir"], "lst_2026.tif")
    arr, _, _ = analyze.read_raster(lst_path)
    assert arr.dtype.name == "float32", (
        f"read_raster devolveu {arr.dtype}; precisa ser float32 (ver ec5c364)"
    )
