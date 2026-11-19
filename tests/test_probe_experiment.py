import unittest

from experiments.probe_experiment import _count_probes
from src.hash_table import HashTable


class ProbeExperimentTests(unittest.TestCase):
    def test_counts_nodes_compared_for_found_and_missing_keys(self) -> None:
        table: HashTable[str] = HashTable(capacity=1, max_load=None)
        table.put("first", "first")
        table.put("second", "second")

        self.assertEqual(_count_probes(table, "second"), 1)
        self.assertEqual(_count_probes(table, "first"), 2)
        self.assertEqual(_count_probes(table, "missing"), 2)

    def test_empty_bucket_miss_has_zero_probes(self) -> None:
        table: HashTable[str] = HashTable(capacity=2, max_load=None)
        table.put("a", "value")

        self.assertEqual(_count_probes(table, "b"), 0)


if __name__ == "__main__":
    unittest.main()
