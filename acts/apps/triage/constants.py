"""
Domain constants — single source of truth for categories, statuses, and scales.
Import from here; never hard-code these lists in views, forms, or templates.
"""

ALL_CATEGORIES: list[str] = [
    'disaster_flooding',
    'transportation_traffic',
    'public_infrastructure',
    'public_safety',
    'other',
    'uncertain',
]

CATEGORY_LABELS: dict[str, str] = {
    'disaster_flooding':      'Flooding / Disaster',
    'transportation_traffic': 'Traffic / Roads',
    'public_infrastructure':  'Infrastructure',
    'public_safety':          'Public Safety',
    'other':                  'Other',
    'uncertain':              'Uncertain',
}

ALL_STATUSES: list[str] = [
    'for_review',
    'reported',
    'acknowledged',
    'in_progress',
    'resolved',
    'dismissed',
]

STATUS_LABELS: dict[str, str] = {
    'for_review':   'For Review',
    'reported':     'Reported',
    'acknowledged': 'Acknowledged',
    'in_progress':  'In Progress',
    'resolved':     'Resolved',
    'dismissed':    'Dismissed',
}

# Statuses that count as active/unresolved (excludes terminal states)
ACTIVE_STATUSES: list[str] = ['reported', 'for_review', 'acknowledged', 'in_progress']

URGENCY_MAX: float = 10.0
