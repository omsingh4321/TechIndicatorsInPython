from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

import pandas as pd

from circular_buffer import CircularBuffer


IndicatorT = TypeVar("IndicatorT", bound="TechIndicator")


class TechIndicator(ABC):
    @abstractmethod
    def update(self, candles: pd.DataFrame | pd.Series | dict) -> pd.Series | float:
        pass

    def getValue(self, candles: pd.DataFrame | None = None) -> float:
        if candles is None:
            return float(getattr(self, "_last_value", 0.0))

        values = self.update(candles)
        if isinstance(values, float):
            return values
        if values.empty:
            return 0.0
        return float(values.iloc[-1])

    def get_value(self, candles: pd.DataFrame | None = None) -> float:
        return self.getValue(candles)


class SMA(TechIndicator):
    def __init__(self, window: int) -> None:
        self._window = window
        self._open_values = CircularBuffer[float](window, typecode="d")
        self._sum = 0.0
        self._last_value = 0.0

    def update(self, candles: pd.DataFrame | pd.Series | dict) -> pd.Series | float:
        if isinstance(candles, pd.DataFrame):
            values = candles["open"].rolling(window=self._window, min_periods=self._window).mean().fillna(0.0)
            self._last_value = 0.0 if values.empty else float(values.iloc[-1])
            self._open_values = CircularBuffer[float](self._window, typecode="d")
            self._sum = 0.0
            for open_value in candles["open"].tail(self._window):
                open_value = float(open_value)
                self._open_values.push(open_value)
                self._sum += open_value
            return values

        # O(1) streaming update: keep only the rolling sum and the last
        # window's open values instead of recalculating pandas rolling().
        open_value = float(candles["open"])

        if self._open_values.is_full():
            front_value = self._open_values.pop()
            if front_value is not None:
                self._sum -= front_value

        self._open_values.push(open_value)
        self._sum += open_value

        if self._open_values.getSize() == self._window and self._window != 0:
            self._last_value = self._sum / self._window
        else:
            self._last_value = 0.0

        return self._last_value


class ATR(TechIndicator):
    def __init__(self, period: int) -> None:
        self._period = period
        self._prev_close = 0.0
        self._atr = 0.0
        self._initialized = False
        self._count = 0
        self._tr_sum = 0.0
        self._last_value = 0.0

    def update(self, candles: pd.DataFrame | pd.Series | dict) -> pd.Series | float:
        if isinstance(candles, pd.DataFrame):
            high_low = candles["high"] - candles["low"]
            high_prev_close = (candles["high"] - candles["close"].shift(1)).abs()
            low_prev_close = (candles["low"] - candles["close"].shift(1)).abs()
            true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)

            if self._period == 0 or len(candles) < self._period:
                self._count = len(candles)
                self._tr_sum = float(true_range.sum())
                self._prev_close = 0.0 if candles.empty else float(candles["close"].iloc[-1])
                self._atr = 0.0
                self._initialized = False
                self._last_value = 0.0
                return pd.Series(0.0, index=candles.index)

            values = true_range.ewm(alpha=1 / self._period, adjust=False, min_periods=self._period).mean().fillna(0.0)
            self._last_value = 0.0 if values.empty else float(values.iloc[-1])
            self._count = len(candles)
            self._prev_close = float(candles["close"].iloc[-1])
            self._atr = self._last_value
            self._initialized = True
            self._tr_sum = 0.0
            return values

        # O(1) streaming update: Wilder ATR is recursive, so keep only the
        # previous close, current ATR, count, and seed sum.
        if self._count == 0:
            true_range = float(candles["high"]) - float(candles["low"])
        else:
            tr1 = float(candles["high"]) - float(candles["low"])
            tr2 = abs(float(candles["high"]) - self._prev_close)
            tr3 = abs(float(candles["low"]) - self._prev_close)
            true_range = max(tr1, tr2, tr3)

        self._count += 1
        self._prev_close = float(candles["close"])

        if not self._initialized:
            self._tr_sum += true_range
            if self._count == self._period and self._period != 0:
                self._atr = self._tr_sum / self._period
                self._initialized = True
        else:
            self._atr = ((self._atr * (self._period - 1)) + true_range) / self._period

        self._last_value = self._atr if self._initialized else 0.0
        return self._last_value


