"""페이지 공용 UI 조각."""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from lib import charts
from lib.data import FREQ_LABEL, infer_freq

DELTA_LABEL = {"D": "전일 대비", "M": "전월 대비", "Q": "전기 대비", "A": "전년 대비"}
SPARK_POINTS = {"D": 90, "M": 24, "Q": 16, "A": 12}


def period_slider(start: pd.Timestamp, end: pd.Timestamp, key: str, default_years: int = 10) -> tuple:
    """데이터 범위 안에서 조회 기간을 고르는 슬라이더."""
    lo, hi = start.date(), end.date()
    default_lo = max(lo, date(hi.year - default_years, hi.month, 1))
    return st.slider("기간", min_value=lo, max_value=hi, value=(default_lo, hi), format="YYYY-MM", key=key)


def clip(df: pd.DataFrame | pd.Series, period: tuple) -> pd.DataFrame | pd.Series:
    return df.loc[pd.Timestamp(period[0]) : pd.Timestamp(period[1])]


def fmt_when(ts: pd.Timestamp, freq: str) -> str:
    if freq == "D":
        return ts.strftime("%Y-%m-%d")
    if freq == "Q":
        return f"{ts.year} Q{(ts.month - 1) // 3 + 1}"
    if freq == "A":
        return f"{ts.year}"
    return ts.strftime("%Y-%m")


def kpi(s: pd.Series, title: str, unit: str, decimals: int = 2) -> None:
    """최신값 + 전기 대비 증감(▲빨강 ▼파랑) + 스파크라인."""
    s = s.dropna()
    if s.empty:
        st.metric(title, "—", border=True)
        return
    freq = infer_freq(s.index)
    last = s.iloc[-1]
    delta = float(last - s.iloc[-2]) if len(s) > 1 else 0.0
    color = "red" if delta > 0 else "blue" if delta < 0 else "gray"
    st.metric(
        f"{title}",
        f"{last:,.{decimals}f} {unit}".strip(),
        delta=f"{delta:+,.{decimals}f}" if delta else "변동 없음",
        delta_color=color,
        delta_description=f"{DELTA_LABEL[freq]} · {fmt_when(s.index[-1], freq)}",
        chart_data=s.iloc[-SPARK_POINTS[freq]:].round(4).tolist(),
        chart_type="line",
        border=True,
        help=f"주기: {FREQ_LABEL[freq]} · 단위: {unit or '—'}",
    )


def chart_kind(key: str) -> str:
    return st.segmented_control("차트", ["라인", "영역", "막대"], default="라인", key=key) or "라인"


def mode() -> str:
    return charts.mode()
