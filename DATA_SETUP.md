# 数据配置说明

仓库已包含与当前版本匹配的研究输入数据和计算结果。本地运行无需另行下载数据；Docker 部署时需将仓库中的数据复制到 `runtime_data/` 对应目录。

| 数据内容 | 本地存放位置 | Docker 宿主机存放位置 |
| --- | --- | --- |
| 全球指标 JSON 文件 | `system/jsondata/` | `runtime_data/jsondata/` |
| 聚合指标 JSON 文件 | `system/jsondata_aggregation/` | `runtime_data/jsondata_aggregation/` |
| 国家及群组 HDI | `system/HDI.json` | `runtime_data/HDI.json` |
| 全球计算结果 | `system/output/` | `runtime_data/output/` |
| 聚合计算结果 | `system/output_aggregation/` | `runtime_data/output_aggregation/` |
| 全球Plus输入与结果 | `system/jsondata_global_plus/`、`system/output_global_plus/` | `runtime_data/jsondata_global_plus/`、`runtime_data/output_global_plus/` |
| 参考工作簿，仅重算群组 HDI 时需要 | `data/reference/` | 应用启动不需要 |

全球和聚合输入目录各包含 18 个 JSON 文件。HDI 文件应包含 EU27 = 0.922389532983744、STLCs = 0.563210609625623。若需重新计算这两个值，将 `EU27_STLCs_population_2025.xlsx` 放入 `data/reference/`，运行 `python system/update_group_hdi.py`。

## 计算与同步

在本地生成全球Plus输入，并计算三种模式：

```sh
cd system
python generate_global_plus.py
python calculate.py
python calculate_aggregation.py
python -c 'from calculate_global_plus import batch_calculate_and_save; batch_calculate_and_save()'
python -c 'from vis_sync import sync_visualization_mode; [sync_visualization_mode(mode) for mode in ("global", "aggregation", "global_plus")]'
```

每种模式生成 39 个 JSON 结果文件，其中包括 10 个统计文件。全球Plus输入自动生成，无需独立维护。容器启动时生成全球Plus输入并同步已有结果，但不会自动重算得分。使用 Docker 部署前，可将仓库内相应目录复制到 `runtime_data/`，也可在界面中重新计算各模式。

## 数据与版本控制

输入数据、HDI、计算结果、参考工作簿和可视化数据均纳入 Git。Python 版本及浮点求和方式可能影响数值末位，跨环境核对结果时应设置合理的数值容差。

OSRI 总分对应开放科学成熟度，三个维度分别为开放获取、开放数据、开放政策。`R.json` 与 `R_zero_fill.json` 使用不同的缺失值处理口径，使用结果时应明确区分。
