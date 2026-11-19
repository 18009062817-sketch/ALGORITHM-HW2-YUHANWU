from __future__ import annotations

from typing import Generic, TypeVar


Value = TypeVar("Value")


class _Entry(Generic[Value]):
    def __init__(self, key: str, value: Value) -> None:
        self.key = key
        self.value = value


class _Deleted:
    pass


_DELETED = _Deleted()


class LinearProbingHashTable(Generic[Value]):
    def __init__(
        self, capacity: int = 8, max_load: float | None = 0.75
    ) -> None:
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if max_load is not None and max_load <= 0:
            raise ValueError("max_load must be positive or None")

        self._capacity = capacity
        self.max_load = max_load
        self._size = 0
        self._slots: list[_Entry[Value] | _Deleted | None] = [None] * capacity

    @property
    def capacity(self) -> int:
        return self._capacity

    def bucket_index(self, key: str) -> int:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

        value = 0
        for character in key:
            value = (31 * value + ord(character)) % self._capacity
        return value

    def slot_index(self, key: str) -> int:
        index = self._find_slot(key)
        if index is None:
            raise KeyError(key)
        return index

    def put(self, key: str, value: Value) -> None:
        existing_index = self._find_slot(key)
        if existing_index is not None:
            entry = self._slots[existing_index]
            if isinstance(entry, _Entry):
                entry.value = value
                return

        if self._size == self._capacity:
            if self.max_load is None:
                raise OverflowError("hash table is full")
            self._resize(self._capacity * 2)

        insertion_index = self._find_insertion_slot(key)
        if insertion_index is None:
            raise OverflowError("hash table is full")

        self._slots[insertion_index] = _Entry(key, value)
        self._size += 1
        if self.max_load is not None and self._size / self._capacity > self.max_load:
            self._resize(self._capacity * 2)

    def get(self, key: str) -> Value:
        index = self._find_slot(key)
        if index is None:
            raise KeyError(key)

        entry = self._slots[index]
        if not isinstance(entry, _Entry):
            raise KeyError(key)
        return entry.value

    def delete(self, key: str) -> Value:
        index = self._find_slot(key)
        if index is None:
            raise KeyError(key)

        entry = self._slots[index]
        if not isinstance(entry, _Entry):
            raise KeyError(key)
        self._slots[index] = _DELETED
        self._size -= 1
        return entry.value

    def __len__(self) -> int:
        return self._size

    def _find_slot(self, key: str) -> int | None:
        start = self.bucket_index(key)
        for offset in range(self._capacity):
            index = (start + offset) % self._capacity
            entry = self._slots[index]
            if entry is None:
                return None
            if isinstance(entry, _Entry) and entry.key == key:
                return index
        return None

    def _find_insertion_slot(self, key: str) -> int | None:
        start = self.bucket_index(key)
        first_deleted: int | None = None
        for offset in range(self._capacity):
            index = (start + offset) % self._capacity
            entry = self._slots[index]
            if isinstance(entry, _Deleted):
                if first_deleted is None:
                    first_deleted = index
            elif entry is None:
                return first_deleted if first_deleted is not None else index
        return first_deleted

    def _resize(self, capacity: int) -> None:
        old_slots = self._slots
        self._capacity = capacity
        self._slots = [None] * capacity
        self._size = 0

        for entry in old_slots:
            if isinstance(entry, _Entry):
                index = self._find_insertion_slot(entry.key)
                if index is None:
                    raise OverflowError("hash table is full")
                self._slots[index] = entry
                self._size += 1
