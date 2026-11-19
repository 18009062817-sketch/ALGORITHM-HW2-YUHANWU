from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from pathlib import Path

from src.hash_table import HashTable
from src.linear_probing import LinearProbingHashTable, _Entry


CAPACITY = 4093
TARGET_LOAD_FACTORS = tuple(step / 10 for step in range(1, 10))
RANDOM_SEED = 20261120
FAILED_QUERY_COUNT = 10_000
RESULTS_CSV = Path(__file__).with_name("strategy_comparison.csv")
RESULTS_SVG = Path(__file__).with_name("strategy_comparison.svg")


@dataclass(frozen=True)
class Comparison:
    target_alpha: float
    actual_alpha: float
    inserted_key_count: int
    chaining_success_measured: float
    chaining_success_theoretical: float
    chaining_failure_measured: float
    chaining_failure_theoretical: float
    linear_success_measured: float
    linear_success_theoretical: float
    linear_failure_measured: float
    linear_failure_theoretical: float


def _random_urls(rng: random.Random, host: str, count: int) -> list[str]:
    return [
        f"https://{host}/{index}-{rng.getrandbits(128):032x}"
        for index in range(count)
    ]


def _count_chaining_probes(table: HashTable[str], key: str) -> int:
    node = table._buckets[table.bucket_index(key)]
    comparisons = 0
    while node is not None:
        comparisons += 1
        if node.key == key:
            break
        node = node.next
    return comparisons


def _count_linear_probes(
    table: LinearProbingHashTable[str], key: str
) -> int:
    start = table.bucket_index(key)
    for offset in range(table.capacity):
        index = (start + offset) % table.capacity
        entry = table._slots[index]
        if entry is None:
            return offset + 1
        if isinstance(entry, _Entry) and entry.key == key:
            return offset + 1
    return table.capacity


def run_experiment() -> list[Comparison]:
    rng = random.Random(RANDOM_SEED)
    comparisons = []

    for target_alpha in TARGET_LOAD_FACTORS:
        key_count = int(CAPACITY * target_alpha)
        keys = _random_urls(rng, "stored.example", key_count)
        failed_keys = _random_urls(rng, "missing.example", FAILED_QUERY_COUNT)
        chaining: HashTable[str] = HashTable(
            capacity=CAPACITY, max_load=None
        )
        linear: LinearProbingHashTable[str] = LinearProbingHashTable(
            capacity=CAPACITY, max_load=None
        )
        for key in keys:
            chaining.put(key, key)
            linear.put(key, key)

        actual_alpha = len(chaining) / chaining.capacity
        if len(linear) / linear.capacity != actual_alpha:
            raise RuntimeError("hash table strategies produced different load factors")

        chaining_success = sum(
            _count_chaining_probes(chaining, key) for key in keys
        ) / key_count
        chaining_failure = sum(
            _count_chaining_probes(chaining, key) for key in failed_keys
        ) / FAILED_QUERY_COUNT
        linear_success = sum(
            _count_linear_probes(linear, key) for key in keys
        ) / key_count
        linear_failure = sum(
            _count_linear_probes(linear, key) for key in failed_keys
        ) / FAILED_QUERY_COUNT

        comparisons.append(
            Comparison(
                target_alpha=target_alpha,
                actual_alpha=actual_alpha,
                inserted_key_count=key_count,
                chaining_success_measured=chaining_success,
                chaining_success_theoretical=1 + actual_alpha / 2,
                chaining_failure_measured=chaining_failure,
                chaining_failure_theoretical=actual_alpha,
                linear_success_measured=linear_success,
                linear_success_theoretical=(
                    1 + 1 / (1 - actual_alpha)
                )
                / 2,
                linear_failure_measured=linear_failure,
                linear_failure_theoretical=(
                    1 + 1 / (1 - actual_alpha) ** 2
                )
                / 2,
            )
        )

    return comparisons


def write_csv(comparisons: list[Comparison]) -> None:
    with RESULTS_CSV.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(
            (
                "capacity",
                "random_seed",
                "target_alpha",
                "actual_alpha",
                "inserted_key_count",
                "successful_query_count",
                "failed_query_count",
                "chaining_success_measured_avg_node_comparisons",
                "chaining_success_theoretical",
                "chaining_failure_measured_avg_node_comparisons_empty_bucket_is_0",
                "chaining_failure_theoretical",
                "linear_success_measured_avg_slots_checked",
                "linear_success_theoretical",
                "linear_failure_measured_avg_slots_checked_including_empty_terminator",
                "linear_failure_theoretical",
            )
        )
        for result in comparisons:
            writer.writerow(
                (
                    CAPACITY,
                    RANDOM_SEED,
                    f"{result.target_alpha:.1f}",
                    f"{result.actual_alpha:.9f}",
                    result.inserted_key_count,
                    result.inserted_key_count,
                    FAILED_QUERY_COUNT,
                    f"{result.chaining_success_measured:.6f}",
                    f"{result.chaining_success_theoretical:.6f}",
                    f"{result.chaining_failure_measured:.6f}",
                    f"{result.chaining_failure_theoretical:.6f}",
                    f"{result.linear_success_measured:.6f}",
                    f"{result.linear_success_theoretical:.6f}",
                    f"{result.linear_failure_measured:.6f}",
                    f"{result.linear_failure_theoretical:.6f}",
                )
            )


