import unittest

from src.base62 import BASE62_ALPHABET, decode, encode


class Base62Tests(unittest.TestCase):
    def test_encode_zero(self):
        self.assertEqual(encode(0), "0")

    def test_encode_and_decode_alphabet(self):
        for value, character in enumerate(BASE62_ALPHABET):
            with self.subTest(value=value, character=character):
                self.assertEqual(encode(value), character)
                self.assertEqual(decode(character), value)

    def test_encode_and_decode_multiple_digits(self):
        self.assertEqual(encode(62), "10")
        for value in (62, 123456789, 62**20 + 12345):
            with self.subTest(value=value):
                self.assertEqual(decode(encode(value)), value)

    def test_encode_rejects_negative_integer(self):
        with self.assertRaises(ValueError):
            encode(-1)

    def test_decode_rejects_empty_or_invalid_string(self):
        for text in ("", "!", "a-"):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    decode(text)


if __name__ == "__main__":
    unittest.main()
