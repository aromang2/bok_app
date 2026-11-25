"""비교 분석: 최대 4개 지표 중첩·이중 축·정규화(기준=100), 상관관계 히트맵."""

import pandas as pd
import streamlit as st

from lib import charts
from lib.data import INDICATORS, load_many, show_error, unit_of
from lib.ui import clip, period_slider

st.title("비교 분석")

# '지표 › 컬럼' 단위로 선택
options = {f"{ind.name} › {col.name}" if len(ind.columns) > 1 else ind.name: (ind.id, col.name)
           for ind in INDICATORS.values() for col in ind.columns}
default = [k for k in options if options[k][1] in ("원/달러", "국고채(3년)", "코스피")][:3]
picked = st.multiselect("비교할 지표 (최대 4개)", list(options), default=default, max_selections=4)

if not picked:
    st.info("비교할 지표를 선택하세요.")
    st.stop()

with st.spinner("ECOS에서 데이터를 불러오는 중..."):
    data, errors = load_many(tuple(sorted({options[p][0] for p in picked})))
show_error(errors)

series: dict[str, pd.Series] = {}
units: dict[str, str] = {}
for p in picked:
    ind_id, col = options[p]
    if ind_id in data and col in data[ind_id]:
        series[p] = data[ind_id][col].dropna()
        units[p] = unit_of(ind_id, col)
if not series:
    st.stop()

lo = min(s.index.min() for s in series.values())
hi = max(s.index.max() for s in series.values())
c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
with c1:
    period = period_slider(lo, hi, key="cmp_period", default_years=5)
with c2:
    how = st.segmented_control("표시 방식", ["중첩", "이중 축", "정규화 (기준=100)"], default="정규화 (기준=100)") \
        or "정규화 (기준=100)"

view = {k: clip(s, period) for k, s in series.items()}
view = {k: s for k, s in view.items() if not s.empty}

if how == "중첩":
    if len(set(units[k] for k in view)) > 1:
        st.caption("⚠️ 단위가 서로 다른 지표가 한 축에 그려집니다. 단위가 다르면 '정규화'나 '이중 축'이 더 정확합니다.")
    charts.show(charts.series_chart(pd.DataFrame(view), units, title="지표 비교"))
elif how == "이중 축":
    st.caption("첫 번째 지표는 왼쪽 축, 나머지는 오른쪽 축에 표시됩니다. 축 눈금이 달라 겹침·교차는 의미가 없으니 추세 방향만 비교하세요.")
    charts.show(charts.dual_axis_chart(view, units, title="지표 비교 — 이중 축"))
else:
    norm, skipped = {}, []
    for k, s in view.items():
        if (s <= 0).any():
            skipped.append(k)
        else:
            norm[k] = s / s.iloc[0] * 100
    if norm:
        charts.show(charts.series_chart(pd.DataFrame(norm), {k: "기준=100" for k in norm},
                                        title=f"지표 비교 — {period[0]:%Y-%m} = 100"))
    if skipped:
        st.caption(f"0 이하 값이 있어 정규화할 수 없는 지표는 제외했습니다: {', '.join(skipped)}")

# ---------------------------------------------------------------- 상관관계
st.subheader("상관관계 히트맵")
st.caption("선택 기간의 월평균 기준 피어슨 상관계수 (분기·연 지표는 다음 값까지 채움)")
if len(view) < 2:
    st.info("상관분석에는 지표가 2개 이상 필요합니다.")
else:
    monthly = pd.DataFrame({k: s.resample("MS").mean() for k, s in view.items()}).ffill(limit=11)
    corr = monthly.corr(min_periods=6)
    charts.show(charts.heatmap(corr))
    st.download_button("⬇️ 비교 데이터 CSV (월평균)", monthly.to_csv().encode("utf-8-sig"),
                       file_name=f"ecos_compare_{period[0]:%Y%m}_{period[1]:%Y%m}.csv", mime="text/csv")