def write_svg(comparisons: list[Comparison]) -> None:
    width, height = 1260, 620
    left, top, right, bottom = 95, 60, 810, 510
    all_values = (
        [result.chaining_success_measured for result in comparisons]
        + [result.chaining_success_theoretical for result in comparisons]
        + [result.chaining_failure_measured for result in comparisons]
        + [result.chaining_failure_theoretical for result in comparisons]
        + [result.linear_success_measured for result in comparisons]
        + [result.linear_success_theoretical for result in comparisons]
        + [result.linear_failure_measured for result in comparisons]
        + [result.linear_failure_theoretical for result in comparisons]
    )
    y_max = max(10, math.ceil(max(all_values) / 10) * 10)

    def x_position(value: float) -> float:
        return left + value * (right - left)

    def y_position(value: float) -> float:
        return bottom - value / y_max * (bottom - top)

    series = (
        (
            "Chaining measured (node comparisons)",
            "#1d4ed8",
            [result.chaining_success_measured for result in comparisons],
            False,
        ),
        (
            "Chaining theory: success",
            "#60a5fa",
            [result.chaining_success_theoretical for result in comparisons],
            True,
        ),
        (
            "Chaining measured failures (node comparisons)",
            "#b91c1c",
            [result.chaining_failure_measured for result in comparisons],
            False,
        ),
        (
            "Chaining theory: failure",
            "#f87171",
            [result.chaining_failure_theoretical for result in comparisons],
            True,
        ),
        (
            "Linear measured (slots checked)",
            "#15803d",
            [result.linear_success_measured for result in comparisons],
            False,
        ),
        (
            "Linear theory: success",
            "#4ade80",
            [result.linear_success_theoretical for result in comparisons],
            True,
        ),
        (
            "Linear measured failures (slots; empty stop included)",
            "#a16207",
            [result.linear_failure_measured for result in comparisons],
            False,
        ),
        (
            "Linear theory: failure",
            "#facc15",
            [result.linear_failure_theoretical for result in comparisons],
            True,
        ),
    )

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Chaining and linear probing comparison</title>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="630" y="32" text-anchor="middle" font-family="sans-serif" font-size="18">Chaining vs linear probing</text>',
    ]

    for tick in range(11):
        alpha = tick / 10
        x = x_position(alpha)
        svg.append(
            f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" stroke="#e5e7eb"/>'
        )
        svg.append(
            f'<text x="{x:.2f}" y="{bottom + 24}" text-anchor="middle" font-family="sans-serif" font-size="12">{alpha:.1f}</text>'
        )

    tick_step = max(1, y_max // 10)
    for tick in range(0, y_max + 1, tick_step):
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
            f'<text x="{(left + right) / 2:.2f}" y="{height - 28}" text-anchor="middle" font-family="sans-serif" font-size="14">Actual load factor (alpha)</text>',
            f'<text x="24" y="{(top + bottom) / 2:.2f}" text-anchor="middle" transform="rotate(-90 24 {(top + bottom) / 2:.2f})" font-family="sans-serif" font-size="14">Average probes per search</text>',
        )
    )

    for label, color, values, dashed in series:
        points = " ".join(
            f"{x_position(result.actual_alpha):.2f},{y_position(value):.2f}"
            for result, value in zip(comparisons, values)
        )
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        svg.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"{dash}/>'
        )
        for result, value in zip(comparisons, values):
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
        y = 82 + index * 30
        dash = ' stroke-dasharray="7 5"' if dashed else ""
        svg.append(
            f'<line x1="840" y1="{y}" x2="875" y2="{y}" stroke="{color}" stroke-width="2"{dash}/>'
        )
        svg.append(
            f'<text x="885" y="{y + 4}" font-family="sans-serif" font-size="13">{label}</text>'
        )

    svg.append("</svg>")
    RESULTS_SVG.write_text("\n".join(svg) + "\n", encoding="utf-8")


def main() -> None:
    comparisons = run_experiment()
    write_csv(comparisons)
    write_svg(comparisons)
    print(f"Wrote {RESULTS_CSV}")
    print(f"Wrote {RESULTS_SVG}")


if __name__ == "__main__":
    main()
