import re
from typing import Any, Dict, Iterable

YEAR_PATTERN = re.compile(r"^\d{4}$")
WORLD_TOTAL_FIELDS = {
    "world_oa_total",
    "world_total",
    "world_retraction",
    "word_scientist",
}
WEIGHT_FIELDS = {"W_OA", "W_OD", "W_OP"}
CALCULATION_REQUIRED_FILES = (
    "OA",
    "cooperation",
    "FWCI",
    "F2",
    "F3",
    "alpha_F",
    "alpha_I",
    "alpha_L",
    "retraction",
    "scientist",
)


def _is_scalar_value(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _ensure(condition: bool, message: str):
    if not condition:
        raise ValueError(message)


def _validate_year_key(year: Any, filename: str):
    _ensure(isinstance(year, str) and YEAR_PATTERN.match(year), f"{filename} 中存在非法年份键: {year}")


def _validate_scalar_map(filename: str, year: str, mapping: Dict[str, Any]):
    _ensure(isinstance(mapping, dict), f"{filename} 的 {year} 年数据必须是对象")
    _ensure(mapping, f"{filename} 的 {year} 年数据不能为空")
    for key, value in mapping.items():
        _ensure(isinstance(key, str) and key.strip(), f"{filename} 的 {year} 年存在非法地区/字段名")
        _ensure(_is_scalar_value(value), f"{filename} 的 {year} 年 {key} 值必须是标量")


def _validate_year_country_dataset(filename: str, data: Dict[str, Any]):
    _ensure(isinstance(data, dict) and data, f"{filename} 数据必须是非空对象")
    normalized_country_sets = set()
    for year, mapping in data.items():
        _validate_year_key(year, filename)
        _validate_scalar_map(filename, year, mapping)
        normalized_country_sets.add(tuple(sorted(mapping.keys())))
    _ensure(len(normalized_country_sets) == 1, f"{filename} 各年份的地区集合必须保持一致")


def _validate_world_total_dataset(filename: str, data: Dict[str, Any]):
    _ensure(isinstance(data, dict) and data, f"{filename} 数据必须是非空对象")
    for year, mapping in data.items():
        _validate_year_key(year, filename)
        _ensure(isinstance(mapping, dict), f"{filename} 的 {year} 年数据必须是对象")
        keys = set(mapping.keys())
        _ensure(keys == WORLD_TOTAL_FIELDS, f"{filename} 的 {year} 年字段必须是 {sorted(WORLD_TOTAL_FIELDS)}")
        for field_name, value in mapping.items():
            _ensure(_is_scalar_value(value), f"{filename} 的 {year} 年 {field_name} 值必须是标量")


def _validate_weight_dataset(filename: str, data: Dict[str, Any]):
    _ensure(isinstance(data, dict) and data, f"{filename} 数据必须是非空对象")
    keys = set(data.keys())
    _ensure(keys == WEIGHT_FIELDS, f"{filename} 的字段必须是 {sorted(WEIGHT_FIELDS)}")
    for key, value in data.items():
        _ensure(isinstance(value, (int, float)), f"{filename} 的 {key} 必须是数字")


def _validate_output_dataset(filename: str, data: Dict[str, Any]):
    _ensure(isinstance(data, dict) and data, f"{filename} 数据必须是非空对象")
    if set(data.keys()) == {"value"}:
        _ensure(_is_scalar_value(data["value"]), f"{filename} 的 value 必须是标量")
        return

    if filename.endswith("_stats_by_country.json"):
        for entity, mapping in data.items():
            _ensure(isinstance(entity, str) and entity.strip(), f"{filename} 中存在非法地区/字段名")
            _validate_scalar_map(filename, entity, mapping)
        return

    for year, mapping in data.items():
        _validate_year_key(year, filename)
        _validate_scalar_map(filename, year, mapping)


def validate_file_payload(directory_name: str, filename: str, data: Dict[str, Any]):
    if directory_name in {"jsondata", "jsondata_aggregation", "jsondata_global_plus"}:
        if filename == "world_total.json":
            _validate_world_total_dataset(filename, data)
            return
        if filename == "weight.json":
            _validate_weight_dataset(filename, data)
            return
        _validate_year_country_dataset(filename, data)
        return

    if directory_name in {"output", "output_aggregation", "output_global_plus"}:
        _validate_output_dataset(filename, data)


def validate_calculation_inputs(data_cache: Dict[str, Dict[str, Any]], label: str):
    total_data = data_cache.get("total")
    _ensure(isinstance(total_data, dict) and total_data, f"{label} total 数据为空，无法计算")

    world_total_data = data_cache.get("world_total")
    _ensure(isinstance(world_total_data, dict) and world_total_data, f"{label} world_total 数据为空，无法计算")

    for year, countries in total_data.items():
        _validate_year_key(year, f"{label}.total")
        _ensure(isinstance(countries, dict) and countries, f"{label} total 的 {year} 年数据不能为空")

        _ensure(year in world_total_data, f"{label} world_total 缺少年份 {year}")

        country_keys = set(countries.keys())
        for file_key in CALCULATION_REQUIRED_FILES:
            file_data = data_cache.get(file_key)
            _ensure(isinstance(file_data, dict) and file_data, f"{label} {file_key} 数据为空，无法计算")
            _ensure(year in file_data, f"{label} {file_key} 缺少年份 {year}")

            year_mapping = file_data[year]
            _ensure(isinstance(year_mapping, dict), f"{label} {file_key} 的 {year} 年数据必须是对象")

            missing_countries = sorted(country_keys - set(year_mapping.keys()))
            _ensure(
                not missing_countries,
                f"{label} {file_key} 的 {year} 年缺少地区: {', '.join(missing_countries[:5])}",
            )
