"""Gera relatório PDF do estado atual do projeto Calor & Verde.

Lê os outputs do pipeline (resumo.json, ranking_conservador.csv, trends/setor_lst.csv)
e compõe um PDF de 6 páginas com capa, sumário executivo, mapa, top-10,
série temporal, metodologia e limitações.

Uso:
  python scripts/relatorio.py                      # usa data/out/ e grava em relatorios/
  python scripts/relatorio.py --saida out.pdf      # custom path
"""
import argparse
import base64
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from weasyprint import HTML

import config as C  # noqa: E402

PALETTE = ["#ffffb2", "#fed976", "#feb24c", "#fd8d3c", "#fc4e2a", "#e31a1c", "#b10026"]
BINS_PRI = [0, 10, 25, 40, 55, 70, 85, 100]


def fmt_num(n, dec=1):
    if n is None:
        return "—"
    s = f"{n:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def read_ranking(out_dir):
    path = Path(out_dir) / "ranking_conservador.csv"
    if not path.exists():
        path = Path(out_dir) / "ranking.csv"
    # nome é código IBGE de 15 dígitos; força str pra bater com trends e geojson
    df = pd.read_csv(path, dtype={"nome": str})
    return df


def read_resumo(out_dir):
    path = Path(out_dir) / "resumo_conservador.json"
    if not path.exists():
        path = Path(out_dir) / "resumo.json"
    return json.loads(path.read_text())


def read_trends(out_dir):
    path = Path(out_dir) / "trends" / "setor_lst.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path, dtype={"nome": str})
    return df


