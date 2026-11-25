"""지표 탐색기: 카테고리 → 지표 → 컬럼 선택, 기간 슬라이더, 차트 전환, 원본 테이블·CSV."""

import streamlit as st

from lib import charts
from lib.data import CATEGORIES, FREQ_LABEL, INDICATORS, infer_freq, load, search, show_error, unit_of
from lib.ecos import EcosError
from lib.ui import chart_kind, clip, kpi, period_slider

st.title("지표 탐색기")

# 홈/검색에서 넘어온 지표가 있으면 미리 선택
pre = st.session_state.pop("explore_id", None)
if pre in INDICATORS:
    st.session_state["exp_cat"] = INDICATORS[pre].category
    st.session_state["exp_id"] = pre

with st.sidebar:
    kw = st.text_input("🔎 지표 검색", placeholder="지표명·컬럼명")
    if kw:
        hits = search(kw)
        if hits.empty:
            st.caption("검색 결과 없음")
        for _, r in hits.head(8).iterrows():
            if st.button(r["지표"], key=f"hit-{r['id']}", width="stretch"):
                st.session_state["exp_cat"] = r["카테고리"]
                st.session_state["exp_id"] = r["id"]
                st.rerun()

c1, c2 = st.columns(2)
cat = c1.selectbox("카테고리", list(CATEGORIES), key="exp_cat")
ids = CATEGORIES[cat]
if st.session_state.get("exp_id") not in ids:
    st.session_state["exp_id"] = ids[0]
ind_id = c2.selectbox("지표", ids, format_func=lambda i: INDICATORS[i].name, key="exp_id")
ind = INDICATORS[ind_id]

try:
    with st.spinner("ECOS에서 데이터를 불러오는 중..."):
        df = load(ind_id)
except EcosError as exc:
    show_error({ind.name: str(exc)})
    st.stop()

if df.empty:
    st.warning("조회된 데이터가 없습니다.")
    st.stop()

columns = list(df.columns)
picked = st.multiselect("컬럼", columns, default=columns, key=f"cols-{ind_id}")
if not picked:
    st.info("표시할 컬럼을 하나 이상 선택하세요.")
    st.stop()

freq = infer_freq(df.index)
st.caption(f"주기: **{FREQ_LABEL[freq]}** · 기간: {df.index.min():%Y-%m} ~ {df.index.max():%Y-%m} · "
           f"단위: {', '.join(sorted({unit_of(ind_id, c) or '—' for c in picked}))} · 출처: 한국은행 ECOS")

mcols = st.columns(min(len(picked), 4))
for i, col in enumerate(picked):
    with mcols[i % len(mcols)]:
        kpi(df[col], col, unit_of(ind_id, col), ind.decimals)

c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
with c1:
    period = period_slider(df.index.min(), df.index.max(), key=f"period-{ind_id}")
with c2:
    kind = chart_kind(key="exp_kind")

view = clip(df[picked], period)

# 단위가 다른 컬럼은 한 축에 섞지 않고 단위별로 차트를 나눈다
groups: dict[str, list[str]] = {}
for col in picked:
    groups.setdefault(unit_of(ind_id, col), []).append(col)
palette = charts.SERIES[charts.mode()]
colors = {c: palette[i % len(palette)] for i, c in enumerate(picked)}
for unit, cols in groups.items():
    title = ind.name if len(groups) == 1 else f"{ind.name} — {unit or '단위 미상'}"
    charts.show(charts.series_chart(view[cols], {c: unit for c in cols}, kind, title=title, colors=colors))

tab_t, tab_s = st.tabs(["원본 테이블", "기초 통계"])
with tab_t:
    table = view.dropna(how="all").sort_index(ascending=False)
    st.dataframe(table, width="stretch", height=360,
                 column_config={"날짜": st.column_config.DateColumn(format="YYYY-MM-DD")})
    st.download_button(
        "⬇️ CSV 다운로드",
        table.to_csv().encode("utf-8-sig"),
        file_name=f"ecos_{ind_id}_{period[0]:%Y%m}_{period[1]:%Y%m}.csv",
        mime="text/csv",
    )
with tab_s:
    st.dataframe(view.describe().T.round(3), width="stretch")
