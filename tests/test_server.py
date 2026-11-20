import http.client
import json
import threading
import unittest
from http.server import HTTPServer

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable
from src.server import create_server
from src.shortener import URLShortener


class URLServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shortener = URLShortener()
        self.server, self.thread, self.port = self.start_server(self.shortener)

    def start_server(
        self, shortener: URLShortener | None = None, strategy: str = "chaining"
    ) -> tuple[HTTPServer, threading.Thread, int]:
        server = create_server("127.0.0.1", 0, shortener, strategy=strategy)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, server.server_address[1]

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
        port: int | None = None,
    ) -> tuple[int, dict[str, str], bytes]:
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.port if port is None else port
        )
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def post_url(
        self, url: str, port: int | None = None
    ) -> tuple[int, dict[str, str], dict[str, str]]:
        status, headers, body = self.request(
            "POST",
            "/shorten",
            json.dumps({"url": url}),
            {"Content-Type": "application/json"},
            port,
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

    def test_linear_probing_mode_shortens_duplicates_and_redirects(self) -> None:
        server, thread, port = self.start_server(strategy="linear-probing")
        url = "https://example.com/linear"

        try:
            status, _, first = self.post_url(url, port)
            self.assertEqual(status, 201)
            status, _, duplicate = self.post_url(url, port)
            self.assertEqual(status, 200)
            self.assertEqual(duplicate["code"], first["code"])

            status, headers, _ = self.request(
                "GET", f"/r/{first['code']}", port=port
            )
            self.assertEqual(status, 302)
            self.assertEqual(headers["Location"], url)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

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

        collision_start = page.index(f'id="bucket-{collision_bucket}"')
        collision_end = page.index("</section>", collision_start)
        collision_section = page[collision_start:collision_end]
        self.assertIn("Chain length: 2", collision_section)
        node_positions = sorted(
            (collision_section.index(first_url), collision_section.index(second_url))
        )
        arrow_position = collision_section.index(
            '<span class="chain-arrow">&rarr;</span>'
        )
        null_position = collision_section.index(
            '<span class="chain-arrow">&rarr; NULL</span>'
        )
        self.assertLess(node_positions[0], arrow_position)
        self.assertLess(arrow_position, node_positions[1])
        self.assertLess(node_positions[1], null_position)

        empty_bucket = next(
            bucket for bucket in range(8) if bucket != collision_bucket
        )
        empty_start = page.index(f'id="bucket-{empty_bucket}"')
        empty_end = page.index("</section>", empty_start)
        self.assertIn("Chain length: 0", page[empty_start:empty_end])

    def test_linear_probing_table_shows_hash_start_and_stored_slot(self) -> None:
        table: LinearProbingHashTable[str] = LinearProbingHashTable(
            capacity=8, max_load=None
        )
        first_by_bucket: dict[int, str] = {}
        collision_urls: tuple[str, str] | None = None
        start_slot = -1
        for index in range(100):
            url = f"https://example.com/linear-{index}"
            start = table.bucket_index(url)
            if start in first_by_bucket:
                collision_urls = first_by_bucket[start], url
                start_slot = start
                break
            first_by_bucket[start] = url

        self.assertIsNotNone(collision_urls)
        assert collision_urls is not None
        first_url, second_url = collision_urls
        stored_slot = (start_slot + 1) % table.capacity
        server, thread, port = self.start_server(strategy="linear-probing")

        try:
            self.assertEqual(self.post_url(first_url, port)[0], 201)
            self.assertEqual(self.post_url(second_url, port)[0], 201)
            status, _, body = self.request("GET", "/table", port=port)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

        page = body.decode("utf-8")
        self.assertEqual(status, 200)
        self.assertIn(f'id="slot-{start_slot}"', page)
        self.assertIn(f'id="slot-{stored_slot}"', page)
        self.assertIn(f"Horner hash start slot: {start_slot}", page)
        self.assertIn(f"Actual stored slot: {stored_slot}", page)
        self.assertIn("Empty slot", page)

    def test_linear_probing_table_shows_probe_count_after_wraparound(self) -> None:
        table: LinearProbingHashTable[str] = LinearProbingHashTable(
            capacity=8, max_load=None
        )
        urls = []
        for index in range(1000):
            url = f"https://example.com/wrap-{index}"
            if table.bucket_index(url) == 7:
                urls.append(url)
                if len(urls) == 3:
                    break

        self.assertEqual(len(urls), 3)
        shortener = URLShortener(strategy="linear-probing")
        server, thread, port = self.start_server(shortener)

        try:
            for url in urls:
                self.assertEqual(self.post_url(url, port)[0], 201)
            status, _, body = self.request("GET", "/table", port=port)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

        stored_table = shortener._url_to_code
        self.assertIsInstance(stored_table, LinearProbingHashTable)
        self.assertEqual([stored_table.slot_index(url) for url in urls], [7, 0, 1])
        self.assertEqual(status, 200)
        self.assertIn("Horner hash start slot: 7", body.decode("utf-8"))
        self.assertIn("Actual stored slot: 1", body.decode("utf-8"))
        self.assertIn("Probes: 3", body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