def _plot_choropleth(gdf, valor_col, bins, palette, saida_png, interp_col=None):
    """Renderiza choropleth zoom-ado na mancha urbana (setores com dado)."""
    com_dado = gdf[gdf[valor_col].notna()].copy()
    if len(com_dado) == 0:
        return False
    minx, miny, maxx, maxy = com_dado.total_bounds

    fig, ax = plt.subplots(figsize=(10, 10))
    # fundo: todo o município em cinza-neblina
    gdf.plot(ax=ax, color="#eef2eb", edgecolor="none")
    # choropleth por bin
    for i, cor in enumerate(palette):
        lo, hi = bins[i], bins[i + 1]
        mask = (com_dado[valor_col] >= lo) & (com_dado[valor_col] < hi)
        sub = com_dado[mask]
        if len(sub):
            sub.plot(ax=ax, color=cor, edgecolor="#555", linewidth=0.2, alpha=0.9)
    # interpolados por cima
    if interp_col and interp_col in gdf.columns:
        interp = gdf[gdf[interp_col] == True]
        if len(interp):
            interp.plot(ax=ax, facecolor="none", edgecolor="#b8860b",
                        linewidth=0.5, linestyle="--")

    pad = max((maxx - minx), (maxy - miny)) * 0.04
    ax.set_xlim(minx - pad, maxx + pad)
    ax.set_ylim(miny - pad, maxy + pad)
    ax.set_axis_off()
    fig.patch.set_facecolor("white")
    fig.savefig(saida_png, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return True


def gerar_mapa_png(geojson_path, saida_png):
    gdf = gpd.read_file(geojson_path).to_crs(C.CRS)
    return _plot_choropleth(gdf, "indice_prioridade", BINS_PRI, PALETTE,
                            saida_png, interp_col="interpolado")


def gerar_mapa_delta_png(geojson_path, trends_df, saida_png):
    """Mapa divergente de variação 2025→2026."""
    if trends_df is None:
        return False
    gdf = gpd.read_file(geojson_path).to_crs(C.CRS)
    t = trends_df.set_index("nome")["delta_total"]
    gdf["_delta"] = gdf["nome"].map(t)
    pal_div = ["#2166ac", "#67a9cf", "#d1e5f0", "#fddbc7", "#ef8a62", "#b2182b", "#67001f"]
    bins_div = [-10, -1, -0.5, 0.5, 1.5, 3, 5, 20]
    return _plot_choropleth(gdf, "_delta", bins_div, pal_div, saida_png)


def embed_image(path):
    data = Path(path).read_bytes()
    b64 = base64.b64encode(data).decode()
    return f"data:image/png;base64,{b64}"


LEAF_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28" style="vertical-align:-6px;margin-right:8px">
  <path d="M11 20 A7 7 0 0 1 9.8 6.1 C15.5 5 17 4.48 19.2 2.96 a1 1 0 0 1 1.8 .4 A7 7 0 0 1 21.4 4.76 C22 11 20 20 11 20 Z" fill="#2d8537"/>
  <path d="M2 21 C2 18, 3.85 15.64, 7.08 15" stroke="#2d8537" stroke-width="2" fill="none" stroke-linecap="round"/>
  <path d="M19 5 L10 14" stroke="#ffffff" stroke-width="1" fill="none" stroke-linecap="round" opacity="0.85"/>
</svg>"""


CSS = """
@page { size: A4; margin: 24mm 18mm; @bottom-right { content: counter(page) " / " counter(pages); font-family: 'Nunito Sans', sans-serif; font-size: 9pt; color: #889590; } }
@page :first { @bottom-right { content: ""; } }
body { font-family: 'Nunito Sans', 'Helvetica', sans-serif; color: #1a2621; line-height: 1.55; font-size: 10pt; widows: 1; orphans: 1; }
h1 { font-family: 'Lora', 'Georgia', serif; font-weight: 700; font-size: 28pt; line-height: 1.15; letter-spacing: -0.01em; margin: 0 0 8pt; }
h2 { font-family: 'Lora', serif; font-weight: 600; font-size: 16pt; margin: 24pt 0 8pt; color: #1a2621; page-break-after: avoid; }
h3 { font-family: 'Lora', serif; font-weight: 600; font-size: 12pt; margin: 14pt 0 4pt; page-break-after: avoid; }
p { margin: 0 0 6pt; }
.capa { page-break-after: always; display: flex; flex-direction: column; justify-content: center; min-height: 220mm; }
.capa .selo { font-family: 'Nunito Sans', sans-serif; font-size: 10pt; color: #5a6b63; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 20pt; }
.capa h1 { font-size: 36pt; }
.capa .sub { font-family: 'Lora', serif; font-style: italic; font-size: 14pt; color: #5a6b63; margin: 8pt 0 32pt; max-width: 140mm; }
.manchete { background: #e3ead8; border-left: 4px solid #2d5a3d; padding: 20pt 24pt; margin: 20pt 0 24pt; border-radius: 2pt; }
.manchete .num { font-family: 'Lora', serif; font-weight: 700; font-size: 48pt; line-height: 1; color: #b10026; }
.manchete .label { font-family: 'Nunito Sans', sans-serif; font-size: 11pt; color: #1a2621; margin-top: 6pt; }
.capa .meta { font-size: 10pt; color: #5a6b63; margin-top: auto; padding-top: 20pt; border-top: 1px solid #c4cfb0; }
.capa .meta b { color: #1a2621; font-weight: 600; }
.sumario ul { padding-left: 0; list-style: none; margin: 0; }
.sumario li { padding: 5pt 0; border-bottom: 1px solid #c4cfb0; display: flex; gap: 14pt; align-items: baseline; }
.sumario li .valor { font-family: 'Lora', serif; font-weight: 700; font-size: 17pt; color: #2d5a3d; min-width: 90pt; font-variant-numeric: tabular-nums; }
.sumario li .texto { flex: 1; font-size: 9.5pt; color: #1a2621; line-height: 1.4; }
.mapa { margin: 6pt 0 10pt; }
.mapa img { width: 100%; max-height: 120mm; object-fit: contain; display: block; }
.mapa-compact img { max-height: 125mm; }
.pg-mapa { page-break-before: always; }
.pg-mapa h2 { margin-top: 0; }
.tabela-pequena { page-break-inside: avoid; }
.mapa .legenda { display: flex; gap: 12pt; margin-top: 4pt; font-size: 8pt; color: #5a6b63; justify-content: center; flex-wrap: wrap; }
.mapa .legenda span { display: inline-flex; align-items: center; gap: 4pt; }
.mapa .legenda i { width: 10pt; height: 10pt; display: inline-block; border: 0.5pt solid rgba(0,0,0,0.2); }
table { width: 100%; border-collapse: collapse; margin: 10pt 0 16pt; font-size: 9pt; }
th, td { padding: 6pt 8pt; text-align: left; border-bottom: 1px solid #c4cfb0; }
tr { page-break-inside: avoid; }
thead { display: table-header-group; }
th { background: #e3ead8; font-family: 'Nunito Sans', sans-serif; font-weight: 600; color: #1a2621; font-size: 8pt; text-transform: uppercase; letter-spacing: 0.03em; }
td.r { text-align: right; font-variant-numeric: tabular-nums; }
tr:nth-child(even) { background: #f7f9f4; }
.nivel { display: inline-block; padding: 2pt 6pt; border-radius: 8pt; font-size: 8pt; font-weight: 600; color: white; }
.nivel-alta { background: #fc4e2a; }
.nivel-critica { background: #b10026; }
.nivel-media { background: #fd8d3c; }
.nivel-baixa { background: #feb24c; color: #1a2621; }
.quente { color: #b10026; font-weight: 600; }
.esfriou { color: #2166ac; font-weight: 600; }
.limitacoes { background: #f7f9f4; border-left: 3px solid #a8b593; padding: 12pt 16pt; margin: 12pt 0; font-size: 9pt; line-height: 1.5; }
.limitacoes h3 { margin-top: 0; }
.limitacoes ul { margin: 6pt 0 0; padding-left: 16pt; }
.ref { font-size: 8.5pt; color: #5a6b63; margin-top: 8pt; padding-top: 5pt; border-top: 1px solid #c4cfb0; }
.ref a { color: #2d5a3d; text-decoration: none; }
.secao-num { font-size: 9pt; color: #889590; text-transform: uppercase; letter-spacing: 0.1em; }
"""


def montar_html(resumo, ranking, trends_df, mapa_pri_png, mapa_delta_png, hoje):
    # agregados
    com_rank = ranking[ranking["indice_prioridade"].notna()]
    n_total = len(ranking)
    n_rank = len(com_rank)
    lst_media = resumo["lst_media_cidade"]
    lst_p75 = resumo["lst_p75_cidade"]
    perda_total = resumo["perda_total_ha"]

    # série temporal
    tem_tendencia = trends_df is not None and len(trends_df) > 0
    delta_medio = quente_pct = n_esquentou = n_esfriou = n_alerta = None
    top_esquentou_html = ""
    if tem_tendencia:
        valid = trends_df.dropna(subset=["delta_total"])
        delta_medio = valid["delta_total"].mean()
        n_esquentou = (valid["delta_total"] > 0).sum()
        n_esfriou = (valid["delta_total"] < 0).sum()
        n_com_dado = len(valid)
        quente_pct = round(100 * n_esquentou / n_com_dado)
        n_alerta = int(valid["alerta"].sum()) if "alerta" in valid else 0
        top5 = valid.nlargest(5, "delta_total")
        top_esquentou_html = "".join(
            f"<tr><td>{r.bairro if pd.notna(r.bairro) else '—'}</td>"
            f"<td class='r'>{r['2025']:.1f}°</td>"
            f"<td class='r'>{r['2026']:.1f}°</td>"
            f"<td class='r quente'>+{r.delta_total:.1f}°C</td></tr>"
            for _, r in top5.iterrows()
        )

    # top10 setores críticos
    top10 = com_rank.nsmallest(10, "rank")
    delta_map = {}
    if tem_tendencia:
        delta_map = trends_df.set_index("nome")["delta_total"].to_dict()
    top10_html = ""
    for _, r in top10.iterrows():
        d = delta_map.get(r["nome"])
        d_cell = f"<td class='r quente'>+{d:.1f}°</td>" if d and d > 0 else (
            f"<td class='r esfriou'>−{abs(d):.1f}°</td>" if d and d < 0 else "<td class='r'>—</td>"
        )
        nivel_class = (
            "nivel-critica" if r.indice_prioridade >= 85
            else "nivel-alta" if r.indice_prioridade >= 55
            else "nivel-media" if r.indice_prioridade >= 25
            else "nivel-baixa"
        )
        nivel_label = (
            "crítica" if r.indice_prioridade >= 85
            else "alta" if r.indice_prioridade >= 55
            else "média" if r.indice_prioridade >= 25
            else "baixa"
        )
        top10_html += (
            f"<tr>"
            f"<td>{int(r['rank'])}</td>"
            f"<td>{str(r['nome'])[-3:]}</td>"
            f"<td>{r.get('bairro', '') or '—'}</td>"
            f"<td class='r'>{r.indice_prioridade:.1f} <span class='nivel {nivel_class}'>{nivel_label}</span></td>"
            f"<td class='r'>{r.lst_mean:.1f}°</td>"
            f"{d_cell}"
            f"</tr>"
        )

    # manchete da capa
    if tem_tendencia:
        manchete_num = f"+{delta_medio:.1f}°C"
        manchete_label = f"de aquecimento médio da superfície entre as estações secas de {C.YEAR_NOW-1} e {C.YEAR_NOW}, com {quente_pct}% dos {n_com_dado} setores com dado em ambos os anos."
    else:
        manchete_num = f"{int(round(perda_total)):,}".replace(",", ".") + " ha"
        manchete_label = f"de vegetação perdida desde {C.YEAR_BASE}. Equivale a cerca de {perda_total/100:.0f} km² sobre {int(ranking['area_ha'].sum()/100):,} km² avaliados da cidade.".replace(",", ".")

    # mapa delta opcional
    secao_delta = ""
    if tem_tendencia and mapa_delta_png:
        secao_delta = f"""
<section class="pg-mapa">
  <div class="secao-num">04 · Variação de temperatura</div>
  <h2>Mapa de variação {C.YEAR_NOW-1}→{C.YEAR_NOW}</h2>
  <p>Choropleth divergente da variação de temperatura da superfície entre as duas estações secas. Vermelho = esquentou; azul = esfriou.</p>
  <div class="mapa mapa-compact"><img src="{embed_image(mapa_delta_png)}" alt="Mapa de variação"></div>
  <div class="tabela-pequena">
  <h3>Setores que mais esquentaram</h3>
  <table>
    <thead><tr><th>Bairro</th><th class="r">LST {C.YEAR_NOW-1}</th><th class="r">LST {C.YEAR_NOW}</th><th class="r">Variação</th></tr></thead>
    <tbody>{top_esquentou_html}</tbody>
  </table>
  </div>
</section>
        """

    # POIs em zona de calor extremo (do resumo)
    zq = resumo.get("pois_em_zona_quente") or {}
    tt = resumo.get("pois_total") or {}
    poi_labels = [("Escolas", "educacao"), ("Postos de saúde", "saude"), ("Pontos de ônibus", "ponto_onibus")]
    poi_rows_html = ""
    for label, chave in poi_labels:
        i, t = int(zq.get(chave) or 0), int(tt.get(chave) or 0)
        if t == 0:
            continue
        pct = round(100 * i / t)
        # cor baseada na severidade (igual nivel na tabela)
        cor = "#b10026" if pct >= 85 else "#fc4e2a" if pct >= 55 else "#fd8d3c" if pct >= 25 else "#feb24c"
        poi_rows_html += (
            f"<tr><td>{label}</td>"
            f"<td class='r'><b>{i}</b> de {t}</td>"
            f"<td class='r' style='color:{cor};font-weight:600'>{pct}%</td></tr>"
        )

    # equivalente em campos de futebol (105x68m = 0,714 ha)
    campos_futebol = int(round(perda_total / 0.714))
    perda_ha_fmt = f"{int(round(perda_total)):,}".replace(",", ".")
    campos_fmt = f"{campos_futebol:,}".replace(",", ".")

    stats_sumario = []
    stats_sumario.append((fmt_num(lst_media) + "°C", f"temperatura média do chão em {C.YEAR_NOW} na estação seca; medida pelo Landsat 8/9"))
    stats_sumario.append((perda_ha_fmt + " ha", f"de vegetação perdida entre {C.YEAR_BASE} e {C.YEAR_NOW} &mdash; equivalente a cerca de <b>{campos_fmt} campos de futebol</b> (padrão FIFA 105×68 m)"))
    stats_sumario.append((f"{n_rank}", f"setores censitários com dado confiável; {n_total - n_rank} descartados por nuvem persistente"))
    if tem_tendencia:
        stats_sumario.append((f"+{fmt_num(delta_medio)}°C", f"aquecimento médio em um ano ({quente_pct}% dos setores esquentaram)"))
        stats_sumario.append((str(n_alerta), f"setores em alerta por aquecimento acima da média + 1 desvio-padrão"))

    sumario_html = "<ul>" + "".join(
        f"<li><span class='valor'>{v}</span><span class='texto'>{t}</span></li>"
        for v, t in stats_sumario
    ) + "</ul>"

    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Nunito+Sans:wght@400;600;700&display=swap">
<style>{CSS}</style>
</head>
<body>

<section class="capa">
  <div class="selo">{LEAF_SVG}Calor &amp; Verde — Rio Branco</div>
  <h1>Panorama {C.YEAR_NOW}</h1>
  <div class="sub">Onde a cidade mais precisa de árvore. Diagnóstico por satélite da estação seca.</div>
  <div class="manchete">
    <div class="num">{manchete_num}</div>
    <div class="label">{manchete_label}</div>
  </div>
  <div class="meta">
    Rio Branco, Acre · estação seca jun–set/{C.YEAR_NOW}<br>
    Publicado em <b>{hoje.strftime('%d/%m/%Y')}</b> por <b>Marcos Henrique Melo de Araújo</b><br>
    Dados: Landsat 8/9 (NASA/USGS) · Sentinel-2 (ESA) · IBGE 2022 · INPE · OpenStreetMap<br>
    Reprodutível em <a href="https://github.com/marcostorm/calor-verde-rb">github.com/marcostorm/calor-verde-rb</a>
  </div>
</section>

<section>
  <div class="secao-num">01 · Sumário executivo</div>
  <h2>Em cinco números</h2>
  <div class="sumario">{sumario_html}</div>
</section>

<section>
  <div class="secao-num">02 · Os dez setores mais críticos</div>
  <h2>Onde plantar primeiro</h2>
  <p>Classificação pela nota de prioridade. &quot;Setor&quot; mostra os três últimos dígitos do código IBGE. &quot;Variação&quot; compara a temperatura da superfície com a de {C.YEAR_NOW-1}.</p>
  <table>
    <thead><tr>
      <th>#</th><th>Setor</th><th>Bairro</th>
      <th class="r">Prioridade</th>
      <th class="r">LST {C.YEAR_NOW}</th>
      <th class="r">Δ {C.YEAR_NOW-1}→{C.YEAR_NOW}</th>
    </tr></thead>
    <tbody>{top10_html}</tbody>
  </table>
</section>

<section class="pg-mapa">
  <div class="secao-num">03 · Mapa da cidade</div>
  <h2>Prioridade de plantio</h2>
  <p>Cada polígono é um setor censitário do IBGE. A cor combina temperatura da superfície (peso 50%), falta de vegetação (30%) e perda vegetacional desde {C.YEAR_BASE} (20%). Vermelho vinho = plantio crítico; amarelo claro = baixa prioridade.</p>
  <div class="mapa"><img src="{embed_image(mapa_pri_png)}" alt="Mapa de prioridade"></div>
  <div class="legenda">
    <span><i style="background:#ffffb2"></i>baixa</span>
    <span><i style="background:#feb24c"></i>média</span>
    <span><i style="background:#fc4e2a"></i>alta</span>
    <span><i style="background:#b10026"></i>crítica</span>
    <span><i style="background:white;border:1px dashed #b8860b"></i>estimado por buffer</span>
  </div>
  {('<div class="tabela-pequena" style="margin-top:16pt"><h3>Lugares de uso coletivo em zona de calor extremo</h3>'
    '<p style="font-size:9pt;color:#5a6b63;margin:0 0 6pt">Escolas, postos de saúde e pontos de ônibus cujas coordenadas (OpenStreetMap) caem num pixel com temperatura acima do limiar de zona de calor extremo. Alto percentual significa infraestrutura pública exposta e, portanto, prioritária pra sombreamento.</p>'
    '<table><thead><tr><th>Lugar</th><th class="r">Em zona de calor extremo</th><th class="r">%</th></tr></thead>'
    f'<tbody>{poi_rows_html}</tbody></table></div>') if poi_rows_html else ''}
</section>

{secao_delta}

<section>
  <div class="secao-num">05 · Metodologia resumida</div>
  <h2>Como o número foi feito</h2>
  <p><b>Fontes</b>: Landsat 8/9 (temperatura da superfície, 30 m, mediana da estação seca); Sentinel-2 L2A (NDVI, 10 m, Cloud Score+ ≥ 0,6); IBGE 2022 (setores censitários + percentual de moradores em face com árvore); INPE (focos de queimada AQUA_M-T); OpenStreetMap (bairros não-oficiais).</p>
  <p><b>Índice de prioridade</b> = 0,5 × calor normalizado + 0,3 × falta de verde + 0,2 × perda vegetacional desde {C.YEAR_BASE}. Resultado reescalado para 0–100.</p>
  <p><b>Interpolação</b>: setores com menos de 50% de pixels de LST livres de nuvem recebem valor estimado por buffer de 3,5 km consciente de contexto urbano/rural. Aparecem com borda tracejada dourada. Erro típico: ±2,3°C (cross-validation leave-one-out).</p>

  <div class="limitacoes">
    <h3>Limitações a honrar antes de citar</h3>
    <ul>
      <li><b>Temperatura da superfície ≠ temperatura do ar.</b> O Landsat mede o que o chão irradia; termômetro em sombra marca menos. LST serve para comparar áreas entre si, não para política de saúde pública absoluta.</li>
      <li><b>Dois anos de LST ainda não é tendência climática.</b> O aquecimento observado de {C.YEAR_NOW-1} para {C.YEAR_NOW} pode refletir variabilidade interanual (seca mais severa) ou aquecimento regional. Precisamos de 5+ anos para separar os sinais.</li>
      <li><b>Bairros vêm do OpenStreetMap</b>, não da prefeitura. Nomes podem repetir e divisão é informal. O setor censitário IBGE é a unidade formal.</li>
      <li><b>Focos de queimada são detecções pontuais do AQUA_M-T</b>, não contornos de área queimada. Um ponto não equivale a hectares ardidos.</li>
      <li><b>Pesos 50/30/20 são escolha metodológica</b>, documentada em <code>config.py</code>. Podem ser revisados; o código é aberto para isso.</li>
    </ul>
  </div>
</section>

<section>
  <div class="secao-num">06 · Reproduzir e citar</div>
  <h2>Como usar este relatório</h2>
  <p><b>Mapa interativo e lista completa</b>: <a href="https://marcostorm.github.io/calor-verde-rb/">marcostorm.github.io/calor-verde-rb</a> · <b>metodologia completa</b>: <a href="https://marcostorm.github.io/calor-verde-rb/metodo.html">/metodo.html</a> · <b>reprodução</b>: <code>git clone github.com/marcostorm/calor-verde-rb</code> (requer Python 3.12 + GEE) · <b>dados brutos</b>: <code>snapshots/{C.YEAR_NOW}/</code> no repositório.</p>
  <p><b>Como citar</b> (ABNT): ARAÚJO, M. H. M. <i>Calor &amp; Verde — Rio Branco</i>: diagnóstico por satélite da prioridade de plantio na estação seca de {C.YEAR_NOW}. Rio Branco: Storm Lab, {C.YEAR_NOW}. Disponível em: &lt;https://marcostorm.github.io/calor-verde-rb/&gt;. Acesso em: {hoje.strftime('%d/%m/%Y')}.</p>
  <div class="ref">
    Licença dos dados derivados: CC BY 4.0 · Código: ver repositório · Projeto independente, não institucional · Dúvidas e correções: via issues no GitHub.
  </div>
</section>

</body>
</html>
"""
    return html


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=C.OUT_DIR, help="pasta de outputs do pipeline")
    ap.add_argument("--saida", help="caminho do PDF (default: relatorios/calor-verde-rb_YYYY-MM-DD.pdf)")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    hoje = date.today()
    saida = Path(args.saida) if args.saida else Path("relatorios") / f"calor-verde-rb_{hoje.isoformat()}.pdf"
    saida.parent.mkdir(parents=True, exist_ok=True)

    print(f"[relatorio] lendo outputs de {out_dir}")
    resumo = read_resumo(out_dir)
    ranking = read_ranking(out_dir)
    trends_df = read_trends(out_dir)

    # mapas em diretório temporário dentro do out_dir
    tmp_dir = saida.parent / "_tmp_mapas"
    tmp_dir.mkdir(exist_ok=True)
    mapa_pri_png = tmp_dir / "mapa_prioridade.png"
    mapa_delta_png = tmp_dir / "mapa_delta.png"

    geojson_pri = out_dir / "unidades_prioridade_conservador.geojson"
    if not geojson_pri.exists():
        geojson_pri = out_dir / "unidades_prioridade.geojson"
    print(f"[relatorio] renderizando mapa de prioridade...")
    gerar_mapa_png(str(geojson_pri), str(mapa_pri_png))

    tem_mapa_delta = False
    if trends_df is not None:
        print(f"[relatorio] renderizando mapa de variação...")
        tem_mapa_delta = gerar_mapa_delta_png(str(geojson_pri), trends_df, str(mapa_delta_png))

    print(f"[relatorio] montando HTML...")
    html = montar_html(resumo, ranking, trends_df, mapa_pri_png, mapa_delta_png if tem_mapa_delta else None, hoje)

    print(f"[relatorio] renderizando PDF via WeasyPrint...")
    HTML(string=html, base_url=".").write_pdf(saida)

    # cópia estável pro link do viewer/ranking (sempre o mais recente)
    latest = saida.parent / "calor-verde-rb_latest.pdf"
    latest.write_bytes(saida.read_bytes())

    # limpa png temporários
    for p in tmp_dir.glob("*.png"):
        p.unlink()
    tmp_dir.rmdir()

    print(f"[relatorio] gerado {saida} ({saida.stat().st_size // 1024} KB)")
    print(f"[relatorio] cópia estável: {latest}")


if __name__ == "__main__":
    main()
