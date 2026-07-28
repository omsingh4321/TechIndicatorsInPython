from dataclasses import dataclass


@dataclass(frozen=True)
class Candle:
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    oi: float = 0.0
    volume: float = 0.0
