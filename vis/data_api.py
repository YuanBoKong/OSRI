"""
数据可视化后端API
使用FastAPI提供数据接口服务
"""
import json
import os
import base64
import io
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from scipy.interpolate import make_interp_spline

# 配置中文字体
# 尝试设置中文字体，优先使用系统可用的中文字体
try:
    # 查找系统中的中文字体
    font_list = [f.name for f in fm.fontManager.ttflist]
    chinese_fonts = ['SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei', 'STHeiti', 'Arial Unicode MS']
    available_font = None
    for font in chinese_fonts:
        if font in font_list:
            available_font = font
            break
    
    if available_font:
        plt.rcParams['font.sans-serif'] = [available_font] + plt.rcParams['font.sans-serif']
    else:
        # 如果没有找到中文字体，使用默认设置
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans', 'sans-serif']
except:
    # 如果字体查找失败，使用默认设置
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'DejaVu Sans', 'sans-serif']

plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

app = FastAPI(title="开放科学数据可视化API", version="1.0.0")

# 配置CORS，允许跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据目录路径
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_AGGREGATION_DIR = BASE_DIR / "data_aggregation"
DATA_GLOBAL_PLUS_DIR = BASE_DIR / "data_global_plus"
DATA_SOURCE_DIRS = {
    "global": DATA_DIR,
    "aggregation": DATA_AGGREGATION_DIR,
    "global_plus": DATA_GLOBAL_PLUS_DIR,
}

# 缓存数据（按数据源分别缓存，基于文件修改时间自动失效）
_data_cache: Dict[str, Dict[str, Any]] = {}  # key: "{data_source}:{filename}"
_continent_data: Dict[str, Dict[str, Any]] = {}  # key: data_source
_name_mapping: Dict[str, Dict[str, Any]] = {}  # key: data_source


def normalize_data_source(data_source: str = "global") -> str:
    return data_source if data_source in DATA_SOURCE_DIRS else "global"


def get_data_dir(data_source: str = "global") -> Path:
    return DATA_SOURCE_DIRS[normalize_data_source(data_source)]


def load_json_file(file_path: Path) -> Dict:
    """加载JSON文件"""
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path.name}")
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_cached_json(cache: Dict[str, Dict[str, Any]], cache_key: str, file_path: Path):
    """按文件修改时间缓存JSON，文件更新后自动重新加载。"""
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {file_path.name}")
    file_mtime_ns = file_path.stat().st_mtime_ns
    cached = cache.get(cache_key)
    if cached is None or cached.get("mtime_ns") != file_mtime_ns:
        cache[cache_key] = {
            "mtime_ns": file_mtime_ns,
            "data": load_json_file(file_path),
        }
    return cache[cache_key]["data"]


def get_data_file(filename: str, data_source: str = "global") -> Path:
    """获取数据文件路径，根据数据源从对应目录查找"""
    data_source = normalize_data_source(data_source)
    file_path = get_data_dir(data_source) / filename
    
    if file_path.exists():
        return file_path
    raise HTTPException(status_code=404, detail=f"数据文件不存在: {filename} (数据源: {data_source})")


def get_cached_data(filename: str, data_source: str = "global") -> Dict:
    """获取缓存的数据，文件更新后自动重新加载。"""
    data_source = normalize_data_source(data_source)
    cache_key = f"{data_source}:{filename}"
    file_path = get_data_file(filename, data_source)
    return load_cached_json(_data_cache, cache_key, file_path)


def get_continent_data(data_source: str = "global") -> Dict:
    """获取大洲映射数据"""
    data_source = normalize_data_source(data_source)
    file_path = get_data_dir(data_source) / "continent.json"
    return load_cached_json(_continent_data, data_source, file_path)


