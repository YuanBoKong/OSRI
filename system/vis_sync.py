import json
from pathlib import Path
from typing import Dict, List, Optional

from file_storage import atomic_write_json


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
VIS_DATA_DIR = PROJECT_ROOT / "vis" / "data"
VIS_DATA_AGGREGATION_DIR = PROJECT_ROOT / "vis" / "data_aggregation"
VIS_DATA_GLOBAL_PLUS_DIR = PROJECT_ROOT / "vis" / "data_global_plus"

VIS_SYNC_FILES = frozenset({
    "OA.json",
    "R.json",
    "R_zero_fill.json",
    "R_oa_bar.json",
    "R_od_bar.json",
    "R_op_bar.json",
    "cooperation.json",
    "retraction.json",
    "scientist.json",
    "total.json",
})

SOURCE_TO_TARGET_DIR: Dict[str, Path] = {
    "jsondata": VIS_DATA_DIR,
    "output": VIS_DATA_DIR,
    "jsondata_aggregation": VIS_DATA_AGGREGATION_DIR,
    "output_aggregation": VIS_DATA_AGGREGATION_DIR,
    "jsondata_global_plus": VIS_DATA_GLOBAL_PLUS_DIR,
    "output_global_plus": VIS_DATA_GLOBAL_PLUS_DIR,
}

MODE_SOURCE_DIRS: Dict[str, List[Path]] = {
    "global": [
        BASE_DIR / "jsondata",
        BASE_DIR / "output",
    ],
    "aggregation": [
        BASE_DIR / "jsondata_aggregation",
        BASE_DIR / "output_aggregation",
    ],
    "global_plus": [
        BASE_DIR / "jsondata_global_plus",
        BASE_DIR / "output_global_plus",
    ],
}


def is_visualization_tracked_file(filename: str) -> bool:
    return filename in VIS_SYNC_FILES


def _load_json_payload(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def sync_visualization_file(source_file: Path) -> Optional[Path]:
    source_file = source_file.resolve()

    if source_file.suffix != ".json":
        return None
    if source_file.name not in VIS_SYNC_FILES:
        return None

    target_dir = SOURCE_TO_TARGET_DIR.get(source_file.parent.name)
    if target_dir is None:
        return None
    if not source_file.exists():
        return None

    payload = _load_json_payload(source_file)
    target_file = target_dir / source_file.name
    atomic_write_json(target_file, payload)
    return target_file


def sync_visualization_mode(mode: str) -> List[str]:
    if mode not in MODE_SOURCE_DIRS:
        raise ValueError(f"不支持的可视化同步模式: {mode}")

    synced_files = set()
    for source_dir in MODE_SOURCE_DIRS[mode]:
        for filename in VIS_SYNC_FILES:
            source_file = source_dir / filename
            if not source_file.exists():
                continue
            sync_visualization_file(source_file)
            synced_files.add(filename)

    return sorted(synced_files)
