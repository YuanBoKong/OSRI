# 计算具体指标的函数
import json
import os
import math
from functools import lru_cache
from pathlib import Path
from data_validation import validate_calculation_inputs, validate_file_payload
from file_storage import atomic_write_json
from output_statistics import calculate_output_statistics

# 读取所有json文件存储到字典中
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "jsondata"
json_files = {
    "alpha_F": DATA_DIR / "alpha_F.json",
    "cooperation": DATA_DIR / "cooperation.json",
    "OA": DATA_DIR / "OA.json",
    "alpha_I": DATA_DIR / "alpha_I.json",
    "F2": DATA_DIR / "F2.json",
    "IPRI": DATA_DIR / "IPRI.json",
    "platform": DATA_DIR / "platform.json",
    "alpha_L": DATA_DIR / "alpha_L.json",
    "FWCI": DATA_DIR / "FWCI.json",
    "retraction": DATA_DIR / "retraction.json",
    "scientist": DATA_DIR / "scientist.json",
    "total": DATA_DIR / "total.json",
    "world_total": DATA_DIR / "world_total.json",
    "weight": DATA_DIR / "weight.json",
    "F3": DATA_DIR / "F3.json",
    "journals": DATA_DIR / "journals.json",
    "UNESCO": DATA_DIR / "UNESCO.json",
    "policy": DATA_DIR / "policy.json"
}

# ==================== 数据预加载和缓存 ====================
# 预加载所有JSON文件到内存
_data_cache = {}

# HDI 数据（按国家名索引，不是按年份）
_hdi_data = None

# 缓存计算结果
_cache = {
    'constants': {},  # 单值函数的结果
    'functions': {}    # 多参数函数的结果
}

