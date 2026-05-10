from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.request import urlopen


PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.2.min.js"
PLOTLY_LOCAL_NAME = "plotly-2.35.2.min.js"


def _read_csv(path: Path) -> List[Dict]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _run_sort_key(run_dir: Path) -> float:
    summary = run_dir / "summary.json"
    csv_path = run_dir / "metrics_timeseries.csv"
    if summary.exists():
        return summary.stat().st_mtime
    if csv_path.exists():
        return csv_path.stat().st_mtime
    return run_dir.stat().st_mtime


def _mean(arr: List[float]) -> float:
    return sum(arr) / len(arr) if arr else 0.0


def _ensure_local_plotly_asset(outputs_dir: Path) -> bool:
    assets_dir = outputs_dir / "_assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    local_js = assets_dir / PLOTLY_LOCAL_NAME
    if local_js.exists() and local_js.stat().st_size > 1024:
        return True
    try:
        with urlopen(PLOTLY_CDN, timeout=30) as resp:
            data = resp.read()
        if len(data) > 1024:
            local_js.write_bytes(data)
            return True
    except Exception:
        return False
    return False


def _metric_series_for_run(run_dir: Path, metric_key: str) -> Tuple[str, str, List[int], List[float]]:
    rows = _read_csv(run_dir / "metrics_timeseries.csv")
    if not rows:
        return run_dir.name, "unknown", [], []
    years = [int(r.get("tick", i + 1)) for i, r in enumerate(rows)]
    series = [float(r.get(metric_key, 0.0)) for r in rows]
    governance = rows[0].get("governance", "unknown")
    return run_dir.name, governance, years, series


def _overlap_and_band(run_list: List[Path], metric_key: str) -> Dict:
    traces: List[Dict] = []
    aligned: List[List[float]] = []
    min_len = None

    for run in run_list:
        name, gov, years, series = _metric_series_for_run(run, metric_key)
        if not series:
            continue
        color = "#1f77b4" if gov == "human" else "#e76f51"
        traces.append(
            {
                "x": years,
                "y": series,
                "mode": "lines",
                "name": name,
                "line": {"color": color, "width": 1.6},
                "opacity": 0.35,
            }
        )
        aligned.append(series)
        min_len = len(series) if min_len is None else min(min_len, len(series))

    if not aligned or not min_len:
        return {"traces": traces, "mean": [], "min": [], "max": [], "x": []}

    cut = [s[:min_len] for s in aligned]
    x = list(range(1, min_len + 1))
    mean_vals: List[float] = []
    min_vals: List[float] = []
    max_vals: List[float] = []
    for i in range(min_len):
        col = [s[i] for s in cut]
        mean_vals.append(_mean(col))
        min_vals.append(min(col))
        max_vals.append(max(col))

    return {"traces": traces, "mean": mean_vals, "min": min_vals, "max": max_vals, "x": x}


def _group_band(run_list: List[Path], metric_key: str, governance_prefix: str) -> Dict:
    picked = [r for r in run_list if r.name.startswith(governance_prefix)]
    return _overlap_and_band(picked, metric_key)


