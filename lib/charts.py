"""Plotly 헬퍼 — 일관된 차트 스타일(최소 그리드, 호버 툴팁, 한글 폰트)."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# 검증된 범주형 팔레트(고정 순서). 색은 지표 순서가 아니라 선택 순서를 따른다.
SERIES = {
    "light": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"],
    "dark": ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#0ca30c", "#9085e9", "#e66767"],
}
SURFACE = {"light": "#fcfcfb", "dark": "#1a1a19"}
TEXT = {"light": "#0b0b0b", "dark": "#f0efec"}
TEXT2 = {"light": "#52514e", "dark": "#c3c2b7"}
GRID = {"light": "#e1e0d9", "dark": "#2c2c2a"}
AXIS = {"light": "#c3c2b7", "dark": "#383835"}
UP = {"light": "#d03b3b", "dark": "#e66767"}  # 국내 관례: 상승=빨강
DOWN = {"light": "#2a78d6", "dark": "#3987e5"}  # 하락=파랑
MID = {"light": "#f0efec", "dark": "#383835"}
FONT = "Pretendard, -apple-system, 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif"
PLOT_CONFIG = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


def mode() -> str:
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:
        return "light"


def show(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOT_CONFIG)


def style(fig: go.Figure, title: str | None = None, height: int = 400, legend: bool = True) -> go.Figure:
    m = mode()
    fig.update_layout(
        height=height,
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15, color=TEXT[m])) if title else None,
        font=dict(family=FONT, color=TEXT2[m], size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=8, t=56 if title else 24, b=8),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=SURFACE[m], bordercolor=AXIS[m], font=dict(family=FONT, color=TEXT[m])),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="right", x=1, font=dict(color=TEXT[m])),
    )
    fig.update_xaxes(showgrid=False, linecolor=AXIS[m], showspikes=True, spikemode="across",
                     spikethickness=1, spikedash="solid", spikecolor=AXIS[m])
    fig.update_yaxes(gridcolor=GRID[m], zeroline=False)
    return fig


def add_range_slider(fig: go.Figure) -> go.Figure:
    m = mode()
    fig.update_xaxes(
        rangeslider=dict(visible=True, thickness=0.06, bgcolor="rgba(0,0,0,0)", bordercolor=GRID[m]),
        rangeselector=dict(
            buttons=[dict(count=1, label="1Y", step="year", stepmode="backward"),
                     dict(count=3, label="3Y", step="year", stepmode="backward"),
                     dict(count=5, label="5Y", step="year", stepmode="backward"),
                     dict(count=10, label="10Y", step="year", stepmode="backward"),
                     dict(step="all", label="전체")],
            bgcolor=GRID[m], activecolor=AXIS[m], font=dict(color=TEXT[m]), x=0, y=1.0, yanchor="bottom",
        ),
    )
    fig.update_layout(margin=dict(t=max(fig.layout.margin.t or 0, 56) + 28))
    return fig


def _trace(kind: str, x, y, name: str, color: str, unit: str, yaxis: str = "y", step: bool = False):
    hover = f"%{{y:,.2f}} {unit}<extra>{name}</extra>"
    if kind == "막대":
        return go.Bar(x=x, y=y, name=name, marker=dict(color=color, line=dict(width=0)), hovertemplate=hover,
                      yaxis=yaxis)
    return go.Scatter(
        x=x, y=y, name=name, mode="lines", yaxis=yaxis, hovertemplate=hover, connectgaps=True,
        line=dict(width=2, color=color, shape="hv" if step else "linear"),
        fill="tozeroy" if kind == "영역" else None,
        fillcolor=color + "22" if kind == "영역" else None,
    )


def series_chart(df: pd.DataFrame, units: dict[str, str], kind: str = "라인", title: str | None = None,
                 slider: bool = True, height: int = 420, colors: dict[str, str] | None = None) -> go.Figure:
    """한 DataFrame의 여러 컬럼을 한 축에 그린다 (같은 단위끼리)."""
    m = mode()
    fig = go.Figure()
    for i, col in enumerate(df.columns):
        s = df[col].dropna()
        color = (colors or {}).get(col, SERIES[m][i % len(SERIES[m])])
        fig.add_trace(_trace(kind, s.index, s.values, col, color, units.get(col, ""), step="기준금리" in col))
    style(fig, title, height, legend=len(df.columns) > 1)
    uniq = {u for u in units.values() if u}
    if len(uniq) == 1:
        fig.update_yaxes(title_text=uniq.pop(), title_font=dict(size=11))
    if kind == "막대":
        fig.update_layout(bargap=0.2, barmode="group")
    if slider:
        add_range_slider(fig)
    elif len(df.columns) > 1:
        # 작은 차트는 범례가 제목과 겹치지 않도록 아래로
        fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.12, xanchor="left", x=0),
                          margin=dict(b=40))
    return fig


def dual_axis_chart(series: dict[str, pd.Series], units: dict[str, str], title: str | None = None) -> go.Figure:
    """첫 번째 지표는 왼쪽 축, 나머지는 오른쪽 축."""
    m = mode()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for i, (name, s) in enumerate(series.items()):
        s = s.dropna()
        fig.add_trace(_trace("라인", s.index, s.values, name, SERIES[m][i], units.get(name, "")),
                      secondary_y=i > 0)
    style(fig, title, 460)
    names = list(series)
    fig.update_yaxes(title_text=f"{names[0]} ({units.get(names[0], '')})", secondary_y=False,
                     title_font=dict(size=11, color=SERIES[m][0]))
    right = " · ".join(names[1:])
    fig.update_yaxes(title_text=right, secondary_y=True, showgrid=False, title_font=dict(size=11, color=TEXT2[m]))
    return add_range_slider(fig)


def signed_bar(s: pd.Series, name: str, unit: str, title: str | None = None, height: int = 360) -> go.Figure:
    """부호가 의미 있는 값: 양수=빨강, 음수=파랑."""
    m = mode()
    s = s.dropna()
    fig = go.Figure(go.Bar(x=s.index, y=s.values, name=name, hovertemplate=f"%{{y:,.2f}} {unit}<extra>{name}</extra>",
                           marker=dict(color=[UP[m] if v >= 0 else DOWN[m] for v in s.values], line=dict(width=0))))
    style(fig, title, height, legend=False)
    fig.add_hline(y=0, line_width=1, line_color=AXIS[m])
    fig.update_layout(bargap=0.2)
    fig.update_yaxes(title_text=unit, title_font=dict(size=11))
    return fig


def heatmap(corr: pd.DataFrame, title: str | None = None) -> go.Figure:
    m = mode()
    fig = go.Figure(go.Heatmap(
        z=corr.values, x=list(corr.columns), y=list(corr.index), zmin=-1, zmax=1,
        colorscale=[[0, SERIES[m][0]], [0.5, MID[m]], [1, UP[m]]],
        text=corr.round(2).values, texttemplate="%{text}", textfont=dict(family=FONT, size=13),
        hovertemplate="%{y} × %{x}<br>상관계수 %{z:.2f}<extra></extra>", xgap=2, ygap=2,
        colorbar=dict(thickness=10, outlinewidth=0, tickfont=dict(color=TEXT2[m])),
    ))
    style(fig, title, 120 + 70 * len(corr), legend=False)
    fig.update_layout(hovermode="closest")
    fig.update_xaxes(showspikes=False, linecolor="rgba(0,0,0,0)")
    fig.update_yaxes(showspikes=False, autorange="reversed", gridcolor="rgba(0,0,0,0)")
    return fig
