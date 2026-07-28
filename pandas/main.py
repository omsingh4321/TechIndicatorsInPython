from __future__ import annotations

from pathlib import Path

import pandas as pd

from indicators import ATR, SMA, Donchain, SuperTrend, TechIndicator, make_indicator


def read_csv(filename: Path) -> pd.DataFrame:
    return pd.read_csv(filename)


def build_indicator(name: str, period: int) -> TechIndicator:
    indicator_name = name.strip().lower()

    if indicator_name == "sma":
        return make_indicator(SMA, period)
    if indicator_name == "atr":
        return make_indicator(ATR, period)
    if indicator_name in ("supertrend", "super trend"):
        multiplier = float(input("Enter Multiplier For it.\n"))
        return make_indicator(SuperTrend, period, multiplier)
    if indicator_name in ("donchian", "donchain", "donchian channel", "donchain channel"):
        band = int(input("Enter Band Type: 1 for lower, 2 for middle, 3 for upper.\n"))
        return make_indicator(Donchain, period, band)
    raise ValueError("Unknown indicator")


def main() -> int:
    name = input("Which Indicator You want to form ??\n")
    period = int(input("What period you want ??\n"))

    try:
        indicator: TechIndicator = build_indicator(name, period)
    except ValueError as error:
        print(error)
        return 1

    csv_file = Path(__file__).resolve().parents[1] / "sample_data.csv"
    candles = read_csv(csv_file)

    if candles.empty:
        print("No data loaded from CSV file!")
        return 1

    print(f"Loaded {len(candles)} candles from CSV")
    indicator.update(candles)
    print(f"Result: {indicator.getValue()}")
    indicator.update({"open": 100, "high": 110, "low": 90, "close": 105})
    print(f"Updated Result: {indicator.getValue()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
