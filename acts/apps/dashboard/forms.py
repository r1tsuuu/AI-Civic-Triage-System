from django import forms

CATEGORY_CHOICES = [
    ("disaster_flooding",      "Disaster / Flooding"),
    ("transportation_traffic", "Transportation / Traffic"),
    ("public_infrastructure",  "Public Infrastructure"),
    ("public_safety",          "Public Safety"),
    ("other",                  "Other"),
    ("uncertain",              "Uncertain"),
]


class ReportEditForm(forms.Form):
    """
    Validates the manual-correction payload from the Edit Report modal.
    All fields are optional — only changed fields are persisted.
    """
    category = forms.ChoiceField(
        choices=[("", "— No Change —")] + CATEGORY_CHOICES,
        required=False,
    )
    urgency_score = forms.FloatField(
        min_value=0,
        max_value=100,
        required=False,
    )
    location_text = forms.CharField(
        max_length=255,
        required=False,
        strip=True,
    )
    latitude = forms.FloatField(
        min_value=-90,
        max_value=90,
        required=False,
    )
    longitude = forms.FloatField(
        min_value=-180,
        max_value=180,
        required=False,
    )

    def clean(self):
        cleaned = super().clean()
        lat = cleaned.get("latitude")
        lng = cleaned.get("longitude")
        # lat and lng must be supplied together or not at all
        if (lat is None) != (lng is None):
            raise forms.ValidationError(
                "Both latitude and longitude must be provided together."
            )
        return cleaned
