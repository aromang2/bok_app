"""데이터 계층: 지표 카탈로그 + ECOS 호출 + 캐시."""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

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


# 원천 시계열 캐시: (통계표, 주기, 항목) → (받은 시각, Series).
# 스레드에서 병렬로 채우기 위해 st.cache_data 대신 프로세스 전역 dict를 쓴다(모든 세션이 공유).
_RAW: dict[tuple[str, str, str], tuple[float, pd.Series]] = {}
_LOCK = threading.Lock()
MAX_WORKERS = 6  # 동시 호출 수 (ECOS 한도 3분 300회 고려)


def _series(key: tuple[str, str, str]) -> pd.Series:
    with _LOCK:
        hit = _RAW.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    s = ecos.series(*key)
    with _LOCK:
        _RAW[key] = (time.time(), s)
    return s


def clear_cache() -> None:
    with _LOCK:
        _RAW.clear()


def _build(ind: Indicator) -> pd.DataFrame:
    parts = [_apply(c, _series((c.stat, c.cycle, c.item))) for c in ind.columns]
    df = pd.concat(parts, axis=1).sort_index()
    df.index.name = "날짜"
    return df


def load_many(ids: tuple[str, ...]) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """여러 지표를 받는다. 필요한 원천 시계열을 중복 없이 모아 병렬로 호출한다."""
    keys = list(dict.fromkeys((c.stat, c.cycle, c.item) for i in ids for c in INDICATORS[i].columns))
    failed: dict[tuple, Exception] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        for key, fut in [(k, pool.submit(_series, k)) for k in keys]:
            try:
                fut.result()
            except ecos.EcosError as exc:
                failed[key] = exc

    data, errors = {}, {}
    for i in ids:
        ind = INDICATORS[i]
        bad = [failed[(c.stat, c.cycle, c.item)] for c in ind.columns if (c.stat, c.cycle, c.item) in failed]
        if bad:
            exc = bad[0]
            errors[ind.name] = f"ERROR-602 {exc}" if isinstance(exc, ecos.EcosRateLimit) else str(exc)
        else:
            data[i] = _build(ind)
    return data, errors


def load(ind_id: str) -> pd.DataFrame:
    data, errors = load_many((ind_id,))
    if errors:
        msg = next(iter(errors.values()))
        raise ecos.EcosRateLimit(msg) if msg.startswith("ERROR-602") else ecos.EcosError(msg)
    return data[ind_id]


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
        clear_cache()
        st.rerun()
