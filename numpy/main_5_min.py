from __future__ import annotations

from pathlib import Path

import numpy as np


OHLCV_DTYPE = [
    ("time", "U32"),
    ("open", "f8"),
    ("high", "f8"),
    ("low", "f8"),
    ("close", "f8"),
    ("volume", "f8"),
]


def read_csv(filename: Path) -> np.ndarray:
    data = np.genfromtxt(
        filename,
        delimiter=",",
        names=True,
        dtype=None,
        encoding="utf-8",
    )

    if data.size == 0:
        return np.array([], dtype=OHLCV_DTYPE)

    return np.atleast_1d(data)


def floor_time_to_interval(timestamp: str, interval_minutes: int) -> str:
    minute = int(timestamp[14:16])
    interval_start = (minute // interval_minutes) * interval_minutes
    return f"{timestamp[:14]}{interval_start:02d}{timestamp[16:]}"


def make_five_minute_candles(
    candles: np.ndarray,
    interval_minutes: int = 5,
    include_partial: bool = False,
) -> np.ndarray:
    if candles.size == 0:
        return np.array([], dtype=OHLCV_DTYPE)

    bucket_times = np.array(
        [floor_time_to_interval(str(time), interval_minutes) for time in candles["time"]]
    )
    bucket_starts = np.r_[0, np.flatnonzero(bucket_times[1:] != bucket_times[:-1]) + 1]
    bucket_ends = np.r_[bucket_starts[1:], candles.size]

    five_minute_rows = []
    for start, end in zip(bucket_starts, bucket_ends):
        candle_count = end - start
        if candle_count != interval_minutes and not include_partial:
            continue

        five_minute_rows.append(
            (
                bucket_times[start],
                float(candles["open"][start]),
                float(np.max(candles["high"][start:end])),
                float(np.min(candles["low"][start:end])),
                float(candles["close"][end - 1]),
                float(np.sum(candles["volume"][start:end])),
            )
        )

    return np.array(five_minute_rows, dtype=OHLCV_DTYPE)


def write_csv(filename: Path, candles: np.ndarray) -> None:
    np.savetxt(
        filename,
        candles,
        delimiter=",",
        header="time,open,high,low,close,volume",
        comments="",
        fmt=["%s", "%.10g", "%.10g", "%.10g", "%.10g", "%.10g"],
    )


def main() -> int:
    project_dir = Path(__file__).resolve().parents[1]
    input_file = project_dir / "sample_data.csv"
    output_file = project_dir / "sample_data_5_min.csv"

    one_minute_candles = read_csv(input_file)
    five_minute_candles = make_five_minute_candles(one_minute_candles)

    if five_minute_candles.size == 0:
        print("No complete 5-minute candles were created.")
        return 1

    write_csv(output_file, five_minute_candles)
    print(f"Read {one_minute_candles.size} 1-minute candles from {input_file}")
    print(f"Wrote {five_minute_candles.size} 5-minute candles to {output_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
