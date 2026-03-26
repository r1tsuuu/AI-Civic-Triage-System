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


def get_reply_text(category: str, lgu_name: str = "Lipa City LGU") -> str:
    template = REPLY_TEMPLATES.get(category, DEFAULT_TEMPLATE)
    return template.format(lgu_name=lgu_name) if '{lgu_name}' in template else template
