BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def encode(n: int) -> str:
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return "0"

    encoded = []
    while n:
        n, remainder = divmod(n, len(BASE62_ALPHABET))
        encoded.append(BASE62_ALPHABET[remainder])
    return "".join(reversed(encoded))


def decode(s: str) -> int:
    if not s:
        raise ValueError("s must not be empty")

    value = 0
    for character in s:
        digit = BASE62_ALPHABET.find(character)
        if digit == -1:
            raise ValueError(f"invalid Base62 character: {character}")
        value = value * len(BASE62_ALPHABET) + digit
    return value
