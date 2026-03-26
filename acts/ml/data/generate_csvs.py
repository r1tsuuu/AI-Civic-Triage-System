import csv
import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
    "Pinagtongulan": (13.91, 121.13),
}

# ── Gazetteer CSV ────────────────────────────────────────────────────────────
gazetteer_path = os.path.join(BASE_DIR, "gazetteer.csv")
with open(gazetteer_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["location_name", "latitude", "longitude"])
    for b, coords in barangays.items():
        writer.writerow([b, coords[0], coords[1]])

print(f"Gazetteer written to {gazetteer_path}")

# ── Seed training data ────────────────────────────────────────────────────────
templates = {
    "disaster": [
        "Tulong, lampas tao na baha sa {brgy}!",
        "Saklolo, naiipit kami sa baha dito sa {brgy}",
        "Hanggang dibdib na baha sa {brgy}, kailangan ng rescue",
        "May mga bata at matanda dito sa {brgy} na kailangan i-rescue",
        "Baha sa {brgy}, hindi na makalabas ang mga tao",
        "Rescue please sa {brgy}, tulong!",
        "Pati mga hayop namin nalunod na sa {brgy}",
        "Grabe na ang baha sa {brgy}, umabot na sa bubong ng bahay",
        "SOS mula sa {brgy}, pamilya namin nangangailangan ng tulong",
        "Hindi makalabas ng bahay ang mga kapitbahay sa {brgy}, naiipit sa baha",
    ],
    "transport": [
        "Traffic sa {brgy} dahil sa baha",
        "Hindi makadaan ang mga sasakyan sa {brgy}",
        "May stranded na truck sa {brgy}",
        "Sira ang kalsada sa {brgy}, sobrang traffic",
        "Stranded po kami dito sa {brgy}",
        "Puno ang kalsada sa {brgy} ng basura, hindi makadaan",
        "Sira ang tulay sa {brgy} kaya walang makadaan",
        "Nabalisa na ang mga driver sa {brgy} dahil sa sirang daan",
        "Grabe ang traffic sa {brgy}, matagal na kaming nakatayo dito",
        "Napadaan po kami sa {brgy} at sira na ang aspalto",
    ],
    "infrastructure": [
        "Bagsak ang poste ng kuryente sa {brgy}",
        "Sira ang tulay sa {brgy}",
        "Nabuwal ang puno sa kalsada sa {brgy}",
        "Nawalan ng ilaw sa poste ng {brgy}",
        "Tumutulo ang tubig sa sirang tubo sa {brgy}",
        "Walang tubig na dumadating sa {brgy} simula kahapon",
        "Sira ang drainage sa {brgy}, bumabaha palagi",
        "Gumuho ang bahagi ng kalsada sa {brgy}",
        "May butas na malaki sa daan sa {brgy}, mapanganib sa mga sasakyan",
        "Ang parol na ilaw sa {brgy} ay sira na matagal na",
    ],
    "safety": [
        "May nakawan na nangyayari dito sa {brgy}",
        "Nasaan ang police? May nag-aaway sa {brgy}",
        "May sunog sa {brgy}, tumawag kayo ng bumbero",
        "May aksidente sa motor sa {brgy}, duguan",
        "Ang dilim ng kalsada sa {brgy}, delikado maglakad",
        "May holdap na naganap kanina sa {brgy}",
        "Takot maglakad sa gabi sa {brgy} dahil walang ilaw",
        "Tumawag na ng ambulansya sa {brgy}, may natamaan",
        "Nagsisigaw ng tulong ang babae sa {brgy}, pakicheck",
        "May nang-iipit ng mga bata sa {brgy}, kailangan ng pulis",
    ],
    "other": [
        "Kailan ang fiesta sa {brgy}?",
        "Napakaganda ng panahon ngayon sa {brgy}",
        "May bago bang bukas na kainan sa {brgy}?",
        "Nawawala ang aso ko sa {brgy}",
        "Meeting po ang mga officials bukas sa {brgy}",
        "Maganda ang bagong park sa {brgy}",
        "Salamat sa mga nagbakuna dito sa {brgy}",
        "Masayang-masaya ang programa kanina sa {brgy}",
        "Nagtatanong lang tungkol sa schedule ng basura sa {brgy}",
        "Kailan ang susunod na baranggay assembly sa {brgy}?",
    ],
}

categories = list(templates.keys())
# 60 samples per category = 300 total
pool = []
for c in categories:
    pool.extend([c] * 60)
random.shuffle(pool)

seed_data_path = os.path.join(BASE_DIR, "seed_data.csv")
with open(seed_data_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["text", "category"])
    for cat in pool:
        brgy = random.choice(list(barangays.keys()))
        text = random.choice(templates[cat]).format(brgy=brgy)
        writer.writerow([text, cat])

print(f"Seed data written to {seed_data_path} ({len(pool)} rows)")
print("CSV generation complete.")
