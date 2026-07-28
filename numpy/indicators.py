from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from candle import Candle
from circular_buffer import CircularBuffer


IndicatorT = TypeVar("IndicatorT", bound="TechIndicator")


class TechIndicator(ABC):
    @abstractmethod
    def update(self, candle: Candle) -> None:
        pass

    @abstractmethod
    def get_value(self) -> float:
        pass


class SMA(TechIndicator):
    def __init__(self, window: int) -> None:
        self._window = window
        self._candles_queue = CircularBuffer[float](window, dtype=float)
        self._sum = 0.0

    def update(self, candle: Candle) -> None:
        open_value = candle.open

        if self._candles_queue.is_full():
            front_candle = self._candles_queue.pop()
            if front_candle is not None:
                self._sum -= front_candle

        self._sum += open_value
        self._candles_queue.push(open_value)

    def get_value(self) -> float:
        if self._candles_queue.get_size() == self._window and self._window != 0:
            return self._sum / self._window
        return 0.0


class ATR(TechIndicator):
    def __init__(self, period: int) -> None:
        self._period = period
        self._prev_close = 0.0
        self._atr = 0.0
        self._initialized = False
        self._count = 0
        self._tr_sum = 0.0

    def update(self, candle: Candle) -> None:
        if self._count == 0:
            true_range = candle.high - candle.low
        else:
            tr1 = candle.high - candle.low
            tr2 = abs(candle.high - self._prev_close)
            tr3 = abs(candle.low - self._prev_close)
            true_range = max(tr1, tr2, tr3)

        self._count += 1
        self._prev_close = candle.close

        if not self._initialized:
            self._tr_sum += true_range
            if self._count == self._period and self._period != 0:
                self._atr = self._tr_sum / self._period
                self._initialized = True
        else:
            self._atr = (self._atr * (self._period - 1) + true_range) / self._period

    def get_value(self) -> float:
        return self._atr if self._initialized else 0.0


class Donchain(TechIndicator):
    def __init__(self, period: int, band: int) -> None:
        self._period = period
        self._index = 0
        self._high_queue = CircularBuffer[tuple[int, float]](period + 1)
        self._low_queue = CircularBuffer[tuple[int, float]](period + 1)
        self._band_type = band
        self._upper_band = 0.0
        self._lower_band = 0.0
        self._middle_band = 0.0
        self._initialized = False

    def update(self, candle: Candle) -> None:
        # Loop required because update() receives one candle at a time; these
        # monotonic queues keep rolling max/min without rescanning the window.
        # Using only built-in np.max/np.min here would mean rebuilding or
        # scanning the whole rolling window on every update, which is simpler
        # but slower for streaming data.
        while not self._high_queue.is_empty():
            back = self._high_queue.back_value()
            if back is None or back[1] > candle.high:
                break
            self._high_queue.pop_back()
        self._high_queue.push_back((self._index, candle.high))

        while not self._low_queue.is_empty():
            back = self._low_queue.back_value()
            if back is None or back[1] < candle.low:
                break
            self._low_queue.pop_back()
        self._low_queue.push_back((self._index, candle.low))

        while not self._high_queue.is_empty():
            front = self._high_queue.front_value()
            if front is None or front[0] > self._index - self._period:
                break
            self._high_queue.pop_front()

        while not self._low_queue.is_empty():
            front = self._low_queue.front_value()
            if front is None or front[0] > self._index - self._period:
                break
            self._low_queue.pop_front()

        self._index += 1

        if self._index >= self._period and self._period != 0:
            high_front = self._high_queue.front_value()
            low_front = self._low_queue.front_value()
            if high_front is not None and low_front is not None:
                self._upper_band = high_front[1]
                self._lower_band = low_front[1]
                self._middle_band = (self._upper_band + self._lower_band) / 2.0
                self._initialized = True

    def get_value(self) -> float:
        if not self._initialized:
            return 0.0
        if self._band_type == 1:
            return self._lower_band
        if self._band_type == 2:
            return self._middle_band
        if self._band_type == 3:
            return self._upper_band
        return 0.0


class SuperTrend(TechIndicator):
    def __init__(self, period: int, multiplier: float) -> None:
        self._period = period
        self._multiplier = multiplier
        self._atr = ATR(period)
        self._prev_close = 0.0
        self._prev_final_upper_band = 0.0
        self._prev_final_lower_band = 0.0
        self._super_trend = 0.0
        self._initialized = False

    def update(self, candle: Candle) -> None:
        self._atr.update(candle)
        atr_value = self._atr.get_value()

        if atr_value == 0:
            self._prev_close = candle.close
            return

        hl2 = (candle.high + candle.low) / 2.0
        basic_upper_band = hl2 + (self._multiplier * atr_value)
        basic_lower_band = hl2 - (self._multiplier * atr_value)

        if not self._initialized:
            self._prev_final_upper_band = basic_upper_band
            self._prev_final_lower_band = basic_lower_band
            if candle.close <= self._prev_final_upper_band:
                self._super_trend = self._prev_final_upper_band
            else:
                self._super_trend = self._prev_final_lower_band
            self._initialized = True
            self._prev_close = candle.close
            return

        if basic_upper_band < self._prev_final_upper_band or self._prev_close > self._prev_final_upper_band:
            final_upper_band = basic_upper_band
        else:
            final_upper_band = self._prev_final_upper_band

        if basic_lower_band > self._prev_final_lower_band or self._prev_close < self._prev_final_lower_band:
            final_lower_band = basic_lower_band
        else:
            final_lower_band = self._prev_final_lower_band

        if self._super_trend == self._prev_final_upper_band:
            if candle.close <= final_upper_band:
                self._super_trend = final_upper_band
            else:
                self._super_trend = final_lower_band
        else:
            if candle.close >= final_lower_band:
                self._super_trend = final_lower_band
            else:
                self._super_trend = final_upper_band

        self._prev_final_upper_band = final_upper_band
        self._prev_final_lower_band = final_lower_band
        self._prev_close = candle.close

    def get_value(self) -> float:
        return self._super_trend if self._initialized else 0.0


def make_indicator(indicator_type: type[IndicatorT], *args) -> IndicatorT:
    return indicator_type(*args)
