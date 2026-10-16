import copy
import json
from pathlib import Path

from file_storage import atomic_write_json


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
GLOBAL_DATA_DIR = BASE_DIR / "jsondata"
AGGREGATION_DATA_DIR = BASE_DIR / "jsondata_aggregation"
GLOBAL_PLUS_DATA_DIR = BASE_DIR / "jsondata_global_plus"
VIS_DATA_DIR = PROJECT_ROOT / "vis" / "data"
VIS_GLOBAL_PLUS_DATA_DIR = PROJECT_ROOT / "vis" / "data_global_plus"

PICK_ENTITIES = ("EU27", "STLCs")

MERGE_FILES = (
    "total.json",
    "OA.json",
    "cooperation.json",
    "retraction.json",
    "FWCI.json",
    "F2.json",
    "F3.json",
    "scientist.json",
    "IPRI.json",
    "UNESCO.json",
    "policy.json",
    "journals.json",
    "platform.json",
    "alpha_L.json",
    "alpha_F.json",
    "alpha_I.json",
)

COPY_ONLY_FILES = (
    "world_total.json",
    "weight.json",
)


def _load_json(file_path: Path):
    if not file_path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_global_country_order_by_year():
    total_data = _load_json(GLOBAL_DATA_DIR / "total.json")
    country_order_by_year = {}
    for year, year_data in total_data.items():
        if not isinstance(year_data, dict):
            raise ValueError(f"total.json 的 {year} 年数据必须是对象")
        country_order_by_year[year] = list(year_data.keys())
    return country_order_by_year


def _merge_year_country_file(filename: str, country_order_by_year):
    global_data = _load_json(GLOBAL_DATA_DIR / filename)
    aggregation_data = _load_json(AGGREGATION_DATA_DIR / filename)
    merged = {}

    for year, country_order in country_order_by_year.items():
        if year not in global_data or not isinstance(global_data[year], dict):
            raise ValueError(f"{filename} 全球版缺少年份 {year}")
        if year not in aggregation_data or not isinstance(aggregation_data[year], dict):
            raise ValueError(f"{filename} 聚合版缺少年份 {year}")

        global_year_data = global_data[year]
        year_data = {
            country: copy.deepcopy(global_year_data.get(country))
            for country in country_order
        }
        if not isinstance(year_data, dict):
            raise ValueError(f"{filename} 的 {year} 年数据必须是对象")

        aggregation_year_data = aggregation_data[year]
        for entity in PICK_ENTITIES:
            if entity not in aggregation_year_data:
                raise ValueError(f"{filename} 聚合版 {year} 缺少 {entity}")
            year_data[entity] = copy.deepcopy(aggregation_year_data[entity])
        merged[year] = year_data

    return merged


def _sync_vis_metadata():
    VIS_GLOBAL_PLUS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    name_file = VIS_DATA_DIR / "name.json"
    if name_file.exists():
        atomic_write_json(VIS_GLOBAL_PLUS_DATA_DIR / "name.json", _load_json(name_file))

    continent_file = VIS_DATA_DIR / "continent.json"
    if continent_file.exists():
        continent_data = _load_json(continent_file)
        continent_data["Groups"] = list(PICK_ENTITIES)
        atomic_write_json(VIS_GLOBAL_PLUS_DATA_DIR / "continent.json", continent_data)


def build_global_plus_jsondata(sync_vis_metadata: bool = True):
    GLOBAL_PLUS_DATA_DIR.mkdir(parents=True, exist_ok=True)
    country_order_by_year = _load_global_country_order_by_year()

    written_files = []
    for filename in MERGE_FILES:
        merged_data = _merge_year_country_file(filename, country_order_by_year)
        atomic_write_json(GLOBAL_PLUS_DATA_DIR / filename, merged_data)
        written_files.append(filename)

    for filename in COPY_ONLY_FILES:
        atomic_write_json(GLOBAL_PLUS_DATA_DIR / filename, _load_json(GLOBAL_DATA_DIR / filename))
        written_files.append(filename)

    if sync_vis_metadata:
        _sync_vis_metadata()

    return sorted(written_files)


if __name__ == "__main__":
    files = build_global_plus_jsondata()
    print(f"已生成 jsondata_global_plus: {', '.join(files)}")