def generate_report(run_dir: Path) -> Path:
    summary_path = run_dir / "summary.json"
    csv_path = run_dir / "metrics_timeseries.csv"

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rows = _read_csv(csv_path)

    years = [int(r["tick"]) for r in rows]
    mean_u = [float(r["mean_u"]) for r in rows]
    gini_e = [float(r["gini_e"]) for r in rows]
    eff = [float(r["efficiency"]) for r in rows]
    corruption = [float(r["corruption_rate"]) for r in rows]
    legitimacy = [float(r["legitimacy"]) for r in rows]
    info_mean = [float(r["info_mean"]) for r in rows]
    freedom = [float(r["std_m"]) + float(r["behavior_entropy"]) / 5.0 for r in rows]
    gdp = [float(r["produced"]) for r in rows]
    resources = [float(r["resources"]) for r in rows]
    shock = [int(r["shock"]) for r in rows]
    holders_90_ratio = [float(r.get("holders_90_ratio", 0.0)) for r in rows]
    class_low_ratio = [float(r.get("class_low_ratio", 0.0)) for r in rows]
    class_mid_ratio = [float(r.get("class_mid_ratio", 0.0)) for r in rows]
    class_high_ratio = [float(r.get("class_high_ratio", 0.0)) for r in rows]

    cumulative_gdp: List[float] = []
    s = 0.0
    for v in gdp:
        s += v
        cumulative_gdp.append(s)

    radar_labels = ["自由异质性", "廉洁度", "公平性", "幸福感", "效率", "合法性", "信息对称"]

    tail = rows[-50:] if len(rows) >= 50 else rows
    avg_freedom = _mean([float(x["std_m"]) + float(x["behavior_entropy"]) / 5.0 for x in tail])
    avg_corruption_clean = 1.0 - _mean([float(x["corruption_rate"]) for x in tail])
    avg_fairness = 1.0 - _mean([float(x["gini_e"]) for x in tail])
    avg_happiness = _mean([float(x["mean_u"]) for x in tail]) / 100.0
    avg_efficiency = _mean([float(x["efficiency"]) for x in tail])
    avg_legitimacy = _mean([float(x["legitimacy"]) for x in tail])
    avg_info = _mean([float(x["info_mean"]) for x in tail])

    eff_scale = max(1.0, max(eff) if eff else 1.0)
    radar_values = [
        _clamp01(avg_freedom),
        _clamp01(avg_corruption_clean),
        _clamp01(avg_fairness),
        _clamp01(avg_happiness),
        _clamp01(avg_efficiency / eff_scale),
        _clamp01(avg_legitimacy),
        _clamp01(avg_info),
    ]

    html = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>治理仿真报告</title>
  <script src=\"{PLOTLY_CDN}\"></script>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; margin: 24px; background: linear-gradient(135deg,#f8f4ec,#e8eef7); color:#1f2937; }}
    h1 {{ margin: 0 0 8px 0; }}
    .meta {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap:10px; margin: 14px 0 20px 0; }}
    .card {{ background:white; border-radius:10px; padding:10px 12px; box-shadow:0 1px 8px rgba(0,0,0,.08); }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .plot {{ background:white; border-radius:10px; padding:8px; box-shadow:0 1px 8px rgba(0,0,0,.08); min-height:340px; }}
    @media (max-width: 900px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>治理仿真报告</h1>
  <div>体制: <b>{summary.get('governance','unknown')}</b> | 种子: <b>{summary.get('seed','')}</b></div>
  <div class=\"meta\">
    <div class=\"card\">个体数量: {summary.get('n_agents','')}</div>
    <div class=\"card\">迭代轮次: {summary.get('n_ticks','')}</div>
    <div class=\"card\">近50轮平均幸福度: {summary.get('avg_mean_u',0):.2f}</div>
    <div class=\"card\">近50轮平均基尼: {summary.get('avg_gini_e',0):.4f}</div>
    <div class=\"card\">近50轮平均GDP(产出): {summary.get('avg_produced',0):.2f}</div>
    <div class=\"card\">近50轮平均人均效率: {summary.get('avg_efficiency',0):.4f}</div>
    <div class=\"card\">近50轮平均合法性: {summary.get('avg_legitimacy',0):.4f}</div>
    <div class=\"card\">近50轮平均腐败损失率: {summary.get('avg_corruption_rate',0):.4f}</div>
    <div class=\"card\">近50轮平均合法套利收益: {summary.get('avg_legal_arbitrage_gain',0):.4f}</div>
    <div class=\"card\">近50轮平均非法套利收益: {summary.get('avg_illegal_arbitrage_gain',0):.4f}</div>
    <div class=\"card\">近50轮平均非法侦测次数: {summary.get('avg_detected_illegal_cases',0):.4f}</div>
    <div class=\"card\">90%社会财富所需人口占比: {summary.get('avg_holders_90_ratio',0)*100:.2f}%</div>
    <div class=\"card\">高阶层占比(近50年均值): {summary.get('avg_class_high_ratio',0)*100:.2f}%</div>
    <div class=\"card\">中阶层占比(近50年均值): {summary.get('avg_class_mid_ratio',0)*100:.2f}%</div>
    <div class=\"card\">低阶层占比(近50年均值): {summary.get('avg_class_low_ratio',0)*100:.2f}%</div>
  </div>
  <div class=\"grid\">
    <div id=\"line1\" class=\"plot\"></div>
    <div id=\"line2\" class=\"plot\"></div>
    <div id=\"line3\" class=\"plot\"></div>
    <div id=\"line4\" class=\"plot\"></div>
    <div id=\"line5\" class=\"plot\"></div>
    <div id=\"line6\" class=\"plot\"></div>
    <div id=\"line7\" class=\"plot\"></div>
    <div id=\"radar\" class=\"plot\"></div>
  </div>
<script>
const years = {json.dumps(years)};
const meanU = {json.dumps(mean_u)};
const gini = {json.dumps(gini_e)};
const efficiency = {json.dumps(eff)};
const corruption = {json.dumps(corruption)};
const legitimacy = {json.dumps(legitimacy)};
const infoMean = {json.dumps(info_mean)};
const freedom = {json.dumps(freedom)};
const gdp = {json.dumps(gdp)};
const cumulativeGDP = {json.dumps(cumulative_gdp)};
const resources = {json.dumps(resources)};
const shock = {json.dumps(shock)};
const holders90 = {json.dumps(holders_90_ratio)};
const classLow = {json.dumps(class_low_ratio)};
const classMid = {json.dumps(class_mid_ratio)};
const classHigh = {json.dumps(class_high_ratio)};
const shockY = shock.map(v => v > 0 ? 100 : null);

Plotly.newPlot('line1', [
  {{x:years, y:meanU, mode:'lines', name:'平均幸福度 U'}},
  {{x:years, y:legitimacy.map(v=>v*100), mode:'lines', name:'合法性 L x100'}},
  {{x:years, y:shockY, mode:'markers', name:'冲击事件', marker:{{color:'#dc2626', size:5}}}}
], {{title:'幸福度与合法性', xaxis:{{title:'年份'}}, margin:{{t:40,r:20,b:40,l:40}}}});

Plotly.newPlot('line2', [
  {{x:years, y:gini, mode:'lines', name:'基尼系数 Gini(E)'}},
  {{x:years, y:corruption, mode:'lines', name:'腐败损失率'}}
], {{title:'公平与腐败', xaxis:{{title:'年份'}}, margin:{{t:40,r:20,b:40,l:40}}}});

Plotly.newPlot('line3', [
  {{x:years, y:efficiency, mode:'lines', name:'人均效率'}},
  {{x:years, y:infoMean, mode:'lines', name:'信息透明均值'}},
  {{x:years, y:freedom, mode:'lines', name:'自由异质性代理'}}
], {{title:'效率、信息、自由异质性', xaxis:{{title:'年份'}}, margin:{{t:40,r:20,b:40,l:40}}}});

Plotly.newPlot('line4', [
  {{x:years, y:gdp, mode:'lines', name:'当期GDP(产出)'}},
  {{x:years, y:cumulativeGDP, mode:'lines', name:'累计GDP'}}
], {{title:'GDP走势', xaxis:{{title:'年份'}}, margin:{{t:40,r:20,b:40,l:40}}}});

Plotly.newPlot('line5', [
  {{x:years, y:resources, mode:'lines', name:'社会总资源池 R(t)'}},
  {{x:years, y:gdp, mode:'lines', name:'当期GDP(产出)', yaxis:'y2'}}
], {{
  title:'资源池与当期GDP',
  xaxis:{{title:'年份'}},
  yaxis:{{title:'资源池'}},
  yaxis2:{{title:'当期GDP', overlaying:'y', side:'right'}},
  margin:{{t:40,r:20,b:40,l:40}}
}});

Plotly.newPlot('line6', [
  {{x:years, y:holders90.map(v=>v*100), mode:'lines', name:'掌握90%财富所需人口占比(%)'}}
], {{title:'财富集中度：90%社会财富集中到多少人手中', xaxis:{{title:'年份'}}, yaxis:{{title:'人口占比(%)'}}, margin:{{t:40,r:20,b:40,l:40}}}});

Plotly.newPlot('line7', [
  {{x:years, y:classLow.map(v=>v*100), mode:'lines', stackgroup:'one', name:'低阶层占比'}},
  {{x:years, y:classMid.map(v=>v*100), mode:'lines', stackgroup:'one', name:'中阶层占比'}},
  {{x:years, y:classHigh.map(v=>v*100), mode:'lines', stackgroup:'one', name:'高阶层占比'}}
], {{title:'社会阶层结构占比（高/中/低）', xaxis:{{title:'年份'}}, yaxis:{{title:'占比(%)', range:[0,100]}}, margin:{{t:40,r:20,b:40,l:40}}}});

Plotly.newPlot('radar', [{{
  type: 'scatterpolar',
  r: {json.dumps(radar_values + [radar_values[0]])},
  theta: {json.dumps(radar_labels + [radar_labels[0]])},
  fill: 'toself',
  name: '近50轮均值'
}}], {{title:'归一化雷达图', polar:{{radialaxis:{{visible:true, range:[0,1]}}}}, margin:{{t:40,r:20,b:40,l:20}}}});
</script>
</body>
</html>"""

    has_local_js = _ensure_local_plotly_asset(run_dir.parent)
    offline_src = "../_assets/" + PLOTLY_LOCAL_NAME if has_local_js else PLOTLY_CDN
    html_offline = html.replace(PLOTLY_CDN, offline_src)

    out = run_dir / "report.html"
    out.write_text(html, encoding="utf-8")
    out_offline = run_dir / "report_offline.html"
    out_offline.write_text(html_offline, encoding="utf-8")
    return out


def _collect_runs(out_dir: Path) -> List[Path]:
    runs: List[Path] = []
    if not out_dir.exists():
        return runs
    for p in out_dir.iterdir():
        if not p.is_dir():
            continue
        if (p / "summary.json").exists() and (p / "metrics_timeseries.csv").exists():
            runs.append(p)
    runs.sort(key=_run_sort_key, reverse=True)
    return runs


def _aggregate_stats(runs: List[Path]) -> Dict[str, float]:
    vals_u: List[float] = []
    vals_gdp: List[float] = []
    vals_gini: List[float] = []
    vals_legitimacy: List[float] = []
    vals_corruption: List[float] = []
    for run in runs:
        rows = _read_csv(run / "metrics_timeseries.csv")
        tail = rows[-50:] if len(rows) >= 50 else rows
        if not tail:
            continue
        vals_u.append(_mean([float(r["mean_u"]) for r in tail]))
        vals_gdp.append(_mean([float(r["produced"]) for r in tail]))
        vals_gini.append(_mean([float(r["gini_e"]) for r in tail]))
        vals_legitimacy.append(_mean([float(r["legitimacy"]) for r in tail]))
        vals_corruption.append(_mean([float(r["corruption_rate"]) for r in tail]))
    if not vals_u:
        return {"count": 0}
    return {
        "count": len(vals_u),
        "u_avg": _mean(vals_u),
        "u_min": min(vals_u),
        "u_max": max(vals_u),
        "gdp_avg": _mean(vals_gdp),
        "gdp_min": min(vals_gdp),
        "gdp_max": max(vals_gdp),
        "gini_avg": _mean(vals_gini),
        "gini_min": min(vals_gini),
        "gini_max": max(vals_gini),
        "leg_avg": _mean(vals_legitimacy),
        "leg_min": min(vals_legitimacy),
        "leg_max": max(vals_legitimacy),
        "cor_avg": _mean(vals_corruption),
        "cor_min": min(vals_corruption),
        "cor_max": max(vals_corruption),
    }


def generate_aggregate_report(out_dir: Path, filename: str = "aggregate_report.html") -> Path:
    runs = _collect_runs(out_dir)
    recent3 = runs[:3]
    recent10 = runs[:10]
    all_runs = runs

    stats3 = _aggregate_stats(recent3)
    stats10 = _aggregate_stats(recent10)
    stats_all = _aggregate_stats(all_runs)

    r3_u = _overlap_and_band(recent3, "mean_u")
    r3_gdp = _overlap_and_band(recent3, "produced")
    r3_gini = _overlap_and_band(recent3, "gini_e")
    r3_leg = _overlap_and_band(recent3, "legitimacy")
    r10_u = _overlap_and_band(recent10, "mean_u")
    r10_gdp = _overlap_and_band(recent10, "produced")
    r10_gini = _overlap_and_band(recent10, "gini_e")
    r10_leg = _overlap_and_band(recent10, "legitimacy")
    all_u = _overlap_and_band(all_runs, "mean_u")
    all_gdp = _overlap_and_band(all_runs, "produced")
    all_gini = _overlap_and_band(all_runs, "gini_e")
    all_leg = _overlap_and_band(all_runs, "legitimacy")

    ai_like_runs = [r for r in all_runs if r.name.startswith("ai_") or r.name.startswith("ai_strong_")]
    human_u = _group_band(all_runs, "mean_u", "human_")
    ai_u = _overlap_and_band(ai_like_runs, "mean_u")
    human_gdp = _group_band(all_runs, "produced", "human_")
    ai_gdp = _overlap_and_band(ai_like_runs, "produced")
    human_gini = _group_band(all_runs, "gini_e", "human_")
    ai_gini = _overlap_and_band(ai_like_runs, "gini_e")
    human_leg = _group_band(all_runs, "legitimacy", "human_")
    ai_leg = _overlap_and_band(ai_like_runs, "legitimacy")

    human_count = len([r for r in all_runs if r.name.startswith("human_")])
    ai_count = len([r for r in all_runs if r.name.startswith("ai_") or r.name.startswith("ai_strong_")])

    html = f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>治理仿真综合分析报告</title>
  <script src=\"{PLOTLY_CDN}\"></script>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; margin: 24px; background: linear-gradient(135deg,#f8f4ec,#e8eef7); color:#1f2937; }}
    h1 {{ margin: 0 0 8px 0; }}
    .hint {{ margin-bottom: 14px; color:#374151; }}
    .meta {{ display:grid; grid-template-columns: repeat(auto-fit,minmax(260px,1fr)); gap:10px; margin: 14px 0 20px 0; }}
    .card {{ background:white; border-radius:10px; padding:10px 12px; box-shadow:0 1px 8px rgba(0,0,0,.08); }}
    .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .plot {{ background:white; border-radius:10px; padding:8px; box-shadow:0 1px 8px rgba(0,0,0,.08); min-height:360px; }}
    @media (max-width: 1000px) {{ .grid {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <h1>治理仿真综合分析报告</h1>
  <div class=\"hint\">自动扫描当前输出目录中的有效运行数据。删除某次运行后，重新生成将自动反映变化（同名覆盖）。</div>
  <div class=\"meta\">
    <div class=\"card\">统计时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
    <div class=\"card\">纳入运行总数: {len(all_runs)}</div>
    <div class=\"card\">最近3次: {len(recent3)} | 最近10次: {len(recent10)}</div>
    <div class=\"card\">体制样本: 人治 {human_count} / AI治理 {ai_count}</div>
    <div class=\"card\">综合报告文件: {filename}</div>
  </div>

  <div class=\"meta\">
    <div class=\"card\"><b>最近3次（近50年）</b><br/>幸福均值: {stats3.get('u_avg',0):.2f}（{stats3.get('u_min',0):.2f}~{stats3.get('u_max',0):.2f}）<br/>GDP均值: {stats3.get('gdp_avg',0):.2f}（{stats3.get('gdp_min',0):.2f}~{stats3.get('gdp_max',0):.2f}）<br/>基尼均值: {stats3.get('gini_avg',0):.4f}（{stats3.get('gini_min',0):.4f}~{stats3.get('gini_max',0):.4f}）<br/>合法性均值: {stats3.get('leg_avg',0):.4f}（{stats3.get('leg_min',0):.4f}~{stats3.get('leg_max',0):.4f}）</div>
    <div class=\"card\"><b>最近10次（近50年）</b><br/>幸福均值: {stats10.get('u_avg',0):.2f}（{stats10.get('u_min',0):.2f}~{stats10.get('u_max',0):.2f}）<br/>GDP均值: {stats10.get('gdp_avg',0):.2f}（{stats10.get('gdp_min',0):.2f}~{stats10.get('gdp_max',0):.2f}）<br/>基尼均值: {stats10.get('gini_avg',0):.4f}（{stats10.get('gini_min',0):.4f}~{stats10.get('gini_max',0):.4f}）<br/>合法性均值: {stats10.get('leg_avg',0):.4f}（{stats10.get('leg_min',0):.4f}~{stats10.get('leg_max',0):.4f}）</div>
    <div class=\"card\"><b>全部运行（近50年）</b><br/>幸福均值: {stats_all.get('u_avg',0):.2f}（{stats_all.get('u_min',0):.2f}~{stats_all.get('u_max',0):.2f}）<br/>GDP均值: {stats_all.get('gdp_avg',0):.2f}（{stats_all.get('gdp_min',0):.2f}~{stats_all.get('gdp_max',0):.2f}）<br/>基尼均值: {stats_all.get('gini_avg',0):.4f}（{stats_all.get('gini_min',0):.4f}~{stats_all.get('gini_max',0):.4f}）<br/>合法性均值: {stats_all.get('leg_avg',0):.4f}（{stats_all.get('leg_min',0):.4f}~{stats_all.get('leg_max',0):.4f}）</div>
  </div>

  <div class=\"grid\">
    <div id=\"plot3u\" class=\"plot\"></div>
    <div id=\"plot3gdp\" class=\"plot\"></div>
    <div id=\"plot3gini\" class=\"plot\"></div>
    <div id=\"plot3leg\" class=\"plot\"></div>
    <div id=\"plot10u\" class=\"plot\"></div>
    <div id=\"plot10gdp\" class=\"plot\"></div>
    <div id=\"plot10gini\" class=\"plot\"></div>
    <div id=\"plot10leg\" class=\"plot\"></div>
    <div id=\"plotallu\" class=\"plot\"></div>
    <div id=\"plotallgdp\" class=\"plot\"></div>
    <div id=\"plotallgini\" class=\"plot\"></div>
    <div id=\"plotallleg\" class=\"plot\"></div>
    <div id=\"plotGovU\" class=\"plot\"></div>
    <div id=\"plotGovGDP\" class=\"plot\"></div>
    <div id=\"plotGovGini\" class=\"plot\"></div>
    <div id=\"plotGovLeg\" class=\"plot\"></div>
  </div>

<script>
function mergeOverlap(payload, labelPrefix) {{
  const minTrace = {{x: payload.x, y: payload.min, mode:'lines', line:{{width:0}}, hoverinfo:'skip', showlegend:false, name: labelPrefix+'最小值'}};
  const maxTrace = {{x: payload.x, y: payload.max, mode:'lines', fill:'tonexty', fillcolor:'rgba(100,116,139,0.15)', line:{{width:0}}, hoverinfo:'skip', showlegend:true, name: labelPrefix+'极值带(最小~最大)'}};
  const meanTrace = {{x: payload.x, y: payload.mean, mode:'lines', line:{{color:'#111827', width:3}}, name: labelPrefix+'平均值'}};
  return payload.traces.concat([minTrace, maxTrace, meanTrace]);
}}

const r3u = {json.dumps(r3_u)};
const r3gdp = {json.dumps(r3_gdp)};
const r3gini = {json.dumps(r3_gini)};
const r3leg = {json.dumps(r3_leg)};
const r10u = {json.dumps(r10_u)};
const r10gdp = {json.dumps(r10_gdp)};
const r10gini = {json.dumps(r10_gini)};
const r10leg = {json.dumps(r10_leg)};
const allu = {json.dumps(all_u)};
const allgdp = {json.dumps(all_gdp)};
const allgini = {json.dumps(all_gini)};
const allleg = {json.dumps(all_leg)};
const humanU = {json.dumps(human_u)};
const aiU = {json.dumps(ai_u)};
const humanGDP = {json.dumps(human_gdp)};
const aiGDP = {json.dumps(ai_gdp)};
const humanGini = {json.dumps(human_gini)};
const aiGini = {json.dumps(ai_gini)};
const humanLeg = {json.dumps(human_leg)};
const aiLeg = {json.dumps(ai_leg)};

function pairBand(h, a, nameH, nameA) {{
  const hMin = {{x:h.x, y:h.min, mode:'lines', line:{{width:0}}, showlegend:false, hoverinfo:'skip'}};
  const hMax = {{x:h.x, y:h.max, mode:'lines', fill:'tonexty', fillcolor:'rgba(31,119,180,0.14)', line:{{width:0}}, name:nameH+'极值带'}};
  const hMean = {{x:h.x, y:h.mean, mode:'lines', line:{{color:'#1f77b4', width:3}}, name:nameH+'均值'}};
  const aMin = {{x:a.x, y:a.min, mode:'lines', line:{{width:0}}, showlegend:false, hoverinfo:'skip'}};
  const aMax = {{x:a.x, y:a.max, mode:'lines', fill:'tonexty', fillcolor:'rgba(231,111,81,0.14)', line:{{width:0}}, name:nameA+'极值带'}};
  const aMean = {{x:a.x, y:a.mean, mode:'lines', line:{{color:'#e76f51', width:3}}, name:nameA+'均值'}};
  return [hMin,hMax,hMean,aMin,aMax,aMean];
}}

Plotly.newPlot('plot3u', mergeOverlap(r3u, '最近3次-幸福度'), {{title:'最近3次：幸福度（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'幸福度 U'}}}});
Plotly.newPlot('plot3gdp', mergeOverlap(r3gdp, '最近3次-GDP'), {{title:'最近3次：GDP（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'GDP(产出)'}}}});
Plotly.newPlot('plot3gini', mergeOverlap(r3gini, '最近3次-基尼'), {{title:'最近3次：基尼（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'Gini(E)'}}}});
Plotly.newPlot('plot3leg', mergeOverlap(r3leg, '最近3次-合法性'), {{title:'最近3次：合法性（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'Legitimacy'}}}});
Plotly.newPlot('plot10u', mergeOverlap(r10u, '最近10次-幸福度'), {{title:'最近10次：幸福度（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'幸福度 U'}}}});
Plotly.newPlot('plot10gdp', mergeOverlap(r10gdp, '最近10次-GDP'), {{title:'最近10次：GDP（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'GDP(产出)'}}}});
Plotly.newPlot('plot10gini', mergeOverlap(r10gini, '最近10次-基尼'), {{title:'最近10次：基尼（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'Gini(E)'}}}});
Plotly.newPlot('plot10leg', mergeOverlap(r10leg, '最近10次-合法性'), {{title:'最近10次：合法性（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'Legitimacy'}}}});
Plotly.newPlot('plotallu', mergeOverlap(allu, '全部运行-幸福度'), {{title:'全部运行：幸福度（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'幸福度 U'}}}});
Plotly.newPlot('plotallgdp', mergeOverlap(allgdp, '全部运行-GDP'), {{title:'全部运行：GDP（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'GDP(产出)'}}}});
Plotly.newPlot('plotallgini', mergeOverlap(allgini, '全部运行-基尼'), {{title:'全部运行：基尼（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'Gini(E)'}}}});
Plotly.newPlot('plotallleg', mergeOverlap(allleg, '全部运行-合法性'), {{title:'全部运行：合法性（重叠 + 均值 + 极值）', xaxis:{{title:'年份'}}, yaxis:{{title:'Legitimacy'}}}});
Plotly.newPlot('plotGovU', pairBand(humanU, aiU, '人治', 'AI治理'), {{title:'体制分组对比：幸福度（均值+极值带）', xaxis:{{title:'年份'}}, yaxis:{{title:'幸福度 U'}}}});
Plotly.newPlot('plotGovGDP', pairBand(humanGDP, aiGDP, '人治', 'AI治理'), {{title:'体制分组对比：GDP（均值+极值带）', xaxis:{{title:'年份'}}, yaxis:{{title:'GDP(产出)'}}}});
Plotly.newPlot('plotGovGini', pairBand(humanGini, aiGini, '人治', 'AI治理'), {{title:'体制分组对比：基尼（均值+极值带）', xaxis:{{title:'年份'}}, yaxis:{{title:'Gini(E)'}}}});
Plotly.newPlot('plotGovLeg', pairBand(humanLeg, aiLeg, '人治', 'AI治理'), {{title:'体制分组对比：合法性（均值+极值带）', xaxis:{{title:'年份'}}, yaxis:{{title:'Legitimacy'}}}});
</script>
</body>
</html>"""

    out = out_dir / filename
    out.write_text(html, encoding="utf-8")
    has_local_js = _ensure_local_plotly_asset(out_dir)
    offline_src = "_assets/" + PLOTLY_LOCAL_NAME if has_local_js else PLOTLY_CDN
    html_offline = html.replace(PLOTLY_CDN, offline_src)
    out_offline = out_dir / "aggregate_report_offline.html"
    out_offline.write_text(html_offline, encoding="utf-8")
    return out
