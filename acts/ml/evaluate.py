"""
Classifier evaluation script.
AC-02: accuracy must be ≥ 80% on a held-out set.

Usage (from acts/):
    python ml/evaluate.py

Exit code 0 if accuracy ≥ 80%, exit code 1 otherwise.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(BASE_DIR, "data", "seed_data.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "classifier_v2.pkl")
THRESHOLD = 0.80


def main():
    # ── Imports ──────────────────────────────────────────────────────────────
    try:
        import joblib
        import pandas as pd
        from sklearn.metrics import accuracy_score, classification_report
        from sklearn.model_selection import train_test_split
    except ImportError as e:
        print(f"ERROR: missing dependency — {e}")
        print("Run: pip install joblib scikit-learn pandas")
        sys.exit(1)

    # ── Load data ─────────────────────────────────────────────────────────────
    if not os.path.exists(DATA_PATH):
        print(f"ERROR: seed_data.csv not found at {DATA_PATH}")
        print("Run: python ml/data/generate_csvs.py")
        sys.exit(1)

    df = pd.read_csv(DATA_PATH)
    if "text" not in df.columns or "category" not in df.columns:
        print("ERROR: seed_data.csv must have 'text' and 'category' columns")
        sys.exit(1)

    X, y = df["text"], df["category"]

    # ── Load model ────────────────────────────────────────────────────────────
    if not os.path.exists(MODEL_PATH):
        print(f"ERROR: classifier model not found at {MODEL_PATH}")
        print("Run: python ml/train_classifier.py")
        sys.exit(1)

    model = joblib.load(MODEL_PATH)

    # ── Evaluate on a consistent 20% held-out split ───────────────────────────
    _, X_test, _, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)

    print("=" * 50)
    print(f"Held-out accuracy : {acc:.4f}  ({acc * 100:.1f}%)")
    print(f"Target            : {THRESHOLD * 100:.0f}%")
    print("=" * 50)
    print()
    print(classification_report(y_test, preds))

    if acc >= THRESHOLD:
        print(f"✓ AC-02 PASS — accuracy {acc * 100:.1f}% ≥ {THRESHOLD * 100:.0f}%")
        sys.exit(0)
    else:
        print(f"✗ AC-02 FAIL — accuracy {acc * 100:.1f}% < {THRESHOLD * 100:.0f}%")
        sys.exit(1)


if __name__ == "__main__":
    main()
