import csv
import os
import random

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

barangays = {
    "Sabang":          (13.95, 121.16),
    "Mataas na Lupa":  (13.94, 121.16),
    "Marawoy":         (13.96, 121.17),
    "Banaybanay":      (13.98, 121.15),
    "Inosluban":       (13.99, 121.14),
    "Lumbang":         (13.93, 121.18),
    "Dagatan":         (13.92, 121.19),
    "Plaridel":        (13.97, 121.15),
    "Tambois":         (13.92, 121.14),
    "Pinagtongulan":   (13.91, 121.13),
}

# ── Gazetteer CSV ────────────────────────────────────────────────────────────
# Landmarks from CONSTITUTION.md §16 — canonical names that the alias map resolves to
landmarks = {
    "De La Salle Lipa":                        (13.9544, 121.1631),
    "Metropolitan Cathedral of San Sebastian": (13.9422, 121.1635),
    "SM City Lipa":                            (13.9297, 121.1703),
    "Robinsons Place Lipa":                    (13.9384, 121.1676),
    "Bigben Commercial Center":                (13.9411, 121.1624),
    "Lipa City Public Market":                 (13.9437, 121.1618),
    "Lipa City Hall":                          (13.9420, 121.1628),
    "Lipa City Sports Complex":                (13.9382, 121.1543),
    "Mabini Shrine":                           (13.9489, 121.1604),
    "Ospital ng Lipa":                         (13.9359, 121.1692),
    "Lipa City Fire Station":                  (13.9428, 121.1631),
    "Lipa City Police Station":                (13.9425, 121.1629),
}

gazetteer_path = os.path.join(BASE_DIR, "gazetteer.csv")
with open(gazetteer_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["location_name", "latitude", "longitude"])
    for name, coords in barangays.items():
        writer.writerow([name, coords[0], coords[1]])
    for name, coords in landmarks.items():
        writer.writerow([name, coords[0], coords[1]])

print(f"Gazetteer written to {gazetteer_path} ({len(barangays)} barangays + {len(landmarks)} landmarks)")

