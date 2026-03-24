from __future__ import annotations
import io
import json
import pandas as pd
import plotly.graph_objects as go
from jinja2 import Template

from app.models.schemas import ChartType, DatasetSchema

HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>VEDA - Dataset Report</title>
<style>
  body { background: #0d1117; color: #c9d1d9; font-family: 'Consolas', 'Courier New', monospace; padding: 2rem; }
  h1 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 0.5rem; }
  h2 { color: #79c0ff; }
  .insight { background: #161b22; border-left: 3px solid #f0883e; padding: 0.8rem 1rem; margin: 0.5rem 0; border-radius: 4px; }
  .insight.critical { border-left-color: #f85149; }
  .insight.warning { border-left-color: #d29922; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
  th, td { border: 1px solid #30363d; padding: 0.5rem; text-align: right; }
  th { background: #161b22; color: #58a6ff; }
  .chart-container { margin: 1rem 0; }
</style>
</head>
<body>
<h1>VEDA Report</h1>
<h2>Summary</h2>
<p>{{ summary }}</p>
<h2>Insights</h2>
{% for item in insights %}
<div class="insight {{ item.severity }}">
  <strong>{{ item.title }}</strong>
  <p>{{ item.description }}</p>
</div>
{% endfor %}
<h2>Statistics</h2>
<table>
<tr><th>Column</th><th>Count</th><th>Mean</th><th>Std</th><th>Min</th><th>Max</th><th>Median</th></tr>
{% for col, s in stats.items() %}
<tr>
  <td style="text-align:left">{{ col }}</td>
  <td>{{ s.count }}</td>
  <td>{{ s.mean }}</td>
  <td>{{ s.std }}</td>
  <td>{{ s.min }}</td>
  <td>{{ s.max }}</td>
  <td>{{ s.median }}</td>
</tr>
{% endfor %}
</table>
{% if chart_html %}
<h2>Chart</h2>
<div class="chart-container">{{ chart_html }}</div>
{% endif %}
</body>
</html>""")


def export_chart_png(chart_data: dict, chart_type: str = "line") -> bytes:
    fig = _build_figure(chart_data, chart_type)
    return fig.to_image(format="png", width=1400, height=700, scale=2)


def export_metrics_csv(stats: dict) -> bytes:
    rows = []
    for col, s in stats.items():
        row = {"column": col, **s}
        rows.append(row)
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def export_report_html(
    chart_data: dict,
    chart_type: str,
    stats: dict,
    insights: list[dict],
    summary: str,
) -> str:
    fig = _build_figure(chart_data, chart_type)
    chart_html = fig.to_html(include_plotlyjs="cdn", full_html=False)

    return HTML_TEMPLATE.render(
        summary=summary,
        insights=insights,
        stats=stats,
        chart_html=chart_html,
    )


def _build_figure(chart_data: dict, chart_type: str) -> go.Figure:
    fig = go.Figure()
    x = chart_data.get("x", [])

    if chart_type in ("ohlc", "candlestick") and "ohlc" in chart_data:
        ohlc = chart_data["ohlc"]
        trace_cls = go.Ohlc if chart_type == "ohlc" else go.Candlestick
        fig.add_trace(trace_cls(
            x=x,
            open=ohlc.get("open", []),
            high=ohlc.get("high", []),
            low=ohlc.get("low", []),
            close=ohlc.get("close", []),
            name="OHLC",
        ))
    else:
        for name, values in chart_data.get("series", {}).items():
            fig.add_trace(go.Scatter(x=x, y=values, mode="lines", name=name))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        font=dict(family="Consolas, Courier New, monospace", color="#c9d1d9"),
        xaxis=dict(gridcolor="#21262d"),
        yaxis=dict(gridcolor="#21262d"),
        margin=dict(l=50, r=30, t=40, b=40),
    )
    return fig
