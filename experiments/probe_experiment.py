from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable


CAPACITY = 4093
TARGET_LOAD_FACTORS = (0.25, 0.5, 1, 2, 4)
RANDOM_SEED = 20261119
FAILED_QUERY_COUNT = 10_000
RESULTS_CSV = Path(__file__).with_name("results.csv")
RESULTS_SVG = Path(__file__).with_name("results.svg")


@dataclass(frozen=True)
class Measurement:
    target_alpha: float
    actual_alpha: float
    successful_measured: float
    successful_theoretical: float
    unsuccessful_measured: float
    unsuccessful_theoretical: float


def _count_probes(table: HashTable[str], key: str) -> int:
    node = table._buckets[table.bucket_index(key)]
    comparisons = 0
    while node is not None:
        comparisons += 1
        if node.key == key:
            break
        node = node.next
    return comparisons


def run_experiment() -> list[Measurement]:
    rng = random.Random(RANDOM_SEED)
    measurements = []

    for target_alpha in TARGET_LOAD_FACTORS:
        key_count = int(CAPACITY * target_alpha)
        keys = [
            f"https://stored.example/{index}-{rng.getrandbits(128):032x}"
            for index in range(key_count)
        ]
        table: HashTable[str] = HashTable(capacity=CAPACITY, max_load=None)
        for key in keys:
            table.put(key, key)

        actual_alpha = len(table) / table.capacity
        successful_measured = sum(
            _count_probes(table, key) for key in keys
        ) / len(keys)

        unsuccessful_keys = (
            f"https://missing.example/{index}-{rng.getrandbits(128):032x}"
            for index in range(FAILED_QUERY_COUNT)
        )
        unsuccessful_measured = sum(
            _count_probes(table, key) for key in unsuccessful_keys
        ) / FAILED_QUERY_COUNT

        measurements.append(
            Measurement(
                target_alpha=target_alpha,
                actual_alpha=actual_alpha,
                successful_measured=successful_measured,
                successful_theoretical=1 + actual_alpha / 2,
                unsuccessful_measured=unsuccessful_measured,
                unsuccessful_theoretical=actual_alpha,
            )
        )

    return measurements


def write_csv(measurements: list[Measurement]) -> None:
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            (
                "target_load_factor",
                "actual_load_factor",
                "successful_measured_avg",
                "successful_theoretical",
                "unsuccessful_measured_avg",
                "unsuccessful_theoretical",
            )
        )
        for result in measurements:
            writer.writerow(
                (
                    f"{result.target_alpha:.2f}",
                    f"{result.actual_alpha:.6f}",
                    f"{result.successful_measured:.6f}",
                    f"{result.successful_theoretical:.6f}",
                    f"{result.unsuccessful_measured:.6f}",
                    f"{result.unsuccessful_theoretical:.6f}",
                )
            )


def write_svg(measurements: list[Measurement]) -> None:
    width, height = 1020, 560
    left, top, right, bottom = 90, 55, 755, 455
    x_max = max(4.0, max(result.actual_alpha for result in measurements))
    y_max = math.ceil(
        max(
            result.successful_measured
            for result in measurements
        )
        + 0.5
    )
    y_max = max(
        y_max,
        math.ceil(
            max(result.unsuccessful_measured for result in measurements) + 0.5
        ),
    )

    def x_position(value: float) -> float:
        return left + value / x_max * (right - left)

    def y_position(value: float) -> float:
        return bottom - value / y_max * (bottom - top)

    series = (
        (
            "Successful (measured)",
            "#1d4ed8",
            [result.successful_measured for result in measurements],
            False,
        ),
        (
            "Successful (theoretical)",
            "#60a5fa",
            [result.successful_theoretical for result in measurements],
            True,
        ),
        (
            "Unsuccessful (measured)",
            "#b91c1c",
            [result.unsuccessful_measured for result in measurements],
            False,
        ),
        (
            "Unsuccessful (theoretical)",
            "#f87171",
            [result.unsuccessful_theoretical for result in measurements],
            True,
        ),
    )

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Separate chaining probe cost</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="510" y="30" text-anchor="middle" font-family="sans-serif" font-size="18">Separate chaining probe cost</text>',
    ]

    for tick in range(math.ceil(x_max) + 1):
        x = x_position(tick)
        svg.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" stroke="#e5e7eb"/>'
        )
        svg.append(
            f'<text x="{x:.2f}" y="{bottom + 24}" text-anchor="middle" font-family="sans-serif" font-size="12">{tick}</text>'
        )

    for tick in range(y_max + 1):
        y = y_position(tick)
        svg.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="#e5e7eb"/>'
        )
        svg.append(
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" font-family="sans-serif" font-size="12">{tick}</text>'
        )

    svg.extend(
        (
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#111827"/>',
            f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#111827"/>',
            f'<text x="{(left + right) / 2:.2f}" y="{height - 24}" text-anchor="middle" font-family="sans-serif" font-size="14">Actual load factor (alpha)</text>',
            f'<text x="22" y="{(top + bottom) / 2:.2f}" text-anchor="middle" transform="rotate(-90 22 {(top + bottom) / 2:.2f})" font-family="sans-serif" font-size="14">Average nodes compared</text>',
        )
    )

    for label, color, values, dashed in series:
        points = " ".join(
            f"{x_position(result.actual_alpha):.2f},{y_position(value):.2f}"
            for result, value in zip(measurements, values)
        )
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        svg.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"{dash}/>'
        )
        for result, value in zip(measurements, values):
            x = x_position(result.actual_alpha)
            y = y_position(value)
            if dashed:
                svg.append(
                    f'<rect x="{x - 3:.2f}" y="{y - 3:.2f}" width="6" height="6" fill="{color}"/>'
                )
            else:
                svg.append(
                    f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}"/>'
                )

    for index, (label, color, _, dashed) in enumerate(series):
        y = 90 + index * 28
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        svg.append(
            f'<line x1="790" y1="{y}" x2="825" y2="{y}" stroke="{color}" stroke-width="2"{dash}/>'
        )
        svg.append(
            f'<text x="835" y="{y + 4}" font-family="sans-serif" font-size="13">{label}</text>'
        )

    svg.append("</svg>")
    RESULTS_SVG.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main() -> None:
    measurements = run_experiment()
    write_csv(measurements)
    write_svg(measurements)
    print(f"Wrote {RESULTS_CSV}")
    print(f"Wrote {RESULTS_SVG}")


if __name__ == "__main__":
    main()
