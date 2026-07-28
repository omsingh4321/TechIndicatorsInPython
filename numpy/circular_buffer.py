from __future__ import annotations

from typing import Generic, TypeVar

import numpy as np


T = TypeVar("T")


class CircularBuffer(Generic[T]):
    def __init__(self, capacity: int, dtype: type | str = object) -> None:
        if capacity < 0:
            raise ValueError("capacity must be non-negative")

        self._capacity = capacity
        self._data = np.empty(capacity, dtype=dtype)
        self._front = 0
        self._rear = 0
        self._count = 0

    def push(self, value: T) -> None:
        if self.is_full() or self._capacity == 0:
            return

        self._data[self._rear] = value
        self._rear = (self._rear + 1) % self._capacity
        self._count += 1

    def pop(self) -> T | None:
        if self.is_empty() or self._capacity == 0:
            return None

        value = self._data[self._front]
        self._front = (self._front + 1) % self._capacity
        self._count -= 1
        return value.item() if hasattr(value, "item") else value

    def pop_back(self) -> T | None:
        if self.is_empty() or self._capacity == 0:
            return None

        self._rear = (self._rear - 1 + self._capacity) % self._capacity
        value = self._data[self._rear]
        self._count -= 1
        return value.item() if hasattr(value, "item") else value

    def push_back(self, value: T) -> None:
        self.push(value)

    def pop_front(self) -> T | None:
        return self.pop()

    def front_value(self) -> T | None:
        if self.is_empty() or self._capacity == 0:
            return None

        value = self._data[self._front]
        return value.item() if hasattr(value, "item") else value

    def back_value(self) -> T | None:
        if self.is_empty() or self._capacity == 0:
            return None

        value = self._data[(self._rear - 1 + self._capacity) % self._capacity]
        return value.item() if hasattr(value, "item") else value

    def get_size(self) -> int:
        return self._count

    def get_capacity(self) -> int:
        return self._capacity

    def is_full(self) -> bool:
        return self._count == self._capacity

    def is_empty(self) -> bool:
        return self._count == 0
