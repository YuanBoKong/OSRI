#!/usr/bin/env sh
set -eu

npm ci
npm run build

echo "Frontend build completed: system/frontend/dist/"
echo "Serve the compiled files through the Docker image or the Nginx configuration in this repository."