# ── Seed training data ────────────────────────────────────────────────────────
# IMPORTANT: Category names must match Report.category choices exactly.
# Categories: disaster_flooding | transportation_traffic | public_infrastructure
#             | public_safety | other
templates = {
    "disaster_flooding": [
        "Tulong! Lampas tao na ang baha dito sa {brgy}, hindi na makawala ang mga tao!",
        "Saklolo po! Hanggang dibdib na ang tubig baha sa {brgy}, may mga bata at matatanda kami!",
        "Naiipit kami sa baha sa {brgy}! Kailangan na ng rescue! Tulong!",
        "SOS! Lampas tuhod na ang baha sa {brgy}, hindi na kaya ng mga matatanda!",
        "Rescue po sa {brgy}! Pati mga hayop namin nalunod na sa mataas na tubig!",
        "Grabe ang baha sa {brgy}, umabot na sa bubong ng mga bahay! Tulong sa aming lugar!",
        "Hindi na makalabas ng bahay ang mga kapitbahay sa {brgy}, naiipit sa baha!",
        "May bata at buntis dito sa {brgy} na kailangan ng tulong, patuloy tumataas ang tubig!",
        "Emergency! Baha sa {brgy}, hindi na kaya ng drainage, patuloy ang pagbaha!",
        "Ang tubig sa {brgy} ay patuloy pang tumataas, kailangan na ng evacuation!",
        "May matanda na walang makasama dito sa {brgy}, naiipit sa baha, agahan ninyo!",
        "Update mula sa {brgy}: Hindi pa bumababa ang baha, marami pang pamilya ang naiipit.",
        "Stranded kami sa {brgy} dahil sa mataas na tubig baha, walang makaalis!",
        "Baha na naman sa {brgy}, hindi na maubos-ubos. Lampas na sa kalye ang tubig.",
        "Pati ang evacuation center sa {brgy} ay may tubig na, saan pa kami lilipat?",
    ],
    "transportation_traffic": [
        "Sobrang traffic sa {brgy} dahil sa nabagsak na puno sa kalsada, walang makadaan!",
        "May stranded na truck sa {brgy}, nakaharang sa kalsada, puro traffic na.",
        "Sira ang kalsada sa {brgy}, puno ng butas, mapanganib sa motor at kotse.",
        "Hindi makadaan ang mga jeepney at bus sa {brgy} dahil sa blockage sa daan.",
        "Stranded po kami dito sa {brgy}, sira ang tulay, walang ibang daanan para sa sasakyan.",
        "Traffic grabe sa {brgy} road, dalawang oras na kaming hindi gumagalaw sa kalsada.",
        "Napakaraming sasakyan ang naghihintay sa {brgy}, may isinasarang daan ngayon.",
        "Nabuwal ang malaking puno sa kalsada ng {brgy} dahil sa bagyo, naharang ang trapiko.",
        "Hindi na mapasok ng mga delivery truck ang {brgy} dahil sa sirang aspalto at butas.",
        "May aksidente sa intersection sa {brgy}, naka-block ang isang lane ng kalsada.",
        "Grabe ang trapik sa {brgy} ngayong umaga, may nagkachoke na sasakyan sa gitna.",
        "Walang pumapasok na pampublikong sasakyan sa {brgy}, stranded ang mga pasahero.",
        "Sira na talaga ang aspalto sa {brgy} Road, mapanganib na sa mga motorista.",
        "Hay nako, traffic ulit sa {brgy} dahil sa construction na walang babala sa mga driver.",
        "Mag-ingat sa {brgy} road, may malalim na butas sa kalsada na bago pa lang nagbukas!",
    ],
    "public_infrastructure": [
        "Bagsak ang poste ng kuryente sa {brgy}, nakasabit pa ang wire sa kalsada, mapanganib!",
        "Sira ang pangunahing linya ng tubig sa {brgy}, wala kaming tubig simula kahapon.",
        "Nawalan ng ilaw ang kalahati ng {brgy} dahil sa sirang transformer, kelan aayusin?",
        "Tumutulo ang tubig mula sa sirang tubo ng NAWASA sa kalsada ng {brgy}.",
        "Sira ang drainage sa {brgy}, bumabaha palagi kahit maliit na ulan dahil sa blockage.",
        "Gumuho ang bahagi ng kalsada sa {brgy} malapit sa eskwelahan, mapanganib sa bata.",
        "May butas na malaki sa daan sa {brgy}, nasira na ang ilang gulong ng mga sasakyan.",
        "Ang street light sa {brgy} ay patay na ng matagal, delikado maglakad ng gabi doon.",
        "Walang tubig na dumadating sa {brgy} simula kagabi, may naputol na linya ng NAWASA.",
        "Sira ang footbridge sa {brgy}, mapanganib na tumawid ang mga bata at matatanda.",
        "Hindi pa nagaayos ng drainage sa {brgy} kahit ilang beses na naming irineport sa LGU.",
        "Biglang naging madilim ang {brgy} kanina, may nasunog na transformer ng Meralco.",
        "Ang canal sa {brgy} ay puno na ng basura, nagsisimulang mag-overflow sa kalsada.",
        "Sira ang paaralan sa {brgy}, naputol ang koneksyon ng kuryente at tubig.",
        "Nabuwal ang electric post sa {brgy} road, wire nakasabit pa, delikado para sa lahat.",
    ],
    "public_safety": [
        "May nakawan na nangyayari dito sa {brgy}, nasaan ang barangay tanod at police?",
        "May sunog sa {brgy}! Tumawag na ng bumbero! Tatlong bahay na ang apektado!",
        "May aksidente sa motor sa {brgy}, duguan ang driver at pasahero, kailangan ng ambulansya!",
        "Ang dilim ng kalsada sa {brgy} ng gabi, delikado para sa mga naglalakad.",
        "May holdap na naganap kanina ng gabi sa {brgy}, mag-ingat tayong lahat!",
        "May nang-iistorbo at nagbabanta sa mga residente ng {brgy}, pakicheck ng pulis.",
        "Takot maglakad sa gabi sa {brgy} dahil walang ilaw at maraming suspicious na tao.",
        "May nagaaway na grupo sa kanto ng {brgy}, baka may masamang mangyari agad!",
        "Nagsisigawan ang mga tao sa {brgy}, pakicheck ng barangay tanod o police ngayon!",
        "May abandoned na sasakyan na nakaka-suspecha sa {brgy} ng ilang araw na.",
        "Pakipatrolan ang {brgy} ngayong gabi, may sinasabing magnanakaw na lumalagala doon.",
        "Sunog sa {brgy}! Kumakalat na ang apoy! Tumawag na ng bumbero at police!",
        "Aksidente sa {brgy}, nasangkot ang isang bata, kailangan ng emergency response agad!",
        "Security issue sa {brgy}: may mga naka-motor na naglilibot parang nagre-recon ng area.",
        "May mabangis na aso sa {brgy} na nakakagat ng mga bata, pakiaksyon ng barangay.",
    ],
    "other": [
        "Kailan ang fiesta sa {brgy}? Gusto naming makilahok sa selebrasyon.",
        "Napakaganda ng panahon ngayon sa {brgy}, sana lagi ganito ang klima!",
        "May bago bang bukas na kainan sa {brgy}? Gustong gusto ko ang lutong Batangas.",
        "Nawawala ang aso ko sa {brgy}, puti, malaki, may tuldok na itim sa tagiliran.",
        "Meeting po ang mga officials bukas sa {brgy}, pakibroadcast sa mga residente.",
        "Maganda ang bagong park sa {brgy}, salamat sa LGU sa proyektong ito!",
        "Salamat sa mga nagbakuna dito sa {brgy} kahapon, maayos ang programa ng health center.",
        "Masayang-masaya ang programa ng {brgy} kanina sa plaza, maraming dumalo!",
        "Nagtatanong lang tungkol sa schedule ng koleksyon ng basura sa {brgy} ngayong linggo.",
        "Kailan ang susunod na barangay assembly sa {brgy}? May gusto akong itanong sa captain.",
        "Balita ko may bagong barangay health center sa {brgy}, totoo ba ito?",
        "Congrats sa {brgy} sa award na natanggap nila mula sa lungsod ngayong taon!",
        "Tanong lang po, may libreng seminar ba para sa mga magsasaka sa {brgy} ngayong buwan?",
        "Salamat sa mga volunteer na naglinis ng {brgy} kahapon, maganda na ang tingin ngayon.",
        "Kelan ang distribution ng relief goods sa {brgy}? Hindi pa kami nakakatanggap.",
    ],
}

# 60 samples per category = 300 total (balanced for maximum classifier accuracy)
pool = []
for cat in templates:
    pool.extend([cat] * 60)
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
