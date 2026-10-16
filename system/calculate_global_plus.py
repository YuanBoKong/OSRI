from pathlib import Path
import importlib.util


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "jsondata_global_plus"
OUTPUT_DIR = BASE_DIR / "output_global_plus"


def _load_global_calculation_engine():
    spec = importlib.util.spec_from_file_location(
        "_calculate_global_plus_engine",
        BASE_DIR / "calculate.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("无法加载全球Plus计算引擎")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_engine = _load_global_calculation_engine()
_engine.DATA_DIR = DATA_DIR
_engine.json_files = {
    key: DATA_DIR / path.name
    for key, path in _engine.json_files.items()
}
_engine._output_dir = OUTPUT_DIR
OUTPUT_DIR.mkdir(exist_ok=True)
_engine.reload_data_cache()


def reload_data_cache():
    _engine.reload_data_cache()


def batch_calculate_and_save():
    _engine.batch_calculate_and_save()


R = _engine.R
R_zero_fill = _engine.R_zero_fill
