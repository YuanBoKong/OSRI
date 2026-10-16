"""
FastAPI后端接口
提供jsondata和output文件夹的JSON文件增删改查功能，以及批量计算接口
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import pandas as pd
from io import BytesIO
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from fastapi.responses import StreamingResponse, FileResponse
from data_validation import validate_file_payload
from file_storage import atomic_write_json, compute_json_revision, file_lock
from vis_sync import sync_visualization_file, sync_visualization_mode

# 数据目录路径
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
VIS_DIR = PROJECT_ROOT / "vis"
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
FRONTEND_STATIC_DIR = FRONTEND_DIST_DIR / "static"
FRONTEND_INDEX = FRONTEND_DIST_DIR / "index.html"


def _load_vis_subapp() -> FastAPI:
    module_path = VIS_DIR / "data_api.py"
    spec = importlib.util.spec_from_file_location("pdq_vis_data_api", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载可视化子应用: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


# 导入计算模块
from calculate import batch_calculate_and_save, reload_data_cache
from calculate_aggregation import batch_calculate_and_save as batch_calculate_and_save_aggregation, reload_data_cache as reload_data_cache_aggregation
from calculate_global_plus import batch_calculate_and_save as batch_calculate_and_save_global_plus, reload_data_cache as reload_data_cache_global_plus
from generate_global_plus import build_global_plus_jsondata

app = FastAPI(title="OSRI API", version="1.1.0")

@app.middleware("http")
async def normalize_application_prefix(request, call_next):
    if request.scope["path"] == "/OSRI":
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/OSRI/")
    if request.scope["path"].startswith("/OSRI/"):
        request.scope["path"] = request.scope["path"][5:]
        request.scope["raw_path"] = request.scope["path"].encode("utf-8")
    return await call_next(request)


# 配置CORS，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

JSONDATA_DIR = BASE_DIR / "jsondata"
OUTPUT_DIR = BASE_DIR / "output"
JSONDATA_AGGREGATION_DIR = BASE_DIR / "jsondata_aggregation"
OUTPUT_AGGREGATION_DIR = BASE_DIR / "output_aggregation"
JSONDATA_GLOBAL_PLUS_DIR = BASE_DIR / "jsondata_global_plus"
OUTPUT_GLOBAL_PLUS_DIR = BASE_DIR / "output_global_plus"
RUNTIME_DIR = BASE_DIR / ".runtime"

# 确保目录存在
JSONDATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
JSONDATA_AGGREGATION_DIR.mkdir(exist_ok=True)
OUTPUT_AGGREGATION_DIR.mkdir(exist_ok=True)
JSONDATA_GLOBAL_PLUS_DIR.mkdir(exist_ok=True)
OUTPUT_GLOBAL_PLUS_DIR.mkdir(exist_ok=True)
RUNTIME_DIR.mkdir(exist_ok=True)

VIS_DIR.mkdir(exist_ok=True)

CALCULATION_STATUS_FILES = {
    "global": RUNTIME_DIR / "calculate_global_status.json",
    "global_plus": RUNTIME_DIR / "calculate_global_plus_status.json",
    "aggregation": RUNTIME_DIR / "calculate_aggregation_status.json",
}

MODE_LABELS = {
    "global": "全球版本",
    "global_plus": "全球Plus版本",
    "aggregation": "聚合版本",
}

vis_subapp = _load_vis_subapp()
app.mount("/vis-api", vis_subapp)
app.mount("/osri-vis", StaticFiles(directory=str(VIS_DIR), html=True), name="osri-vis")
if FRONTEND_STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_STATIC_DIR)), name="frontend-static")


# ==================== 数据模型 ====================
class FileUpdateRequest(BaseModel):
    """文件更新请求模型"""
    data: Dict[str, Any]
    expected_revision: Optional[str] = None


class AddDataRequest(BaseModel):
    """添加数据请求模型"""
    year: Optional[str] = None  # 添加年份时使用
    country: Optional[str] = None  # 添加国家时使用
    value: Any  # 添加的值，可以是单个值或字典（取决于数据类型）
    expected_revision: Optional[str] = None


class DeleteDataRequest(BaseModel):
    """删除数据请求模型"""
    year: Optional[str] = None  # 删除年份
    country: Optional[str] = None  # 删除国家（从所有年份中删除）
    expected_revision: Optional[str] = None


class CalculateResponse(BaseModel):
    """计算响应模型"""
    status: str
    message: str


class ExcelImportResponse(BaseModel):
    """Excel导入响应模型"""
    status: str
    message: str
    added_years: List[str] = []
    added_countries: List[str] = []
    updated_cells: int = 0
    errors: List[str] = []
    revision: Optional[str] = None
    vis_updated: bool = False


class FilterRequest(BaseModel):
    """筛选请求模型"""
    years: Optional[List[str]] = None  # 筛选的年份列表，None表示不过滤年份
    countries: Optional[List[str]] = None  # 筛选的国家列表，None表示不过滤国家


# ==================== 辅助函数 ====================
def _load_json_from_disk(file_path: Path) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    validate_file_payload(file_path.parent.name, file_path.name, data)
    return data


def _restore_from_backup(file_path: Path) -> Dict[str, Any]:
    backup_path = file_path.with_suffix('.json.bak')
    if not backup_path.exists():
        raise HTTPException(status_code=400, detail=f"JSON格式或结构错误，且无备份文件: {file_path.name}")

    try:
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        validate_file_payload(file_path.parent.name, file_path.name, backup_data)
        atomic_write_json(file_path, backup_data)
        print(f"✓ 已从备份恢复文件: {file_path.name}")
        return backup_data
    except Exception as restore_error:
        raise HTTPException(status_code=500, detail=f"从备份恢复失败: {str(restore_error)}")


def read_json_file(file_path: Path) -> Dict[str, Any]:
    """读取JSON文件并校验结构。"""
    data, _ = read_json_file_with_revision(file_path)
    return data


def read_json_file_with_revision(file_path: Path):
    """读取JSON文件并返回内容与修订号。"""
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path.name}")

    try:
        with file_lock(file_path):
            try:
                data = _load_json_from_disk(file_path)
            except (json.JSONDecodeError, ValueError) as read_error:
                print(f"警告: {file_path.name} 当前文件无效，尝试恢复备份: {read_error}")
                data = _restore_from_backup(file_path)
        return data, compute_json_revision(data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


def write_json_file(file_path: Path, data: Dict[str, Any], expected_revision: Optional[str] = None) -> str:
    """写入JSON文件，写入前校验结构、校验版本并创建备份。"""
    try:
        validate_file_payload(file_path.parent.name, file_path.name, data)
        new_revision = compute_json_revision(data)
        backup_path = file_path.with_suffix('.json.bak')

        with file_lock(file_path):
            current_data = None
            current_revision = None
            if file_path.exists():
                current_data = _load_json_from_disk(file_path)
                current_revision = compute_json_revision(current_data)

            if expected_revision is not None and current_revision != expected_revision:
                raise HTTPException(status_code=409, detail=f"文件已被其他操作更新，请刷新后重试: {file_path.name}")

            if current_data is not None:
                try:
                    atomic_write_json(backup_path, current_data)
                except Exception as backup_error:
                    print(f"警告: 创建备份失败: {backup_error}")

            atomic_write_json(file_path, data)
            return new_revision
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"写入文件失败: {str(e)}")


def filter_data(data: Dict[str, Any], years: Optional[List[str]] = None, countries: Optional[List[str]] = None) -> Dict[str, Any]:
    """根据年份和国家筛选数据"""
    # 处理单值文件（如{"value": 0.4036}）
    if 'value' in data and len(data) == 1:
        return data  # 单值文件不进行筛选
    
    filtered_data = {}
    
    # 转换年份列表为字符串集合（用于快速查找）
    years_set = None
    if years is not None:
        years_set = set(str(y) for y in years)
    
    # 转换国家列表为集合（用于快速查找）
    countries_set = None
    if countries is not None:
        countries_set = set(str(c) for c in countries)
    
    # 遍历所有年份
    for year_key, year_data in data.items():
        # 如果指定了年份筛选，且当前年份不在筛选列表中，跳过
        if years_set is not None and year_key not in years_set:
            continue
        
        # 如果年份数据不是字典，直接复制
        if not isinstance(year_data, dict):
            filtered_data[year_key] = year_data
            continue
        
        # 筛选国家
        filtered_year_data = {}
        for country_key, country_value in year_data.items():
            # 如果指定了国家筛选，且当前国家不在筛选列表中，跳过
            if countries_set is not None and country_key not in countries_set:
                continue
            filtered_year_data[country_key] = country_value
        
        # 如果筛选后该年份还有数据，则添加到结果中
        if filtered_year_data:
            filtered_data[year_key] = filtered_year_data
    
    return filtered_data


def _round_value_for_excel_export(value: Any) -> Any:
    """仅在导出Excel时处理：超过3位小数的浮点数四舍五入到3位。"""
    if isinstance(value, bool) or not isinstance(value, float):
        return value

    if pd.isna(value):
        return value

    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return value

    # 小数位数 <= 3 时保持原值
    if decimal_value.as_tuple().exponent >= -3:
        return value

    try:
        return float(decimal_value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))
    except InvalidOperation:
        return value


def format_dataframe_for_excel_export(df: pd.DataFrame) -> pd.DataFrame:
    """仅用于Excel导出，不影响页面展示和原始数据。"""
    return df.apply(lambda col: col.map(_round_value_for_excel_export))


def _excel_primary_key_name(filename: str) -> str:
    return "国家/地区/组织" if filename.endswith("_stats_by_country.json") else "年份"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mode_label(mode: str) -> str:
    return MODE_LABELS.get(mode, mode)


def _default_calculation_status(mode: str) -> Dict[str, Any]:
    label = _mode_label(mode)
    return {
        "mode": mode,
        "status": "idle",
        "message": f"{label}尚未开始批量计算",
        "started_at": None,
        "finished_at": None,
        "synced_files": [],
        "error": None,
    }


def _get_calculation_status_file(mode: str) -> Path:
    if mode not in CALCULATION_STATUS_FILES:
        raise HTTPException(status_code=400, detail=f"不支持的计算模式: {mode}")
    return CALCULATION_STATUS_FILES[mode]


def _read_calculation_status(mode: str) -> Dict[str, Any]:
    status_file = _get_calculation_status_file(mode)
    status = _default_calculation_status(mode)
    if not status_file.exists():
        return status

    try:
        with file_lock(status_file):
            with open(status_file, "r", encoding="utf-8") as f:
                payload = json.load(f)
        if isinstance(payload, dict):
            status.update(payload)
    except Exception as e:
        print(f"警告: 读取计算状态失败 ({mode}): {e}")
    return status


def _write_calculation_status(mode: str, **updates) -> Dict[str, Any]:
    status_file = _get_calculation_status_file(mode)
    with file_lock(status_file):
        status = _default_calculation_status(mode)
        if status_file.exists():
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    status.update(payload)
            except Exception as e:
                print(f"警告: 读取现有计算状态失败 ({mode}): {e}")
        status.update(updates)
        status["mode"] = mode
        atomic_write_json(status_file, status)
    return status


def _queue_calculation(mode: str):
    status_file = _get_calculation_status_file(mode)
    label = _mode_label(mode)

    with file_lock(status_file):
        status = _default_calculation_status(mode)
        if status_file.exists():
            try:
                with open(status_file, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                if isinstance(payload, dict):
                    status.update(payload)
            except Exception as e:
                print(f"警告: 读取现有计算状态失败 ({mode}): {e}")

        if status.get("status") in {"queued", "running", "syncing"}:
            raise HTTPException(status_code=409, detail=f"{label}批量计算正在执行中，请等待完成后重试")

        started_at = _utc_now_iso()
        status.update({
            "status": "queued",
            "message": f"{label}批量计算已入队，等待后台执行",
            "started_at": started_at,
            "finished_at": None,
            "synced_files": [],
            "error": None,
        })
        atomic_write_json(status_file, status)


def _run_batch_calculation_pipeline(mode: str):
    label = _mode_label(mode)
    current_status = _read_calculation_status(mode)
    started_at = current_status.get("started_at") or _utc_now_iso()
    _write_calculation_status(
        mode,
        status="running",
        message=f"{label}批量计算进行中",
        started_at=started_at,
        finished_at=None,
        synced_files=[],
        error=None,
    )

    try:
        if mode == "aggregation":
            batch_calculate_and_save_aggregation()
        elif mode == "global_plus":
            build_global_plus_jsondata()
            reload_data_cache_global_plus()
            batch_calculate_and_save_global_plus()
        else:
            batch_calculate_and_save()

        _write_calculation_status(
            mode,
            status="syncing",
            message=f"{label}批量计算完成，正在同步可视化数据",
            started_at=started_at,
            finished_at=None,
            synced_files=[],
            error=None,
        )
        synced_files = sync_visualization_mode(mode)
        _write_calculation_status(
            mode,
            status="completed",
            message=f"{label}批量计算和可视化同步已完成",
            started_at=started_at,
            finished_at=_utc_now_iso(),
            synced_files=synced_files,
            error=None,
        )
    except Exception as e:
        _write_calculation_status(
            mode,
            status="failed",
            message=f"{label}批量计算失败: {str(e)}",
            started_at=started_at,
            finished_at=_utc_now_iso(),
            synced_files=[],
            error=str(e),
        )
        print(f"批量计算失败 ({mode}): {e}")


def _reload_input_cache_after_write(file_path: Path):
    directory_name = file_path.parent.name
    if directory_name == "jsondata":
        try:
            reload_data_cache()
        except Exception as e:
            print(f"警告: 重新加载数据缓存失败: {e}")
    elif directory_name == "jsondata_aggregation":
        try:
            reload_data_cache_aggregation()
        except Exception as e:
            print(f"警告: 重新加载聚合版本数据缓存失败: {e}")
    elif directory_name == "jsondata_global_plus":
        try:
            reload_data_cache_global_plus()
        except Exception as e:
            print(f"警告: 重新加载全球Plus版本数据缓存失败: {e}")


def _sync_visualization_after_write(file_path: Path) -> bool:
    try:
        return sync_visualization_file(file_path) is not None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件已保存，但同步可视化数据失败: {str(e)}")


def _post_write_refresh(file_path: Path) -> bool:
    _reload_input_cache_after_write(file_path)
    return _sync_visualization_after_write(file_path)


def _ensure_json_filename(filename: str):
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")


def _list_directory_json_files(directory: Path):
    files = []
    for file_path in directory.glob("*.json"):
        files.append({
            "filename": file_path.name,
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime
        })
    return {"files": sorted(files, key=lambda x: x["filename"])}


def _get_directory_json_file(directory: Path, filename: str):
    _ensure_json_filename(filename)
    data, revision = read_json_file_with_revision(directory / filename)
    return {"filename": filename, "data": data, "revision": revision}


def _filter_directory_json_file(directory: Path, filename: str, request: FilterRequest):
    _ensure_json_filename(filename)
    data = read_json_file(directory / filename)
    filtered_data = filter_data(data, request.years, request.countries)
    return {
        "filename": filename,
        "data": filtered_data,
        "filter": {
            "years": request.years,
            "countries": request.countries
        }
    }


def _update_directory_json_file(directory: Path, filename: str, request: FileUpdateRequest):
    _ensure_json_filename(filename)
    if not isinstance(request.data, dict):
        raise HTTPException(status_code=400, detail="数据必须是JSON对象")

    file_path = directory / filename
    revision = write_json_file(file_path, request.data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)

    return {
        "message": f"文件 {filename} 已更新",
        "filename": filename,
        "revision": revision,
        "vis_updated": vis_updated,
    }


def _add_directory_data(directory: Path, filename: str, request: AddDataRequest, *, reject_single_value: bool = False):
    _ensure_json_filename(filename)
    file_path = directory / filename
    data = read_json_file(file_path)

    if reject_single_value and "value" in data and len(data) == 1:
        raise HTTPException(status_code=400, detail="单值函数不支持添加数据")

    if request.year:
        if request.year in data:
            raise HTTPException(status_code=400, detail=f"年份 {request.year} 已存在")
        data[request.year] = request.value
    elif request.country:
        if not data:
            raise HTTPException(status_code=400, detail="文件为空，无法添加国家")

        exists = any(request.country in year_data for year_data in data.values() if isinstance(year_data, dict))
        if exists:
            raise HTTPException(status_code=400, detail=f"国家 {request.country} 已存在")

        for year_key in data.keys():
            if isinstance(data[year_key], dict):
                data[year_key][request.country] = request.value
    else:
        raise HTTPException(status_code=400, detail="必须提供year或country参数")

    revision = write_json_file(file_path, data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    return {"message": "数据已添加", "filename": filename, "revision": revision, "vis_updated": vis_updated}


def _delete_directory_data(directory: Path, filename: str, request: DeleteDataRequest, *, reject_single_value: bool = False):
    _ensure_json_filename(filename)
    file_path = directory / filename
    data = read_json_file(file_path)

    if reject_single_value and "value" in data and len(data) == 1:
        raise HTTPException(status_code=400, detail="单值函数不支持删除数据")

    deleted = False

    if request.year:
        if request.year in data:
            del data[request.year]
            deleted = True
        else:
            raise HTTPException(status_code=404, detail=f"年份 {request.year} 不存在")
    elif request.country:
        for year_key in data.keys():
            if isinstance(data[year_key], dict) and request.country in data[year_key]:
                del data[year_key][request.country]
                deleted = True

        if not deleted:
            raise HTTPException(status_code=404, detail=f"国家 {request.country} 不存在")
    else:
        raise HTTPException(status_code=400, detail="必须提供year或country参数")

    revision = write_json_file(file_path, data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    return {"message": "数据已删除", "filename": filename, "revision": revision, "vis_updated": vis_updated}


def _export_directory_json_to_excel(directory: Path, filename: str):
    try:
        _ensure_json_filename(filename)
        file_path = directory / filename

        try:
            data = read_json_file(file_path)
        except HTTPException as e:
            if e.status_code == 404:
                raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")
            raise

        if not data or len(data) == 0:
            raise HTTPException(status_code=400, detail="文件数据为空")

        if 'value' in data and len(data) == 1:
            df = pd.DataFrame([{'函数名': filename.replace('.json', ''), '值': data['value']}])
        else:
            years = sorted(data.keys())
            all_countries = set()
            for year_data in data.values():
                if isinstance(year_data, dict):
                    all_countries.update(year_data.keys())

            all_countries = sorted(list(all_countries))
            rows = []
            for year in years:
                row = {_excel_primary_key_name(filename): year}
                if isinstance(data[year], dict):
                    for country in all_countries:
                        row[country] = data[year].get(country, None)
                rows.append(row)

            df = pd.DataFrame(rows)

        export_df = format_dataframe_for_excel_export(df)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='数据')

        output.seek(0)

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename.replace('.json', '')}.xlsx"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"导出Excel错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"导出Excel失败: {str(e)}")


# ==================== jsondata API ====================
@app.get("/api/jsondata/files")
async def list_jsondata_files():
    """列出jsondata文件夹中的所有JSON文件"""
    files = []
    for file_path in JSONDATA_DIR.glob("*.json"):
        files.append({
            "filename": file_path.name,
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime
        })
    return {"files": sorted(files, key=lambda x: x["filename"])}


@app.get("/api/jsondata/{filename}")
async def get_jsondata_file(filename: str):
    """读取jsondata文件夹中的JSON文件"""
    file_path = JSONDATA_DIR / filename
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    data, revision = read_json_file_with_revision(file_path)
    return {"filename": filename, "data": data, "revision": revision}


@app.post("/api/jsondata/{filename}/filter")
async def filter_jsondata_file(filename: str, request: FilterRequest):
    """筛选jsondata文件夹中的JSON文件数据"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = JSONDATA_DIR / filename
    data = read_json_file(file_path)
    
    # 应用筛选
    filtered_data = filter_data(data, request.years, request.countries)
    
    return {
        "filename": filename,
        "data": filtered_data,
        "filter": {
            "years": request.years,
            "countries": request.countries
        }
    }


