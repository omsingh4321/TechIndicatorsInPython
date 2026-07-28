from __future__ import annotations

from pathlib import Path

import numpy as np

from candle import Candle
from indicators import ATR, SMA, Donchain, SuperTrend, TechIndicator, make_indicator


def read_csv(filename: Path) -> list[Candle]:
    data = np.genfromtxt(
        filename,
        delimiter=",",
        names=True,
        dtype=None,
        encoding="utf-8",
    )

    if data.size == 0:
        return []

    rows = np.atleast_1d(data)
    return [
        Candle(
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            oi=0.0,
            volume=float(row["volume"]),
        )
        for row in rows
    ]


def build_indicator(name: str, period: int) -> TechIndicator:
    if name.lower() == "sma":
        return make_indicator(SMA, period)
    if name.lower() == "atr":
        return make_indicator(ATR, period)
    if name.lower() in ("supertrend", "superTrend".lower()):
        multiplier = float(input("Enter Multiplier For it.\n"))
        return make_indicator(SuperTrend, period, multiplier)
    if name.lower() in ("donchian", "donchain"):
        band = int(input("Enter Band Type: 1 for lower, 2 for middle, 3 for upper.\n"))
        return make_indicator(Donchain, period, band)
    raise ValueError("Unknown indicator")


def main() -> int:
    name = input("Which Indicator You want to form ??\n")
    period = int(input("What period you want ??\n"))

    indicator: TechIndicator = build_indicator(name, period)
    csv_file = Path(__file__).resolve().parents[1] / "sample_data.csv"
    candles = read_csv(csv_file)

    if not candles:
        print("No data loaded from CSV file!")
        return 1

    print(f"Loaded {len(candles)} candles from CSV")

    for candle in candles:
        indicator.update(candle)  # Not a loop just simulation of candle updates

    print(f"Result: {indicator.get_value()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
