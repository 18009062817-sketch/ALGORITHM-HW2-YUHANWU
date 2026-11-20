import unittest

from src.linear_probing import LinearProbingHashTable


class LinearProbingHashTableTests(unittest.TestCase):
    def test_colliding_keys_wrap_around_and_keep_separate_values(self):
        table = LinearProbingHashTable(capacity=8, max_load=None)
        keys = ("g", "o", "w")

        for key in keys:
            self.assertEqual(table.bucket_index(key), 7)

        for key, value in zip(keys, ("first", "second", "third")):
            table.put(key, value)

        self.assertEqual([table.slot_index(key) for key in keys], [7, 0, 1])
        self.assertEqual(table.get("g"), "first")
        self.assertEqual(table.get("o"), "second")
        self.assertEqual(table.get("w"), "third")
        self.assertEqual(len(table), 3)

    def test_updating_existing_key_preserves_size(self):
        table = LinearProbingHashTable(capacity=8, max_load=None)

        table.put("g", "first")
        table.put("g", "updated")

        self.assertEqual(table.get("g"), "updated")
        self.assertEqual(table.slot_index("g"), 7)
        self.assertEqual(len(table), 1)

    def test_deleting_first_key_keeps_later_cluster_keys_reachable(self):
        table = LinearProbingHashTable(capacity=8, max_load=None)
        table.put("g", "first")
        table.put("o", "second")
        table.put("w", "third")

        self.assertEqual(table.delete("g"), "first")

        self.assertEqual(table.get("o"), "second")
        self.assertEqual(table.get("w"), "third")
        self.assertEqual(len(table), 2)

    def test_full_table_updates_existing_key_and_bounds_missing_search(self):
        table = LinearProbingHashTable(capacity=8, max_load=None)
        for index in range(8):
            table.put(f"key-{index}", index)

        table.put("key-0", "updated")

        self.assertEqual(table.get("key-0"), "updated")
        self.assertEqual(len(table), 8)
        with self.assertRaises(OverflowError):
            table.put("new-key", "new value")
        self.assertEqual(table.find("missing"), (None, 8))


if __name__ == "__main__":
    unittest.main()
