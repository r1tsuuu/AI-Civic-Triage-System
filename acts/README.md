# ACTS — AI-powered Civic Triage System

> "Citizens should not have to change how they communicate for their government to hear them."

**Team CodeBlooded** — EXPE21ENCE YSES: The HackFest

---

## What is ACTS?

ACTS monitors a Philippine LGU's Facebook page, automatically classifies incoming civic
complaints using NLP, and presents them to moderators as a structured, prioritized dashboard.
When a moderator resolves an issue, the platform replies to the citizen on Facebook.

## Quick Start (Development)

```bash
# 1. Clone and enter the repo
git clone <repo-url> acts && cd acts

# 2. Create and activate a virtual environment
python3.11 -m venv .venv && source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy and fill in environment variables
cp .env.example .env
# Edit .env — set SECRET_KEY, DATABASE_URL, META_* tokens, DEMO_PASSWORD

# 5. Run migrations
python manage.py migrate

# 6. Start the dev server
python manage.py runserver
```

## Deployed Demo

> _To be filled in after TASK-061 (Day 4)_

- **URL:** `https://`
- **Test Facebook page:** _name here_
- **Smoke test date:** _date here_
- **Demo password:** _shared separately with judges_

## Architecture

See `CONSTITUTION.md` for the full system specification.

## Acceptance Test Results

See `docs/acceptance_test_results.md`.
