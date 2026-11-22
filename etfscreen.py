"""ETF를 104주선과 역대 고점 대비 낙폭으로 걸러 텔레그램으로 보낸다.

두 조건을 모두 만족하는 종목만 알린다.
  조건1  최근 일봉 종가 < 104주 이동평균 (주봉 종가 104개의 평균)
  조건2  최근 일봉 종가 <= 역대 일봉 고가 * (1 - 0.30)

텔레그램 환경변수:
  TELEGRAM_TOKEN
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

GROUPS: list[tuple[str, list[str]]] = [
    (
        "그룹1",
        ["SPY", "QQQ", "IOO", "VEA", "SCHD", "SPYD", "VYMI", "MOAT"],
    ),
    (
        "그룹2",
        ["XLF", "XLK", "XLC", "XLV", "XLI", "XLY", "XLP", "XLE", "XLU", "XLB", "XLRE"],
    ),
    (
        "그룹3",
        ["SMH", "IGV", "CIBR", "PAVE", "GRID", "IHI", "ITA", "GPZ", "IBIT", "IAU"],
    ),
]


@dataclass
class Quote:
    ticker: str
    current: float
    ma: float | None
    ath: float
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


def screen(symbols: list[str]) -> tuple[dict[str, Quote], str]:
    weekly = download(symbols, "1wk")
    daily = download(symbols, "1d")

    quotes: dict[str, Quote] = {}
    asof_dates: list[pd.Timestamp] = []

    for ticker in symbols:
        weekly_close = price_series(weekly, ticker, "Close")
        daily_high = price_series(daily, ticker, "High")
        daily_close = price_series(daily, ticker, "Close")
        if weekly_close is None or daily_high is None or daily_close is None:
            continue

        current = float(daily_close.iloc[-1])
        ath = float(daily_high.max())
        weeks = len(weekly_close)
        ma = float(weekly_close.tail(WEEKS).mean()) if weeks >= WEEKS else None
        ts = pd.Timestamp(daily_close.index[-1])
        asof_dates.append(ts)
        quotes[ticker] = Quote(
            ticker=ticker,
            current=current,
            ma=ma,
            ath=ath,
            asof=ts.strftime("%m/%d"),
        )

    latest_date = max(asof_dates).strftime("%m/%d") if asof_dates else ""
    return quotes, latest_date


def format_report(quotes: dict[str, Quote], asof: str) -> str:
    header = f"📈 {asof}" if asof else "📈"
    lines: list[str] = [header]
    for group_name, tickers in GROUPS:
        lines.append(group_name)
        hits = [
            quotes[t]
            for t in tickers
            if t in quotes and quotes[t].hit
        ]
        hits.sort(key=lambda q: q.drawdown)
        if not hits:
            lines.append("없음")
        else:
            for q in hits:
                lines.append(f"{q.ticker}({q.drawdown:.1%})")
        lines.append("")
    return "\n".join(lines).strip()


def send_telegram(text: str) -> None:
    token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 없어 전송을 건너뜁니다.")
        return

    payload = json.dumps(
        {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    ).encode()
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
    quotes, asof = screen(all_tickers())
    if not quotes:
        sys.exit("시세를 한 종목도 가져오지 못했습니다.")

    report = format_report(quotes, asof)
    print(report)
    send_telegram(report)


if __name__ == "__main__":
    main()
