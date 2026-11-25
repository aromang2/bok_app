"""홈(요약): 핵심 KPI 카드 + 지표 검색 + 카테고리 개요."""

import streamlit as st

from lib.data import CATEGORIES, INDICATORS, load_many, search, show_error, unit_of
from lib.ui import kpi

# (지표 id, 컬럼, 카드 제목, 소수 자릿수)
KPIS = [
    ("rate_short", "한국은행 기준금리", "기준금리", 2),
    ("fx_major", "원/달러", "원/달러 환율", 1),
    ("stock", "코스피", "코스피", 2),
    ("cpi", "소비자물가", "소비자물가 상승률", 1),
    ("labor", "실업률", "실업률", 1),
    ("growth", "경제성장률", "경제성장률 (전기비)", 1),
]

st.title("한국은행 금융경제 스냅샷")
st.caption("금리 · 환율 · 물가 · 성장 · 고용 핵심 지표를 한눈에 — 출처: 한국은행 ECOS")

with st.spinner("ECOS에서 지표를 불러오는 중..."):
    data, errors = load_many(tuple(dict.fromkeys(k[0] for k in KPIS if k[0] in INDICATORS)))
show_error(errors)

for row in (KPIS[:3], KPIS[3:]):
    cols = st.columns(3)
    for col, (ind_id, column, title, dec) in zip(cols, row):
        with col:
            df = data.get(ind_id)
            if df is None or column not in df:
                st.metric(title, "—", border=True)
            else:
                kpi(df[column], title, unit_of(ind_id, column), dec)

st.divider()

# ---------------------------------------------------------------- 검색
st.subheader("지표 검색")
kw = st.text_input("지표명·컬럼명 키워드", placeholder="예: 금리, 환율, 고용, 수출, 물가", label_visibility="collapsed")
if kw:
    hits = search(kw)
    if hits.empty:
        st.info(f"'{kw}'에 해당하는 지표가 없습니다.")
    for _, r in hits.iterrows():
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f"**{r['지표']}** · `{r['카테고리']}`  \n{', '.join(r['컬럼'])}")
        if c2.button("탐색기에서 열기", key=f"open-{r['id']}"):
            st.session_state["explore_id"] = r["id"]
            st.switch_page("pages/explorer.py")

st.divider()

# ---------------------------------------------------------------- 카테고리 개요
st.subheader("카테고리")
cols = st.columns(3)
for i, (cat, ids) in enumerate(CATEGORIES.items()):
    with cols[i % 3].container(border=True):
        st.markdown(f"**{cat}** · {len(ids)}개 지표")
        st.caption(" · ".join(INDICATORS[x].name for x in ids))
        if st.button("대시보드 보기", key=f"cat-{cat}"):
            st.session_state["category"] = cat
            st.switch_page("pages/category.py")
