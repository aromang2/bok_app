"""한국은행 ECOS 금융경제 스냅샷 대시보드 — 진입점·내비게이션.

실행: uv run streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="ECOS 경제 대시보드", page_icon="📊", layout="wide")

# 커스텀 CSS는 폰트와 여백 정도로 최소화
st.markdown(
    """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
html, body, p, li, label, input, textarea, h1, h2, h3, h4,
[data-testid="stMarkdownContainer"], [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
  font-family: Pretendard, -apple-system, 'Malgun Gothic', sans-serif;
}
.block-container { padding-top: 2.6rem; max-width: 1400px; }
h1, h2, h3 { letter-spacing: -0.02em; }
[data-testid="stMetricValue"] { font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
</style>
""",
    unsafe_allow_html=True,
)

pages = [
    st.Page("pages/home.py", title="홈", icon=":material/home:", default=True),
    st.Page("pages/explorer.py", title="지표 탐색기", icon=":material/query_stats:"),
    st.Page("pages/compare.py", title="비교 분석", icon=":material/compare_arrows:"),
    st.Page("pages/category.py", title="카테고리 대시보드", icon=":material/dashboard:"),
]
nav = st.navigation(pages)

with st.sidebar:
    st.caption("데이터 출처: **한국은행 ECOS Open API**  \n인증키: `.env`의 `ECOS_API_KEY` · 1시간 캐시")

nav.run()
