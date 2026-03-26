# ml/data — Training Data

## Target LGU

Chosen demo LGU: `Lipa City, Batangas`

> **AI Engineer:** Document your chosen LGU here before starting TASK-021.
>
> Include:
> - City/municipality name
> - Facebook page URL (public LGU group)
> - Reason for selection (active, publicly accessible, sufficient post volume)
>
> This choice affects: NER model, gazetteer (TASK-072), and seed training data (TASK-021).

Current demo focus:
- City/municipality name: `Lipa City, Batangas`
- Reason for selection: existing demo fixtures, NER examples, and geocoding defaults in this repo already target Lipa City
- Facebook page URL: to be finalized by the team before live demo hookup

---

## Files in this directory

| File | Created by | Description |
|------|-----------|-------------|
| `seed_data.csv` | AI (TASK-021) | ≥50 manually written examples across 5 categories in Filipino/Taglish/English |
| `gazetteer.csv` | AI (TASK-072) | All barangay names in target LGU with lat/lng from PSA or OpenStreetMap |
| `README.md` | SWE-1 (TASK-000) | This file |

## CSV Schema

### seed_data.csv
```
text,category
"Baha na sa Brgy. San Jose, tulong po!",disaster_flooding
```

Categories (exhaustive for v1):
- `disaster_flooding`
- `transportation_traffic`
- `public_infrastructure`
- `public_safety`
- `other`

### gazetteer.csv
```
barangay_name,city,lat,lng,aliases
```

## Data Privacy Reminder (CONSTITUTION §15)

- Export **post text only** — no Facebook user IDs, names, or profile data
- Do not commit raw scraped data — only annotated CSVs
- Model binaries (`.pkl`, `.pt`) are excluded from git via `.gitignore`
