import unittest

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable


class HashTableTestCases:
    table_type = HashTable

    def test_find_membership_and_load_factor(self):
        table = self.table_type(capacity=8, max_load=None)
        self.assertEqual(table.load_factor, 0)

        table.put("a", "first")
        table.put("i", "second")

        self.assertIn("a", table)
        self.assertIn("i", table)
        self.assertNotIn("missing", table)
        self.assertEqual(table.find("a")[0], "first")
        self.assertEqual(table.find("i")[0], "second")
        self.assertIsNone(table.find("missing")[0])
        self.assertEqual(table.load_factor, 2 / 8)

        table.put("nullable", None)
        self.assertIn("nullable", table)
        self.assertEqual(table.load_factor, 3 / 8)

    def test_colliding_keys_keep_separate_values(self):
        table = self.table_type(capacity=8)
        self.assertEqual(table.bucket_index("a"), table.bucket_index("i"))

        table.put("a", "first")
        table.put("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")

    def test_put_updates_existing_key_without_increasing_size(self):
        table = self.table_type(capacity=8)

        table.put("a", "first")
        table.put("a", "second")

        self.assertEqual(table.get("a"), "second")
        self.assertEqual(len(table), 1)

    def test_resizes_only_after_load_factor_exceeds_three_quarters(self):
        table = self.table_type(capacity=8)

        for index in range(6):
            table.put(f"key-{index}", index)
        self.assertEqual(table.capacity, 8)

        table.put("key-6", 6)

        self.assertEqual(table.capacity, 16)
        for index in range(7):
            with self.subTest(index=index):
                self.assertEqual(table.get(f"key-{index}"), index)

    def test_horner_hash_uses_unicode_code_point_for_korean_key(self):
        table = self.table_type(capacity=8)

        self.assertEqual(table.bucket_index("가"), 0)
        self.assertEqual(table.bucket_index("ab"), 1)


class HashTableProbeCountingTests(unittest.TestCase):
    def test_find_counts_chained_nodes_and_linear_slots(self):
        chaining = HashTable(capacity=8, max_load=None)
        linear = LinearProbingHashTable(capacity=8, max_load=None)
        for table in (chaining, linear):
            table.put("g", "first")
            table.put("o", "second")
            table.put("w", "third")

        self.assertEqual(chaining.find("g"), ("first", 3))
        self.assertEqual(chaining.find("w"), ("third", 1))
        self.assertEqual(chaining.find("?"), (None, 3))
        self.assertEqual(linear.find("g"), ("first", 1))
        self.assertEqual(linear.find("o"), ("second", 2))
        self.assertEqual(linear.find("w"), ("third", 3))
        self.assertEqual(linear.find("?"), (None, 4))


class HashTableTests(HashTableTestCases, unittest.TestCase):
    table_type = HashTable

    def test_max_load_none_disables_resizing(self):
        table = HashTable(capacity=8, max_load=None)

        for index in range(9):
            table.put(f"key-{index}", index)

        self.assertEqual(table.capacity, 8)
        for index in range(9):
            with self.subTest(index=index):
                self.assertEqual(table.get(f"key-{index}"), index)


class LinearProbingHashTableCommonTests(HashTableTestCases, unittest.TestCase):
    table_type = LinearProbingHashTable


if __name__ == "__main__":
    unittest.main()