class Donchain(TechIndicator):
    def __init__(self, period: int, band: int) -> None:
        self._period = period
        self._band_type = band
        self._index = 0
        self._high_queue = CircularBuffer[tuple[int, float]](period + 1)
        self._low_queue = CircularBuffer[tuple[int, float]](period + 1)
        self._upper_band = 0.0
        self._lower_band = 0.0
        self._middle_band = 0.0
        self._initialized = False
        self._last_value = 0.0

    def update(self, candles: pd.DataFrame | pd.Series | dict) -> pd.Series | float:
        if isinstance(candles, pd.DataFrame):
            upper_band = candles["high"].rolling(window=self._period, min_periods=self._period).max().fillna(0.0)
            lower_band = candles["low"].rolling(window=self._period, min_periods=self._period).min().fillna(0.0)
            middle_band = (upper_band + lower_band) / 2.0

            self._index = len(candles)
            self._high_queue = CircularBuffer[tuple[int, float]](self._period + 1)
            self._low_queue = CircularBuffer[tuple[int, float]](self._period + 1)

            start_index = max(0, len(candles) - self._period)
            for index in range(start_index, len(candles)):
                high = float(candles["high"].iloc[index])
                low = float(candles["low"].iloc[index])

                while not self._high_queue.is_empty():
                    back = self._high_queue.backValue()
                    if back is None or back[1] > high:
                        break
                    self._high_queue.pop_back()
                self._high_queue.push_back((index, high))

                while not self._low_queue.is_empty():
                    back = self._low_queue.backValue()
                    if back is None or back[1] < low:
                        break
                    self._low_queue.pop_back()
                self._low_queue.push_back((index, low))

            self._initialized = len(candles) >= self._period and self._period != 0
            if self._initialized:
                high_front = self._high_queue.frontValue()
                low_front = self._low_queue.frontValue()
                if high_front is not None and low_front is not None:
                    self._upper_band = high_front[1]
                    self._lower_band = low_front[1]
                    self._middle_band = (self._upper_band + self._lower_band) / 2.0

            if self._band_type == 1:
                self._last_value = 0.0 if lower_band.empty else float(lower_band.iloc[-1])
                return lower_band
            if self._band_type == 2:
                self._last_value = 0.0 if middle_band.empty else float(middle_band.iloc[-1])
                return middle_band
            if self._band_type == 3:
                self._last_value = 0.0 if upper_band.empty else float(upper_band.iloc[-1])
                return upper_band
            return pd.Series(0.0, index=candles.index)

        # O(1) amortized streaming update: monotonic queues keep rolling
        # max/min without calling rolling().max()/min() on the full column.
        high = float(candles["high"])
        low = float(candles["low"])

        while not self._high_queue.is_empty():
            back = self._high_queue.backValue()
            if back is None or back[1] > high:
                break
            self._high_queue.pop_back()
        self._high_queue.push_back((self._index, high))

        while not self._low_queue.is_empty():
            back = self._low_queue.backValue()
            if back is None or back[1] < low:
                break
            self._low_queue.pop_back()
        self._low_queue.push_back((self._index, low))

        while not self._high_queue.is_empty():
            front = self._high_queue.frontValue()
            if front is None or front[0] > self._index - self._period:
                break
            self._high_queue.pop_front()

        while not self._low_queue.is_empty():
            front = self._low_queue.frontValue()
            if front is None or front[0] > self._index - self._period:
                break
            self._low_queue.pop_front()

        self._index += 1

        if self._index >= self._period and self._period != 0:
            high_front = self._high_queue.frontValue()
            low_front = self._low_queue.frontValue()
            if high_front is not None and low_front is not None:
                self._upper_band = high_front[1]
                self._lower_band = low_front[1]
                self._middle_band = (self._upper_band + self._lower_band) / 2.0
                self._initialized = True

        if not self._initialized:
            self._last_value = 0.0
        elif self._band_type == 1:
            self._last_value = self._lower_band
        elif self._band_type == 2:
            self._last_value = self._middle_band
        elif self._band_type == 3:
            self._last_value = self._upper_band
        else:
            self._last_value = 0.0

        return self._last_value


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
        self._last_value = 0.0

    def update(self, candles: pd.DataFrame | pd.Series | dict) -> pd.Series | float:
        if isinstance(candles, pd.DataFrame):
            atr = self._atr.update(candles)
            hl2 = (candles["high"] + candles["low"]) / 2.0
            basic_upper_band = hl2 + (self._multiplier * atr)
            basic_lower_band = hl2 - (self._multiplier * atr)

            super_trend = pd.Series(0.0, index=candles.index)
            final_upper_band = pd.Series(0.0, index=candles.index)
            final_lower_band = pd.Series(0.0, index=candles.index)

            initialized = False
            prev_close = 0.0
            prev_final_upper_band = 0.0
            prev_final_lower_band = 0.0
            prev_super_trend = 0.0

            # Loop required because SuperTrend is stateful: each final band and
            # trend decision depends on the previous candle's bands and trend.
            for index in range(len(candles)):
                if atr.iloc[index] == 0:
                    prev_close = candles["close"].iloc[index]
                    continue

                if not initialized:
                    prev_final_upper_band = basic_upper_band.iloc[index]
                    prev_final_lower_band = basic_lower_band.iloc[index]
                    if candles["close"].iloc[index] <= prev_final_upper_band:
                        prev_super_trend = prev_final_upper_band
                    else:
                        prev_super_trend = prev_final_lower_band

                    final_upper_band.iloc[index] = prev_final_upper_band
                    final_lower_band.iloc[index] = prev_final_lower_band
                    super_trend.iloc[index] = prev_super_trend
                    initialized = True
                    prev_close = candles["close"].iloc[index]
                    continue

                if basic_upper_band.iloc[index] < prev_final_upper_band or prev_close > prev_final_upper_band:
                    current_final_upper_band = basic_upper_band.iloc[index]
                else:
                    current_final_upper_band = prev_final_upper_band

                if basic_lower_band.iloc[index] > prev_final_lower_band or prev_close < prev_final_lower_band:
                    current_final_lower_band = basic_lower_band.iloc[index]
                else:
                    current_final_lower_band = prev_final_lower_band

                if prev_super_trend == prev_final_upper_band:
                    if candles["close"].iloc[index] <= current_final_upper_band:
                        current_super_trend = current_final_upper_band
                    else:
                        current_super_trend = current_final_lower_band
                else:
                    if candles["close"].iloc[index] >= current_final_lower_band:
                        current_super_trend = current_final_lower_band
                    else:
                        current_super_trend = current_final_upper_band

                final_upper_band.iloc[index] = current_final_upper_band
                final_lower_band.iloc[index] = current_final_lower_band
                super_trend.iloc[index] = current_super_trend

                prev_final_upper_band = current_final_upper_band
                prev_final_lower_band = current_final_lower_band
                prev_super_trend = current_super_trend
                prev_close = candles["close"].iloc[index]

            self._initialized = initialized
            self._prev_close = 0.0 if candles.empty else float(candles["close"].iloc[-1])
            self._prev_final_upper_band = prev_final_upper_band
            self._prev_final_lower_band = prev_final_lower_band
            self._super_trend = prev_super_trend
            self._last_value = 0.0 if super_trend.empty else float(super_trend.iloc[-1])
            return super_trend

        # O(1) streaming update: SuperTrend only needs the current candle,
        # current ATR, and previous final bands/trend.
        atr_value = self._atr.update(candles)

        if atr_value == 0:
            self._prev_close = float(candles["close"])
            self._last_value = 0.0
            return self._last_value

        hl2 = (float(candles["high"]) + float(candles["low"])) / 2.0
        basic_upper_band = hl2 + (self._multiplier * atr_value)
        basic_lower_band = hl2 - (self._multiplier * atr_value)

        if not self._initialized:
            self._prev_final_upper_band = basic_upper_band
            self._prev_final_lower_band = basic_lower_band
            if float(candles["close"]) <= self._prev_final_upper_band:
                self._super_trend = self._prev_final_upper_band
            else:
                self._super_trend = self._prev_final_lower_band
            self._initialized = True
            self._prev_close = float(candles["close"])
            self._last_value = self._super_trend
            return self._last_value

        if basic_upper_band < self._prev_final_upper_band or self._prev_close > self._prev_final_upper_band:
            final_upper_band = basic_upper_band
        else:
            final_upper_band = self._prev_final_upper_band

        if basic_lower_band > self._prev_final_lower_band or self._prev_close < self._prev_final_lower_band:
            final_lower_band = basic_lower_band
        else:
            final_lower_band = self._prev_final_lower_band

        if self._super_trend == self._prev_final_upper_band:
            if float(candles["close"]) <= final_upper_band:
                self._super_trend = final_upper_band
            else:
                self._super_trend = final_lower_band
        else:
            if float(candles["close"]) >= final_lower_band:
                self._super_trend = final_lower_band
            else:
                self._super_trend = final_upper_band

        self._prev_final_upper_band = final_upper_band
        self._prev_final_lower_band = final_lower_band
        self._prev_close = float(candles["close"])
        self._last_value = self._super_trend
        return self._last_value


def make_indicator(indicator_type: type[IndicatorT], *args) -> IndicatorT:
    return indicator_type(*args)
