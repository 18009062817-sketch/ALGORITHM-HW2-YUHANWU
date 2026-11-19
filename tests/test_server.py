import http.client
import json
import threading
import unittest

from src.hash_table import HashTable
from src.server import create_server
from src.shortener import URLShortener


class URLServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shortener = URLShortener()
        self.server = create_server("127.0.0.1", 0, self.shortener)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(
        self,
        method: str,
        path: str,
        body: bytes | str | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port)
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def post_url(self, url: str) -> tuple[int, dict[str, str], dict[str, str]]:
        status, headers, body = self.request(
            "POST",
            "/shorten",
            json.dumps({"url": url}),
            {"Content-Type": "application/json"},
        )
        return status, headers, json.loads(body)

    def test_home_page_has_url_form_and_clickable_result_link(self) -> None:
        status, headers, body = self.request("GET", "/")
        page = body.decode("utf-8")

        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("<form", page)
        self.assertIn("fetch('/shorten'", page)
        self.assertIn('<a id="short-url"', page)

    def test_post_shortens_new_url_then_returns_same_code_for_duplicate(self) -> None:
        url = "https://example.com/a?q=1"

        status, _, first = self.post_url(url)
        self.assertEqual(status, 201)
        self.assertEqual(first["code"], "0")
        self.assertEqual(
            first["short_url"],
            f"http://127.0.0.1:{self.port}/r/0",
        )

        status, _, second = self.post_url(url)
        self.assertEqual(status, 200)
        self.assertEqual(second, first)

    def test_short_url_uses_forwarded_codespaces_host_and_https(self) -> None:
        status, _, response = self.request(
            "POST",
            "/shorten",
            json.dumps({"url": "https://example.com/"}),
            {
                "Content-Type": "application/json",
                "X-Forwarded-Host": "sample-8000.app.github.dev",
                "X-Forwarded-Proto": "https",
            },
        )

        self.assertEqual(status, 201)
        self.assertEqual(
            json.loads(response)["short_url"],
            "https://sample-8000.app.github.dev/r/0",
        )

    def test_post_rejects_malformed_json_and_invalid_url(self) -> None:
        status, _, body = self.request(
            "POST",
            "/shorten",
            b'{"url":',
            {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

        status, _, body = self.request(
            "POST",
            "/shorten",
            json.dumps({"url": "ftp://example.com"}),
            {"Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertIn("error", json.loads(body))

    def test_redirect_and_not_found_or_invalid_codes(self) -> None:
        url = "https://example.com/redirect"
        _, _, response = self.post_url(url)
        code = response["code"]

        status, headers, _ = self.request("GET", f"/r/{code}")
        self.assertEqual(status, 302)
        self.assertEqual(headers["Location"], url)

        status, _, _ = self.request("GET", "/r/Z")
        self.assertEqual(status, 404)

        status, _, _ = self.request("GET", "/r/a-")
        self.assertEqual(status, 400)

    def test_table_shows_all_buckets_collisions_links_and_horner_steps(self) -> None:
        table: HashTable[str] = HashTable()
        first_by_bucket: dict[int, str] = {}
        collision_urls: tuple[str, str] | None = None
        collision_bucket = -1
        for index in range(100):
            url = f"https://example.com/item-{index}"
            bucket = table.bucket_index(url)
            if bucket in first_by_bucket:
                collision_urls = first_by_bucket[bucket], url
                collision_bucket = bucket
                break
            first_by_bucket[bucket] = url

        self.assertIsNotNone(collision_urls)
        assert collision_urls is not None
        first_url, second_url = collision_urls
        first_code = self.shortener.shorten(first_url)
        second_code = self.shortener.shorten(second_url)

        status, _, body = self.request("GET", "/table")
        page = body.decode("utf-8")

        self.assertEqual(status, 200)
        for bucket in range(8):
            self.assertIn(f'id="bucket-{bucket}"', page)
        self.assertIn("Empty bucket", page)
        self.assertIn("&rarr;", page)
        self.assertIn(first_url, page)
        self.assertIn(second_url, page)
        self.assertIn(f"/r/{first_code}", page)
        self.assertIn(f"/r/{second_code}", page)
        self.assertIn("Horner hash steps", page)
        self.assertIn("Final bucket", page)
        self.assertIn(f"Bucket {collision_bucket}", page)


if __name__ == "__main__":
    unittest.main()
