"""한국은행 ECOS Open API 클라이언트 (인증키: .env 의 ECOS_API_KEY)."""

from __future__ import annotations

import os
from datetime import date

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://ecos.bok.or.kr/api"
PAGE_SIZE = 100_000  # ECOS 1회 최대 조회 건수
TIMEOUT = 20
FULL_START = {"D": date(1995, 1, 1), "M": date(1960, 1, 1), "Q": date(1960, 1, 1), "A": date(1960, 1, 1)}


class EcosError(RuntimeError):
    """ECOS가 오류 코드를 돌려줬거나 요청이 실패한 경우."""


class EcosRateLimit(EcosError):
    """ERROR-602: 3분간 300회 초과 호출로 30분간 이용 제한."""


def api_key() -> str | None:
    key = os.getenv("ECOS_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st

        return str(st.secrets["ECOS_API_KEY"]).strip() or None
    except Exception:
        return None


def _get(path: str) -> dict:
    key = api_key()
    if not key:
        raise EcosError("ECOS_API_KEY가 설정되지 않았습니다. 프로젝트 폴더의 .env 파일을 확인하세요.")
    try:
        resp = requests.get(f"{BASE_URL}/{path.format(key=key)}", timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        # 예외 메시지에 인증키가 담긴 URL이 들어가지 않도록 정리
        raise EcosError(f"ECOS 요청 실패: {type(exc).__name__}") from None
    if "RESULT" in data:
        code, msg = data["RESULT"].get("CODE", ""), data["RESULT"].get("MESSAGE", "")
        if code == "INFO-200":  # 데이터 없음
            return {}
        if code == "ERROR-602":
            raise EcosRateLimit(msg)
        raise EcosError(f"{code}: {msg}")
    return data


def fmt_period(d: date, cycle: str) -> str:
    if cycle == "D":
        return d.strftime("%Y%m%d")
    if cycle == "M":
        return d.strftime("%Y%m")
    if cycle == "Q":
        return f"{d.year}Q{(d.month - 1) // 3 + 1}"
    return str(d.year)


def _parse_time(values: pd.Series, cycle: str) -> pd.DatetimeIndex:
    if cycle == "D":
        return pd.DatetimeIndex(pd.to_datetime(values, format="%Y%m%d"))
    if cycle == "M":
        return pd.DatetimeIndex(pd.to_datetime(values, format="%Y%m"))
    if cycle == "Q":
        return pd.PeriodIndex(values.str.replace("Q", "-Q"), freq="Q").to_timestamp()
    return pd.DatetimeIndex(pd.to_datetime(values, format="%Y"))


def series(stat_code: str, cycle: str, item_code: str, start: date | None = None,
           end: date | None = None) -> pd.Series:
    """StatisticSearch: 단일 항목 시계열 (DatetimeIndex → float)."""
    start = start or FULL_START[cycle]
    end = end or date.today()
    items = item_code.split("/")  # 항목코드가 여러 단계면 '/'로 구분
    path = (f"StatisticSearch/{{key}}/json/kr/1/{PAGE_SIZE}/{stat_code}/{cycle}/"
            f"{fmt_period(start, cycle)}/{fmt_period(end, cycle)}/" + "/".join(items))
    body = _get(path).get("StatisticSearch")
    if not body:
        return pd.Series(dtype=float)
    df = pd.DataFrame(body["row"])
    values = pd.to_numeric(df["DATA_VALUE"].astype(str).str.replace(",", ""), errors="coerce")
    s = pd.Series(values.to_numpy(), index=_parse_time(df["TIME"], cycle), name=item_code)
    s.index.name = "날짜"
    return s.dropna().sort_index()


def key_statistics() -> pd.DataFrame:
    """KeyStatisticList: 100대 통계지표 최신값."""
    body = _get("KeyStatisticList/{key}/json/kr/1/200").get("KeyStatisticList")
    if not body:
        return pd.DataFrame()
    return pd.DataFrame(body["row"]).rename(columns={
        "CLASS_NAME": "분류", "KEYSTAT_NAME": "지표", "DATA_VALUE": "값", "CYCLE": "기준시점", "UNIT_NAME": "단위"
    })[["분류", "지표", "값", "단위", "기준시점"]]


def table_list() -> pd.DataFrame:
    """StatisticTableList: 검색 가능한 통계표 목록."""
    body = _get("StatisticTableList/{key}/json/kr/1/10000").get("StatisticTableList")
    df = pd.DataFrame(body["row"]) if body else pd.DataFrame()
    return df[df["SRCH_YN"] == "Y"][["STAT_CODE", "STAT_NAME", "CYCLE"]].reset_index(drop=True) if not df.empty else df


def item_list(stat_code: str) -> pd.DataFrame:
    """StatisticItemList: 통계표의 항목·주기·기간·단위."""
    body = _get(f"StatisticItemList/{{key}}/json/kr/1/10000/{stat_code}").get("StatisticItemList")
    return pd.DataFrame(body["row"]) if body else pd.DataFrame()
