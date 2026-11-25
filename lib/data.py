"""데이터 계층: 지표 카탈로그 + ECOS 호출 + 캐시."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lib import ecos
from lib.catalog import CATALOG, Col, Indicator

TTL = 3600
FREQ_LABEL = {"D": "일", "M": "월", "Q": "분기", "A": "연"}

INDICATORS: dict[str, Indicator] = {ind.id: ind for ind in CATALOG}
CATEGORIES: dict[str, list[str]] = {}
for _ind in CATALOG:
    CATEGORIES.setdefault(_ind.category, []).append(_ind.id)


def unit_of(ind_id: str, column: str) -> str:
    ind = INDICATORS.get(ind_id)
    if not ind:
        return ""
    return next((c.unit for c in ind.columns if c.name == column), "")


def infer_freq(index: pd.DatetimeIndex) -> str:
    if len(index) < 3:
        return "A"
    gap = pd.Series(index[-24:]).diff().dt.days.median()
    return "D" if gap <= 5 else "M" if gap <= 40 else "Q" if gap <= 120 else "A"


def _apply(col: Col, s: pd.Series) -> pd.Series:
    if col.transform == "yoy":  # 전년동기 대비 증감률(%)
        lag = {"M": 12, "Q": 4, "A": 1, "D": 365}[col.cycle]
        s = (s / s.shift(lag) - 1) * 100
    elif col.transform == "diff_yoy":
        s = s - s.shift(12)
    return (s * col.scale).dropna().rename(col.name)


@st.cache_data(ttl=TTL, show_spinner=False)
def _series(stat: str, cycle: str, item: str) -> pd.Series:
    """원천 시계열 1개 = ECOS 호출 1회. 같은 시계열은 지표가 달라도 캐시를 공유한다."""
    return ecos.series(stat, cycle, item)


def _fetch(ind: Indicator) -> pd.DataFrame:
    parts = [_apply(c, _series(c.stat, c.cycle, c.item)) for c in ind.columns]
    df = pd.concat(parts, axis=1).sort_index()
    df.index.name = "날짜"
    return df


@st.cache_data(ttl=TTL, show_spinner=False)
def load(ind_id: str) -> pd.DataFrame:
    return _fetch(INDICATORS[ind_id])


def load_many(ids: tuple[str, ...]) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """여러 지표를 순서대로 받는다.

    Streamlit 캐시는 스크립트 스레드에서 호출해야 세션 간에 공유되므로 병렬화하지 않는다.
    첫 로딩 이후에는 캐시(1시간)에서 바로 읽고, ECOS 호출 한도(3분 300회)도 지킬 수 있다.
    """
    data, errors = {}, {}
    for i in ids:
        try:
            data[i] = load(i)
        except ecos.EcosRateLimit as exc:
            errors[INDICATORS[i].name] = f"ERROR-602 {exc}"
            break  # 한도 초과면 나머지도 실패하므로 바로 중단
        except ecos.EcosError as exc:
            errors[INDICATORS[i].name] = str(exc)
    return data, errors


def list_indicators() -> pd.DataFrame:
    return pd.DataFrame(
        [{"id": i.id, "지표": i.name, "카테고리": i.category, "컬럼": [c.name for c in i.columns]} for i in CATALOG]
    )


def search(keyword: str) -> pd.DataFrame:
    """지표명·컬럼명 키워드 검색."""
    df = list_indicators()
    kw = keyword.strip().lower()
    if not kw:
        return df.iloc[0:0]
    hit = df["지표"].str.lower().str.contains(kw, regex=False) | df["컬럼"].map(
        lambda cols: any(kw in c.lower() for c in cols))
    return df[hit]


def show_error(errors: dict[str, str]) -> None:
    """호출 실패 안내 + 재시도 버튼."""
    if not errors:
        return
    if any("ERROR-602" in e or "과도한" in e for e in errors.values()):
        st.error("ECOS 호출 한도(3분간 300회)를 넘어 30분간 이용이 제한되었습니다. 잠시 후 다시 시도하세요.", icon="⏳")
    else:
        detail = "  \n".join(f"- **{k}**: {v}" for k, v in errors.items())
        st.error(f"데이터를 불러오지 못한 지표가 있습니다.  \n{detail}", icon="⚠️")
    if st.button("다시 시도", key=f"retry-{'-'.join(errors)}"):
        _series.clear()
        load.clear()
        st.rerun()
