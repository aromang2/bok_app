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
        Col("CD(91일)", "817Y002", "D", "010502000", "%"),
        Col("KORIBOR(3개월)", "817Y002", "D", "010150000", "%"),
    ]),
    Indicator("rate_long", "주요 장기 시장금리", "금리", [
        Col("통안증권(1년)", "817Y002", "D", "010400001", "%"),
        Col("국고채(3년)", "817Y002", "D", "010200000", "%"),
        Col("국고채(5년)", "817Y002", "D", "010200001", "%"),
        Col("국고채(10년)", "817Y002", "D", "010210000", "%"),
        Col("회사채(3년, AA-)", "817Y002", "D", "010300000", "%"),
    ], decimals=3),
    # ── 통화·신용
    Indicator("money", "협의 및 광의 통화", "통화·신용", [
        Col("M1(협의통화, 평잔)", "161Y002", "M", "BBLA00", "조원", scale=1e-3),
        Col("M2(광의통화, 평잔)", "161Y006", "M", "BBHA00", "조원", scale=1e-3),
        Col("Lf(금융기관유동성, 평잔)", "171Y004", "M", "LA00000", "조원", scale=1e-3),
    ], decimals=1),
    Indicator("household_credit", "가계신용", "통화·신용", [
        Col("가계신용", "151Y001", "Q", "1000000", "조원", scale=1e-3),
    ], decimals=1),
    # ── 환율·시장
    Indicator("fx_major", "주요 환율", "환율·시장", [
        Col("원/달러", "731Y001", "D", "0000001", "원"),
        Col("원/100엔", "731Y001", "D", "0000002", "원"),
        Col("원/유로", "731Y001", "D", "0000003", "원"),
        Col("원/위안", "731Y001", "D", "0000053", "원"),
    ]),
    Indicator("stock", "코스피 및 코스닥 지수", "환율·시장", [
        Col("코스피", "802Y001", "D", "0001000", "pt"),
        Col("코스닥", "802Y001", "D", "0089000", "pt"),
    ]),
    # ── 성장·생산
    Indicator("growth", "경제성장률", "성장·생산", [
        Col("경제성장률", "200Y102", "Q", "10111", "%"),
    ], decimals=1, signed=True),
    Indicator("production", "전산업생산지수", "성장·생산", [
        Col("전산업생산지수(계절조정)", "901Y033", "M", "A00/2", "2020=100"),
        Col("광공업(계절조정)", "901Y033", "M", "AB00/2", "2020=100"),
        Col("서비스업(계절조정)", "901Y033", "M", "AC00/2", "2020=100"),
    ], decimals=1),
    # ── 소비·투자
    Indicator("demand", "민간소비·설비투자·건설투자 증감률", "소비·투자", [
        Col("민간소비", "200Y102", "Q", "10122", "%"),
        Col("설비투자", "200Y102", "Q", "10123", "%"),
        Col("건설투자", "200Y102", "Q", "10124", "%"),
        Col("재화수출", "200Y102", "Q", "10125", "%"),
    ], decimals=1),
    # ── 경기·심리
    Indicator("business_cycle", "경기순환지표", "경기·심리", [
        Col("동행지수순환변동치", "901Y067", "M", "I16D", "2020=100"),
        Col("선행지수순환변동치", "901Y067", "M", "I16E", "2020=100"),
    ], decimals=1),
    Indicator("sentiment", "심리지표", "경기·심리", [
        Col("소비자심리지수", "511Y002", "M", "FME", "지수"),
        Col("경제심리지수", "513Y001", "M", "E1000", "지수"),
    ], decimals=1),
    # ── 고용
    Indicator("labor", "실업률 및 고용률", "고용", [
        Col("실업률", "901Y027", "M", "I61BC", "%"),
        Col("고용률", "901Y027", "M", "I61E", "%"),
    ], decimals=1),
    Indicator("employed", "취업자수", "고용", [
        Col("취업자수", "901Y027", "M", "I61BA", "만명", scale=0.1),
    ], decimals=1),
    # ── 대외
    Indicator("current_account", "경상수지", "대외", [
        Col("경상수지", "301Y013", "M", "000000", "억달러", scale=1e-2),
        Col("상품수지", "301Y013", "M", "100000", "억달러", scale=1e-2),
    ], decimals=1, signed=True),
    Indicator("trade", "수출입 금액", "대외", [
        Col("수출금액", "901Y118", "M", "T002", "억달러", scale=1e-5),
        Col("수입금액", "901Y118", "M", "T004", "억달러", scale=1e-5),
    ], decimals=1),
    Indicator("reserve", "외환보유액", "대외", [
        Col("외환보유액", "732Y001", "M", "99", "억달러", scale=1e-5),
    ], decimals=1),
    Indicator("external_debt", "대외채무", "대외", [
        Col("대외채무", "311Y004", "Q", "A000000", "억달러", scale=1e-2),
    ], decimals=1),
    # ── 물가·자산
    Indicator("cpi", "소비자물가 상승률", "물가·자산", [
        Col("소비자물가", "901Y009", "M", "0", "%", transform="yoy"),
        Col("농산물 및 석유류 제외", "901Y010", "M", "QB", "%", transform="yoy"),
        Col("생활물가", "901Y010", "M", "110", "%", transform="yoy"),
    ], decimals=1),
    Indicator("ppi", "생산자물가 상승률", "물가·자산", [
        Col("생산자물가", "404Y014", "M", "*AA", "%", transform="yoy"),
    ], decimals=1),
    Indicator("house", "주택매매가격 상승률(KB)", "물가·자산", [
        Col("주택매매가격(전국)", "901Y062", "M", "P63A", "%", transform="yoy"),
        Col("주택매매가격(서울)", "901Y062", "M", "P63AD", "%", transform="yoy"),
    ], decimals=1),
]
