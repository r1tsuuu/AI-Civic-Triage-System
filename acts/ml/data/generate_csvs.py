import csv
import random

barangays = {
    "Sabang": (13.95, 121.16),
    "Mataas na Lupa": (13.94, 121.16),
    "Marawoy": (13.96, 121.17),
    "Banaybanay": (13.98, 121.15),
    "Inosluban": (13.99, 121.14),
    "Lumbang": (13.93, 121.18),
    "Dagatan": (13.92, 121.19),
    "Plaridel": (13.97, 121.15),
    "Tambois": (13.92, 121.14),
    "Pinagtongulan": (13.91, 121.13)
}

gazetteer_path = r"c:\Users\jaren\Desktop\ML Projects\hackathon\AI-Civic-Triage-System\acts\ml\data\gazetteer.csv"
with open(gazetteer_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["location_name", "latitude", "longitude"])
    for b, coords in barangays.items():
        writer.writerow([b, coords[0], coords[1]])

templates = {
    "disaster": [
        "Tulong, lampas tao na baha sa {brgy}!",
        "Saklolo, naiipit kami sa baha dito sa {brgy}",
        "Hanggang dibdib na baha sa {brgy}, kailangan ng rescue",
        "May mga bata at matanda dito sa {brgy} na kailangan i-rescue",
        "Baha sa {brgy}, hindi na makalabas ang mga tao",
        "Rescue please sa {brgy}, tulong!"
    ],
    "transport": [
        "Traffic sa {brgy} dahil sa baha",
        "Hindi makadaan ang mga sasakyan sa {brgy}",
        "May stranded na truck sa {brgy}",
        "Sira ang kalsada sa {brgy}, sobrang traffic",
        "Stranded po kami dito sa {brgy}"
    ],
    "infrastructure": [
        "Bagsak ang poste ng kuryente sa {brgy}",
        "Sira ang tulay sa {brgy}",
        "Nabuwal ang puno sa kalsada sa {brgy}",
        "Nawalan ng ilaw sa poste ng {brgy}",
        "Tumutulo ang tubig sa sirang tubo sa {brgy}"
    ],
    "safety": [
        "May nakawan na nangyayari dito sa {brgy}",
        "Nasaan ang police? May nag-aaway sa {brgy}",
        "May sunog sa {brgy}, tumawag kayo ng bumbero",
        "May aksidente sa motor sa {brgy}, duguan",
        "Ang dilim ng kalsada sa {brgy}, delikado maglakad"
    ],
    "other": [
        "Kailan ang fiesta sa {brgy}?",
        "Napakaganda ng panahon ngayon sa {brgy}",
        "May bago bang bukas na kainan sa {brgy}?",
        "Nawawala ang aso ko sa {brgy}",
        "Meeting po ang mga officials bukas sa {brgy}"
    ]
}

seed_data_path = r"c:\Users\jaren\Desktop\ML Projects\hackathon\AI-Civic-Triage-System\acts\ml\data\seed_data.csv"
categories = ["disaster", "transport", "infrastructure", "safety", "other"]

pool = []
for c in categories:
    pool.extend([c] * 60)
random.shuffle(pool)

with open(seed_data_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["text", "category"])
    for cat in pool:
        brgy = random.choice(list(barangays.keys()))
        text = random.choice(templates[cat]).format(brgy=brgy)
        writer.writerow([text, cat])

print("CSV generation complete.")
