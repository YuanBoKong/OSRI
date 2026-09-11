#!/usr/bin/env python3
import os
import json
from typing import Any, Dict
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_DIR = os.path.join(BASE_DIR, "jsondata")


def is_year_key(key: str) -> bool:
    if not isinstance(key, str):
        return False
    if len(key) != 4 or not key.isdigit():
        return False
    return True


def filter_years(data: Dict[str, Any], min_year: int = 2014) -> Dict[str, Any]:
    filtered: Dict[str, Any] = {}
    for k, v in data.items():
        if is_year_key(k):
            if int(k) >= min_year:
                filtered[k] = v
        else:
            # 非年份键保持不变（兼容可能的元数据字段）
            filtered[k] = v
    return filtered


def backup_file(path: str) -> str:
    bak_path = f"{path}.bak"
    # 若已存在 .bak，不覆盖；生成带时间戳的备份
    if os.path.exists(bak_path):
        ts = datetime.now().strftime("%Y%m%d%H%M%S")
        bak_path = f"{path}.bak.{ts}"
    with open(path, "rb") as rf, open(bak_path, "wb") as wf:
        wf.write(rf.read())
    return bak_path


def process_file(filepath: str, min_year: int = 2014) -> str:
    filename = os.path.basename(filepath)
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read().strip()
            if not text:
                return f"[SKIP] {filename}: empty file"
            data = json.loads(text)
    except Exception as e:
        return f"[FAIL] {filename}: load error -> {e}"

    # 仅处理顶层为 dict 且包含年份键的结构；否则跳过
    if not isinstance(data, dict):
        return f"[SKIP] {filename}: top-level is not dict"

    has_year_key = any(is_year_key(k) for k in data.keys())
    if not has_year_key:
        return f"[SKIP] {filename}: no year-like keys"

    filtered = filter_years(data, min_year=min_year)

    # 若过滤后没有任何年份数据，但仍保留非年份字段
    try:
        backup_path = backup_file(filepath)
        with open(filepath, "w", encoding="utf-8") as wf:
            json.dump(filtered, wf, ensure_ascii=False, indent=2)
        return f"[OK] {filename}: backed up to {os.path.basename(backup_path)}, years >= {min_year} preserved"
    except Exception as e:
        return f"[FAIL] {filename}: write error -> {e}"


def main():
    if not os.path.isdir(JSON_DIR):
        print(f"[ERROR] jsondata directory not found: {JSON_DIR}")
        return

    entries = sorted([p for p in os.listdir(JSON_DIR) if p.endswith(".json")])
    if not entries:
        print("[INFO] No JSON files found.")
        return

    print(f"[INFO] Processing {len(entries)} files in {JSON_DIR}")
    for name in entries:
        path = os.path.join(JSON_DIR, name)
        result = process_file(path, min_year=2014)
        print(result)


if __name__ == "__main__":
    main()

