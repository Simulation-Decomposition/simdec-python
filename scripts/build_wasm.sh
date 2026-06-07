#!/usr/bin/env bash
set -euo pipefail
# Logging
set -x

# Setup paths and environment
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/dist/pyodide"

# Wipe old build before starting
if [ -d "${OUT_DIR}" ]; then
    echo "Cleaning old build..."
    rm -rf "${OUT_DIR}"
fi

cd "${ROOT_DIR}"

# Determine which Python interpreter to use
HOST_PYTHON="${PYTHON_BIN:-}"
if [[ -z "${HOST_PYTHON}" ]]; then
    if command -v python3 >/dev/null 2>&1; then
        HOST_PYTHON="python3"
    elif command -v python >/dev/null 2>&1; then
        HOST_PYTHON="python"
    else
        echo "Error: No python interpreter found. Install python3 and retry."
        exit 1
    fi
fi

# Create build virtual environment
VENV_DIR="${ROOT_DIR}/.wasm-build-venv"
if [[ ! -d "${VENV_DIR}" ]]; then
    echo "Creating build virtual environment at ${VENV_DIR}..."
    "${HOST_PYTHON}" -m venv "${VENV_DIR}"
fi

PYTHON_BIN="${VENV_DIR}/bin/python"

# Install build dependencies and build the wheel
echo "Installing build tools and generating local wheel..."
"${PYTHON_BIN}" -m pip install --upgrade pip build panel matplotlib seaborn scipy SALib

# Clean old builds to avoid picking up the wrong wheel
rm -rf dist/*.whl
"${PYTHON_BIN}" -m build --wheel .

# Identify the generated wheel file
SIMDEC_WHEEL_PATH=$(ls dist/*.whl | head -n 1 || echo "")

if [[ -z "${SIMDEC_WHEEL_PATH}" ]]; then
    echo "Error: No wheel file found in dist/. Build failed."
    exit 1
fi

WHEEL_FILENAME=$(basename "${SIMDEC_WHEEL_PATH}")

# Prepare output directory - USE ABSOLUTE PATH
OUT_DIR="${ROOT_DIR}/dist/pyodide"
mkdir -p "${OUT_DIR}/_static"
mkdir -p "${OUT_DIR}/data"

# Copy the wheel into the output directory so it's accessible via HTTP
cp "${SIMDEC_WHEEL_PATH}" "${OUT_DIR}/"

# Copy the assets to where the Python scripts expect them
mkdir -p panel/_static
if [ -d "docs/_static" ]; then
  # Use || true to prevent failure if it's empty
  cp -r docs/_static/* panel/_static/ || true
fi

echo "Converting Panel apps to Pyodide worker output..."
export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"

# Change directory into 'panel' so relative paths resolve correctly
cd "${ROOT_DIR}/panel"

# Bring the wheel into the current folder so we can pass just the filename
cp "${ROOT_DIR}/${SIMDEC_WHEEL_PATH}" .

# Safe file checking that won't trigger set -e
echo "Checking necessary files locally before conversion..."
if [[ ! -f "simdec_app.py" ]]; then echo "Warning: simdec_app.py not found in panel directory!"; fi
if [[ ! -f "sampling.py" ]]; then echo "Warning: sampling.py not found in panel directory!"; fi

# Ensure data/stress.csv exists relative to the current 'panel' dir
if [[ ! -f "data/stress.csv" ]]; then
    echo "Warning: panel/data/stress.csv missing."
    if [[ -f "../data/stress.csv" ]]; then
        echo "Found stress.csv in root. Copying to panel/data..."
        mkdir -p data
        cp "../data/stress.csv" data/
    else
        echo "Error: stress.csv not found anywhere! Conversion may fail."
    fi
fi

# Copy stress.csv to output directory
cp "data/stress.csv" "${OUT_DIR}/data/"

# Run conversion
"${PYTHON_BIN}" -m panel convert \
    simdec_app.py \
    sampling.py \
    --to pyodide-worker \
    --out "${OUT_DIR}" \
    --requirements "${WHEEL_FILENAME}[dashboard]" panel "bokeh==3.9.0" numpy pandas matplotlib seaborn scipy SALib \
    --resources data/stress.csv

cp "./${WHEEL_FILENAME}" "${OUT_DIR}/"

# Clean up the copied wheel
rm "${WHEEL_FILENAME}"

# Step back out to the root directory for the rest of the script
cd "${ROOT_DIR}"

# Copy custom index page and static assets
echo "Copying custom index page and static assets..."

# Copy images/thumbnails from docs/_static if they exist
if [ -d "docs/_static" ]; then
    cp -r docs/_static/* "${OUT_DIR}/_static/" || true
fi

# Overwrite default index.html with your custom homepage
if [ -f "panel/index.html" ]; then
    cp panel/index.html "${OUT_DIR}/index.html"
else
    echo "Warning: panel/index.html not found. Using default Panel index."
fi

echo "---"
echo "WASM site successfully generated at ${OUT_DIR}"
