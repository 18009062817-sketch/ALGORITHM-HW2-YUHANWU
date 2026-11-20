from __future__ import annotations

from typing import Generic, TypeVar


Value = TypeVar("Value")


class _Node(Generic[Value]):
    def __init__(
        self, key: str, value: Value, next_node: _Node[Value] | None = None
    ) -> None:
        self.key = key
        self.value = value
        self.next = next_node


class HashTable(Generic[Value]):
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
        self._buckets: list[_Node[Value] | None] = [None] * capacity

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def load_factor(self) -> float:
        return self._size / self._capacity

    def bucket_index(self, key: str) -> int:
        if not isinstance(key, str):
            raise TypeError("key must be a string")

        value = 0
        for character in key:
            value = (31 * value + ord(character)) % self._capacity
        return value

    def put(self, key: str, value: Value) -> None:
        index = self.bucket_index(key)
        node = self._buckets[index]
        while node is not None:
            if node.key == key:
                node.value = value
                return
            node = node.next

        self._buckets[index] = _Node(key, value, self._buckets[index])
        self._size += 1
        if self.max_load is not None and self.load_factor > self.max_load:
            self._resize(self._capacity * 2)

    def get(self, key: str) -> Value:
        node, _ = self._find_node(key)
        if node is None:
            raise KeyError(key)
        return node.value

    def find(self, key: str) -> tuple[Value | None, int]:
        node, probes = self._find_node(key)
        return (None if node is None else node.value), probes

    def __contains__(self, key: object) -> bool:
        if not isinstance(key, str):
            return False
        node, _ = self._find_node(key)
        return node is not None

    def _find_node(self, key: str) -> tuple[_Node[Value] | None, int]:
        node = self._buckets[self.bucket_index(key)]
        probes = 0
        while node is not None:
            probes += 1
            if node.key == key:
                return node, probes
            node = node.next
        return None, probes

    def delete(self, key: str) -> Value:
        index = self.bucket_index(key)
        node = self._buckets[index]
        previous: _Node[Value] | None = None
        while node is not None:
            if node.key == key:
                if previous is None:
                    self._buckets[index] = node.next
                else:
                    previous.next = node.next
                self._size -= 1
                return node.value
            previous = node
            node = node.next
        raise KeyError(key)

    def __len__(self) -> int:
        return self._size

    def _resize(self, capacity: int) -> None:
        old_buckets = self._buckets
        self._capacity = capacity
        self._buckets = [None] * capacity

        for bucket in old_buckets:
            node = bucket
            while node is not None:
                next_node = node.next
                index = self.bucket_index(node.key)
                node.next = self._buckets[index]
                self._buckets[index] = node
                node = next_node
