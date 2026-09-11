# OSRI Calculation and Visualization System

This repository contains the full source code for the Open Science Readiness Index (OSRI) calculation system and its web interface. It supports country-year data management, OSRI calculation, result export, and interactive visualization.

## Repository contents

- `system/`: Python backend, calculation modules, data-management utilities, and the Vue management interface.
- `vis/`: visualization API, static visualization application, and chart source files.
- `docker/`, `Dockerfile.backend`, and `docker-compose.yml`: containerized deployment files.
- `deploy/`: Nginx reverse-proxy configuration.
- `DATA_SETUP.md`: instructions for installing the Figshare data package.
- `DEPLOYMENT.md`: local development and production deployment instructions.
- `FUNCTIONALITY.md`: description of the implemented functions.

## Quick start

1. Download the OSRI data package from Figshare and follow `DATA_SETUP.md`.
2. Install the Python and frontend dependencies.
3. Start the backend from `system/` with `python api.py`.
4. Start the frontend from `system/frontend/` with `npm run dev`.
5. Open `http://127.0.0.1:6002/OSRI/`.

Detailed instructions are provided in `DEPLOYMENT.md`.

## Licence

The code is released under the MIT License. The associated dataset is distributed separately through Figshare and has its own licence and citation.
