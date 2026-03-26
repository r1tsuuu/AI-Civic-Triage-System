"""
ACTS Final Acceptance Criteria Check — TASK-074

AC-02: Classifier accuracy ≥ 80% on held-out set.
AC-03: At least 12/20 test posts containing Lipa City barangay names
       produce valid (non-null) coordinates via the gazetteer.

Usage (from acts/):
    python ml/final_check.py

Exit code 0 if both AC-02 and AC-03 pass, exit code 1 otherwise.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "seed_data.csv")
MODEL_PATH = os.path.join(BASE_DIR, "models", "classifier_v2.pkl")
GAZETTEER_PATH = os.path.join(BASE_DIR, "data", "gazetteer.csv")

AC02_ACCURACY_THRESHOLD = 0.80
AC03_MIN_PASS = 12
AC03_TOTAL = 20

# 20 test posts — 2 per barangay, with natural variation to exercise fuzzy matching
AC03_TEST_POSTS = [
    ("Tulong, lampas tao na baha sa Sabang!",                          "Sabang"),
    ("Rescue please dito sa Brgy. Sabang, naiipit kami",               "Sabang"),
    ("Sira ang kalsada sa Marawoy, hindi makadaan ang sasakyan",       "Marawoy"),
    ("Traffic grabe dito sa Marawoy, may stranded na truck",           "Marawoy"),
    ("Bagsak ang poste ng kuryente sa Inosluban",                      "Inosluban"),
    ("Walang ilaw sa buong Inosluban simula kagabi",                   "Inosluban"),
    ("May nakawan na nangyayari dito sa Plaridel",                     "Plaridel"),
    ("May aksidente sa motor sa Plaridel, duguan ang driver",          "Plaridel"),
    ("Hanggang dibdib na baha sa Mataas na Lupa",                      "Mataas na Lupa"),
    ("Hindi makalabas ng bahay ang mga tao sa Mataas na Lupa",         "Mataas na Lupa"),
    ("Traffic sa Banaybanay dahil sa baha",                            "Banaybanay"),
    ("Nabuwal ang puno sa kalsada sa Banaybanay",                      "Banaybanay"),
    ("Sira ang tulay sa Lumbang, walang makadaan",                     "Lumbang"),
    ("Sira ang drainage sa Lumbang, bumabaha palagi",                  "Lumbang"),
    ("May sunog sa Dagatan, tumawag ng bumbero",                       "Dagatan"),
    ("Gumuho ang bahagi ng kalsada sa Dagatan",                        "Dagatan"),
    ("Nabuwal ang puno sa kalsada sa Tambois",                         "Tambois"),
    ("May aksidente dito sa Tambois, kailangan ng ambulansya",         "Tambois"),
    ("Walang tubig sa Pinagtongulan simula kahapon",                   "Pinagtongulan"),
    ("SOS mula sa Pinagtongulan, pamilya nangangailangan ng tulong",   "Pinagtongulan"),
]


def _separator():
    print("=" * 55)


def check_ac02():
    """AC-02: Classifier accuracy ≥ 80% on 20% held-out split."""
    _separator()
    print("AC-02 — Classifier accuracy")
    _separator()

    try:
        import joblib
        import pandas as pd
        from sklearn.metrics import accuracy_score, classification_report
        from sklearn.model_selection import train_test_split
    except ImportError as e:
        print(f"  ERROR: missing dependency — {e}")
        print("  Run: pip install joblib scikit-learn pandas")
        return False

    if not os.path.exists(DATA_PATH):
        print(f"  ERROR: seed_data.csv not found at {DATA_PATH}")
        print("  Run: python ml/data/generate_csvs.py")
        return False

    if not os.path.exists(MODEL_PATH):
        print(f"  ERROR: classifier model not found at {MODEL_PATH}")
        print("  Run: python ml/train_classifier.py")
        return False

    df = pd.read_csv(DATA_PATH)
    X, y = df["text"], df["category"]
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)

    model = joblib.load(MODEL_PATH)
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)

    print(f"  Held-out accuracy : {acc:.4f}  ({acc * 100:.1f}%)")
    print(f"  Target            : {AC02_ACCURACY_THRESHOLD * 100:.0f}%")
    print()
    print(classification_report(y_test, preds))

    passed = acc >= AC02_ACCURACY_THRESHOLD
    status = "PASS ✓" if passed else "FAIL ✗"
    print(f"  AC-02 {status} — {acc * 100:.1f}% {'≥' if passed else '<'} {AC02_ACCURACY_THRESHOLD * 100:.0f}%")
    return passed


def check_ac03():
    """
    AC-03: ≥ 12/20 test posts with barangay names produce valid coordinates.

    Uses the same gazetteer + fuzzy-match logic as apps/triage/ner.py,
    run standalone (no Django required).
    """
    _separator()
    print("AC-03 — Gazetteer geocoding coverage")
    _separator()

    try:
        import pandas as pd
        from fuzzywuzzy import process
    except ImportError as e:
        print(f"  ERROR: missing dependency — {e}")
        print("  Run: pip install pandas fuzzywuzzy python-Levenshtein")
        return False

    if not os.path.exists(GAZETTEER_PATH):
        print(f"  ERROR: gazetteer.csv not found at {GAZETTEER_PATH}")
        print("  Run: python ml/data/generate_csvs.py")
        return False

    df = pd.read_csv(GAZETTEER_PATH)
    gazetteer = {
        row["location_name"]: (float(row["latitude"]), float(row["longitude"]))
        for _, row in df.iterrows()
    }
    gaz_keys = list(gazetteer.keys())
    print(f"  Gazetteer entries : {len(gaz_keys)}")
    print()

    resolved = 0
    for i, (post_text, barangay) in enumerate(AC03_TEST_POSTS, 1):
        match = process.extractOne(barangay, gaz_keys)
        if match and match[1] > 85:
            lat, lng = gazetteer[match[0]]
            resolved += 1
            status = f"✓  ({lat:.4f}, {lng:.4f})  matched '{match[0]}' [{match[1]}%]"
        else:
            status = f"✗  no gazetteer match for '{barangay}'"
        print(f"  [{i:02d}] {status}")

    print()
    print(f"  Resolved : {resolved}/{AC03_TOTAL}")
    print(f"  Target   : {AC03_MIN_PASS}/{AC03_TOTAL} (≥ 60%)")

    passed = resolved >= AC03_MIN_PASS
    status = "PASS ✓" if passed else "FAIL ✗"
    print(f"  AC-03 {status} — {resolved}/{AC03_TOTAL} resolved")
    return passed


def main():
    print()
    print("  ACTS — Final Acceptance Criteria Check")
    print()

    ac02 = check_ac02()
    print()
    ac03 = check_ac03()

    _separator()
    print("SUMMARY")
    _separator()
    print(f"  AC-02 (Classifier ≥ 80%)           : {'PASS ✓' if ac02 else 'FAIL ✗'}")
    print(f"  AC-03 (Geocoding 12/20 barangays)  : {'PASS ✓' if ac03 else 'FAIL ✗'}")
    _separator()

    if ac02 and ac03:
        print("  All acceptance criteria met. Ready for demo.")
        sys.exit(0)
    else:
        print("  One or more criteria failed. See details above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
