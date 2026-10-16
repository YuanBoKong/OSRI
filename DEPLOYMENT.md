# 部署说明

## 本地开发

推荐使用 Python 3.11 或 3.12，以及 Node.js 20 或更高版本。先按照 DATA_SETUP.md 安装数据，再启动后端：

```sh
python3 -m venv .venv
source .venv/bin/activate
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

访问 http://127.0.0.1:6002/OSRI/，后端接口使用 6001 端口。若需由后端统一提供页面，在 `system/frontend` 中执行 `npm run build`，重启后端后访问 http://127.0.0.1:6001/OSRI/。

## Docker 部署

启动前安装全球输入、聚合输入及 HDI 文件：

```sh
mkdir -p runtime_data/jsondata runtime_data/jsondata_aggregation runtime_data/output runtime_data/output_aggregation runtime_data/jsondata_global_plus runtime_data/output_global_plus runtime_data/runtime
# 将全球与聚合 JSON 输入复制到对应目录。
# 将包含国家及群组数据的 HDI.json 复制到 runtime_data/HDI.json。
docker compose up --build -d
```

访问 http://127.0.0.1:6001/OSRI/。镜像构建时编译前端，宿主机挂载目录保存三种模式的数据、结果和运行状态。HDI 文件以只读方式挂载，启动前必须确认该路径为已存在的文件。更换输入数据后，通过界面重新计算对应模式。

## Nginx 代理

使用 `deploy/nginx-osri-location.conf` 将系统部署在 `/OSRI/` 路径下。配置将请求转发到 6001 端口，并移除外部路径前缀。后端也支持直接访问带 `/OSRI/` 前缀的页面、静态资源和可视化接口。

构建产物、依赖、研究数据及运行状态不纳入代码发布。应用镜像中无需包含用于重新计算群组 HDI 的参考工作簿。
