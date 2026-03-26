# ACTS — AI Civic Triage System

> *"Citizens should not have to change how they communicate for their government to hear them."*

**Team CodeBlooded** — EXPE21ENCE YSES: The HackFest

ACTS is a web platform that monitors a Philippine LGU's Facebook page, automatically classifies incoming civic complaints using NLP, and presents them to government moderators as a structured, prioritized triage queue. When a moderator resolves an issue, the platform closes the communication loop — without asking citizens to do anything differently.

**Target LGU (merely for the sake of the Hackathon, not tailored to the city only):** Lipa City, Batangas &nbsp;·&nbsp; **Alignment:** SDG 11 — Sustainable Cities and Communities

---

## The Problem

Filipino citizens report civic emergencies — floods, potholes, power outages, rescue requests — on their barangay's Facebook page. During typhoons, hundreds of distress posts per hour flood LGU pages with zero systematic response. Local governments use Facebook as a broadcast tool, not a listening tool. This erodes civic trust and costs lives.

ACTS fixes the infrastructure gap.

---

## What It Does

| Layer | Capability |
|---|---|
| **Intake** | Receives Facebook posts via Meta Webhook (HMAC-SHA256 validated) |
| **Classification** | TF-IDF + SVM classifier — 5 civic categories, 95%+ accuracy |
| **Location Extraction** | spaCy NER + fuzzy gazetteer — extracts barangay names and landmarks |
| **Urgency Scoring** | Rule-based signal scoring (distress keywords, flood depth, vulnerable persons) |
| **Confidence Gating** | Reports below 65% classifier confidence are flagged `For Review` for human verification |
| **LGU Dashboard** | Full triage interface: list view, map, report detail, status pipeline, history |
| **Manual Correction** | Click-to-pin Leaflet map lets moderators correct AI location errors; corrections marked as ground-truth |
| **Impact Analytics** | Executive summary — avg. response time, top emergency zone, resolution rate |
| **Transparency Portal** | Public-facing map at `/` showing anonymised civic activity for citizens |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2 + Django REST Framework |
| NLP | TF-IDF + SVM (scikit-learn), spaCy NER |
| Maps | Leaflet.js + OpenStreetMap |
| Frontend | Django templates + Bootstrap 5 (no JS framework) |
| Database | SQLite (dev) / PostgreSQL (production) |
| Deployment | Railway (Gunicorn + WhiteNoise) |

---

## Setup

### Prerequisites

- Python 3.11
- Git

### 1. Clone and enter the project

```bash
git clone https://github.com/r1tsuuu/AI-Civic-Triage-System.git
cd AI-Civic-Triage-System/acts
```

### 2. Create and activate a virtual environment

```bash
python3.11 -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
SECRET_KEY=        # any long random string
DEMO_PASSWORD=     # password to enter the LGU dashboard
```

To generate a secure `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Leave `DATABASE_URL` blank to use SQLite locally.

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Train the ML models

The model files are not committed to the repository and must be generated once locally.

```bash
# Generate seed training data and gazetteer
python ml/data/generate_csvs.py

# Train the classifier (TF-IDF + SVM)
python ml/train_classifier.py

# Train the NER model
python ml/train_ner.py

# Verify accuracy (target: ≥ 80%)
python ml/evaluate.py
```

### 7. Start the server

```bash
python manage.py runserver
```

---

## Routes

| URL | Description |
|-----|-------------|
| `/` | Citizen Transparency Portal — anonymised public map of civic activity |
| `/gate/` | LGU dashboard login (enter `DEMO_PASSWORD`) |
| `/dashboard/` | LGU triage dashboard |
| `/dashboard/reports/` | Full report list with filters |
| `/dashboard/reports/map/` | Leaflet map of all geolocated reports |
| `/dashboard/history/` | Status change audit trail |
| `/admin/` | Django admin (requires superuser) |
| `/webhook/` | Meta webhook endpoint (GET: verification, POST: event intake) |

---

## NLP Pipeline

```
RawPost.post_text
    │
    ├── classify(text)          → category + confidence (0–1)
    │       │
    │       └── if confidence < 0.65 → status = for_review, category = uncertain
    │
    ├── extract_locations(text) → list of place names (NER + fuzzy gazetteer)
    │
    ├── geocode(location)       → latitude, longitude, confidence
    │
    └── compute_score(text)     → urgency_score (0–100)
                                   (distress, flood depth, vulnerable persons,
                                    stranded signals)
```

**Categories:** `disaster_flooding` · `transportation_traffic` · `public_infrastructure` · `public_safety` · `other`

**Status machine:** `for_review` / `reported` → `acknowledged` → `in_progress` → `resolved` | `dismissed`

---

## Human-in-the-Loop

Every AI classification decision is visible to the moderator with its confidence percentage. Low-confidence reports surface a warning banner. The Edit Report modal allows moderators to:

- Correct the category (dropdown)
- Adjust the urgency score (slider)
- Fix the location name (text input)
- Pin the exact location on a map (click-to-pin Leaflet map)

Corrected reports are flagged `is_manually_corrected = True` — usable as ground-truth for future model retraining.

---

## Running Tests

```bash
# All tests
python manage.py test

# Webhook app only
python manage.py test apps.webhook

# Dashboard app only
python manage.py test apps.dashboard
```

---

## Project Structure

```
acts/
├── apps/
│   ├── webhook/        Webhook intake — HMAC validation, RawPost model
│   ├── triage/         NLP pipeline — classifier, NER, scorer, Report model
│   ├── dashboard/      LGU dashboard — all views, forms, middleware
│   ├── response/       Auto-reply stub (Graph API sender)
│   └── accounts/       Not used in hackathon build
├── config/
│   └── settings/
│       ├── base.py
│       ├── development.py
│       └── production.py
├── ml/
│   ├── data/           Seed CSV generation + gazetteer
│   ├── models/         Trained model files (gitignored — generate locally)
│   ├── train_classifier.py
│   ├── train_ner.py
│   └── evaluate.py
├── static/             CSS, JS
├── templates/
│   ├── gate.html
│   └── portal/         Citizen transparency portal
└── manage.py
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SECRET_KEY` | ✅ | Django secret key |
| `DEBUG` | ✅ | `True` for dev, `False` for production |
| `ALLOWED_HOSTS` | ✅ | Comma-separated hostnames |
| `DEMO_PASSWORD` | ✅ | Password for the LGU dashboard gate |
| `DATABASE_URL` | ⬜ | Postgres connection URL — leave blank for SQLite |
| `NLP_MODEL_PATH` | ⬜ | Path to `classifier_v2.pkl` (default: `ml/models/classifier_v2.pkl`) |
| `NER_MODEL_PATH` | ⬜ | Path to trained spaCy NER model directory |
| `NLP_CONFIDENCE_THRESHOLD` | ⬜ | Float — reports below this confidence go to review (default: `0.65`) |
| `META_APP_ID` | ⬜ | Meta Developer dashboard |
| `META_APP_SECRET` | ⬜ | Meta Developer dashboard |
| `META_VERIFY_TOKEN` | ⬜ | Arbitrary string set during webhook registration |
| `META_PAGE_ACCESS_TOKEN` | ⬜ | From LGU Facebook page settings |

---

## Deployment (Railway)

```bash
# Push to main — Railway auto-deploys via Procfile
git push origin main
```

The `Procfile` runs:
```
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
```

Set all environment variables in Railway's dashboard. `DJANGO_SETTINGS_MODULE` should be `config.settings.production`.

---

*Built for EXPE21ENCE YSES: The HackFest by Team CodeBlooded.*
