# Deployment Guide

## Local development

### Prerequisites

- Python 3.11 or later
- Node.js 20 or later
- npm

### Backend

Install the Python dependencies from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r system/requirements.txt
```

Install the OSRI data package as described in `DATA_SETUP.md`, then start the backend:

```bash
cd system
python api.py
```

The backend is available at `http://127.0.0.1:6001`.

### Frontend

In a second terminal, install the frontend dependencies and start the Vite development server:

```bash
cd system/frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:6002/OSRI/` in a browser.

## Production deployment with Docker

Create local runtime directories and install the Figshare data package before starting the container:

```bash
mkdir -p runtime_data/jsondata runtime_data/output runtime_data/jsondata_aggregation runtime_data/output_aggregation runtime_data/runtime
cp -R /path/to/figshare/reproduction_inputs/jsondata/. runtime_data/jsondata/
cp /path/to/figshare/reproduction_inputs/HDI.json runtime_data/HDI.json
docker compose up --build -d
```

The service listens on `127.0.0.1:6001`. Open `http://127.0.0.1:6001/OSRI/` to use the management interface. The container mounts the runtime data directories so that input data and calculation outputs persist across image updates.

## Nginx reverse proxy

Use `deploy/nginx-osri-location.conf` as a location-level configuration when the service is deployed below `/OSRI/`. The configuration proxies the management interface, calculation API, visualization page, and visualization API to the Docker service.

## Rebuilding the frontend

For a non-container deployment, build the Vue application with:

```bash
cd system/frontend
npm ci
npm run build
```

The compiled files are written to `system/frontend/dist/`. This build directory is excluded from the repository because it is generated from the frontend source code.