def _to_number_or_none(value):
    """把输入值安全转换为浮点数；无法转换时返回None"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if s == "" or s == "-":
            return None
        try:
            # 尝试去掉千位分隔符
            s = s.replace(",", "")
            return float(s)
        except Exception:
            return None
    return None

def _adjust_with_hdi(raw_value, country, alpha=0.6):
    """
    使用加权平均法，将原始分数与 HDI 进行融合：
        S_final = alpha * S_raw + (1 - alpha) * HDI
    
    - 当某个国家没有 HDI 数据时，保持原始值不变
    - 当原始值为 None 时，处理后也为 None（即不使用 HDI 填补）
    
    Args:
        raw_value: 原始分数（float 或 None）
        country: 国家名称
        alpha: 权重系数，默认 0.6
    
    Returns:
        调整后的分数（float 或 None）
    """
    if not (0.0 <= alpha <= 1.0):
        raise ValueError("alpha 必须在 [0, 1] 区间内")
    
    # 原始值为 None：结果也为 None（不使用 HDI 填补）
    if raw_value is None:
        return None
    
    # 获取 HDI 值
    hdi_value = _hdi_data.get(country) if _hdi_data else None
    
    # 只有原始分，没有 HDI：保持原始值
    if hdi_value is None:
        return raw_value
    
    # 正常加权
    s_final = alpha * float(raw_value) + (1.0 - alpha) * float(hdi_value)
    return s_final

def reload_data_cache():
    """重新加载所有JSON文件到内存（当文件被修改后调用）"""
    global _data_cache, _cache, _hdi_data
    _data_cache = {}
    for key, path in json_files.items():
        try:
            if not os.path.exists(path):
                print(f"警告: 文件不存在，跳过: {path}")
                _data_cache[key] = {}
                continue
            # 尝试读取文件
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                validate_file_payload(path.parent.name, path.name, data)
                _data_cache[key] = data
            except (json.JSONDecodeError, ValueError) as e:
                # JSON格式或结构错误，尝试从备份恢复
                backup_path = path.with_suffix(path.suffix + '.bak')
                if os.path.exists(backup_path):
                    print(f"警告: {path} JSON格式错误，尝试从备份恢复...")
                    try:
                        with open(backup_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        validate_file_payload(path.parent.name, path.name, data)
                        _data_cache[key] = data
                        # 尝试修复原文件
                        try:
                            atomic_write_json(path, data)
                            print(f"      ✓ 已从备份恢复并修复文件: {path}")
                        except:
                            print(f"      已从备份恢复数据，但无法修复文件")
                    except Exception as restore_error:
                        print(f"      ✗ 从备份恢复失败: {str(restore_error)}")
                        _data_cache[key] = {}
                else:
                    print(f"错误: JSON文件格式错误且无备份 {path}: {str(e)}")
                    _data_cache[key] = {}
        except Exception as e:
            print(f"错误: 读取文件失败 {path}: {str(e)}")
            _data_cache[key] = {}
    
    # 加载 HDI 数据
    hdi_path = BASE_DIR / "HDI.json"
    try:
        if os.path.exists(hdi_path):
            with open(hdi_path, 'r', encoding='utf-8') as f:
                _hdi_data = json.load(f)
        else:
            print(f"警告: HDI文件不存在: {hdi_path}")
            _hdi_data = {}
    except Exception as e:
        print(f"错误: 读取HDI文件失败 {hdi_path}: {str(e)}")
        _hdi_data = {}
    
    # 清空计算结果缓存，因为数据已更新
    _cache = {
        'constants': {},
        'functions': {}
    }

# 初始加载
reload_data_cache()

# 输出文件夹
_output_dir = BASE_DIR / "output"
os.makedirs(_output_dir, exist_ok=True)

def save_to_json(func_name, data):
    """保存计算结果到JSON文件"""
    output_path = _output_dir / f"{func_name}.json"
    atomic_write_json(output_path, data)

# ==================== 辅助函数 ====================
def get_cache_key(func_name, *args):
    """生成缓存key"""
    if args:
        return f"{func_name}_{args[0]}_{args[1]}"
    return func_name

def get_from_cache(func_name, *args):
    """从缓存获取值"""
    key = get_cache_key(func_name, *args)
    if args:
        year_str = str(args[0])
        country = args[1]
        if func_name in _cache['functions']:
            if year_str in _cache['functions'][func_name]:
                if country in _cache['functions'][func_name][year_str]:
                    return _cache['functions'][func_name][year_str][country]
    else:
        if func_name in _cache['constants']:
            return _cache['constants'][func_name]
    return None

def set_cache(func_name, value, *args):
    """设置缓存值"""
    if args:
        year_str = str(args[0])
        country = args[1]
        if func_name not in _cache['functions']:
            _cache['functions'][func_name] = {}
        if year_str not in _cache['functions'][func_name]:
            _cache['functions'][func_name][year_str] = {}
        _cache['functions'][func_name][year_str][country] = value
    else:
        _cache['constants'][func_name] = value

# ==================== 基础函数 ====================
# 2
def r_open_t1():
    '''计算r_open_t1'''
    if 'r_open_t1' in _cache['constants']:
        return _cache['constants']['r_open_t1']
    
    data_oa = _data_cache['OA']
    data_total = _data_cache['total']
    
    years = sorted([int(y) for y in data_oa.keys()])
    year_avg_ratios = []
    
    for year in years:
        year_str = str(year)
        oa_values = data_oa[year_str]
        total_values = data_total[year_str]
        
        country_ratios = []
        for country in oa_values.keys():
            if country in total_values:
                oa_val = oa_values[country]
                total_val = total_values[country]
                if oa_val is not None and total_val is not None and total_val > 0:
                    ratio = oa_val / total_val
                    country_ratios.append(ratio)
        
        if country_ratios:
            avg_ratio = sum(country_ratios) / len(country_ratios)
            year_avg_ratios.append((year, avg_ratio))
    
    if not year_avg_ratios:
        result = None
    else:
        result = max(year_avg_ratios, key=lambda x: x[1])[1]
    
    _cache['constants']['r_open_t1'] = result
    save_to_json('r_open_t1', {"value": result})
    return result

# 3
def r_open_t(year, country):
    '''公式：该年该国家的OA/该年该国家的total'''
    cached = get_from_cache('r_open_t', year, country)
    if cached is not None:
        return cached
    
    data_oa = _data_cache['OA']
    data_total = _data_cache['total']
    year_str = str(year)

    if year_str not in data_oa or year_str not in data_total:
        result = None
    elif country not in data_oa[year_str] or country not in data_total[year_str]:
        result = None
    else:
        oa_val = data_oa[year_str][country]
        total_val = data_total[year_str][country]
        
        if oa_val is None or total_val is None or total_val == 0:
            result = None
        else:
            result = oa_val / total_val
    
    set_cache('r_open_t', result, year, country)
    return result

# 4
def P_open_t1():
    '''计算P_open_t1'''
    if 'P_open_t1' in _cache['constants']:
        return _cache['constants']['P_open_t1']
    
    data_oa = _data_cache['OA']
    years = sorted([int(y) for y in data_oa.keys()])
    year_avg_ratios = []
    
    for year in years:
        year_str = str(year)
        oa_values = data_oa[year_str]
        
        oa_sum = sum(v for v in oa_values.values() if v is not None)
        country_count = sum(1 for v in oa_values.values() if v is not None)
        
        if country_count > 0:
            avg_per_region = oa_sum / country_count
            year_avg_ratios.append(avg_per_region)
    
    result = max(year_avg_ratios) if year_avg_ratios else None
    
    _cache['constants']['P_open_t1'] = result
    save_to_json('P_open_t1', {"value": result})
    return result

# 5
def P_open_t(year, country):
    '''计算P_open_t'''
    cached = get_from_cache('P_open_t', year, country)
    if cached is not None:
        return cached
    
    year_str = str(year)
    data_oa = _data_cache['OA']
    result = data_oa[year_str][country]
    
    set_cache('P_open_t', result, year, country)
    return result

# 计算R_open的函数
def R_open(year, country):
    '''计算R_open'''
    cached = get_from_cache('R_open', year, country)
    if cached is not None:
        return cached
    
    r_open_t_value = r_open_t(year, country)
    p_open_t_value = P_open_t(year, country)
    r_open_t1_value = r_open_t1()
    p_open_t1_value = P_open_t1()
    
    if r_open_t_value is None or p_open_t_value is None or r_open_t1_value is None or p_open_t1_value is None:
        result = None
    else:
        valueac = r_open_t_value / r_open_t1_value
        valuebd = p_open_t_value / p_open_t1_value
        result = 0.5 * (valueac + valuebd)
    
    set_cache('R_open', result, year, country)
    return result

# 6
def r_incl_t(year, country):
    '''计算r_incl_t'''
    cached = get_from_cache('r_incl_t', year, country)
    if cached is not None:
        return cached
    
    year_str = str(year)
    data_cooperation = _data_cache['cooperation']
    data_total = _data_cache['total']
    # 安全取数并转换
    coop_raw = data_cooperation.get(year_str, {}).get(country)
    total_raw = data_total.get(year_str, {}).get(country)
    coop_val = _to_number_or_none(coop_raw)
    total_val = _to_number_or_none(total_raw)
    if coop_val is None or total_val is None or total_val <= 0:
        result = None
    else:
        result = coop_val / total_val
    
    set_cache('r_incl_t', result, year, country)
    return result

# 7
def r_incl_t1():
    '''计算r_incl_t1'''
    if 'r_incl_t1' in _cache['constants']:
        return _cache['constants']['r_incl_t1']
    
    data_cooperation = _data_cache['cooperation']
    data_total = _data_cache['total']
    
    years = sorted([int(y) for y in data_cooperation.keys()])
    year_avg_ratios = []
    
    for year in years:
        year_str = str(year)
        
        if year_str not in data_cooperation or year_str not in data_total:
            continue
        
        cooperation_values = data_cooperation[year_str]
        total_values = data_total[year_str]
        
        country_r_incl_values = []
        for country in cooperation_values.keys():
            if country in total_values:
                cooperation_val = _to_number_or_none(cooperation_values[country])
                total_val = _to_number_or_none(total_values[country])
                
                if cooperation_val is not None and total_val is not None and total_val > 0:
                    r_incl_value = cooperation_val / total_val
                    country_r_incl_values.append(r_incl_value)
        
        if country_r_incl_values:
            avg_ratio = sum(country_r_incl_values) / len(country_r_incl_values)
            year_avg_ratios.append(avg_ratio)
    
    result = max(year_avg_ratios) if year_avg_ratios else None
    
    _cache['constants']['r_incl_t1'] = result
    save_to_json('r_incl_t1', {"value": result})
    return result

# 8
def P_incl_t(year, country):
    '''计算P_incl_t'''
    cached = get_from_cache('P_incl_t', year, country)
    if cached is not None:
        return cached
    
    year_str = str(year)
    data_cooperation = _data_cache['cooperation']
    raw_val = data_cooperation.get(year_str, {}).get(country)
    result = _to_number_or_none(raw_val)
    
    set_cache('P_incl_t', result, year, country)
    return result

# 9
def P_incl_t1():
    '''计算P_incl_t1'''
    if 'P_incl_t1' in _cache['constants']:
        return _cache['constants']['P_incl_t1']
    
    data_cooperation = _data_cache['cooperation']
    years = sorted([int(y) for y in data_cooperation.keys()])
    year_avg_values = []
    
    for year in years:
        year_str = str(year)
        
        if year_str not in data_cooperation:
            continue
        
        cooperation_values = data_cooperation[year_str]
        # 仅统计可转换为数值的项
        country_p_incl_values = []
        for v in cooperation_values.values():
            num = _to_number_or_none(v)
            if num is not None:
                country_p_incl_values.append(num)
        
        if country_p_incl_values:
            avg_value = sum(country_p_incl_values) / len(country_p_incl_values)
            year_avg_values.append(avg_value)
    
    result = max(year_avg_values) if year_avg_values else None
    
    _cache['constants']['P_incl_t1'] = result
    save_to_json('P_incl_t1', {"value": result})
    return result

# 计算R_incl的函数
def R_incl(year, country):
    '''计算R_incl'''
    cached = get_from_cache('R_incl', year, country)
    if cached is not None:
        return cached
    
    r_incl_t_value = r_incl_t(year, country)
    p_incl_t_value = P_incl_t(year, country)
    r_incl_t1_value = r_incl_t1()
    p_incl_t1_value = P_incl_t1()
    
    if r_incl_t_value is None or p_incl_t_value is None or r_incl_t1_value is None or p_incl_t1_value is None:
        print("--------------------------------R_incl: None--------------------------------")
        result = None
    else:
        valueac = r_incl_t_value / r_incl_t1_value
        valuebd = p_incl_t_value / p_incl_t1_value
        result = 0.5 * (valueac + valuebd)
    
    set_cache('R_incl', result, year, country)
    return result

# 计算R_oa的函数
def R_oa(year, country):
    '''计算R_oa'''
    cached = get_from_cache('R_oa', year, country)
    if cached is not None:
        return cached
    R_open_value = R_open(year, country)
    R_incl_value = R_incl(year, country)
    
    if R_open_value is None or R_incl_value is None:
        result = None
    else:
        result = math.sqrt(R_open_value ** 2 + R_incl_value ** 2)
    
    set_cache('R_oa', result, year, country)
    return result

# 计算R_oa_bar的函数
def R_oa_bar(year, country):
    '''计算R_oa_bar'''
    cached = get_from_cache('R_oa_bar', year, country)
    if cached is not None:
        return cached
    
    # 检查是否有缓存的历年最大值
    cache_key_max = 'R_oa_bar_max_of_max'
    if cache_key_max in _cache['constants']:
        max_of_max = _cache['constants'][cache_key_max]
    else:
        # 计算历年最大值
        data_oa = _data_cache['OA']
        years = sorted([int(y) for y in data_oa.keys()])
        year_max_R_oa = []
        
        for y in years:
            year_str = str(y)
            countries = list(data_oa[year_str].keys())
            
            country_R_oa_values = []
            for c in countries:
                r_oa_val = R_oa(y, c)
                if r_oa_val is not None:
                    country_R_oa_values.append(r_oa_val)
            
            if country_R_oa_values:
                max_R_oa = max(country_R_oa_values)
                year_max_R_oa.append(max_R_oa)
        
        max_of_max = max(year_max_R_oa) if year_max_R_oa else None
        _cache['constants'][cache_key_max] = max_of_max
    
    R_oa_current = R_oa(year, country)
    
    if R_oa_current is None or max_of_max is None or max_of_max == 0:
        result = None
    else:
        result = R_oa_current / max_of_max
    
    # HDI 调整
    result = _adjust_with_hdi(result, country, alpha=0.6)
    
    set_cache('R_oa_bar', result, year, country)
    return result

# 10
def f1(year, country):
    '''计算f1'''
    cached = get_from_cache('f1', year, country)
    if cached is not None:
        return cached
    
    year_int = int(year) if isinstance(year, str) else year
    year_str = str(year)
    
    data_fwci = _data_cache['FWCI']
    
    if year_str not in data_fwci or country not in data_fwci[year_str]:
        result = None
    else:
        fwci_value = _to_number_or_none(data_fwci[year_str][country])
        # 对 FWCI 做广义对数变换，避免极端值拉高或过小
        if fwci_value is not None:
            fwci_value = math.log10(10 * fwci_value + 1)
        
        if fwci_value is None:
            result = None
        elif year_int < 2014:
            result = fwci_value
        else:
            data_scientist = _data_cache['scientist']
            data_world_total = _data_cache['world_total']
            
            if year_str not in data_scientist or country not in data_scientist[year_str]:
                result = None
            elif year_str not in data_world_total:
                result = None
            else:
                scientist_value = data_scientist[year_str][country]
                word_scientist_value = data_world_total[year_str].get('word_scientist')
                
                if scientist_value is None or word_scientist_value is None or word_scientist_value == 0:
                    result = fwci_value
                else:
                    Au_current = scientist_value / word_scientist_value
                    
                    Au_ratios = []
                    for c in data_scientist[year_str].keys():
                        sci_val = data_scientist[year_str][c]
                        if sci_val is not None and word_scientist_value is not None and word_scientist_value > 0:
                            Au_ratio = sci_val / word_scientist_value
                            Au_ratios.append(Au_ratio)
                    
                    if not Au_ratios or sum(Au_ratios) / len(Au_ratios) == 0:
                        result = fwci_value
                    else:
                        Au_average = sum(Au_ratios) / len(Au_ratios)
                        result = 0.2 * fwci_value + 0.8 * (Au_current / Au_average)
    
    set_cache('f1', result, year, country)
    return result

# 11
def f2(year, country):
    '''计算f2'''
    cached = get_from_cache('f2', year, country)
    if cached is not None:
        return cached
    
    year_str = str(year)
    data_f2 = _data_cache['F2']
    result = data_f2[year_str][country]
    
    set_cache('f2', result, year, country)
    return result

# 12
def f3(year, country):
    '''计算f3'''
    cached = get_from_cache('f3', year, country)
    if cached is not None:
        return cached
    
    year_str = str(year)
    data_retraction = _data_cache['retraction']
    data_total = _data_cache['total']
    data_world_total = _data_cache['world_total']

    if year_str not in data_retraction or year_str not in data_total or year_str not in data_world_total:
        result = None
    else:
        country_retraction = _to_number_or_none(data_retraction[year_str].get(country))
        country_total = _to_number_or_none(data_total[year_str].get(country))
        world_retraction = _to_number_or_none(data_world_total[year_str].get('world_retraction'))
        world_total = _to_number_or_none(data_world_total[year_str].get('world_total'))

        if (country_retraction is None or country_total is None or
                world_retraction is None or world_total is None or
                country_total <= 0 or world_total <= 0 or world_retraction < 0 or country_retraction < 0):
            result = None
        else:
            # 若该国该年撤稿数为0，直接返回0
            if country_retraction == 0:
                result = 0
            else:
                country_rate = country_retraction / country_total  # 该国撤稿率
                world_rate = world_retraction / world_total        # 全球撤稿率

                if world_rate is None or world_rate <= 0:
                    result = None
                else:
                    ratio = country_rate / world_rate
                    result = min(1.2, 1 / ratio) if ratio > 0 else 1.2
    
    set_cache('f3', result, year, country)
    return result

# 13
def S_od_t(year, country):
    '''计算S_od_t'''
    cached = get_from_cache('S_od_t', year, country)
    if cached is not None:
        return cached
    
    year_str = str(year)
    
    f1_value = f1(year, country)
    f2_value = f2(year, country)
    f3_value = f3(year, country)
    
    # 任一分项缺失则无法计算（避免 None + 数值 的报错）
    if f1_value is None or f2_value is None or f3_value is None:
        result = None
    else:
        avg_f = (f1_value + f2_value + f3_value) / 3
        
        data_oa = _data_cache['OA']

        if year_str not in data_oa or country not in data_oa[year_str]:
            result = None
        else:
            country_oa = _to_number_or_none(data_oa[year_str][country])
            if country_oa is None:
                result = None
            else:
                # 计算该年全球OA的最大值（仅使用可转换为数值的项）
                year_oa_numbers = []
                for v in data_oa[year_str].values():
                    num = _to_number_or_none(v)
                    if num is not None and num >= 0:
                        year_oa_numbers.append(num)

                if not year_oa_numbers:
                    result = None
                else:
                    max_oa = max(year_oa_numbers)
                    denom = math.log10(max_oa + 1) if max_oa is not None else None

                    if denom is None or denom <= 0:
                        result = None
                    else:
                        ratio = math.log10(country_oa + 1) / denom
                        result = avg_f * ratio
    
    set_cache('S_od_t', result, year, country)
    return result

# 14
def S_od_t1():
    '''计算S_od_t1'''
    if 'S_od_t1' in _cache['constants']:
        return _cache['constants']['S_od_t1']
    
    data_total = _data_cache['total']
    years = sorted([int(y) for y in data_total.keys()])
    year_avg_values = []
    
    for year in years:
        year_str = str(year)
        
        if year_str not in data_total:
            continue
        
        countries = list(data_total[year_str].keys())
        country_S_od_values = []
        
        for country in countries:
            s_od_value = S_od_t(year, country)
            if s_od_value is not None:
                country_S_od_values.append(s_od_value)
        
        if country_S_od_values:
            avg_value = sum(country_S_od_values) / len(country_S_od_values)
            year_avg_values.append(avg_value)
    
    result = max(year_avg_values) if year_avg_values else None
    
    _cache['constants']['S_od_t1'] = result
    save_to_json('S_od_t1', {"value": result})
    return result

# 15
def A_od_t(year, country):
    '''计算A_od_t'''
    cached = get_from_cache('A_od_t', year, country)
    if cached is not None:
        return cached
    
    year_str = str(year)
    data_world_total = _data_cache['world_total']
    data_alpha_L = _data_cache['alpha_L']
    data_alpha_F = _data_cache['alpha_F']
    data_alpha_I = _data_cache['alpha_I']
    
    result = data_world_total[year_str]['world_oa_total'] * \
             data_alpha_L[year_str][country] * \
             data_alpha_F[year_str][country] * \
             data_alpha_I[year_str][country]
    
    set_cache('A_od_t', result, year, country)
    return result

# 16
def A_od_t1():
    '''计算A_od_t1'''
    if 'A_od_t1' in _cache['constants']:
        return _cache['constants']['A_od_t1']
    
    data_world_total = _data_cache['world_total']
    years = sorted([int(y) for y in data_world_total.keys()])
    
    if not years:
        result = None
    else:
        first_year = str(years[0])
        data_alpha_L = _data_cache['alpha_L']
        
        if first_year not in data_alpha_L:
            result = None
        else:
            countries = list(data_alpha_L[first_year].keys())
            year_avg_values = []
            
            for y in years:
                year_str = str(y)
                
                if year_str not in data_world_total:
                    continue
                
                if 'world_oa_total' not in data_world_total[year_str] or \
                   data_world_total[year_str]['world_oa_total'] is None:
                    continue
                
                country_A_od_values = []
                for c in countries:
                    a_od_value = A_od_t(y, c)
                    if a_od_value is not None:
                        country_A_od_values.append(a_od_value)
                
                if country_A_od_values:
                    avg_value = sum(country_A_od_values) / len(country_A_od_values)
                    year_avg_values.append(avg_value)
            
            result = max(year_avg_values) if year_avg_values else None
    
    _cache['constants']['A_od_t1'] = result
    save_to_json('A_od_t1', {"value": result})
    return result

# 17 计算R_od的函数
def R_od(year, country):
    '''计算R_od'''
    cached = get_from_cache('R_od', year, country)
    if cached is not None:
        return cached
    
    S_od_t_value = S_od_t(year, country)
    A_od_t_value = A_od_t(year, country)
    S_od_t1_value = S_od_t1()
    A_od_t1_value = A_od_t1()
    
    if S_od_t_value is None or A_od_t_value is None or \
       S_od_t1_value is None or A_od_t1_value is None:
        result = None
    else:
        valueac = S_od_t_value / S_od_t1_value
        valuebd = A_od_t_value / A_od_t1_value
        result = math.sqrt(valueac ** 2 + valuebd ** 2)
    
    set_cache('R_od', result, year, country)
    return result

# 计算R_od_bar的函数
def R_od_bar(year, country):
    '''计算R_od_bar'''
    cached = get_from_cache('R_od_bar', year, country)
    if cached is not None:
        return cached
    
    # 检查是否有缓存的历年最大值
    cache_key_max = 'R_od_bar_max_of_max'
    if cache_key_max in _cache['constants']:
        max_of_max = _cache['constants'][cache_key_max]
    else:
        # 计算历年最大值
        data_total = _data_cache['total']
        years = sorted([int(y) for y in data_total.keys()])
        year_max_R_od = []
        
        for y in years:
            year_str = str(y)
            countries = list(data_total[year_str].keys())
            
            country_R_od_values = []
            for c in countries:
                r_od_val = R_od(y, c)
                if r_od_val is not None:
                    country_R_od_values.append(r_od_val)
            
            if country_R_od_values:
                max_R_od = max(country_R_od_values)
                year_max_R_od.append(max_R_od)
        
        max_of_max = max(year_max_R_od) if year_max_R_od else None
        _cache['constants'][cache_key_max] = max_of_max
    
    R_od_current = R_od(year, country)
    
    if R_od_current is None or max_of_max is None or max_of_max == 0:
        result = None
    else:
        result = R_od_current / max_of_max
    
    # HDI 调整
    result = _adjust_with_hdi(result, country, alpha=0.6)
    
    set_cache('R_od_bar', result, year, country)
    return result

# 18 计算S_{Journal}(t)
def S_journal_t(year, country):
    r'''计算S_{Journal}(t)
   公式： $$S_{Journal}(t) = 1.25 \times \frac{\ln(N_{Jour}(c, t) + 1)}{\ln(N_{Jour}^{max}(t) + 1)}$$
    '''
    cached = get_from_cache('S_journal_t', year, country)
    if cached is not None:
        return cached

    year_str = str(year)
    data_journals = _data_cache.get('journals')

    if not data_journals or year_str not in data_journals:
        result = None
    else:
        country_val = _to_number_or_none(data_journals[year_str].get(country))
        # 收集当年所有可用的数值以求最大值
        year_vals = []
        for v in data_journals[year_str].values():
            num = _to_number_or_none(v)
            if num is not None and num >= 0:
                year_vals.append(num)

        if country_val is None or not year_vals:
            result = None
        else:
            max_val = max(year_vals)
            denom = math.log10(max_val + 1) if max_val is not None else None
            if denom is None or denom <= 0:
                result = None
            else:
                numer = math.log10(country_val + 1)
                result = 1.25 * (numer / denom)

    set_cache('S_journal_t', result, year, country)
    return result


# 19 计算S_{Policy}(t)
def S_policy_t(year, country):
    r'''计算S_{Policy}(t)
    公式：$$S_{Policy}(t) = \min\left(1.25, \ \left[ 1.25 \times \frac{\ln(N_{Pol}(c, t) + 1)}{\ln(N_{Pol}^{max}(t) + 1)} \right] \times \alpha_{UNESCO} \right)$$
    '''
    cached = get_from_cache('S_policy_t', year, country)
    if cached is not None:
        return cached

    year_str = str(year)
    data_policy = _data_cache.get('policy')
    data_unesco = _data_cache.get('UNESCO')

    if not data_policy or not data_unesco or year_str not in data_policy or year_str not in data_unesco:
        result = None
    else:
        policy_val = _to_number_or_none(data_policy[year_str].get(country))
        unesco_val = _to_number_or_none(data_unesco[year_str].get(country))

        # 收集该年所有policy数值以求最大值
        year_policy_vals = []
        for v in data_policy[year_str].values():
            num = _to_number_or_none(v)
            if num is not None and num >= 0:
                year_policy_vals.append(num)

        if policy_val is None or unesco_val is None or not year_policy_vals:
            result = None
        else:
            max_policy = max(year_policy_vals)
            denom = math.log10(max_policy + 1) if max_policy is not None else None
            if denom is None or denom <= 0:
                result = None
            else:
                numer = math.log10(policy_val + 1)
                core = 1.25 * (numer / denom)
                result = min(1.25, core * unesco_val)

    set_cache('S_policy_t', result, year, country)
    return result

# 20 计算R_law(t)
def S_law_t(year, country):
    '''
    计算S_law_t(t)
    公式：$$S_{Law}(t) = 1.25 \times \frac{IPRI_{Score}(c, t)}{10}$$
    '''
    cached = get_from_cache('S_law_t', year, country)
    if cached is not None:
        return cached
    
    year_str = str(year)
    data_ipri = _data_cache['IPRI']
    
    if (not data_ipri) or (year_str not in data_ipri):
        result = None
    else:
        ipri_val = _to_number_or_none(data_ipri[year_str].get(country))
        if ipri_val is None:
            result = None
        else:
            result = 1.25 * (ipri_val / 10.0)
    
    set_cache('S_law_t', result, year, country)
    return result

# 21 计算S_platform(t)
def S_platform_t(year, country):
    r'''计算S_platform(t)
    公式：$$S_{Platform}(t) = 1.25 \times \frac{\ln(N_{Repo}(c, t) + 1)}{\ln(N_{Repo}^{max}(t) + 1)}$$
    '''
    cached = get_from_cache('S_platform_t', year, country)
    if cached is not None:
        return cached

    year_str = str(year)
    data_platform = _data_cache.get('platform')

    if not data_platform or year_str not in data_platform:
        result = None
    else:
        country_val = _to_number_or_none(data_platform[year_str].get(country))

        # 收集当年所有可用的数值以求最大值
        year_vals = []
        for v in data_platform[year_str].values():
            num = _to_number_or_none(v)
            if num is not None and num >= 0:
                year_vals.append(num)

        if country_val is None or not year_vals:
            result = None
        else:
            max_val = max(year_vals)
            denom = math.log10(max_val + 1) if max_val is not None else None
            if denom is None or denom <= 0:
                result = None
            else:
                numer = math.log10(country_val + 1)
                result = 1.25 * (numer / denom)

    set_cache('S_platform_t', result, year, country)
    return result

# 22. 计算R_op_t
def R_op_t(year, country):
    '''计算R_op_t
    公式：$$R_{OP}(t) =(S_{Law}(t) + S_{Platform}(t) + S_{Journal}(t) + S_{Policy}(t))/5$$
    '''
    cached = get_from_cache('R_op_t', year, country)
    if cached is not None:
        return cached

    s_law = S_law_t(year, country)
    s_platform = S_platform_t(year, country)
    s_journal = S_journal_t(year, country)
    s_policy = S_policy_t(year, country)

    # 缺失项按 0 处理；分母固定为 5（按用户要求公式不变）
    s_law = 0.0 if s_law is None else s_law
    s_platform = 0.0 if s_platform is None else s_platform
    s_journal = 0.0 if s_journal is None else s_journal
    s_policy = 0.0 if s_policy is None else s_policy
    result = (s_law + s_platform + s_journal + s_policy) / 5.0

    set_cache('R_op_t', result, year, country)
    return result

# 计算R_op_bar的函数
def R_op_bar(year, country):
    '''
    输入year和地区，计算该年该地区的OP指标。
    公式：各国该年固定值/ max(该年所有国家中的最大值)
    '''
    # 检查缓存
    cached = get_from_cache('R_op_bar', year, country)
    if cached is not None:
        return cached
    
    year_str = str(year)
    # 基于动态计算的 R_op_t 做归一化，避免依赖 jsondata/OP.json
    data_total = _data_cache.get('total', {})
    if year_str not in data_total:
        result = None
    else:
        countries = list(data_total[year_str].keys())
        year_vals = []
        for c in countries:
            v = R_op_t(year, c)
            if v is not None:
                year_vals.append(v)

        denom = max(year_vals) if year_vals else None
        current = R_op_t(year, country)
        if current is None or denom is None or denom == 0:
            result = None
        else:
            result = current / denom
    
    # HDI 调整
    result = _adjust_with_hdi(result, country, alpha=0.6)
    
    set_cache('R_op_bar', result, year, country)
    return result


def _calculate_R_from_parts(data_weight, R_oa_bar_value, R_od_bar_value, R_op_bar_value, *, zero_fill=False):
    values = (R_oa_bar_value, R_od_bar_value, R_op_bar_value)
    if zero_fill:
        if all(value is None for value in values):
            return None
        R_oa_bar_value = 0 if R_oa_bar_value is None else R_oa_bar_value
        R_od_bar_value = 0 if R_od_bar_value is None else R_od_bar_value
        R_op_bar_value = 0 if R_op_bar_value is None else R_op_bar_value
    elif any(value is None for value in values):
        return None

    return data_weight['W_OA'] * R_oa_bar_value + \
           data_weight['W_OD'] * R_od_bar_value + \
           data_weight['W_OP'] * R_op_bar_value


def R(year, country):
    '''计算R'''
    cached = get_from_cache('R', year, country)
    if cached is not None:
        return cached
    
    year_str = str(year)
    data_weight = _data_cache['weight']
    R_oa_bar_value = R_oa_bar(year_str, country)
    R_od_bar_value = R_od_bar(year_str, country)
    R_op_bar_value = R_op_bar(year_str, country)

    result = _calculate_R_from_parts(data_weight, R_oa_bar_value, R_od_bar_value, R_op_bar_value)
    
    set_cache('R', result, year_str, country)
    return result


def R_zero_fill(year, country):
    '''计算缺失补零口径R'''
    cached = get_from_cache('R_zero_fill', year, country)
    if cached is not None:
        return cached

    year_str = str(year)
    data_weight = _data_cache['weight']
    R_oa_bar_value = R_oa_bar(year_str, country)
    R_od_bar_value = R_od_bar(year_str, country)
    R_op_bar_value = R_op_bar(year_str, country)

    result = _calculate_R_from_parts(
        data_weight,
        R_oa_bar_value,
        R_od_bar_value,
        R_op_bar_value,
        zero_fill=True,
    )

    set_cache('R_zero_fill', result, year_str, country)
    return result

# ==================== 批量计算和保存函数 ====================
def batch_calculate_and_save():
    """批量计算所有函数的所有(year, country)组合，并保存到JSON文件"""
    validate_calculation_inputs(_data_cache, "global")
    # 获取所有年份和国家
    data_total = _data_cache['total']
    years = sorted([int(y) for y in data_total.keys()])
    countries = list(data_total[str(years[0])].keys())
    
    print(f"开始批量计算: {len(years)}年 × {len(countries)}国家 = {len(years) * len(countries)}个组合")
    
    # 需要计算的函数列表（按依赖顺序）
    functions_to_calculate = [
        ('r_open_t', r_open_t),
        ('P_open_t', P_open_t),
        ('R_open', R_open),
        ('r_incl_t', r_incl_t),
        ('P_incl_t', P_incl_t),
        ('R_incl', R_incl),
        ('R_oa', R_oa),
        ('f1', f1),
        ('f2', f2),
        ('f3', f3),
        ('S_od_t', S_od_t),
        ('A_od_t', A_od_t),
        ('R_od', R_od),
        ('S_journal_t', S_journal_t),
        ('S_policy_t', S_policy_t),
        ('S_law_t', S_law_t),
        ('S_platform_t', S_platform_t),
        ('R_op_t', R_op_t),
        ('R_oa_bar', R_oa_bar),
        ('R_od_bar', R_od_bar),
        ('R_op_bar', R_op_bar),
        ('R', R),
        ('R_zero_fill', R_zero_fill),
    ]
    
    # 计算每个函数的所有组合
    for func_name, func in functions_to_calculate:
        print(f"计算 {func_name}...")
        results = {}
        
        for year in years:
            year_str = str(year)
            results[year_str] = {}
            
            for country in countries:
                try:
                    value = func(year, country)
                    results[year_str][country] = value
                except Exception as e:
                    print(f"  错误: {year}年 {country} - {e}")
                    results[year_str][country] = None
        
        # 保存到JSON
        save_to_json(func_name, results)
        print(f"  ✓ {func_name} 计算完成并已保存")

    stats_files = calculate_output_statistics(_output_dir)
    if stats_files:
        print(f"  ✓ 统计量计算完成并已保存: {', '.join(stats_files)}")
    
    print("\n所有计算完成！")

if __name__ == "__main__":
    batch_calculate_and_save()
