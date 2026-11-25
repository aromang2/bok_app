"""카테고리 대시보드: 사전 구성 뷰(금리 곡선·스프레드, 환율 4종, 물가 3종) + 카테고리 전체 지표."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from lib import charts
from lib.data import CATEGORIES, INDICATORS, load_many, show_error, unit_of
from lib.ui import clip

st.title("카테고리 대시보드")

if st.session_state.get("category") not in CATEGORIES:
    st.session_state["category"] = "금리"
cat = st.pills("카테고리", list(CATEGORIES), key="category", label_visibility="collapsed") or "금리"
years = st.segmented_control("기간", ["1Y", "3Y", "5Y", "10Y", "전체"], default="5Y", key="cat_years") or "5Y"

ids = CATEGORIES[cat]
with st.spinner("ECOS에서 데이터를 불러오는 중..."):
    data, errors = load_many(tuple(ids))
show_error(errors)

end = pd.Timestamp.today().normalize()
start = pd.Timestamp("1900-01-01") if years == "전체" else end - pd.DateOffset(years=int(years[:-1]))
period = (start, end)
m = charts.mode()


def col(ind_id: str, name: str) -> pd.Series:
    df = data.get(ind_id)
    return df[name].dropna() if df is not None and name in df else pd.Series(dtype=float)


# ---------------------------------------------------------------- 사전 구성 뷰
if cat == "금리" and "rate_short" in data and "rate_long" in data:
    st.subheader("금리 곡선")
    curve_pts = [("rate_short", "콜금리(익일물)", "익일"), ("rate_short", "CD(91일)", "3개월"),
                 ("rate_long", "통안증권(1년)", "1년"), ("rate_long", "국고채(3년)", "3년"),
                 ("rate_long", "국고채(5년)", "5년"), ("rate_long", "국고채(10년)", "10년")]
    c1, c2 = st.columns(2)
    with c1:
        fig = go.Figure()
        for i, (label, offset) in enumerate([("최근", 0), ("1년 전", 1)]):
            xs, ys = [], []
            for ind_id, name, tenor in curve_pts:
                s = col(ind_id, name)
                s = s[s.index <= end - pd.DateOffset(years=offset)]
                if not s.empty:
                    xs.append(tenor)
                    ys.append(s.iloc[-1])
            fig.add_trace(go.Scatter(x=xs, y=ys, name=label, mode="lines+markers",
                                     line=dict(width=2, color=charts.SERIES[m][i], dash="solid" if i == 0 else "dot"),
                                     marker=dict(size=8), hovertemplate="%{x}: %{y:.3f}%<extra>" + label + "</extra>"))
        charts.style(fig, "만기별 금리 (최근 vs 1년 전)", 380)
        fig.update_layout(hovermode="closest")
        fig.update_yaxes(title_text="%")
        charts.show(fig)
    with c2:
        long_, short_ = col("rate_long", "국고채(10년)"), col("rate_long", "국고채(3년)")
        spread = (long_ - short_).dropna() * 100
        charts.show(charts.signed_bar(clip(spread, period).resample("MS").mean(), "장단기 스프레드", "bp",
                                      title="장단기 스프레드 (국고채 10년 − 3년, 월평균)", height=380))

elif cat == "환율·시장" and "fx_major" in data:
    st.subheader("환율 4종 비교")
    fx = clip(data["fx_major"], period)
    names = [c for c in ["원/달러", "원/100엔", "원/유로", "원/위안"] if c in fx]
    fig = make_subplots(rows=2, cols=2, shared_xaxes=True, subplot_titles=names, vertical_spacing=0.12)
    for i, name in enumerate(names):
        s = fx[name].dropna()
        fig.add_trace(go.Scatter(x=s.index, y=s.values, name=name, mode="lines",
                                 line=dict(width=2, color=charts.SERIES[m][i]),
                                 hovertemplate="%{y:,.2f}원<extra>" + name + "</extra>"),
                      row=i // 2 + 1, col=i % 2 + 1)
    charts.style(fig, None, 560, legend=False)
    fig.update_annotations(font=dict(size=13, color=charts.TEXT[m]))
    charts.show(fig)

elif cat == "물가·자산" and "cpi" in data:
    st.subheader("물가 3종 추이")
    cpi = clip(data["cpi"], period)
    fig = charts.series_chart(cpi, {c: "%" for c in cpi}, title="소비자물가 상승률 (전년동월비)", slider=False)
    fig.add_hline(y=2, line_dash="dot", line_color=charts.TEXT2[m], annotation_text="물가안정목표 2%",
                  annotation_position="top left")
    charts.show(fig)

# ---------------------------------------------------------------- 카테고리 전체 지표
st.subheader(f"{cat} 전체 지표")
cols = st.columns(2)
for i, ind_id in enumerate(ids):
    if ind_id not in data:
        continue
    ind = INDICATORS[ind_id]
    df = clip(data[ind_id], period)
    with cols[i % 2]:
        units = {c: unit_of(ind_id, c) for c in df.columns}
        if len(set(units.values())) > 1:  # 단위가 섞이면 첫 단위 그룹만, 나머지는 탐색기에서
            first = next(iter(units.values()))
            df = df[[c for c in df.columns if units[c] == first]]
        if ind.signed and len(df.columns) == 1:
            fig = charts.signed_bar(df.iloc[:, 0], df.columns[0], units[df.columns[0]], title=ind.name, height=320)
        else:
            fig = charts.series_chart(df, units, title=ind.name, slider=False, height=320)
        charts.show(fig)
        if st.button("탐색기에서 자세히", key=f"exp-{ind_id}"):
            st.session_state["explore_id"] = ind_id
            st.switch_page("pages/explorer.py")
