#!/usr/bin/env bash
# Run on a machine with Node.js to refresh committed production assets.
set -euo pipefail
cd "$(dirname "$0")/../frontend"
npm ci
npm run build
echo "Built frontend/dist — commit those files for Cloudera deployment (no npm on Workbench)."
