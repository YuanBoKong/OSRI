# OSRI 开放科学成熟度计算与可视化系统

本系统用于开放科学成熟度（Open Science Readiness Index，OSRI）的计算与可视化分析，围绕开放获取、开放数据、开放政策三个维度，提供国家与年份数据管理、指标计算、统计汇总、Excel 导入导出和交互式可视化功能。后端使用 FastAPI，前端使用 Vue 3，数据以 JSON 文件保存。

系统支持全球、聚合和全球Plus三种模式。全球Plus将全球国家数据与 EU27、STLCs 两个群组的数据合并计算。

系统保留要求三个维度完整的总分，同时提供缺失维度补零总分，以及按年份、按国家或群组汇总的统计结果。全球Plus输入由全球与聚合输入生成，不支持直接导入 Excel；需长期保留的修正应在源数据中完成。

## 本地启动

仓库已包含当前版本的输入数据和计算结果。安装依赖后即可启动后端：

```sh
pip install -r system/requirements.txt
cd system
python generate_global_plus.py
python api.py
```

在另一终端启动前端：

```sh
cd system/frontend
npm ci
npm run dev
```

访问 http://127.0.0.1:6002/OSRI/
参考：https://insightlens.cn/OSRI/
生产部署方式见 [部署说明](DEPLOYMENT.md)，
各模块功能见 [功能说明](FUNCTIONALITY.md)。

## 代码与数据

仓库包含全球、聚合和全球Plus三种模式的输入数据、HDI、计算结果及可视化数据。代码采用 MIT 许可证，数据和计算结果采用 CC BY 4.0 许可证。依赖目录、前端构建产物、缓存、日志及运行状态不纳入 Git 版本控制。
