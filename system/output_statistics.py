import math
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from file_storage import atomic_write_json


STAT_SOURCE_FILES = (
    "R.json",
    "R_zero_fill.json",
    "R_oa_bar.json",
    "R_od_bar.json",
    "R_op_bar.json",
)

YEAR_STAT_FIELDS = (
    "mean",
    "median",
    "std",
    "variance",
    "min",
    "max",
    "q1",
    "q3",
    "p10",
    "p90",
    "count",
    "missing_count",
)

COUNTRY_STAT_FIELDS = (
    "mean",
    "median",
    "std",
    "variance",
    "min",
    "max",
    "first",
    "last",
    "change",
    "change_rate",
    "count",
    "missing_count",
)


def _to_number(value) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if not text or text == "-":
            return None
        try:
            number = float(text)
        except ValueError:
            return None
        if math.isnan(number) or math.isinf(number):
            return None
        return number
    return None


def _percentile(sorted_values: List[float], percentile: float) -> Optional[float]:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (len(sorted_values) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[int(position)]

    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def _distribution_stats(values: Iterable, total_count: int, fields=YEAR_STAT_FIELDS) -> Dict[str, Optional[float]]:
    numeric_values = [_to_number(value) for value in values]
    numeric_values = [value for value in numeric_values if value is not None]
    count = len(numeric_values)
    missing_count = max(total_count - count, 0)

    stats = {field: None for field in fields}
    stats["count"] = count
    stats["missing_count"] = missing_count

    if not numeric_values:
        return stats

    sorted_values = sorted(numeric_values)
    mean = sum(sorted_values) / count
    variance = sum((value - mean) ** 2 for value in sorted_values) / count

    stats.update({
        "mean": mean,
        "median": _percentile(sorted_values, 0.5),
        "std": math.sqrt(variance),
        "variance": variance,
        "min": sorted_values[0],
        "max": sorted_values[-1],
    })

    if "q1" in stats:
        stats["q1"] = _percentile(sorted_values, 0.25)
    if "q3" in stats:
        stats["q3"] = _percentile(sorted_values, 0.75)
    if "p10" in stats:
        stats["p10"] = _percentile(sorted_values, 0.10)
    if "p90" in stats:
        stats["p90"] = _percentile(sorted_values, 0.90)

    return stats


def _stats_by_year(data: Dict) -> Dict:
    result = {}
    for year in sorted(data.keys()):
        year_data = data.get(year)
        if not isinstance(year_data, dict):
            continue
        result[year] = _distribution_stats(year_data.values(), len(year_data), YEAR_STAT_FIELDS)
    return result


def _stats_by_country(data: Dict) -> Dict:
    years = sorted(data.keys())
    countries = []
    seen = set()
    for year in years:
        year_data = data.get(year)
        if not isinstance(year_data, dict):
            continue
        for country in year_data.keys():
            if country not in seen:
                seen.add(country)
                countries.append(country)

    result = {}
    for country in countries:
        values = [
            data.get(year, {}).get(country)
            if isinstance(data.get(year), dict)
            else None
            for year in years
        ]
        stats = _distribution_stats(values, len(years), COUNTRY_STAT_FIELDS)
        first = _to_number(values[0]) if values else None
        last = _to_number(values[-1]) if values else None
        change = last - first if first is not None and last is not None else None
        change_rate = (
            change / first
            if change is not None and first not in (None, 0)
            else None
        )
        stats.update({
            "first": first,
            "last": last,
            "change": change,
            "change_rate": change_rate,
        })
        result[country] = stats

    return result


def _load_json(file_path: Path):
    import json

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_output_statistics(output_dir: Path) -> List[str]:
    output_dir = Path(output_dir)
    written_files = []

    for filename in STAT_SOURCE_FILES:
        source_file = output_dir / filename
        if not source_file.exists():
            continue

        data = _load_json(source_file)
        if not isinstance(data, dict) or set(data.keys()) == {"value"}:
            continue

        stem = source_file.stem
        by_year_filename = f"{stem}_stats_by_year.json"
        by_country_filename = f"{stem}_stats_by_country.json"

        atomic_write_json(output_dir / by_year_filename, _stats_by_year(data))
        atomic_write_json(output_dir / by_country_filename, _stats_by_country(data))
        written_files.extend([by_year_filename, by_country_filename])

    return written_files
