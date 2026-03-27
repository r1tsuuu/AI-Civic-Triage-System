REPLY_TEMPLATES = {
    'disaster_flooding': (
        "Kumusta po kayo? Natanggap na ng aming opisina ang inyong ulat tungkol sa "
        "kalagayan ng baha sa inyong lugar. Naresolba na po ito. "
        "Salamat sa inyong ulat at patuloy na pag-uulat ng mga alalahanin sa aming komunidad!"
    ),
    'transportation_traffic': (
        "Salamat sa inyong ulat! Ang isyu tungkol sa trapiko o transportasyon ay "
        "naresolba na po. Patuloy kaming nagtatrabaho para sa ligtas na pagbiyahe "
        "ng aming mga mamamayan."
    ),
    'public_infrastructure': (
        "Salamat sa inyong ulat! Ang isyu tungkol sa imprastraktura ay naresolba na po. "
        "Patuloy kaming nagtatrabaho para sa inyong komunidad."
    ),
    'public_safety': (
        "Salamat sa inyong ulat! Ang isyu tungkol sa kaligtasan ng publiko ay "
        "naresolba na po. Ang inyong kaligtasan ang aming prayoridad."
    ),
    'other': (
        "Salamat sa inyong ulat! Naresolba na ang inyong concern. "
        "Patuloy kaming naglilingkod para sa inyo."
    ),
}

DEFAULT_TEMPLATE = (
    "Salamat sa inyong ulat! Naresolba na ang inyong concern. — {lgu_name}"
)

STATUS_TEMPLATES = {
    "acknowledged": (
        "Natanggap na po ng {lgu_name} ang inyong ulat at na-review na ito ng aming team. "
        "Salamat sa inyong pakikiisa."
    ),
    "in_progress": (
        "May aksyon na pong ginagawa ang {lgu_name} sa inyong ulat. "
        "Magbibigay kami ng panibagong update kapag tapos na ang proseso."
    ),
    "dismissed": (
        "Salamat sa inyong ulat. Na-review ito ng {lgu_name} ngunit hindi ito maipagpapatuloy "
        "dahil duplicate, kulang ang detalye, o hindi sakop ng civic issue workflow."
    ),
}

DEFAULT_STATUS_TEMPLATE = (
    "May update na po sa inyong ulat mula sa {lgu_name}."
)


def get_reply_text(category: str, lgu_name: str = "Lipa City LGU") -> str:
    template = REPLY_TEMPLATES.get(category, DEFAULT_TEMPLATE)
    return template.format(lgu_name=lgu_name) if '{lgu_name}' in template else template


def get_status_update_text(
    category: str,
    status: str,
    lgu_name: str = "Lipa City LGU",
) -> str:
    if status == "resolved":
        return get_reply_text(category, lgu_name=lgu_name)

    template = STATUS_TEMPLATES.get(status, DEFAULT_STATUS_TEMPLATE)
    return template.format(lgu_name=lgu_name)
