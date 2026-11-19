import unittest

from src.hash_table import HashTable


class HashTableTests(unittest.TestCase):
    def test_colliding_keys_keep_separate_values(self):
        table = HashTable(capacity=8)
        self.assertEqual(table.bucket_index("a"), table.bucket_index("i"))

        table.put("a", "first")
        table.put("i", "second")

        self.assertEqual(table.get("a"), "first")
        self.assertEqual(table.get("i"), "second")

    def test_put_updates_existing_key_without_increasing_size(self):
        table = HashTable(capacity=8)

        table.put("a", "first")
        table.put("a", "second")

        self.assertEqual(table.get("a"), "second")
        self.assertEqual(len(table), 1)

    def test_resizes_only_after_load_factor_exceeds_three_quarters(self):
        table = HashTable(capacity=8)

        for index in range(6):
            table.put(f"key-{index}", index)
        self.assertEqual(table.capacity, 8)

        table.put("key-6", 6)

        self.assertEqual(table.capacity, 16)
        for index in range(7):
            with self.subTest(index=index):
                self.assertEqual(table.get(f"key-{index}"), index)

    def test_max_load_none_disables_resizing(self):
        table = HashTable(capacity=8, max_load=None)

        for index in range(9):
            table.put(f"key-{index}", index)

        self.assertEqual(table.capacity, 8)
        for index in range(9):
            with self.subTest(index=index):
                self.assertEqual(table.get(f"key-{index}"), index)

    def test_horner_hash_uses_unicode_code_point_for_korean_key(self):
        table = HashTable(capacity=8)

        self.assertEqual(table.bucket_index("가"), 0)
        self.assertEqual(table.bucket_index("ab"), 1)

if __name__ == "__main__":
    unittest.main()
