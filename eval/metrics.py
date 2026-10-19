"""Pure selection metrics and a deliberately limited numerical faithfulness check."""

from dataclasses import dataclass
import math
import re


def wilson(successes, n, z=1.959963984540054):
    """Wilson score bounds; fractional successes give descriptive macro bounds."""
    if n == 0:
        return None
    if n < 0 or not 0 <= successes <= n:
        raise ValueError("Counts must satisfy 0 <= successes <= n")
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    radius = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0, centre - radius), min(1, centre + radius)


def selection_scores(expected, got):
    """Order-independent exact match and per-question precision/recall.

    Both empty is perfect; an empty/nonempty mismatch gets zero for both.
    """
    expected, got = set(expected), set(got)
    overlap = len(expected & got)
    precision = overlap / len(got) if got else float(not expected)
    recall = overlap / len(expected) if expected else float(not got)
    return dict(exact=int(expected == got), precision=precision, recall=recall)


@dataclass(frozen=True)
class ExtractedNumber:
    value: float
    kind: str
    tolerance: float


NUMBER = re.compile(
    r"(?<![\w.])(?P<before>[+-]?)(?P<currency>\$)?(?P<after>[+-]?)"
    r"(?P<number>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)"
    r"(?P<scale>[kKmMbB])?(?P<percent>\s*%)?(?!\w)"
)


def extract_numbers(text):
    numbers = []
    for match in NUMBER.finditer(text):
        if match['before'] and match['after']:
            continue
        value = match['number'].replace(',', '')
        places = len(value.split('.')[1]) if '.' in value else 0
        scale = {'k': 1000, 'm': 1_000_000, 'b': 1_000_000_000}.get(
            (match['scale'] or '').lower(), 1)
        sign = -1 if '-' in (match['before'] + match['after']) else 1
        kind = 'dollar' if match['currency'] else 'percent' if match['percent'] else 'number'
        numbers.append(ExtractedNumber(sign * float(value) * scale, kind,
                                      0.5 * scale * 10 ** -places + 1e-9))
    return numbers


def numeric_values(payload):
    if isinstance(payload, dict):
        return [number for value in payload.values() for number in numeric_values(value)]
    if isinstance(payload, (list, tuple)):
        return [number for value in payload for number in numeric_values(value)]
    if isinstance(payload, (int, float)) and not isinstance(payload, bool) and math.isfinite(payload):
        return [float(payload)]
    return []


def numbers_are_grounded(answer, raw_data, computed_data):
    """Return None for no $/% figures; otherwise require every figure to match.

    This checks numeric presence within displayed rounding precision, not units,
    attribution, arithmetic reasoning, omissions, or prose truthfulness.
    """
    figures = [number for number in extract_numbers(answer) if number.kind != 'number']
    if not figures:
        return None
    available = numeric_values([raw_data, computed_data])
    return all(any(abs(figure.value - value) <= figure.tolerance for value in available)
               for figure in figures)
