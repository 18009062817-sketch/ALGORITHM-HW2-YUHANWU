import unittest

from src.shortener import URLShortener


class URLShortenerTestCases:
    strategy = "chaining"

    def setUp(self):
        self.shortener = URLShortener(strategy=self.strategy)

    def test_duplicate_url_reuses_code_without_consuming_an_id(self):
        url = "https://example.com/"

        first_code = self.shortener.shorten(url)
        duplicate_code = self.shortener.shorten(url)
        next_code = self.shortener.shorten("https://example.org/")

        self.assertEqual(first_code, "0")
        self.assertEqual(duplicate_code, first_code)
        self.assertEqual(next_code, "1")

    def test_2048_character_url_is_accepted_and_2049_is_rejected(self):
        prefix = "https://example.com/"
        url_2048 = prefix + "a" * (2048 - len(prefix))
        url_2049 = url_2048 + "a"

        code = self.shortener.shorten(url_2048)
        self.assertEqual(code, "0")
        self.assertEqual(self.shortener.expand(code), url_2048)

        with self.assertRaises(ValueError):
            self.shortener.shorten(url_2049)

        self.assertEqual(self.shortener.shorten("https://example.org/"), "1")

    def test_invalid_urls_raise_value_error_without_consuming_ids(self):
        invalid_urls = (
            "",
            "example.com",
            "ftp://example.com",
            "https:///path",
            "https://example.com:0/",
            " https://example.com/",
        )

        for url in invalid_urls:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    self.shortener.shorten(url)

        self.assertEqual(self.shortener.shorten("https://example.com/a?q=1"), "0")

    def test_distinct_url_strings_get_distinct_codes(self):
        without_trailing_slash = self.shortener.shorten("https://example.com")
        with_trailing_slash = self.shortener.shorten("https://example.com/")

        self.assertNotEqual(without_trailing_slash, with_trailing_slash)

    def test_expand_returns_original_url(self):
        url = "http://localhost:8000/"

        code = self.shortener.shorten(url)

        self.assertEqual(self.shortener.expand(code), url)

    def test_expand_rejects_unregistered_and_malformed_codes(self):
        with self.assertRaises(KeyError):
            self.shortener.expand("Z")

        for code in ("", "a-"):
            with self.subTest(code=code):
                with self.assertRaises(ValueError):
                    self.shortener.expand(code)

    def test_chaining_and_linear_probing_modes_reuse_codes(self):
        url = "https://example.com/shared"

        for strategy in ("chaining", "linear-probing"):
            with self.subTest(strategy=strategy):
                shortener = URLShortener(strategy=strategy)
                first_code = shortener.shorten(url)
                duplicate_code = shortener.shorten(url)

                self.assertEqual(first_code, "0")
                self.assertEqual(duplicate_code, first_code)
                self.assertEqual(shortener.expand(first_code), url)
                self.assertEqual(shortener.shorten("https://example.org/"), "1")

    def test_chaining_remains_the_default_strategy(self):
        self.assertEqual(URLShortener().strategy, "chaining")


class URLShortenerTests(URLShortenerTestCases, unittest.TestCase):
    strategy = "chaining"


class LinearProbingURLShortenerTests(URLShortenerTestCases, unittest.TestCase):
    strategy = "linear-probing"


if __name__ == "__main__":
    unittest.main()
