"""지표 카탈로그: PRD 카테고리 → 지표 → 컬럼(ECOS 통계표코드·주기·항목코드).

코드는 ECOS StatisticItemList로 확인한 것만 넣는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Col:
    name: str
    stat: str  # 통계표코드
    cycle: str  # D / M / Q / A
    item: str  # 항목코드 (여러 단계면 'A/B')
    unit: str
    scale: float = 1.0  # 원 단위 → 표시 단위 배수
    transform: str | None = None  # "yoy": 전년동기 대비 증감률(%)


@dataclass(frozen=True)
class Indicator:
    id: str
    name: str
    category: str
    columns: list[Col] = field(default_factory=list)
    decimals: int = 2
    signed: bool = False  # 부호가 의미 있는 값(막대: 양수 빨강·음수 파랑)


CATALOG: list[Indicator] = [
    # ── 금리
    Indicator("rate_short", "주요 단기 시장금리", "금리", [
        Col("한국은행 기준금리", "722Y001", "D", "0101000", "%"),
        Col("콜금리(익일물)", "817Y002", "D", "010101000", "%"),
    ]),
    Indicator("rate_long", "주요 장기 시장금리", "금리", [
        Col("국고채(3년)", "817Y002", "D", "010200000", "%"),
        Col("국고채(5년)", "817Y002", "D", "010200001", "%"),
        Col("국고채(10년)", "817Y002", "D", "010210000", "%"),
    ], decimals=3),
    # ── 통화·신용
    Indicator("money", "광의통화(M2)", "통화·신용", [
        Col("M2(광의통화, 평잔)", "161Y006", "M", "BBHA00", "조원", scale=1e-3),
    ], decimals=1),
    # ── 환율·시장
    Indicator("fx_major", "주요 환율", "환율·시장", [
        Col("원/달러", "731Y001", "D", "0000001", "원"),
        Col("원/100엔", "731Y001", "D", "0000002", "원"),
        Col("원/유로", "731Y001", "D", "0000003", "원"),
        Col("원/위안", "731Y001", "D", "0000053", "원"),
    ]),
    # ── 성장·생산
    Indicator("growth", "경제성장률", "성장·생산", [
        Col("경제성장률", "200Y102", "Q", "10111", "%"),
    ], decimals=1, signed=True),
    # ── 대외
    Indicator("current_account", "경상수지", "대외", [
        Col("경상수지", "301Y013", "M", "000000", "억달러", scale=1e-2),
        Col("상품수지", "301Y013", "M", "100000", "억달러", scale=1e-2),
    ], decimals=1, signed=True),
    Indicator("reserve", "외환보유액", "대외", [
        Col("외환보유액", "732Y001", "M", "99", "억달러", scale=1e-5),
    ], decimals=1),
    # ── 물가·자산
    Indicator("cpi", "소비자물가 상승률", "물가·자산", [
        Col("소비자물가", "901Y009", "M", "0", "%", transform="yoy"),
    ], decimals=1),
]
