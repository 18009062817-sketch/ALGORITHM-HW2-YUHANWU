from unicodedata import category
from urllib.parse import urlsplit

from src.base62 import decode, encode
from src.hash_table import HashTable


class URLShortener:
    def __init__(self) -> None:
        self._url_to_code: HashTable[str] = HashTable()
        self._code_to_url: HashTable[str] = HashTable()
        self._next_id = 0

    def shorten(self, url: str) -> str:
        self._validate_url(url)

        try:
            return self._url_to_code.get(url)
        except KeyError:
            pass

        code = encode(self._next_id)
        self._url_to_code.put(url, code)
        self._code_to_url.put(code, url)
        self._next_id += 1
        return code

    def expand(self, code: str) -> str:
        decode(code)
        return self._code_to_url.get(code)

    @staticmethod
    def _validate_url(url: str) -> None:
        if not isinstance(url, str) or not url or len(url) > 2048:
            raise ValueError("URL must contain between 1 and 2048 characters")
        if any(character.isspace() or category(character) == "Cc" for character in url):
            raise ValueError("URL must not contain whitespace or control characters")

        try:
            parsed = urlsplit(url)
            host = parsed.hostname
            port = parsed.port
        except ValueError as error:
            raise ValueError("URL has an invalid authority") from error

        if parsed.scheme.lower() not in ("http", "https") or not host:
            raise ValueError("URL must be an absolute HTTP or HTTPS URL with a host")
        if parsed.netloc.endswith(":"):
            raise ValueError("URL port must be between 1 and 65535")
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("URL port must be between 1 and 65535")
