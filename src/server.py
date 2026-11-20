from __future__ import annotations

import argparse
import json
from html import escape
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote, urlsplit

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable, _Deleted, _Entry
from src.shortener import URLShortener


HOME_PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>URL Shortener</title>
</head>
<body>
  <main>
    <h1>URL Shortener</h1>
    <form id="shorten-form">
      <label for="url">URL</label>
      <input id="url" name="url" type="url" required>
      <button type="submit">Shorten</button>
    </form>
    <p id="error" role="alert"></p>
    <a id="short-url" hidden></a>
  </main>
  <script>
    const form = document.getElementById('shorten-form');
    const error = document.getElementById('error');
    const link = document.getElementById('short-url');
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      error.textContent = '';
      link.hidden = true;
      try {
        const response = await fetch('/shorten', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: document.getElementById('url').value })
        });
        const data = await response.json();
        if (!response.ok) {
          error.textContent = data.error || 'Unable to shorten this URL.';
          return;
        }
        link.href = data.short_url;
        link.textContent = data.short_url;
        link.hidden = false;
      } catch {
        error.textContent = 'Unable to contact the URL shortener.';
      }
    });
  </script>
</body>
</html>
"""


def create_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    shortener: URLShortener | None = None,
    strategy: str = "chaining",
) -> HTTPServer:
    url_shortener = (
        shortener if shortener is not None else URLShortener(strategy=strategy)
    )

    class URLShortenerHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/":
                self._send_html(HOME_PAGE)
            elif path == "/table":
                self._send_html(self._render_table())
            elif path.startswith("/r/"):
                self._redirect(unquote(path[3:]))
            else:
                self._send_json(404, {"error": "Not found"})

        def do_POST(self) -> None:
            if urlsplit(self.path).path != "/shorten":
                self._send_json(404, {"error": "Not found"})
                return

            content_length = self.headers.get("Content-Length")
            try:
                length = int(content_length) if content_length is not None else -1
            except ValueError:
                length = -1
            if length < 0 or length > 16_384:
                self._send_json(400, {"error": "Invalid JSON request body"})
                return

            try:
                payload = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json(400, {"error": "Invalid JSON request body"})
                return
            if not isinstance(payload, dict) or not isinstance(
                payload.get("url"), str
            ):
                self._send_json(400, {"error": "JSON body must contain a URL string"})
                return

            try:
                code, is_new = url_shortener.shorten_with_status(payload["url"])
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
                return

            short_url = f"{self._public_base_url()}/r/{code}"
            self._send_json(
                201 if is_new else 200,
                {"code": code, "short_url": short_url},
            )

        def _redirect(self, code: str) -> None:
            try:
                url = url_shortener.expand(code)
            except ValueError as error:
                self._send_json(400, {"error": str(error)})
                return
            except KeyError:
                self._send_json(404, {"error": "Short code not found"})
                return

            self.send_response(302)
            self.send_header("Location", url)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _public_base_url(self) -> str:
            forwarded_host = self.headers.get("X-Forwarded-Host")
            host = (forwarded_host or self.headers.get("Host") or "").split(",")[
                0
            ].strip()
            if not host:
                host = f"{self.server.server_name}:{self.server.server_port}"

            forwarded_proto = self.headers.get("X-Forwarded-Proto", "http")
            scheme = forwarded_proto.split(",")[0].strip().lower()
            if scheme not in ("http", "https"):
                scheme = "http"
            return f"{scheme}://{host}"

        def _render_table(self) -> str:
            table = url_shortener._url_to_code
            if isinstance(table, HashTable):
                return self._render_chaining_table(table)
            if isinstance(table, LinearProbingHashTable):
                return self._render_linear_table(table)
            raise RuntimeError("unsupported hash table strategy")

        def _render_chaining_table(self, table: HashTable[str]) -> str:
            parts = [
                "<!doctype html>",
                '<html lang="en"><head><meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                "<title>Hash table</title></head><body>",
                "<h1>URL-to-code hash table</h1>",
            ]
            for bucket_index, first_node in enumerate(table._buckets):
                parts.append(
                    f'<section id="bucket-{bucket_index}"><h2>Bucket {bucket_index}</h2>'
                )
                if first_node is None:
                    parts.append("<p>Empty bucket</p>")
                else:
                    parts.append('<div class="chain">')
                    node = first_node
                    while node is not None:
                        parts.append(
                            self._render_entry(
                                table, node.key, node.value, bucket_index, False
                            )
                        )
                        if node.next is not None:
                            parts.append('<span class="chain-arrow">&rarr;</span>')
                        node = node.next
                    parts.append("</div>")
                parts.append("</section>")
            parts.append("</body></html>")
            return "\n".join(parts)

        def _render_linear_table(self, table: LinearProbingHashTable[str]) -> str:
            parts = [
                "<!doctype html>",
                '<html lang="en"><head><meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                "<title>Linear probing hash table</title></head><body>",
                "<h1>URL-to-code linear probing table</h1>",
            ]
            for slot_index, entry in enumerate(table._slots):
                parts.append(
                    f'<section id="slot-{slot_index}"><h2>Slot {slot_index}</h2>'
                )
                if entry is None:
                    parts.append("<p>Empty slot</p>")
                elif isinstance(entry, _Deleted):
                    parts.append("<p>Deleted slot</p>")
                elif isinstance(entry, _Entry):
                    parts.append(
                        self._render_entry(
                            table, entry.key, entry.value, slot_index, True
                        )
                    )
                parts.append("</section>")
            parts.append("</body></html>")
            return "\n".join(parts)

        def _render_entry(
            self,
            table: HashTable[str] | LinearProbingHashTable[str],
            url: str,
            code: str,
            actual_index: int,
            linear_probing: bool,
        ) -> str:
            start_index = table.bucket_index(url)
            short_url = f"{self._public_base_url()}/r/{code}"
            start_label = (
                "Horner hash start slot"
                if linear_probing
                else "Horner hash start bucket"
            )
            actual_label = (
                "Actual stored slot" if linear_probing else "Stored bucket"
            )
            parts = [
                "<article><details><summary>",
                f"{escape(url)} &rarr; {escape(code)}",
                "</summary>",
                f"<p>URL: {escape(url)}</p>",
                f"<p>Code: {escape(code)}</p>",
                f'<p>Short link: <a href="{escape(short_url, quote=True)}">',
                f"{escape(short_url)}</a></p>",
                f"<p>{start_label}: {start_index}</p>",
                f"<p>{actual_label}: {actual_index}</p>",
            ]
            if linear_probing:
                parts.append(f"<p>Probes: {table.find(url)[1]}</p>")
            parts.append("<details><summary>Horner hash steps</summary><ol>")
            value = 0
            for character in url:
                previous = value
                value = (31 * value + ord(character)) % table.capacity
                parts.append(
                    "<li>"
                    f"h = (31 * {previous} + ord({escape(repr(character))})) "
                    f"% {table.capacity} = {value}"
                    "</li>"
                )
            parts.append(
                f"</ol><p>Final bucket: {value}</p></details></details></article>"
            )
            return "\n".join(parts)

        def _send_html(self, content: str) -> None:
            self._send_body(200, content.encode("utf-8"), "text/html; charset=utf-8")

        def _send_json(self, status: int, payload: dict[str, str]) -> None:
            content = json.dumps(payload).encode("utf-8")
            self._send_body(status, content, "application/json; charset=utf-8")

        def _send_body(self, status: int, content: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    return HTTPServer((host, port), URLShortenerHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the URL shortener web server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--strategy",
        choices=("chaining", "linear-probing"),
        default="chaining",
    )
    args = parser.parse_args()

    server = create_server(args.host, args.port, strategy=args.strategy)
    print(f"Serving on http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
