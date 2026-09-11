import json
from pathlib import Path

import pandas as pd


def _to_native_number(value):
    """将Excel单元格安全转换为 int/float，空值返回None，无法转换则原样返回字符串"""
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        # 保留整数形式
        return int(value) if float(value).is_integer() else float(value)
    # 尝试把字符串转换为数字
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return None
        try:
            num = float(s.replace(",", ""))
            return int(num) if num.is_integer() else num
        except Exception:
            return s
    return value


def convert_excel_to_json(src_path: Path, dst_path: Path):
    """将第一列为Year/年，后续列为国家/地区的数据表转为 {year: {country: value}} 结构"""
    df = pd.read_excel(src_path)

    # 识别年份列（大小写兼容）
    year_cols = [c for c in df.columns if str(c).strip().lower() == "year"]
    if not year_cols:
        raise ValueError(f"{src_path}: 未找到 year 列")
    year_col = year_cols[0]

    output = {}
    for _, row in df.iterrows():
        year_val = row[year_col]
        if pd.isna(year_val):
            continue
        try:
            year_str = str(int(float(year_val)))
        except Exception:
            # 无法解析年份则跳过
            continue

        row_dict = {}
        for col, val in row.items():
            if col == year_col:
                continue
            row_dict[str(col)] = _to_native_number(val)

        output[year_str] = row_dict

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    dst_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ 写入 {dst_path}")


def main():
    base = Path(__file__).resolve().parent
    tasks = [
        (base / "excel" / "IPRI.xlsx", base / "jsondata" / "IPRI.json")
    ]
    for src, dst in tasks:
        convert_excel_to_json(src, dst)


if __name__ == "__main__":
    main()

