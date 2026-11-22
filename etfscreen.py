"""ETF를 104주선과 역대 고점 대비 낙폭으로 걸러 텔레그램으로 보낸다.

두 조건을 모두 만족하는 종목만 알린다.
  조건1  최근 일봉 종가 < 104주 이동평균 (주봉 종가 104개의 평균)
  조건2  최근 일봉 종가 <= 역대 일봉 고가 * (1 - 0.30)

가격은 분할만 반영된 시세다. 배당 조정가는 현재 호가와 기준이 달라 쓰지 않는다.
상장 후 104주가 안 된 종목은 조건1을 계산할 수 없어 제외하고, 메시지 아래에 적는다.

텔레그램은 환경변수로 받는다. 둘 다 없으면 결과만 출력하고 전송은 건너뛴다.
  TELEGRAM_BOT_TOKEN
  TELEGRAM_CHAT_ID
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
import warnings
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*inplace.*")

DRAWDOWN = 0.30
WEEKS = 104

# 그룹 1은 9개라고 했지만 받은 티커는 8개다. 적힌 심볼만 넣었다.
# 그룹 3은 9개라고 했지만 받은 티커는 10개다. 적힌 심볼을 모두 넣었다.
GROUPS: list[tuple[str, list[str]]] = [
    (
        "핵심 자산",
        ["SPY", "QQQ", "IOO", "VEA", "SCHD", "SPYD", "VYMI", "MOAT"],
    ),
    (
        "미국 11개 섹터",
        ["XLF", "XLK", "XLC", "XLV", "XLI", "XLY", "XLP", "XLE", "XLU", "XLB", "XLRE"],
    ),
    (
        "구조적 성장 테마",
        ["SMH", "IGV", "CIBR", "PAVE", "GRID", "IHI", "ITA", "GPZ", "IBIT", "IAU"],
    ),
]

NAMES = {
    "SPY": "S&P500",
    "QQQ": "나스닥100",
    "IOO": "글로벌100",
    "VEA": "선진국(미국제외)",
    "SCHD": "배당성장",
    "SPYD": "고배당",
    "VYMI": "해외고배당",
    "MOAT": "와이드모트",
    "XLF": "금융",
    "XLK": "기술",
    "XLC": "통신",
    "XLV": "헬스케어",
    "XLI": "산업재",
    "XLY": "경기소비재",
    "XLP": "필수소비재",
    "XLE": "에너지",
    "XLU": "유틸리티",
    "XLB": "소재",
    "XLRE": "부동산",
    "SMH": "반도체",
    "IGV": "소프트웨어",
    "CIBR": "사이버보안",
    "PAVE": "인프라",
    "GRID": "전력망",
    "IHI": "의료기기",
    "ITA": "항공우주/방산",
    "GPZ": "대체자산운용사",
    "IBIT": "비트코인",
    "IAU": "금",
}


@dataclass
class Quote:
    ticker: str
    group: str
    current: float
    ma: float | None
    ath: float
    weeks: int
    asof: str

    @property
    def below_ma(self) -> bool:
        return self.ma is not None and self.current < self.ma

    @property
    def deep_drawdown(self) -> bool:
        return self.current <= self.ath * (1 - DRAWDOWN)

    @property
    def hit(self) -> bool:
        return self.below_ma and self.deep_drawdown

    @property
    def drawdown(self) -> float:
        return self.current / self.ath - 1


def all_tickers() -> list[str]:
    symbols: list[str] = []
    seen: set[str] = set()
    for _, tickers in GROUPS:
        for ticker in tickers:
            if ticker not in seen:
                seen.add(ticker)
                symbols.append(ticker)
    return symbols


def price_series(frame: pd.DataFrame, symbol: str, field: str) -> pd.Series | None:
    """group_by='ticker' 다운로드 결과에서 한 종목의 가격 열을 꺼낸다."""
    if frame.empty or not isinstance(frame.columns, pd.MultiIndex):
        return None
    if symbol not in frame.columns.get_level_values(0):
        return None
    ticker_frame = frame[symbol]
    if field not in ticker_frame.columns:
        return None
    series = pd.to_numeric(ticker_frame[field], errors="coerce").dropna()
    if series.empty:
        return None
    return series


def download(symbols: list[str], interval: str) -> pd.DataFrame:
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            frame = yf.download(
                symbols,
                period="max",
                interval=interval,
                auto_adjust=False,
                group_by="ticker",
                threads=True,
                progress=False,
            )
            if isinstance(frame, pd.DataFrame) and not frame.empty:
                return frame
            last_error = RuntimeError(f"{interval} 시세가 비어 있음")
        except Exception as exc:
            last_error = exc
        if attempt < 2:
            time.sleep(5 * (attempt + 1))
    sys.exit(f"{interval} 시세 다운로드 실패: {last_error}")


def screen(symbols: list[str]) -> tuple[list[Quote], list[str], str]:
    group_of = {ticker: name for name, tickers in GROUPS for ticker in tickers}
    print(f"시세 다운로드: {len(symbols)}종목 (주봉 104주선, 일봉 역대 고가)")
    weekly = download(symbols, "1wk")
    daily = download(symbols, "1d")

    quotes: list[Quote] = []
    failed: list[str] = []
    asof_dates: list[str] = []

    for ticker in symbols:
        weekly_close = price_series(weekly, ticker, "Close")
        daily_high = price_series(daily, ticker, "High")
        daily_close = price_series(daily, ticker, "Close")
        if weekly_close is None or daily_high is None or daily_close is None:
            failed.append(ticker)
            print(f"  제외 {ticker}: 시세 없음")
            continue

        current = float(daily_close.iloc[-1])
        ath = float(daily_high.max())
        weeks = len(weekly_close)
        ma = float(weekly_close.tail(WEEKS).mean()) if weeks >= WEEKS else None
        asof = pd.Timestamp(daily_close.index[-1]).strftime("%Y-%m-%d")
        asof_dates.append(asof)
        quote = Quote(ticker, group_of[ticker], current, ma, ath, weeks, asof)
        quotes.append(quote)

        ma_text = "n/a" if ma is None else f"{ma:.2f}"
        print(
            f"  {ticker}: 현재가 {current:.2f} | 104주선 {ma_text} | "
            f"최고가 {ath:.2f} | 낙폭 {quote.drawdown:.1%} | "
            f"조건1 {quote.below_ma} | 조건2 {quote.deep_drawdown}"
        )

    asof = max(asof_dates) if asof_dates else ""
    return quotes, failed, asof


def format_report(quotes: list[Quote], failed: list[str], asof: str) -> str:
    lines = [
        f"ETF 스크리너 {asof}",
        "104주선 아래 + 역대 고점 대비 -30% 이상",
        "",
    ]
    hits = [quote for quote in quotes if quote.hit]
    if not hits:
        lines.append("두 조건을 모두 만족하는 ETF 없음")
        lines.append("")

    by_ticker = {quote.ticker: quote for quote in quotes}
    for name, tickers in GROUPS:
        lines.append(f"[{name}]")
        group_hits = [by_ticker[ticker] for ticker in tickers if ticker in by_ticker and by_ticker[ticker].hit]
        group_hits.sort(key=lambda quote: quote.drawdown)
        if not group_hits:
            lines.append("해당 없음")
        for quote in group_hits:
            label = NAMES.get(quote.ticker, "")
            lines.append(
                f"{quote.ticker} {label}  {quote.current:.2f} | "
                f"104주 {quote.ma:.2f} | 고점대비 {quote.drawdown:.1%}"
            )
        lines.append("")

    short = [quote.ticker for quote in quotes if quote.ma is None]
    if short:
        lines.append("104주 미만이라 제외: " + ", ".join(short))
    if failed:
        lines.append("시세 없음: " + ", ".join(failed))
    return "\n".join(lines).rstrip() + "\n"


def send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("TELEGRAM_BOT_TOKEN 또는 TELEGRAM_CHAT_ID가 없어 전송을 건너뜁니다.")
        return

    payload = json.dumps({"chat_id": chat_id, "text": text, "disable_web_page_preview": True}).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        sys.exit(f"텔레그램 전송 실패: HTTP {exc.code} {detail}")
    except urllib.error.URLError as exc:
        sys.exit(f"텔레그램 전송 실패: {exc.reason}")

    if not body.get("ok"):
        sys.exit(f"텔레그램 전송 실패: {body}")
    print("텔레그램 전송 완료")


def main() -> None:
    quotes, failed, asof = screen(all_tickers())
    if not quotes and failed:
        sys.exit("시세를 한 종목도 가져오지 못했습니다: " + ", ".join(failed))

    report = format_report(quotes, failed, asof)
    print()
    print(report, end="")
    send_telegram(report)
    hits = sum(quote.hit for quote in quotes)
    print(f"조건 충족 {hits}종목")


if __name__ == "__main__":
    main()
