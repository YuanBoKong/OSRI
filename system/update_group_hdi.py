import json
from pathlib import Path

import pandas as pd

from file_storage import atomic_write_json


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
HDI_FILE = BASE_DIR / "HDI.json"
POPULATION_FILE = PROJECT_ROOT / "data" / "reference" / "EU27_STLCs_population_2025.xlsx"
GROUPS = ("EU27", "STLCs")


def calculate_group_hdi(population_file: Path = POPULATION_FILE, hdi_file: Path = HDI_FILE):
    with open(hdi_file, "r", encoding="utf-8") as f:
        hdi_data = json.load(f)

    population_data = pd.read_excel(population_file)
    required_columns = {"country", "tag", "population"}
    missing_columns = required_columns - set(population_data.columns)
    if missing_columns:
        raise ValueError(f"人口表缺少列: {', '.join(sorted(missing_columns))}")

    group_hdi = {}
    for group in GROUPS:
        group_rows = population_data[population_data["tag"] == group]
        if group_rows.empty:
            raise ValueError(f"人口表缺少分组: {group}")

        missing_countries = [
            country
            for country in group_rows["country"]
            if country not in hdi_data
        ]
        if missing_countries:
            raise ValueError(f"{group} 中存在没有HDI的国家: {', '.join(missing_countries)}")

        weighted_sum = sum(
            float(hdi_data[row.country]) * float(row.population)
            for row in group_rows.itertuples()
        )
        population_sum = float(group_rows["population"].sum())
        group_hdi[group] = weighted_sum / population_sum

    return group_hdi


def update_hdi_json(population_file: Path = POPULATION_FILE, hdi_file: Path = HDI_FILE):
    with open(hdi_file, "r", encoding="utf-8") as f:
        hdi_data = json.load(f)

    hdi_data.update(calculate_group_hdi(population_file, hdi_file))
    atomic_write_json(hdi_file, hdi_data, indent=4)
    return {group: hdi_data[group] for group in GROUPS}


if __name__ == "__main__":
    updated = update_hdi_json()
    for group, value in updated.items():
        print(f"{group}: {value}")