@app.put("/api/jsondata/{filename}")
async def update_jsondata_file(filename: str, request: FileUpdateRequest):
    """更新jsondata文件夹中的JSON文件（完全覆盖）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = JSONDATA_DIR / filename
    
    # 验证数据格式
    if not isinstance(request.data, dict):
        raise HTTPException(status_code=400, detail="数据必须是JSON对象")
    
    revision = write_json_file(file_path, request.data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    
    return {
        "message": f"文件 {filename} 已更新",
        "filename": filename,
        "revision": revision,
        "vis_updated": vis_updated,
    }


@app.post("/api/jsondata/{filename}/add")
async def add_jsondata_data(filename: str, request: AddDataRequest):
    """向jsondata文件中添加数据（添加年份或国家）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = JSONDATA_DIR / filename
    data = read_json_file(file_path)
    
    if request.year:
        # 添加年份
        if request.year in data:
            raise HTTPException(status_code=400, detail=f"年份 {request.year} 已存在")
        data[request.year] = request.value
    elif request.country:
        # 添加国家（向所有年份添加该国家字段）
        if not data:
            raise HTTPException(status_code=400, detail="文件为空，无法添加国家")
        
        # 检查是否已存在该国家（至少在一个年份中）
        exists = any(request.country in year_data for year_data in data.values() if isinstance(year_data, dict))
        if exists:
            raise HTTPException(status_code=400, detail=f"国家 {request.country} 已存在")
        
        # 向所有年份添加该国家字段
        for year_key in data.keys():
            if isinstance(data[year_key], dict):
                data[year_key][request.country] = request.value
    else:
        raise HTTPException(status_code=400, detail="必须提供year或country参数")
    
    revision = write_json_file(file_path, data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    
    return {"message": "数据已添加", "filename": filename, "revision": revision, "vis_updated": vis_updated}


@app.delete("/api/jsondata/{filename}/delete")
async def delete_jsondata_data(filename: str, request: DeleteDataRequest):
    """从jsondata文件中删除数据（删除年份或国家）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = JSONDATA_DIR / filename
    data = read_json_file(file_path)
    
    deleted = False
    
    if request.year:
        # 删除年份
        if request.year in data:
            del data[request.year]
            deleted = True
        else:
            raise HTTPException(status_code=404, detail=f"年份 {request.year} 不存在")
    elif request.country:
        # 删除国家（从所有年份中删除该国家字段）
        for year_key in data.keys():
            if isinstance(data[year_key], dict) and request.country in data[year_key]:
                del data[year_key][request.country]
                deleted = True
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"国家 {request.country} 不存在")
    else:
        raise HTTPException(status_code=400, detail="必须提供year或country参数")
    
    revision = write_json_file(file_path, data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    
    return {"message": "数据已删除", "filename": filename, "revision": revision, "vis_updated": vis_updated}


@app.post("/api/jsondata/{filename}/import-excel", response_model=ExcelImportResponse)
async def import_excel_data(filename: str, file: UploadFile = File(...)):
    """从Excel文件批量导入数据到jsondata文件"""
    try:
        if not filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
        
        # 验证文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="未提供文件名")
        
        if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            raise HTTPException(status_code=400, detail="文件必须是Excel格式(.xlsx或.xls)")
        
        file_path = JSONDATA_DIR / filename
        
        # 读取现有数据（失败时从备份恢复）
        original_data = None
        try:
            data = read_json_file(file_path)
            # 保存原始数据的深拷贝作为备份
            import copy
            original_data = copy.deepcopy(data)
        except HTTPException as e:
            if e.status_code == 404:
                # 如果文件不存在，创建空数据
                data = {}
                original_data = {}
            else:
                raise
        
        # 读取Excel文件
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="上传的文件为空")
        
        # 尝试不同的引擎解析Excel
        df = None
        try:
            df = pd.read_excel(BytesIO(contents), engine='openpyxl')
        except Exception:
            try:
                df = pd.read_excel(BytesIO(contents), engine='xlrd')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Excel文件解析失败: {str(e)}")
        
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="Excel文件为空或无法读取")
        
        # 验证Excel格式：第一列必须是年份列
        first_col = str(df.columns[0]).strip().lower()
        if first_col not in ['年份', 'year', '年']:
            raise HTTPException(
                status_code=400, 
                detail=f"Excel第一列必须是'年份'列，当前为: {df.columns[0]}"
            )
        
        # 统计信息
        added_years = []
        added_countries = []
        updated_cells = 0
        errors = []
        
        # 获取列名
        year_column = df.columns[0]
        country_columns = list(df.columns[1:])
        
        # 遍历Excel数据
        # 记录导入前已有的国家集合（用于统计新增国家）
        existing_countries_before = set()
        for _y, _row in (data or {}).items():
            if isinstance(_row, dict):
                existing_countries_before.update(_row.keys())
        # 在遍历时也记录Excel中出现的国家（即使该列在某些行全为空，也视为应存在的列）
        countries_in_excel_header = [str(c).strip() for c in country_columns]
        new_countries_seen = set()

        for index, row in df.iterrows():
            try:
                # 获取年份值
                year_value = row[year_column]
                if pd.isna(year_value):
                    errors.append(f"第{index+2}行: 年份为空，已跳过")
                    continue
                
                # 转换年份为字符串
                if isinstance(year_value, (int, float)):
                    year_str = str(int(year_value)) if year_value == int(year_value) else str(year_value)
                else:
                    year_str = str(year_value).strip()
                
                if not year_str:
                    errors.append(f"第{index+2}行: 年份无效，已跳过")
                    continue
                
                # 判断年份是否存在
                year_exists = year_str in data
                
                # 如果年份不存在，创建新年份
                if not year_exists:
                    # 新增年份：先初始化为包含所有已知国家的空结构（保持列对齐）
                    data[year_str] = {}
                    # 初始化时不预填国家，后续统一补齐；避免在导入前无法确定全集
                    added_years.append(year_str)
                
                # 遍历所有国家列
                for country_col in country_columns:
                    try:
                        country_name = str(country_col).strip()
                        cell_value = row[country_col]
                        
                        # 记录Excel表头中的国家，便于后续统一补齐所有年份
                        if country_name:
                            if country_name not in existing_countries_before:
                                new_countries_seen.add(country_name)

                        # 跳过空值（实际值为空时不更新该单元格）
                        if pd.isna(cell_value):
                            continue
                        
                        # 处理数值：将numpy类型转换为Python原生类型
                        if isinstance(cell_value, str):
                            if cell_value.strip() == '':
                                continue
                            # 尝试转换为数字
                            try:
                                if '.' in cell_value:
                                    final_value = float(cell_value)
                                    if final_value == int(final_value):
                                        final_value = int(final_value)
                                else:
                                    final_value = int(cell_value)
                            except ValueError:
                                final_value = cell_value  # 保持原值
                        else:
                            # 处理numpy/int64/float64等类型
                            import numpy as np
                            if pd.isna(cell_value):
                                continue
                            # 转换为Python原生类型
                            if isinstance(cell_value, (np.integer, int)):
                                final_value = int(cell_value)
                            elif isinstance(cell_value, (np.floating, float)):
                                final_value = float(cell_value)
                                # 如果是整数形式的浮点数，转为整数
                                if final_value == int(final_value):
                                    final_value = int(final_value)
                            else:
                                # 其他类型，尝试转换
                                try:
                                    final_value = float(cell_value)
                                    if final_value == int(final_value):
                                        final_value = int(final_value)
                                except (ValueError, TypeError):
                                    final_value = str(cell_value)
                        
                        # 判断国家是否存在
                        country_exists_in_year = country_name in data[year_str]
                        
                        # 如果年份存在但国家不存在，新增国家列
                        if not country_exists_in_year:
                            # 仅在该国家原先从未出现过时计为新增国家
                            if country_name not in existing_countries_before:
                                added_countries.append(country_name)
                        
                        # 更新或添加数据
                        data[year_str][country_name] = final_value
                        updated_cells += 1
                    except Exception as e:
                        errors.append(f"第{index+2}行, {country_name}列: 处理失败 ({str(e)})")
                        continue
            except Exception as e:
                errors.append(f"第{index+2}行: 处理失败 ({str(e)})")
                continue
        
        # 统一补齐所有年份的所有国家列，缺失处填充为None，保证各年列一致
        # 计算所有年份集合
        all_years_keys = list(data.keys())
        # 计算所有国家集合：导入前已有 + Excel表头出现的国家 + 导入过程中动态新增的国家
        all_countries = set(existing_countries_before)
        all_countries.update(countries_in_excel_header)
        all_countries.update(new_countries_seen)
        # 遍历各年补齐
        for y in all_years_keys:
            if not isinstance(data.get(y), dict):
                data[y] = {}
            for c in all_countries:
                if c and c not in data[y]:
                    data[y][c] = None

        # 去重统计信息
        added_years = sorted(list(set(added_years)))
        # 以“导入前不存在、导入后存在”为标准统计新增国家
        added_countries = sorted(list(set(added_countries or [])))
        
        # 验证数据是否可以序列化为JSON（在保存前验证）
        try:
            import json
            # 尝试序列化，确保所有值都是JSON兼容的
            json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            # 如果序列化失败，尝试修复数据
            print(f"警告: 数据序列化失败，尝试修复: {str(e)}")
            # 递归转换所有numpy类型
            def convert_to_native_types(obj):
                import numpy as np
                if isinstance(obj, dict):
                    return {k: convert_to_native_types(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_to_native_types(item) for item in obj]
                elif isinstance(obj, (np.integer, int)):
                    return int(obj)
                elif isinstance(obj, (np.floating, float)):
                    val = float(obj)
                    return int(val) if val == int(val) else val
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif pd.isna(obj):
                    return None
                else:
                    return obj
            
            data = convert_to_native_types(data)
            
            # 再次验证
            try:
                json.dumps(data, ensure_ascii=False)
            except (TypeError, ValueError) as e2:
                raise HTTPException(status_code=500, detail=f"数据格式错误，无法保存: {str(e2)}")
        
        # 保存文件（只有在验证通过后才保存）
        revision = write_json_file(file_path, data)
        vis_updated = _post_write_refresh(file_path)
        
        # 构建返回消息
        message_parts = []
        if added_years:
            message_parts.append(f"新增{len(added_years)}个年份: {', '.join(added_years[:5])}")
            if len(added_years) > 5:
                message_parts[-1] += f" 等共{len(added_years)}个"
        if added_countries:
            message_parts.append(f"新增{len(added_countries)}个国家: {', '.join(added_countries[:5])}")
            if len(added_countries) > 5:
                message_parts[-1] += f" 等共{len(added_countries)}个"
        if updated_cells > 0:
            message_parts.append(f"更新{updated_cells}个数据单元格")
        if errors:
            message_parts.append(f"遇到{len(errors)}个错误")
        
        message = "；".join(message_parts) if message_parts else "导入完成，无数据更新"
        
        return ExcelImportResponse(
            status="success",
            message=message,
            added_years=added_years,
            added_countries=added_countries,
            updated_cells=updated_cells,
            errors=errors[:20],  # 最多返回20个错误
            revision=revision,
            vis_updated=vis_updated,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Excel导入错误: {error_detail}")
        
        # 如果导入失败，尝试恢复原始数据
        if original_data is not None and file_path.exists():
            try:
                print(f"尝试恢复原始数据...")
                atomic_write_json(file_path, original_data)
                print(f"✓ 已恢复原始数据到 {file_path.name}")
            except Exception as restore_error:
                print(f"✗ 恢复原始数据失败: {restore_error}")
                # 尝试从备份恢复
                backup_path = file_path.with_suffix('.json.bak')
                if backup_path.exists():
                    try:
                        with open(backup_path, 'r', encoding='utf-8') as f:
                            backup_data = json.load(f)
                        atomic_write_json(file_path, backup_data)
                        print(f"✓ 已从备份恢复 {file_path.name}")
                    except Exception as backup_restore_error:
                        print(f"✗ 从备份恢复也失败: {backup_restore_error}")
        
        raise HTTPException(status_code=500, detail=f"导入过程发生错误: {str(e)}")


# ==================== output API ====================
@app.get("/api/output/files")
async def list_output_files():
    """列出output文件夹中的所有JSON文件"""
    files = []
    for file_path in OUTPUT_DIR.glob("*.json"):
        files.append({
            "filename": file_path.name,
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime
        })
    return {"files": sorted(files, key=lambda x: x["filename"])}


@app.get("/api/output/{filename}")
async def get_output_file(filename: str):
    """读取output文件夹中的JSON文件"""
    file_path = OUTPUT_DIR / filename
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    data, revision = read_json_file_with_revision(file_path)
    return {"filename": filename, "data": data, "revision": revision}


@app.post("/api/output/{filename}/filter")
async def filter_output_file(filename: str, request: FilterRequest):
    """筛选output文件夹中的JSON文件数据"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = OUTPUT_DIR / filename
    data = read_json_file(file_path)
    
    # 应用筛选
    filtered_data = filter_data(data, request.years, request.countries)
    
    return {
        "filename": filename,
        "data": filtered_data,
        "filter": {
            "years": request.years,
            "countries": request.countries
        }
    }


@app.put("/api/output/{filename}")
async def update_output_file(filename: str, request: FileUpdateRequest):
    """更新output文件夹中的JSON文件（完全覆盖）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = OUTPUT_DIR / filename
    
    # 验证数据格式
    if not isinstance(request.data, dict):
        raise HTTPException(status_code=400, detail="数据必须是JSON对象")
    
    revision = write_json_file(file_path, request.data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    
    return {
        "message": f"文件 {filename} 已更新",
        "filename": filename,
        "revision": revision,
        "vis_updated": vis_updated,
    }


@app.post("/api/output/{filename}/add")
async def add_output_data(filename: str, request: AddDataRequest):
    """向output文件中添加数据（添加年份或国家）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = OUTPUT_DIR / filename
    data = read_json_file(file_path)
    
    # 处理单值函数（如r_open_t1.json格式为{"value": 0.4036}）
    if "value" in data and len(data) == 1:
        raise HTTPException(status_code=400, detail="单值函数不支持添加数据")
    
    if request.year:
        # 添加年份
        if request.year in data:
            raise HTTPException(status_code=400, detail=f"年份 {request.year} 已存在")
        data[request.year] = request.value
    elif request.country:
        # 添加国家（向所有年份添加该国家字段）
        if not data:
            raise HTTPException(status_code=400, detail="文件为空，无法添加国家")
        
        # 检查是否已存在该国家（至少在一个年份中）
        exists = any(request.country in year_data for year_data in data.values() if isinstance(year_data, dict))
        if exists:
            raise HTTPException(status_code=400, detail=f"国家 {request.country} 已存在")
        
        # 向所有年份添加该国家字段
        for year_key in data.keys():
            if isinstance(data[year_key], dict):
                data[year_key][request.country] = request.value
    else:
        raise HTTPException(status_code=400, detail="必须提供year或country参数")
    
    revision = write_json_file(file_path, data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    return {"message": "数据已添加", "filename": filename, "revision": revision, "vis_updated": vis_updated}


@app.delete("/api/output/{filename}/delete")
async def delete_output_data(filename: str, request: DeleteDataRequest):
    """从output文件中删除数据（删除年份或国家）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = OUTPUT_DIR / filename
    data = read_json_file(file_path)
    
    # 处理单值函数
    if "value" in data and len(data) == 1:
        raise HTTPException(status_code=400, detail="单值函数不支持删除数据")
    
    deleted = False
    
    if request.year:
        # 删除年份
        if request.year in data:
            del data[request.year]
            deleted = True
        else:
            raise HTTPException(status_code=404, detail=f"年份 {request.year} 不存在")
    elif request.country:
        # 删除国家（从所有年份中删除该国家字段）
        for year_key in data.keys():
            if isinstance(data[year_key], dict) and request.country in data[year_key]:
                del data[year_key][request.country]
                deleted = True
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"国家 {request.country} 不存在")
    else:
        raise HTTPException(status_code=400, detail="必须提供year或country参数")
    
    revision = write_json_file(file_path, data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    return {"message": "数据已删除", "filename": filename, "revision": revision, "vis_updated": vis_updated}


# ==================== 计算API ====================
@app.post("/api/calculate/batch", response_model=CalculateResponse)
async def execute_batch_calculate(background_tasks: BackgroundTasks):
    """执行批量计算"""
    try:
        _queue_calculation("global")
        background_tasks.add_task(_run_batch_calculation_pipeline, "global")
        
        return CalculateResponse(
            status="started",
            message="全球版本批量计算已开始，完成后将自动同步可视化数据"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动计算失败: {str(e)}")


@app.get("/api/calculate/status")
async def get_calculate_status():
    """获取全球版本计算状态"""
    return _read_calculation_status("global")


# ==================== 聚合版本计算API ====================
@app.post("/api/calculate_aggregation/batch", response_model=CalculateResponse)
async def execute_batch_calculate_aggregation(background_tasks: BackgroundTasks):
    """执行聚合版本的批量计算"""
    try:
        _queue_calculation("aggregation")
        background_tasks.add_task(_run_batch_calculation_pipeline, "aggregation")
        
        return CalculateResponse(
            status="started",
            message="聚合版本批量计算已开始，完成后将自动同步可视化数据"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动聚合版本计算失败: {str(e)}")


@app.get("/api/calculate_aggregation/status")
async def get_calculate_aggregation_status():
    """获取聚合版本计算状态"""
    return _read_calculation_status("aggregation")


# ==================== 全球Plus版本计算API ====================
@app.post("/api/calculate_global_plus/batch", response_model=CalculateResponse)
async def execute_batch_calculate_global_plus(background_tasks: BackgroundTasks):
    """执行全球Plus版本的批量计算"""
    try:
        _queue_calculation("global_plus")
        background_tasks.add_task(_run_batch_calculation_pipeline, "global_plus")

        return CalculateResponse(
            status="started",
            message="全球Plus版本批量计算已开始，完成后将自动同步可视化数据"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动全球Plus版本计算失败: {str(e)}")


@app.get("/api/calculate_global_plus/status")
async def get_calculate_global_plus_status():
    """获取全球Plus版本计算状态"""
    return _read_calculation_status("global_plus")


# ==================== 导出Excel功能 ====================
@app.get("/api/jsondata/{filename}/export-excel")
async def export_jsondata_to_excel(filename: str):
    """导出单个jsondata文件为Excel"""
    try:
        if not filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
        
        file_path = JSONDATA_DIR / filename
        
        # 读取JSON数据
        try:
            data = read_json_file(file_path)
        except HTTPException as e:
            if e.status_code == 404:
                raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")
            raise
        
        # 转换为DataFrame
        if not data or len(data) == 0:
            raise HTTPException(status_code=400, detail="文件数据为空")
        
        # 检查是否是单值文件
        if 'value' in data and len(data) == 1:
            # 单值文件，创建一个简单的表格
            df = pd.DataFrame([{'函数名': filename.replace('.json', ''), '值': data['value']}])
        else:
            # 多值文件，转换为DataFrame
            # 收集所有年份和所有国家
            years = sorted(data.keys())
            all_countries = set()
            for year_data in data.values():
                if isinstance(year_data, dict):
                    all_countries.update(year_data.keys())
            
            all_countries = sorted(list(all_countries))
            
            # 构建DataFrame
            rows = []
            for year in years:
                row = {_excel_primary_key_name(filename): year}
                if isinstance(data[year], dict):
                    for country in all_countries:
                        row[country] = data[year].get(country, None)
                rows.append(row)
            
            df = pd.DataFrame(rows)
        
        # 创建Excel文件
        export_df = format_dataframe_for_excel_export(df)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='数据')
        
        output.seek(0)
        
        # 返回文件流
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename.replace('.json', '')}.xlsx"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"导出Excel错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"导出Excel失败: {str(e)}")


@app.get("/api/output/{filename}/export-excel")
async def export_output_to_excel(filename: str):
    """导出单个output文件为Excel"""
    try:
        if not filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
        
        file_path = OUTPUT_DIR / filename
        
        # 读取JSON数据
        try:
            data = read_json_file(file_path)
        except HTTPException as e:
            if e.status_code == 404:
                raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")
            raise
        
        # 转换为DataFrame
        if not data or len(data) == 0:
            raise HTTPException(status_code=400, detail="文件数据为空")
        
        # 检查是否是单值文件
        if 'value' in data and len(data) == 1:
            # 单值文件
            df = pd.DataFrame([{'函数名': filename.replace('.json', ''), '值': data['value']}])
        else:
            # 多值文件
            years = sorted(data.keys())
            all_countries = set()
            for year_data in data.values():
                if isinstance(year_data, dict):
                    all_countries.update(year_data.keys())
            
            all_countries = sorted(list(all_countries))
            
            rows = []
            for year in years:
                row = {_excel_primary_key_name(filename): year}
                if isinstance(data[year], dict):
                    for country in all_countries:
                        row[country] = data[year].get(country, None)
                rows.append(row)
            
            df = pd.DataFrame(rows)
        
        # 创建Excel文件
        export_df = format_dataframe_for_excel_export(df)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='数据')
        
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename.replace('.json', '')}.xlsx"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"导出Excel错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"导出Excel失败: {str(e)}")


# ==================== jsondata_aggregation API ====================
# 聚合版本的 API 端点，复用全球版本的逻辑，但使用不同的目录

@app.get("/api/jsondata_aggregation/files")
async def list_jsondata_aggregation_files():
    """列出jsondata_aggregation文件夹中的所有JSON文件"""
    files = []
    for file_path in JSONDATA_AGGREGATION_DIR.glob("*.json"):
        files.append({
            "filename": file_path.name,
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime
        })
    return {"files": sorted(files, key=lambda x: x["filename"])}


@app.get("/api/jsondata_aggregation/{filename}")
async def get_jsondata_aggregation_file(filename: str):
    """读取jsondata_aggregation文件夹中的JSON文件"""
    file_path = JSONDATA_AGGREGATION_DIR / filename
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    data, revision = read_json_file_with_revision(file_path)
    return {"filename": filename, "data": data, "revision": revision}


@app.post("/api/jsondata_aggregation/{filename}/filter")
async def filter_jsondata_aggregation_file(filename: str, request: FilterRequest):
    """筛选jsondata_aggregation文件夹中的JSON文件数据"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = JSONDATA_AGGREGATION_DIR / filename
    data = read_json_file(file_path)
    
    # 应用筛选
    filtered_data = filter_data(data, request.years, request.countries)
    
    return {
        "filename": filename,
        "data": filtered_data,
        "filter": {
            "years": request.years,
            "countries": request.countries
        }
    }


@app.put("/api/jsondata_aggregation/{filename}")
async def update_jsondata_aggregation_file(filename: str, request: FileUpdateRequest):
    """更新jsondata_aggregation文件夹中的JSON文件（完全覆盖）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = JSONDATA_AGGREGATION_DIR / filename
    
    # 验证数据格式
    if not isinstance(request.data, dict):
        raise HTTPException(status_code=400, detail="数据必须是JSON对象")
    
    revision = write_json_file(file_path, request.data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    
    return {
        "message": f"文件 {filename} 已更新",
        "filename": filename,
        "revision": revision,
        "vis_updated": vis_updated,
    }


@app.post("/api/jsondata_aggregation/{filename}/add")
async def add_jsondata_aggregation_data(filename: str, request: AddDataRequest):
    """向jsondata_aggregation文件中添加数据（添加年份或国家）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = JSONDATA_AGGREGATION_DIR / filename
    data = read_json_file(file_path)
    
    if request.year:
        # 添加年份
        if request.year in data:
            raise HTTPException(status_code=400, detail=f"年份 {request.year} 已存在")
        data[request.year] = request.value
    elif request.country:
        # 添加国家（向所有年份添加该国家字段）
        if not data:
            raise HTTPException(status_code=400, detail="文件为空，无法添加国家")
        
        # 检查是否已存在该国家（至少在一个年份中）
        exists = any(request.country in year_data for year_data in data.values() if isinstance(year_data, dict))
        if exists:
            raise HTTPException(status_code=400, detail=f"国家 {request.country} 已存在")
        
        # 向所有年份添加该国家字段
        for year_key in data.keys():
            if isinstance(data[year_key], dict):
                data[year_key][request.country] = request.value
    else:
        raise HTTPException(status_code=400, detail="必须提供year或country参数")
    
    revision = write_json_file(file_path, data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    
    return {"message": "数据已添加", "filename": filename, "revision": revision, "vis_updated": vis_updated}


@app.delete("/api/jsondata_aggregation/{filename}/delete")
async def delete_jsondata_aggregation_data(filename: str, request: DeleteDataRequest):
    """从jsondata_aggregation文件中删除数据（删除年份或国家）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = JSONDATA_AGGREGATION_DIR / filename
    data = read_json_file(file_path)
    
    deleted = False
    
    if request.year:
        # 删除年份
        if request.year in data:
            del data[request.year]
            deleted = True
        else:
            raise HTTPException(status_code=404, detail=f"年份 {request.year} 不存在")
    elif request.country:
        # 删除国家（从所有年份中删除该国家字段）
        for year_key in data.keys():
            if isinstance(data[year_key], dict) and request.country in data[year_key]:
                del data[year_key][request.country]
                deleted = True
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"国家 {request.country} 不存在")
    else:
        raise HTTPException(status_code=400, detail="必须提供year或country参数")
    
    revision = write_json_file(file_path, data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    
    return {"message": "数据已删除", "filename": filename, "revision": revision, "vis_updated": vis_updated}


@app.post("/api/jsondata_aggregation/{filename}/import-excel", response_model=ExcelImportResponse)
async def import_excel_aggregation_data(filename: str, file: UploadFile = File(...)):
    """从Excel文件批量导入数据到jsondata_aggregation文件"""
    # 复用全球版本的导入逻辑，但使用聚合版本的目录
    try:
        if not filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
        
        # 验证文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="未提供文件名")
        
        if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
            raise HTTPException(status_code=400, detail="文件必须是Excel格式(.xlsx或.xls)")
        
        file_path = JSONDATA_AGGREGATION_DIR / filename
        
        # 读取现有数据
        original_data = None
        try:
            data = read_json_file(file_path)
            import copy
            original_data = copy.deepcopy(data)
        except HTTPException as e:
            if e.status_code == 404:
                data = {}
                original_data = {}
            else:
                raise
        
        # 读取Excel文件
        contents = await file.read()
        if len(contents) == 0:
            raise HTTPException(status_code=400, detail="上传的文件为空")
        
        # 解析Excel
        df = None
        try:
            df = pd.read_excel(BytesIO(contents), engine='openpyxl')
        except Exception:
            try:
                df = pd.read_excel(BytesIO(contents), engine='xlrd')
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Excel文件解析失败: {str(e)}")
        
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail="Excel文件为空或无法读取")
        
        # 验证Excel格式
        first_col = str(df.columns[0]).strip().lower()
        if first_col not in ['年份', 'year', '年']:
            raise HTTPException(
                status_code=400, 
                detail=f"Excel第一列必须是'年份'列，当前为: {df.columns[0]}"
            )
        
        # 统计信息
        added_years = []
        added_countries = []
        updated_cells = 0
        errors = []
        
        year_column = df.columns[0]
        country_columns = list(df.columns[1:])
        
        existing_countries_before = set()
        for _y, _row in (data or {}).items():
            if isinstance(_row, dict):
                existing_countries_before.update(_row.keys())
        
        countries_in_excel_header = [str(c).strip() for c in country_columns]
        new_countries_seen = set()

        for index, row in df.iterrows():
            try:
                year_value = row[year_column]
                if pd.isna(year_value):
                    errors.append(f"第{index+2}行: 年份为空，已跳过")
                    continue
                
                if isinstance(year_value, (int, float)):
                    year_str = str(int(year_value)) if year_value == int(year_value) else str(year_value)
                else:
                    year_str = str(year_value).strip()
                
                if not year_str:
                    errors.append(f"第{index+2}行: 年份无效，已跳过")
                    continue
                
                year_exists = year_str in data
                
                if not year_exists:
                    data[year_str] = {}
                    added_years.append(year_str)
                
                for country_col in country_columns:
                    try:
                        country_name = str(country_col).strip()
                        cell_value = row[country_col]
                        
                        if country_name:
                            if country_name not in existing_countries_before:
                                new_countries_seen.add(country_name)

                        if pd.isna(cell_value):
                            continue
                        
                        if isinstance(cell_value, str):
                            if cell_value.strip() == '':
                                continue
                            try:
                                if '.' in cell_value:
                                    final_value = float(cell_value)
                                    if final_value == int(final_value):
                                        final_value = int(final_value)
                                else:
                                    final_value = int(cell_value)
                            except ValueError:
                                final_value = cell_value
                        else:
                            import numpy as np
                            if pd.isna(cell_value):
                                continue
                            if isinstance(cell_value, (np.integer, int)):
                                final_value = int(cell_value)
                            elif isinstance(cell_value, (np.floating, float)):
                                final_value = float(cell_value)
                                if final_value == int(final_value):
                                    final_value = int(final_value)
                            else:
                                try:
                                    final_value = float(cell_value)
                                    if final_value == int(final_value):
                                        final_value = int(final_value)
                                except (ValueError, TypeError):
                                    final_value = str(cell_value)
                        
                        country_exists_in_year = country_name in data[year_str]
                        
                        if not country_exists_in_year:
                            if country_name not in existing_countries_before:
                                added_countries.append(country_name)
                        
                        data[year_str][country_name] = final_value
                        updated_cells += 1
                    except Exception as e:
                        errors.append(f"第{index+2}行, {country_name}列: 处理失败 ({str(e)})")
                        continue
            except Exception as e:
                errors.append(f"第{index+2}行: 处理失败 ({str(e)})")
                continue
        
        # 统一补齐所有年份的所有国家列
        all_years_keys = list(data.keys())
        all_countries = set(existing_countries_before)
        all_countries.update(countries_in_excel_header)
        all_countries.update(new_countries_seen)
        
        for y in all_years_keys:
            if not isinstance(data.get(y), dict):
                data[y] = {}
            for c in all_countries:
                if c and c not in data[y]:
                    data[y][c] = None

        added_years = sorted(list(set(added_years)))
        added_countries = sorted(list(set(added_countries or [])))
        
        # 验证数据
        try:
            import json
            json.dumps(data, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            def convert_to_native_types(obj):
                import numpy as np
                if isinstance(obj, dict):
                    return {k: convert_to_native_types(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [convert_to_native_types(item) for item in obj]
                elif isinstance(obj, (np.integer, int)):
                    return int(obj)
                elif isinstance(obj, (np.floating, float)):
                    val = float(obj)
                    return int(val) if val == int(val) else val
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
                elif pd.isna(obj):
                    return None
                else:
                    return obj
            
            data = convert_to_native_types(data)
            
            try:
                json.dumps(data, ensure_ascii=False)
            except (TypeError, ValueError) as e2:
                raise HTTPException(status_code=500, detail=f"数据格式错误，无法保存: {str(e2)}")
        
        revision = write_json_file(file_path, data)
        vis_updated = _post_write_refresh(file_path)
        
        message_parts = []
        if added_years:
            message_parts.append(f"新增{len(added_years)}个年份: {', '.join(added_years[:5])}")
            if len(added_years) > 5:
                message_parts[-1] += f" 等共{len(added_years)}个"
        if added_countries:
            message_parts.append(f"新增{len(added_countries)}个国家: {', '.join(added_countries[:5])}")
            if len(added_countries) > 5:
                message_parts[-1] += f" 等共{len(added_countries)}个"
        if updated_cells > 0:
            message_parts.append(f"更新{updated_cells}个数据单元格")
        if errors:
            message_parts.append(f"遇到{len(errors)}个错误")
        
        message = "；".join(message_parts) if message_parts else "导入完成，无数据更新"
        
        return ExcelImportResponse(
            status="success",
            message=message,
            added_years=added_years,
            added_countries=added_countries,
            updated_cells=updated_cells,
            errors=errors[:20],
            revision=revision,
            vis_updated=vis_updated,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Excel导入错误: {error_detail}")
        
        if original_data is not None and file_path.exists():
            try:
                print(f"尝试恢复原始数据...")
                atomic_write_json(file_path, original_data)
                print(f"✓ 已恢复原始数据到 {file_path.name}")
            except Exception as restore_error:
                print(f"✗ 恢复原始数据失败: {restore_error}")
        
        raise HTTPException(status_code=500, detail=f"导入过程发生错误: {str(e)}")


@app.get("/api/jsondata_aggregation/{filename}/export-excel")
async def export_jsondata_aggregation_to_excel(filename: str):
    """导出单个jsondata_aggregation文件为Excel"""
    try:
        if not filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
        
        file_path = JSONDATA_AGGREGATION_DIR / filename
        
        try:
            data = read_json_file(file_path)
        except HTTPException as e:
            if e.status_code == 404:
                raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")
            raise
        
        if not data or len(data) == 0:
            raise HTTPException(status_code=400, detail="文件数据为空")
        
        if 'value' in data and len(data) == 1:
            df = pd.DataFrame([{'函数名': filename.replace('.json', ''), '值': data['value']}])
        else:
            years = sorted(data.keys())
            all_countries = set()
            for year_data in data.values():
                if isinstance(year_data, dict):
                    all_countries.update(year_data.keys())
            
            all_countries = sorted(list(all_countries))
            
            rows = []
            for year in years:
                row = {_excel_primary_key_name(filename): year}
                if isinstance(data[year], dict):
                    for country in all_countries:
                        row[country] = data[year].get(country, None)
                rows.append(row)
            
            df = pd.DataFrame(rows)
        
        export_df = format_dataframe_for_excel_export(df)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='数据')
        
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename.replace('.json', '')}.xlsx"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"导出Excel错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"导出Excel失败: {str(e)}")


# ==================== output_aggregation API ====================

@app.get("/api/output_aggregation/files")
async def list_output_aggregation_files():
    """列出output_aggregation文件夹中的所有JSON文件"""
    files = []
    for file_path in OUTPUT_AGGREGATION_DIR.glob("*.json"):
        files.append({
            "filename": file_path.name,
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime
        })
    return {"files": sorted(files, key=lambda x: x["filename"])}


@app.get("/api/output_aggregation/{filename}")
async def get_output_aggregation_file(filename: str):
    """读取output_aggregation文件夹中的JSON文件"""
    file_path = OUTPUT_AGGREGATION_DIR / filename
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    data, revision = read_json_file_with_revision(file_path)
    return {"filename": filename, "data": data, "revision": revision}


@app.post("/api/output_aggregation/{filename}/filter")
async def filter_output_aggregation_file(filename: str, request: FilterRequest):
    """筛选output_aggregation文件夹中的JSON文件数据"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = OUTPUT_AGGREGATION_DIR / filename
    data = read_json_file(file_path)
    
    # 应用筛选
    filtered_data = filter_data(data, request.years, request.countries)
    
    return {
        "filename": filename,
        "data": filtered_data,
        "filter": {
            "years": request.years,
            "countries": request.countries
        }
    }


@app.put("/api/output_aggregation/{filename}")
async def update_output_aggregation_file(filename: str, request: FileUpdateRequest):
    """更新output_aggregation文件夹中的JSON文件（完全覆盖）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = OUTPUT_AGGREGATION_DIR / filename
    
    # 验证数据格式
    if not isinstance(request.data, dict):
        raise HTTPException(status_code=400, detail="数据必须是JSON对象")
    
    revision = write_json_file(file_path, request.data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    
    return {
        "message": f"文件 {filename} 已更新",
        "filename": filename,
        "revision": revision,
        "vis_updated": vis_updated,
    }


@app.post("/api/output_aggregation/{filename}/add")
async def add_output_aggregation_data(filename: str, request: AddDataRequest):
    """向output_aggregation文件中添加数据（添加年份或国家）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = OUTPUT_AGGREGATION_DIR / filename
    data = read_json_file(file_path)
    
    # 处理单值函数
    if "value" in data and len(data) == 1:
        raise HTTPException(status_code=400, detail="单值函数不支持添加数据")
    
    if request.year:
        # 添加年份
        if request.year in data:
            raise HTTPException(status_code=400, detail=f"年份 {request.year} 已存在")
        data[request.year] = request.value
    elif request.country:
        # 添加国家（向所有年份添加该国家字段）
        if not data:
            raise HTTPException(status_code=400, detail="文件为空，无法添加国家")
        
        # 检查是否已存在该国家（至少在一个年份中）
        exists = any(request.country in year_data for year_data in data.values() if isinstance(year_data, dict))
        if exists:
            raise HTTPException(status_code=400, detail=f"国家 {request.country} 已存在")
        
        # 向所有年份添加该国家字段
        for year_key in data.keys():
            if isinstance(data[year_key], dict):
                data[year_key][request.country] = request.value
    else:
        raise HTTPException(status_code=400, detail="必须提供year或country参数")
    
    revision = write_json_file(file_path, data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    return {"message": "数据已添加", "filename": filename, "revision": revision, "vis_updated": vis_updated}


@app.delete("/api/output_aggregation/{filename}/delete")
async def delete_output_aggregation_data(filename: str, request: DeleteDataRequest):
    """从output_aggregation文件中删除数据（删除年份或国家）"""
    if not filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
    
    file_path = OUTPUT_AGGREGATION_DIR / filename
    data = read_json_file(file_path)
    
    # 处理单值函数
    if "value" in data and len(data) == 1:
        raise HTTPException(status_code=400, detail="单值函数不支持删除数据")
    
    deleted = False
    
    if request.year:
        # 删除年份
        if request.year in data:
            del data[request.year]
            deleted = True
        else:
            raise HTTPException(status_code=404, detail=f"年份 {request.year} 不存在")
    elif request.country:
        # 删除国家（从所有年份中删除该国家字段）
        for year_key in data.keys():
            if isinstance(data[year_key], dict) and request.country in data[year_key]:
                del data[year_key][request.country]
                deleted = True
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"国家 {request.country} 不存在")
    else:
        raise HTTPException(status_code=400, detail="必须提供year或country参数")
    
    revision = write_json_file(file_path, data, request.expected_revision)
    vis_updated = _post_write_refresh(file_path)
    return {"message": "数据已删除", "filename": filename, "revision": revision, "vis_updated": vis_updated}


@app.get("/api/output_aggregation/{filename}/export-excel")
async def export_output_aggregation_to_excel(filename: str):
    """导出单个output_aggregation文件为Excel"""
    try:
        if not filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="文件名必须以.json结尾")
        
        file_path = OUTPUT_AGGREGATION_DIR / filename
        
        try:
            data = read_json_file(file_path)
        except HTTPException as e:
            if e.status_code == 404:
                raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")
            raise
        
        if not data or len(data) == 0:
            raise HTTPException(status_code=400, detail="文件数据为空")
        
        if 'value' in data and len(data) == 1:
            df = pd.DataFrame([{'函数名': filename.replace('.json', ''), '值': data['value']}])
        else:
            years = sorted(data.keys())
            all_countries = set()
            for year_data in data.values():
                if isinstance(year_data, dict):
                    all_countries.update(year_data.keys())
            
            all_countries = sorted(list(all_countries))
            
            rows = []
            for year in years:
                row = {_excel_primary_key_name(filename): year}
                if isinstance(data[year], dict):
                    for country in all_countries:
                        row[country] = data[year].get(country, None)
                rows.append(row)
            
            df = pd.DataFrame(rows)
        
        export_df = format_dataframe_for_excel_export(df)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            export_df.to_excel(writer, index=False, sheet_name='数据')
        
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename.replace('.json', '')}.xlsx"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"导出Excel错误: {error_detail}")
        raise HTTPException(status_code=500, detail=f"导出Excel失败: {str(e)}")


# ==================== jsondata_global_plus API ====================
@app.get("/api/jsondata_global_plus/files")
async def list_jsondata_global_plus_files():
    """列出jsondata_global_plus文件夹中的所有JSON文件"""
    return _list_directory_json_files(JSONDATA_GLOBAL_PLUS_DIR)


@app.get("/api/jsondata_global_plus/{filename}")
async def get_jsondata_global_plus_file(filename: str):
    """读取jsondata_global_plus文件夹中的JSON文件"""
    return _get_directory_json_file(JSONDATA_GLOBAL_PLUS_DIR, filename)


@app.post("/api/jsondata_global_plus/{filename}/filter")
async def filter_jsondata_global_plus_file(filename: str, request: FilterRequest):
    """筛选jsondata_global_plus文件夹中的JSON文件数据"""
    return _filter_directory_json_file(JSONDATA_GLOBAL_PLUS_DIR, filename, request)


@app.put("/api/jsondata_global_plus/{filename}")
async def update_jsondata_global_plus_file(filename: str, request: FileUpdateRequest):
    """更新jsondata_global_plus文件夹中的JSON文件（完全覆盖）"""
    return _update_directory_json_file(JSONDATA_GLOBAL_PLUS_DIR, filename, request)


@app.post("/api/jsondata_global_plus/{filename}/add")
async def add_jsondata_global_plus_data(filename: str, request: AddDataRequest):
    """向jsondata_global_plus文件中添加数据（添加年份或国家）"""
    return _add_directory_data(JSONDATA_GLOBAL_PLUS_DIR, filename, request)


@app.delete("/api/jsondata_global_plus/{filename}/delete")
async def delete_jsondata_global_plus_data(filename: str, request: DeleteDataRequest):
    """从jsondata_global_plus文件中删除数据（删除年份或国家）"""
    return _delete_directory_data(JSONDATA_GLOBAL_PLUS_DIR, filename, request)


@app.post("/api/jsondata_global_plus/{filename}/import-excel", response_model=ExcelImportResponse)
async def import_excel_global_plus_data(filename: str, file: UploadFile = File(...)):
    """全球Plus由全球版和聚合版自动合成，不支持直接导入Excel。"""
    raise HTTPException(status_code=400, detail="全球Plus由全球版和聚合版自动合成，请分别维护源数据后重新计算全球Plus")


@app.get("/api/jsondata_global_plus/{filename}/export-excel")
async def export_jsondata_global_plus_to_excel(filename: str):
    """导出单个jsondata_global_plus文件为Excel"""
    return _export_directory_json_to_excel(JSONDATA_GLOBAL_PLUS_DIR, filename)


# ==================== output_global_plus API ====================
@app.get("/api/output_global_plus/files")
async def list_output_global_plus_files():
    """列出output_global_plus文件夹中的所有JSON文件"""
    return _list_directory_json_files(OUTPUT_GLOBAL_PLUS_DIR)


@app.get("/api/output_global_plus/{filename}")
async def get_output_global_plus_file(filename: str):
    """读取output_global_plus文件夹中的JSON文件"""
    return _get_directory_json_file(OUTPUT_GLOBAL_PLUS_DIR, filename)


@app.post("/api/output_global_plus/{filename}/filter")
async def filter_output_global_plus_file(filename: str, request: FilterRequest):
    """筛选output_global_plus文件夹中的JSON文件数据"""
    return _filter_directory_json_file(OUTPUT_GLOBAL_PLUS_DIR, filename, request)


@app.put("/api/output_global_plus/{filename}")
async def update_output_global_plus_file(filename: str, request: FileUpdateRequest):
    """更新output_global_plus文件夹中的JSON文件（完全覆盖）"""
    return _update_directory_json_file(OUTPUT_GLOBAL_PLUS_DIR, filename, request)


@app.post("/api/output_global_plus/{filename}/add")
async def add_output_global_plus_data(filename: str, request: AddDataRequest):
    """向output_global_plus文件中添加数据（添加年份或国家）"""
    return _add_directory_data(OUTPUT_GLOBAL_PLUS_DIR, filename, request, reject_single_value=True)


@app.delete("/api/output_global_plus/{filename}/delete")
async def delete_output_global_plus_data(filename: str, request: DeleteDataRequest):
    """从output_global_plus文件中删除数据（删除年份或国家）"""
    return _delete_directory_data(OUTPUT_GLOBAL_PLUS_DIR, filename, request, reject_single_value=True)


@app.get("/api/output_global_plus/{filename}/export-excel")
async def export_output_global_plus_to_excel(filename: str):
    """导出单个output_global_plus文件为Excel"""
    return _export_directory_json_to_excel(OUTPUT_GLOBAL_PLUS_DIR, filename)


SPA_ROUTE_PREFIXES = ("jsondata", "output", "datavis")
RESERVED_ROUTE_PREFIXES = ("api", "vis-api", "osri-vis", "static")


def _serve_frontend_index():
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)
    raise HTTPException(status_code=404, detail="前端构建产物不存在，请先执行 Vite build")


@app.get("/", include_in_schema=False)
async def serve_frontend_root():
    return _serve_frontend_index()


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend_spa(full_path: str):
    normalized_path = full_path.strip("/")
    first_segment = normalized_path.split("/", 1)[0] if normalized_path else ""

    if first_segment in RESERVED_ROUTE_PREFIXES:
        raise HTTPException(status_code=404, detail="Not Found")

    if normalized_path == "index.html" or first_segment in SPA_ROUTE_PREFIXES:
        return _serve_frontend_index()

    raise HTTPException(status_code=404, detail="Not Found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6001)
