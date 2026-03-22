# ACTS — AI-powered Civic Triage System

> "Citizens should not have to change how they communicate for their government to hear them."

**Team CodeBlooded** — EXPE21ENCE YSES: The HackFest

---

## Current State (Day 1 Complete)

Phase 1 — Webhook Intake is fully built and tested. The server can receive, validate, and store real Facebook posts. The dashboard password gate is live. NLP pipeline, dashboard UI, and auto-response are not yet built.

---

## Requirements

- Python 3.11
- Git

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/r1tsuuu/AI-Civic-Triage-System.git
cd AI-Civic-Triage-System/acts
```

**2. Create and activate a virtual environment**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Create your `.env` file**
```bash
cp .env.example .env
```

Open `.env` and fill in:
```env
SECRET_KEY=any-long-random-string
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=
NLP_MODEL_PATH=ml/models/classifier.pkl
NER_MODEL_PATH=ml/models/ner_model
NLP_CONFIDENCE_THRESHOLD=0.65
DEMO_PASSWORD=your-chosen-password
META_APP_ID=
META_APP_SECRET=
META_VERIFY_TOKEN=
META_PAGE_ACCESS_TOKEN=
```

> Leave `DATABASE_URL` blank to use SQLite locally.
> Leave all `META_*` fields blank until Day 4 deployment.

To generate a secure `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

**5. Run migrations**
```bash
python manage.py migrate
```

**6. Start the server**
```bash
python manage.py runserver
```

---

## What You Can Do Right Now

### Dashboard gate
Go to `http://127.0.0.1:8000/gate/`

You'll see a password card. Enter the value you set as `DEMO_PASSWORD` in your `.env`. It will redirect you to `/dashboard/` — which returns 404 for now since the dashboard views haven't been built yet (Day 2–3).

To log out and return to the gate:
```
http://127.0.0.1:8000/dashboard/logout/
```

### Django admin
Create a superuser first:
```bash
python manage.py createsuperuser
```

Then go to `http://127.0.0.1:8000/admin/` and log in. You can inspect `RawPost` records here — useful for verifying webhook delivery once Meta is connected on Day 4.

### Webhook endpoint
The webhook lives at:
```
GET  http://127.0.0.1:8000/webhook/facebook/         ← Meta hub.challenge verification
POST http://127.0.0.1:8000/webhook/facebook/receive/  ← incoming Facebook posts
```

You can test the POST endpoint locally with curl:
```bash
# First generate a valid HMAC signature (replace YOUR_META_APP_SECRET)
python -c "
import hmac, hashlib, json
body = json.dumps({
    'entry': [{
        'id': 'page_123',
        'changes': [{
            'value': {
                'post_id': 'test_post_001',
                'message': 'Baha na sa amin, tulong!'
            }
        }]
    }]
}).encode()
secret = b'YOUR_META_APP_SECRET'
sig = hmac.new(secret, body, hashlib.sha256).hexdigest()
print(f'sha256={sig}')
print(body.decode())
"

# Then send the request (replace SIGNATURE and BODY with output above)
curl -X POST http://127.0.0.1:8000/webhook/facebook/receive/ \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: SIGNATURE" \
  -d 'BODY'
```

After a successful POST, the `RawPost` will appear in the Django admin.

---

## Running Tests

```bash
python manage.py test apps.webhook
```

Expected output:
```
Found 17 test(s).
...
Ran 17 tests in 0.025s
OK
```

---

## Project Structure

```
acts/
├── apps/
│   ├── webhook/       ← BUILT — Facebook webhook intake
│   ├── triage/        ← STUB — NLP pipeline (AI engineer, Day 2)
│   ├── dashboard/     ← PARTIAL — password gate only (UI + SWE-2, Day 2-3)
│   ├── response/      ← STUB — auto-reply system (SWE-1, Day 3)
│   └── accounts/      ← STUB — not used in hackathon build
├── config/
│   └── settings/
│       ├── base.py
│       ├── development.py
│       └── production.py
├── ml/                ← STUB — training scripts (AI engineer, Day 2-4)
├── static/            ← STUB — CSS/JS/vendor (UI, Day 2)
├── templates/
│   └── gate.html      ← BUILT — demo password gate page
└── manage.py
```

---

## What's Coming

| Day | Who | What |
|-----|-----|-------|
| Day 2 | AI | NLP pipeline — classifier, NER, urgency scorer |
| Day 2 | SWE-2 + UI | Dashboard skeleton and stats view |
| Day 3 | SWE-2 + UI | Full dashboard, report detail, status pipeline |
| Day 3 | SWE-1 | AutoReply model + Graph API sender |
| Day 4 | SWE-1 | Deployment to Railway/Render |
| Day 4 | AI | Retrain classifier on real LGU posts |
| Day 4 | Everyone | Map view, charts, final acceptance checks |

---

## Environment Variables Reference

| Variable | Required now | Description |
|----------|-------------|-------------|
| `SECRET_KEY` | ✅ | Django secret key |
| `DEBUG` | ✅ | `True` for dev, `False` for prod |
| `ALLOWED_HOSTS` | ✅ | Comma-separated hostnames |
| `DATABASE_URL` | ⬜ | Postgres URL — leave blank for SQLite |
| `DEMO_PASSWORD` | ✅ | Password for the dashboard gate |
| `META_APP_ID` | Day 4 | From Meta Developer dashboard |
| `META_APP_SECRET` | Day 4 | From Meta Developer dashboard |
| `META_VERIFY_TOKEN` | Day 4 | You choose this string |
| `META_PAGE_ACCESS_TOKEN` | Day 4 | From LGU Facebook page |
| `NLP_MODEL_PATH` | Day 2 | Path to trained classifier `.pkl` |
| `NER_MODEL_PATH` | Day 2 | Path to trained spaCy NER model |
| `NLP_CONFIDENCE_THRESHOLD` | Day 2 | Float, e.g. `0.65` |
