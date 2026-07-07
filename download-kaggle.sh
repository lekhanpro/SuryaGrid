#!/bin/bash
# ============================================================================
# Download Kaggle Solar Radiation dataset using curl
# Usage: bash download-kaggle.sh
# Requires: KAGGLE_USERNAME and KAGGLE_KEY in .env or exported
# ============================================================================

set -e

# Load from .env if present
if [ -f .env ]; then
    export $(grep -E '^KAGGLE_(USERNAME|KEY)=' .env | xargs)
fi

if [ -z "$KAGGLE_USERNAME" ] || [ -z "$KAGGLE_KEY" ]; then
    echo "ERROR: Set KAGGLE_USERNAME and KAGGLE_KEY in .env"
    exit 1
fi

DATASET="dronio/SolarEnergy"
OUTPUT_DIR="backend/data/raw/kaggle"
ZIP_FILE="/tmp/kaggle-solar.zip"

mkdir -p "$OUTPUT_DIR"

echo "[1/3] Downloading dataset from Kaggle..."
curl -L -o "$ZIP_FILE" \
    -u "$KAGGLE_USERNAME:$KAGGLE_KEY" \
    "https://www.kaggle.com/api/v1/datasets/download/$DATASET"

echo "[2/3] Extracting..."
unzip -o "$ZIP_FILE" -d "$OUTPUT_DIR"
rm -f "$ZIP_FILE"

echo "[3/3] Done!"
ls -lh "$OUTPUT_DIR"
echo ""
echo "✓ Kaggle dataset ready at $OUTPUT_DIR"
echo ""
echo "Next steps (after containers are running):"
echo "  curl -X POST http://localhost:8080/api/v1/ml/datasets/build-augmented?source=kaggle"
echo "  curl -X POST http://localhost:8080/api/v1/ml/train?model_name=auto"