def get_name_mapping(data_source: str = "global") -> Dict:
    """获取文件名映射数据"""
    data_source = normalize_data_source(data_source)
    file_path = get_data_dir(data_source) / "name.json"
    name_data = load_cached_json(_name_mapping, data_source, file_path)
    return name_data[0] if isinstance(name_data, list) else name_data


@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "message": "开放科学数据可视化API",
        "version": "1.0.0",
        "endpoints": {
            "name": "/api/name - 获取文件名映射表",
            "continent": "/api/continent - 获取大洲映射表",
            "files": "/api/files - 获取所有可用数据文件列表",
            "data": "/api/data/{filename} - 获取完整数据",
            "data_by_year": "/api/data/{filename}/year/{year} - 按年份获取数据",
            "data_by_country": "/api/data/{filename}/country/{country} - 按国家获取时间序列",
            "data_by_continent": "/api/data/{filename}/continent/{continent} - 按大洲获取数据",
            "data_filter": "/api/data/{filename}/filter - 筛选数据（支持多国家、年份范围等）"
        }
    }


@app.get("/api/name")
async def get_name_mapping_api(data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")):
    """返回文件名映射表"""
    return get_name_mapping(data_source)


@app.get("/api/continent")
async def get_continent_mapping(data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")):
    """返回大洲映射表"""
    return get_continent_data(data_source)


@app.get("/api/files")
async def get_available_files(data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")):
    """返回所有可用的数据文件列表"""
    files = []
    name_mapping = get_name_mapping(data_source)
    
    target_dir = get_data_dir(data_source)
    
    # 扫描对应目录
    for file_path in target_dir.glob("*.json"):
        filename = file_path.name
        # 排除配置文件和映射文件
        if filename not in ["continent.json", "name.json"]:
            files.append({
                "filename": filename,
                "path": filename,
                "description": name_mapping.get(filename, ""),
                "type": "data"
            })
    
    return {"files": files, "total": len(files)}


@app.get("/api/data/{filename}")
async def get_full_data(filename: str, data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")):
    """获取完整数据"""
    try:
        data = get_cached_data(filename, data_source)
        return {
            "filename": filename,
            "data": data,
            "years": sorted(data.keys()) if isinstance(data, dict) else [],
            "total_years": len(data.keys()) if isinstance(data, dict) else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据失败: {str(e)}")


@app.get("/api/data/{filename}/year/{year}")
async def get_data_by_year(filename: str, year: str, data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")):
    """按年份获取数据"""
    try:
        data = get_cached_data(filename, data_source)
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="数据格式不支持按年份查询")
        
        if year not in data:
            raise HTTPException(status_code=404, detail=f"年份 {year} 不存在")
        
        year_data = data[year]
        return {
            "filename": filename,
            "year": year,
            "data": year_data,
            "countries": list(year_data.keys()) if isinstance(year_data, dict) else [],
            "total_countries": len(year_data.keys()) if isinstance(year_data, dict) else 0
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据失败: {str(e)}")


@app.get("/api/data/{filename}/country/{country}")
async def get_data_by_country(filename: str, country: str, data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")):
    """按国家获取时间序列数据"""
    try:
        data = get_cached_data(filename, data_source)
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="数据格式不支持按国家查询")
        
        country_data = {}
        for year, year_data in data.items():
            if isinstance(year_data, dict) and country in year_data:
                country_data[year] = year_data[country]
        
        if not country_data:
            raise HTTPException(status_code=404, detail=f"国家 {country} 的数据不存在")
        
        return {
            "filename": filename,
            "country": country,
            "data": country_data,
            "years": sorted(country_data.keys()),
            "total_years": len(country_data)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据失败: {str(e)}")


@app.get("/api/data/{filename}/continent/{continent}")
async def get_data_by_continent(filename: str, continent: str, data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")):
    """按大洲获取数据"""
    try:
        data = get_cached_data(filename, data_source)
        continent_mapping = get_continent_data(data_source)
        
        if continent not in continent_mapping:
            available = list(continent_mapping.keys())
            raise HTTPException(
                status_code=404, 
                detail=f"大洲 {continent} 不存在。可用大洲: {', '.join(available)}"
            )
        
        countries_in_continent = continent_mapping[continent]
        result = {}
        
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="数据格式不支持按大洲查询")
        
        for year, year_data in data.items():
            if isinstance(year_data, dict):
                result[year] = {
                    country: year_data[country]
                    for country in countries_in_continent
                    if country in year_data
                }
        
        return {
            "filename": filename,
            "continent": continent,
            "countries": countries_in_continent,
            "data": result,
            "years": sorted(result.keys()),
            "total_years": len(result)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据失败: {str(e)}")


@app.get("/api/data/{filename}/filter")
async def filter_data(
    filename: str,
    countries: Optional[str] = Query(None, description="国家列表，逗号分隔"),
    start_year: Optional[str] = Query(None, description="起始年份"),
    end_year: Optional[str] = Query(None, description="结束年份"),
    continent: Optional[str] = Query(None, description="大洲名称"),
    format: Optional[str] = Query("nested", description="返回格式: nested(嵌套) 或 flat(扁平)"),
    data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")
):
    """
    筛选数据，支持多种筛选条件
    
    - countries: 国家列表，逗号分隔，如 "China,United States,Germany"
    - start_year: 起始年份
    - end_year: 结束年份
    - continent: 大洲名称
    - format: 返回格式，nested(默认) 或 flat
    - data_source: 数据源，global(默认)、global_plus 或 aggregation
    """
    try:
        data = get_cached_data(filename, data_source)
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="数据格式不支持筛选")
        
        # 确定要筛选的国家列表
        target_countries = set()
        
        if continent:
            continent_mapping = get_continent_data(data_source)
            if continent not in continent_mapping:
                raise HTTPException(status_code=404, detail=f"大洲 {continent} 不存在")
            target_countries.update(continent_mapping[continent])
        
        if countries:
            country_list = [c.strip() for c in countries.split(",")]
            if continent:
                # 如果同时指定了大洲和国家，取交集
                target_countries = target_countries.intersection(set(country_list))
            else:
                target_countries.update(country_list)
        
        # 如果没有指定国家或大洲，返回所有国家
        if not target_countries:
            target_countries = None
        
        # 筛选年份
        all_years = sorted(data.keys())
        if start_year:
            all_years = [y for y in all_years if y >= start_year]
        if end_year:
            all_years = [y for y in all_years if y <= end_year]
        
        # 构建结果
        result = {}
        for year in all_years:
            year_data = data[year]
            if not isinstance(year_data, dict):
                continue
            
            if target_countries:
                result[year] = {
                    country: year_data[country]
                    for country in target_countries
                    if country in year_data
                }
            else:
                result[year] = year_data
        
        # 根据format参数决定返回格式
        if format == "flat":
            # 扁平格式：按国家组织，每个国家包含年份-值的映射
            flat_result = {}
            for year, year_data in result.items():
                for country, value in year_data.items():
                    if country not in flat_result:
                        flat_result[country] = {}
                    flat_result[country][year] = value
            return {
                "filename": filename,
                "format": "flat",
                "filters": {
                    "countries": list(target_countries) if target_countries else "all",
                    "start_year": start_year,
                    "end_year": end_year,
                    "continent": continent
                },
                "data": flat_result,
                "countries": sorted(flat_result.keys()),
                "years": sorted(all_years)
            }
        else:
            # 嵌套格式（默认）：按年份组织
            return {
                "filename": filename,
                "format": "nested",
                "filters": {
                    "countries": list(target_countries) if target_countries else "all",
                    "start_year": start_year,
                    "end_year": end_year,
                    "continent": continent
                },
                "data": result,
                "years": sorted(result.keys()),
                "countries": sorted(set(
                    country for year_data in result.values() 
                    for country in year_data.keys()
                )) if result else []
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"筛选数据失败: {str(e)}")


@app.get("/api/data/{filename}/countries")
async def get_countries_in_data(filename: str, data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")):
    """获取数据文件中包含的所有国家列表"""
    try:
        data = get_cached_data(filename, data_source)
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="数据格式不支持")
        
        all_countries = set()
        for year_data in data.values():
            if isinstance(year_data, dict):
                all_countries.update(year_data.keys())
        
        return {
            "filename": filename,
            "countries": sorted(all_countries),
            "total": len(all_countries)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据失败: {str(e)}")


@app.get("/api/data/{filename}/years")
async def get_years_in_data(filename: str, data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")):
    """获取数据文件中包含的所有年份列表"""
    try:
        data = get_cached_data(filename, data_source)
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="数据格式不支持")
        
        years = sorted(data.keys())
        return {
            "filename": filename,
            "years": years,
            "total": len(years),
            "start_year": years[0] if years else None,
            "end_year": years[-1] if years else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取数据失败: {str(e)}")


@app.get("/api/data/{filename}/top-countries")
async def get_top_countries(
    filename: str,
    year: str = Query(..., description="年份"),
    top_n: int = Query(20, description="返回前N名，默认20"),
    data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")
):
    """
    获取指定年份排名前N的国家列表
    
    返回格式：
    {
        "filename": "R.json",
        "year": "2024",
        "top_n": 20,
        "countries": ["United States", "China", "United Kingdom", ...]
    }
    """
    try:
        data = get_cached_data(filename, data_source)
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="数据格式不支持")
        
        if year not in data:
            raise HTTPException(status_code=404, detail=f"年份 {year} 不存在")
        
        year_data = data[year]
        if not isinstance(year_data, dict):
            raise HTTPException(status_code=400, detail="年份数据格式不支持")
        
        # 获取所有国家的数值
        country_values = {}
        for country, value in year_data.items():
            if isinstance(value, (int, float)):
                country_values[country] = value
        
        # 按值排序（降序）
        sorted_countries = sorted(
            country_values.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # 取前N名
        top_countries = [country for country, value in sorted_countries[:top_n]]
        
        return {
            "filename": filename,
            "year": year,
            "top_n": top_n,
            "countries": top_countries
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取排名国家失败: {str(e)}")


@app.get("/api/data/{filename}/ranking")
async def get_ranking_data(
    filename: str,
    countries: Optional[str] = Query(None, description="国家列表，逗号分隔，为空则返回所有国家"),
    start_year: Optional[str] = Query(None, description="起始年份"),
    end_year: Optional[str] = Query(None, description="结束年份"),
    top_n: Optional[int] = Query(None, description="返回前N名，为空则返回所有"),
    data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")
):
    """
    获取排名数据，按年份返回每个国家的排名和数值
    
    返回格式：
    {
        "years": ["2014", "2015", ...],
        "data": {
            "2014": [
                {"country": "United States", "value": 0.83, "rank": 1},
                {"country": "United Kingdom", "value": 0.35, "rank": 2},
                ...
            ],
            ...
        }
    }
    """
    try:
        data = get_cached_data(filename, data_source)
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="数据格式不支持")
        
        # 确定要筛选的国家
        target_countries = None
        if countries:
            target_countries = set([c.strip() for c in countries.split(",")])
        
        # 筛选年份
        all_years = sorted(data.keys())
        if start_year:
            all_years = [y for y in all_years if y >= start_year]
        if end_year:
            all_years = [y for y in all_years if y <= end_year]
        
        # 构建排名数据
        ranking_data = {}
        for year in all_years:
            year_data = data[year]
            if not isinstance(year_data, dict):
                continue
            
            # 筛选国家
            country_values = {}
            for country, value in year_data.items():
                if target_countries is None or country in target_countries:
                    if isinstance(value, (int, float)):
                        country_values[country] = value
            
            # 按值排序（降序）
            sorted_countries = sorted(
                country_values.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # 应用top_n限制
            if top_n:
                sorted_countries = sorted_countries[:top_n]
            
            # 构建排名列表
            ranking_list = []
            for rank, (country, value) in enumerate(sorted_countries, 1):
                ranking_list.append({
                    "country": country,
                    "value": value,
                    "rank": rank
                })
            
            ranking_data[year] = ranking_list
        
        return {
            "filename": filename,
            "years": all_years,
            "data": ranking_data,
            "total_years": len(all_years)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取排名数据失败: {str(e)}")


@app.get("/api/chart/rank-flow")
async def generate_rank_flow_chart(
    filename: str = Query(..., description="数据文件名"),
    countries: str = Query(..., description="国家列表，逗号分隔"),
    start_year: str = Query(..., description="起始年份"),
    end_year: str = Query(..., description="结束年份"),
    display_limit: int = Query(26, description="显示限制，默认26"),
    title: str = Query("", description="图表标题"),
    data_source: str = Query("global", description="数据源: global、global_plus 或 aggregation")
):
    """
    生成排名变化图（使用Python matplotlib）
    返回base64编码的PNG图片
    """
    try:
        # 解析参数
        country_list = [c.strip() for c in countries.split(',') if c.strip()]
        years_list = []
        start = int(start_year)
        end = int(end_year)
        for y in range(start, end + 1):
            years_list.append(str(y))
        
        # 获取数据
        data = get_cached_data(filename, data_source)
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="数据格式不支持")
        
        # 构建排名数据框（模拟pandas DataFrame）
        rank_data = {}
        for country in country_list:
            rank_data[country] = []
            for year in years_list:
                if year not in data:
                    rank_data[country].append(None)
                    continue
                
                year_data = data[year]
                if not isinstance(year_data, dict) or country not in year_data:
                    rank_data[country].append(None)
                    continue
                
                # 计算排名
                all_scores = [(c, s) for c, s in year_data.items() 
                             if s is not None and not (isinstance(s, float) and np.isnan(s))]
                all_scores.sort(key=lambda x: x[1], reverse=True)
                
                rank = None
                for idx, (c, _) in enumerate(all_scores, 1):
                    if c == country:
                        rank = idx
                        break
                
                rank_data[country].append(rank)
        
        # 生成颜色
        base_colors = plt.cm.get_cmap("tab20", 20)
        colors = np.vstack([base_colors(np.linspace(0, 1, 20)), base_colors(np.linspace(0, 1, 20))])
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(18, 12), facecolor="white")
        x = np.arange(len(years_list))
        x_smooth = np.linspace(0, len(years_list) - 1, 600)
        
        for i, country in enumerate(country_list):
            y_raw = np.array(rank_data[country])
            color = colors[i % 40]
            
            # 处理None值
            valid_mask = ~np.isnan(y_raw)
            if not np.any(valid_mask):
                continue
            
            y_plot = np.where(y_raw > display_limit, display_limit + 2, y_raw)
            y_plot = np.where(np.isnan(y_plot), display_limit + 2, y_plot)
            
            # 平滑曲线（只对有效数据点）
            if np.sum(valid_mask) >= 2:
                x_valid = x[valid_mask]
                y_valid = y_plot[valid_mask]
                try:
                    spl = make_interp_spline(x_valid, y_valid, k=min(3, len(x_valid) - 1))
                    y_smooth = spl(x_smooth)
                    ax.plot(x_smooth, y_smooth, color=color, alpha=0.5, linewidth=2.5, linestyle="-", zorder=1)
                except:
                    # 如果插值失败，直接绘制
                    ax.plot(x[valid_mask], y_valid, color=color, alpha=0.5, linewidth=2.5, linestyle="-", zorder=1)
            
            # 散点（只显示在displayLimit内的点）
            visible_mask = (y_raw <= display_limit) & valid_mask
            if np.any(visible_mask):
                ax.scatter(
                    x[visible_mask],
                    y_raw[visible_mask],
                    color=color,
                    s=80,
                    zorder=3,
                    edgecolors="white",
                    linewidth=0.8,
                )
            
            # 左侧标签（第一个年份）
            if valid_mask[0] and y_raw[0] <= display_limit:
                ax.text(
                    -0.15,
                    y_raw[0],
                    country,
                    ha="right",
                    va="center",
                    fontsize=9,
                    fontweight="bold",
                    color=color,
                )
            
            # 右侧标签（最后一个年份）
            if valid_mask[-1]:
                rank_last = int(y_raw[-1])
                display_rank = rank_last if rank_last <= display_limit else display_limit + 2
                
                # 圆形标记
                circle = plt.Circle((len(years_list) - 1, display_rank), 0.15, color=color, alpha=0.9, zorder=4)
                ax.add_patch(circle)
                
                # 排名数字
                ax.text(
                    len(years_list) - 1,
                    display_rank,
                    str(rank_last),
                    color="white",
                    ha="center",
                    va="center",
                    fontsize=8,
                    fontweight="bold",
                    zorder=5,
                )
                
                # 国家名称
                ax.text(
                    len(years_list) - 0.8,
                    display_rank,
                    f"  {country}",
                    ha="left",
                    va="center",
                    fontsize=9,
                    fontweight="bold",
                    color=color,
                )
        
        # 设置坐标轴
        ax.set_ylim(display_limit + 0.5, 0.5)
        ax.set_xlim(-1.5, len(years_list) + 0.5)
        ax.axis("off")
        
        # 年份标签
        for i, yr in enumerate(years_list):
            ax.text(i, 0, str(yr), ha="center", va="bottom", fontsize=12, fontweight="bold", color="#2c3e50")
        
        # Top 10分界线
        ax.axhline(y=10.5, color="#bdc3c7", linestyle="--", linewidth=1, alpha=0.4, zorder=0)
        ax.text(-1.3, 10.5, "Top 10", color="#95a5a6", fontsize=10, va="center")
        
        # 不显示标题
        chart_title = title or f"{filename} - 排名变化"
        fig.tight_layout()
        
        # 转换为base64
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        
        return {
            "image": f"data:image/png;base64,{img_base64}",
            "filename": filename,
            "title": chart_title
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成图表失败: {str(e)}")


@app.get("/api/all-data")
async def get_all_data():
    """
    获取所有数据文件的内容
    返回data、data_global_plus和data_aggregation目录下的所有数据文件，以JSON格式返回
    
    返回格式：
    {
        "global": {
            "filename1.json": { ... },
            "filename2.json": { ... }
        },
        "global_plus": {
            "filename1.json": { ... },
            "filename2.json": { ... }
        },
        "aggregation": {
            "filename1.json": { ... },
            "filename2.json": { ... }
        }
    }
    """
    try:
        result = {
            "global": {},
            "global_plus": {},
            "aggregation": {}
        }

        for data_source, data_dir in DATA_SOURCE_DIRS.items():
            for file_path in data_dir.glob("*.json"):
                filename = file_path.name
                if filename not in ["continent.json", "name.json"]:
                    try:
                        data = load_json_file(file_path)
                        result[data_source][filename] = data
                    except Exception as e:
                        result[data_source][filename] = {"error": f"Failed to load: {str(e)}"}
        
        return {
            "message": "All data files loaded",
            "data": result,
            "summary": {
                "global": {
                    "total_files": len(result["global"]),
                    "files": list(result["global"].keys())
                },
                "global_plus": {
                    "total_files": len(result["global_plus"]),
                    "files": list(result["global_plus"].keys())
                },
                "aggregation": {
                    "total_files": len(result["aggregation"]),
                    "files": list(result["aggregation"].keys())
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取所有数据失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
