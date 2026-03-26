#!/usr/bin/env bash
# =============================================================================
# ACTS Production Build Script
# Runs during Railway / Render build phase (before the web process starts).
# Working directory is assumed to be acts/ (the Django project root).
# =============================================================================
set -euo pipefail

echo "=== [1/4] Downloading spaCy base model ==="
python -m spacy download xx_ent_wiki_sm

echo "=== [2/4] Generating ML training data ==="
python ml/data/generate_csvs.py

echo "=== [3/4] Training ML models ==="
python ml/train_classifier.py
python ml/train_ner.py

echo "=== [4/4] Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Build complete ==="
