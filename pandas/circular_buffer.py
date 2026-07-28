from __future__ import annotations

from array import array
from typing import Generic, TypeVar


T = TypeVar("T")


class CircularBuffer(Generic[T]):
    def __init__(self, capacity: int, typecode: str | None = None) -> None:
        if capacity < 0:
            raise ValueError("capacity must be non-negative")

        self._capacity = capacity
        self._typecode = typecode
        if typecode is None:
            self._data: list[T | None] | array = [None] * capacity
        else:
            self._data = array(typecode, [0]) * capacity
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
        self._clear_slot(self._front)
        self._front = (self._front + 1) % self._capacity
        self._count -= 1
        return value

    def pop_back(self) -> T | None:
        if self.is_empty() or self._capacity == 0:
            return None

        self._rear = (self._rear - 1 + self._capacity) % self._capacity
        value = self._data[self._rear]
        self._clear_slot(self._rear)
        self._count -= 1
        return value

    def push_back(self, value: T) -> None:
        self.push(value)

    def pop_front(self) -> T | None:
        return self.pop()

    def frontValue(self) -> T | None:
        if self.is_empty() or self._capacity == 0:
            return None

        return self._data[self._front]

    def backValue(self) -> T | None:
        if self.is_empty() or self._capacity == 0:
            return None

        return self._data[(self._rear - 1 + self._capacity) % self._capacity]

    def getSize(self) -> int:
        return self._count

    def getCapacity(self) -> int:
        return self._capacity

    def is_full(self) -> bool:
        return self._count == self._capacity

    def is_empty(self) -> bool:
        return self._count == 0

    def _clear_slot(self, index: int) -> None:
        if self._typecode is None:
            self._data[index] = None
        else:
            self._data[index] = 0
