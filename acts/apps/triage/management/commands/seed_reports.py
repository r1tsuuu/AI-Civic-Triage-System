"""
python manage.py seed_reports

Populates the database with 30 high-accuracy mock civic reports that mimic
casual Filipino/Taglish social-media citizen posts in Lipa City and Batangas City.

Metadata (category, coordinates, urgency, confidence) is hardcoded per entry
so the demo database is always consistent regardless of ML model state.
Status is varied across the workflow to show a realistic live triage queue.

Usage:
    python manage.py seed_reports            # add (skip duplicates)
    python manage.py seed_reports --clear    # wipe seed data then re-insert
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
import random

from apps.webhook.models import RawPost
from apps.triage.models import Report, StatusChange

# ---------------------------------------------------------------------------
# Seed data
# Each entry is a dict with every field we care about.
# coordinates are verified against actual barangay centroids (WGS-84).
# ---------------------------------------------------------------------------

REPORTS: list[dict] = [

    # ── disaster_flooding (10) ─────────────────────────────────────────────

    {
        "post_id": "seed_flood_001",
        "text": (
            "EMERGENCY!! Baha na sa Brgy. Sabang!! Lampas tao na ang tubig sa kanto, "
            "hindi na makalabas ang mga pamilya. May bata at matatanda na naiipit. "
            "Kailangan ng rescue ASAP!! Saan na ang BFP?? 😭"
        ),
        "category": "disaster_flooding",
        "location_text": "Brgy. Sabang, Lipa City",
        "latitude": 13.9385,
        "longitude": 121.1670,
        "urgency_score": 9.6,
        "classifier_confidence": 0.97,
        "status": "in_progress",
    },
    {
        "post_id": "seed_flood_002",
        "text": (
            "Baha na naman sa Marawoy!! Hanggang dibdib na ang tubig sa may palengke, "
            "maraming matanda ang naiipit sa loob ng kanilang bahay. "
            "Di pa naka-respond ang LGU. Saklolo po!!"
        ),
        "category": "disaster_flooding",
        "location_text": "Brgy. Marawoy, Lipa City",
        "latitude": 13.9450,
        "longitude": 121.1580,
        "urgency_score": 9.1,
        "classifier_confidence": 0.95,
        "status": "acknowledged",
    },
    {
        "post_id": "seed_flood_003",
        "text": (
            "Grabe ang baha dito sa Inosluban!! Naanod na yung mga gamit namin, "
            "pati yung aming sasakyan. May buntis pa sa kapitbahay na kailangan i-evacuate ASAP. "
            "Tulong po LGU!!"
        ),
        "category": "disaster_flooding",
        "location_text": "Brgy. Inosluban, Lipa City",
        "latitude": 13.9290,
        "longitude": 121.1510,
        "urgency_score": 9.3,
        "classifier_confidence": 0.96,
        "status": "in_progress",
    },
    {
        "post_id": "seed_flood_004",
        "text": "Baha dito sa Tambo! Kalahating bahay na ang nalubog. Tulong!",
        "category": "disaster_flooding",
        "location_text": "Brgy. Tambo, Lipa City",
        "latitude": 13.9330,
        "longitude": 121.1720,
        "urgency_score": 8.8,
        "classifier_confidence": 0.93,
        "status": "reported",
    },
    {
        "post_id": "seed_flood_005",
        "text": (
            "Paalala lang sa lahat — huwag dumaan sa Pinagtongulan road, "
            "baha na roon hanggang tuhod. Pwedeng ibalik ng daloy ang sasakyan nyo. "
            "Mag-ingat po kayo lalo na sa gabi."
        ),
        "category": "disaster_flooding",
        "location_text": "Brgy. Pinagtongulan, Lipa City",
        "latitude": 13.9620,
        "longitude": 121.1580,
        "urgency_score": 6.5,
        "classifier_confidence": 0.88,
        "status": "reported",
    },
    {
        "post_id": "seed_flood_006",
        "text": (
            "Update: bumaba na ang baha sa Brgy. Dagatan pero marami pa ring naapektuhan. "
            "Kailangan pa ng relief goods — bigas, tubig, at mga bata pang damit. "
            "Salamat sa mga nag-tulong kahapon!"
        ),
        "category": "disaster_flooding",
        "location_text": "Brgy. Dagatan, Lipa City",
        "latitude": 13.9510,
        "longitude": 121.1490,
        "urgency_score": 5.8,
        "classifier_confidence": 0.86,
        "status": "resolved",
    },
    {
        "post_id": "seed_flood_007",
        "text": (
            "Grabe yung ulan kagabi!! Ngayon may baha na sa Kumintang Ibaba, "
            "Batangas City. Pati ang main road sa port area ay hindi na madaanan ng mababang sasakyan. "
            "Mag-ingat sa pagbiyahe!"
        ),
        "category": "disaster_flooding",
        "location_text": "Brgy. Kumintang Ibaba, Batangas City",
        "latitude": 13.7537,
        "longitude": 121.0584,
        "urgency_score": 7.2,
        "classifier_confidence": 0.91,
        "status": "acknowledged",
    },
    {
        "post_id": "seed_flood_008",
        "text": (
            "Batangas Port area — baha na! Di na makapasok ang mga cargo trucks, "
            "naabala ang loading ng mga bangka. Kailangan ng pumping unit dito agad."
        ),
        "category": "disaster_flooding",
        "location_text": "Batangas Port, Batangas City",
        "latitude": 13.7565,
        "longitude": 121.0588,
        "urgency_score": 7.8,
        "classifier_confidence": 0.92,
        "status": "in_progress",
    },
    {
        "post_id": "seed_flood_009",
        "text": (
            "Nakita ko lang habang nagmamaneho — baha sa may Lipa Public Market. "
            "Hindi na makadaan ang mga pedicab at jeepney. Saan na ang drainage maintenance??"
        ),
        "category": "disaster_flooding",
        "location_text": "Lipa Public Market, Poblacion, Lipa City",
        "latitude": 13.9420,
        "longitude": 121.1628,
        "urgency_score": 6.0,
        "classifier_confidence": 0.87,
        "status": "reported",
    },
    {
        "post_id": "seed_flood_010",
        "text": "Tubig na puro putik sa Brgy. Mataas na Lupa! Baha! Huwag puntahan.",
        "category": "disaster_flooding",
        "location_text": "Brgy. Mataas na Lupa, Lipa City",
        "latitude": 13.9280,
        "longitude": 121.1590,
        "urgency_score": 7.5,
        "classifier_confidence": 0.90,
        "status": "for_review",
    },

    # ── transportation_traffic (8) ─────────────────────────────────────────

    {
        "post_id": "seed_traffic_001",
        "text": (
            "Grabe ang trapik sa JP Laurel Highway near SM Lipa!! "
            "Parang 2 km na ang pila ng sasakyan. May aksidente daw sa harap. "
            "Mag-bypass na kayo sa likod ng SM para makalusot. Update ko kayo!"
        ),
        "category": "transportation_traffic",
        "location_text": "JP Laurel Highway near SM Lipa",
        "latitude": 13.9544,
        "longitude": 121.1631,
        "urgency_score": 6.8,
        "classifier_confidence": 0.91,
        "status": "acknowledged",
    },
    {
        "post_id": "seed_traffic_002",
        "text": (
            "Ayala Highway pababa ng Lipa — may nabagsak na malaking puno!! "
            "Nakaharang sa isang lane, sobrang bagal ng trapik. "
            "Wala pang pumaparating na DPWH o LGU para mag-clear. "
            "Ilang oras na itong ganito guys 😤"
        ),
        "category": "transportation_traffic",
        "location_text": "Ayala Highway, Lipa City",
        "latitude": 13.9544,
        "longitude": 121.1600,
        "urgency_score": 7.1,
        "classifier_confidence": 0.89,
        "status": "in_progress",
    },
    {
        "post_id": "seed_traffic_003",
        "text": (
            "Stranded na kaming lahat sa Brgy. Lumbang dahil sa sirang tulay!! "
            "Hindi makalabas ang mga residente — pati ang mga ambulansya at delivery trucks. "
            "Matagal na itong sira, wala pa ring aksyon mula sa mga may kapangyarihan."
        ),
        "category": "transportation_traffic",
        "location_text": "Brgy. Lumbang, Lipa City",
        "latitude": 13.9240,
        "longitude": 121.1650,
        "urgency_score": 8.4,
        "classifier_confidence": 0.93,
        "status": "reported",
    },
    {
        "post_id": "seed_traffic_004",
        "text": (
            "Traffic alert: construction work sa Tambois walang advance notice! "
            "Naiipit ang mga jeepney at bus, hindi makaalis ang mga pasahero. "
            "Naghihintay na ng dalawang oras. Walang traffic enforcer, walang cones. Asan ba ang LTFRB??"
        ),
        "category": "transportation_traffic",
        "location_text": "Brgy. Tambois, Lipa City",
        "latitude": 13.9480,
        "longitude": 121.1700,
        "urgency_score": 6.2,
        "classifier_confidence": 0.87,
        "status": "reported",
    },
    {
        "post_id": "seed_traffic_005",
        "text": (
            "Batangas City — trapik sa P. Burgos Street hanggang Rizal Avenue! "
            "Parang may event sa may plaza, naharang na lahat ng sasakyan. "
            "Kung wala kayong lakad doon, iwasan na muna."
        ),
        "category": "transportation_traffic",
        "location_text": "P. Burgos Street, Batangas City",
        "latitude": 13.7566,
        "longitude": 121.0602,
        "urgency_score": 5.5,
        "classifier_confidence": 0.85,
        "status": "resolved",
    },
    {
        "post_id": "seed_traffic_006",
        "text": (
            "UPDATE: naalis na yung puno sa Lipa-Batangas highway malapit sa Plaridel exit!! "
            "Dalawang lane na ulit ang bukas. Salamat sa mga nag-clear! Mag-ingat pa rin sa putik sa kalsada."
        ),
        "category": "transportation_traffic",
        "location_text": "Brgy. Plaridel, Lipa City",
        "latitude": 13.9185,
        "longitude": 121.1548,
        "urgency_score": 3.5,
        "classifier_confidence": 0.83,
        "status": "resolved",
    },
    {
        "post_id": "seed_traffic_007",
        "text": (
            "Mag-iingat sa national highway malapit sa Batangas City Hospital — "
            "palaging trapik doon ng tanghali dahil sa ambulansya at visitors. "
            "Maagang pumunta o mag-bypass na lang kayo."
        ),
        "category": "transportation_traffic",
        "location_text": "National Highway near Batangas City Hospital",
        "latitude": 13.7548,
        "longitude": 121.0558,
        "urgency_score": 4.8,
        "classifier_confidence": 0.82,
        "status": "reported",
    },
    {
        "post_id": "seed_traffic_008",
        "text": (
            "SM City Batangas area — grabe ang traffic ngayong weekend! "
            "Pati yung parking naapektuhan na. Lumabas na kayo ng maaga bago lumala pa. "
            "Gulod Labac road pabalik ay maayos naman."
        ),
        "category": "transportation_traffic",
        "location_text": "SM City Batangas, Pallocan West, Batangas City",
        "latitude": 13.7665,
        "longitude": 121.0620,
        "urgency_score": 5.0,
        "classifier_confidence": 0.84,
        "status": "reported",
    },

    # ── public_infrastructure (7) ──────────────────────────────────────────

    {
        "post_id": "seed_infra_001",
        "text": (
            "MAPANGANIB!! Bagsak ang poste ng kuryente sa Brgy. Banaybanay kanina ng 5pm!! "
            "Nakasabit pa ang live wire sa gitna ng kalsada!! "
            "Nag-report na kami sa Meralco hotline pero wala pa rin. "
            "Huwag pong dumaan doon!! ⚡⚡"
        ),
        "category": "public_infrastructure",
        "location_text": "Brgy. Banaybanay, Lipa City",
        "latitude": 13.9360,
        "longitude": 121.1650,
        "urgency_score": 9.0,
        "classifier_confidence": 0.94,
        "status": "acknowledged",
    },
    {
        "post_id": "seed_infra_002",
        "text": (
            "Tatlong araw na kaming walang tubig sa Brgy. Dagatan! "
            "Sabi ng NAWASA sira daw ang main pipeline pero wala pa silang timeline kung kailan maaayos. "
            "Matatanda at mga bata ang apektado. Kailangan namin ng water tanker ASAP."
        ),
        "category": "public_infrastructure",
        "location_text": "Brgy. Dagatan, Lipa City",
        "latitude": 13.9510,
        "longitude": 121.1490,
        "urgency_score": 8.0,
        "classifier_confidence": 0.91,
        "status": "in_progress",
    },
    {
        "post_id": "seed_infra_003",
        "text": (
            "Sira na ang drainage sa Pinagtongulan! "
            "Bumabaha tuwing umuulan kahit maliit lang — naharang ang kanal ng basura at putik. "
            "Ilang taon na naming idinireklamo ito sa barangay, wala pa ring aksyon."
        ),
        "category": "public_infrastructure",
        "location_text": "Brgy. Pinagtongulan, Lipa City",
        "latitude": 13.9620,
        "longitude": 121.1580,
        "urgency_score": 7.0,
        "classifier_confidence": 0.89,
        "status": "reported",
    },
    {
        "post_id": "seed_infra_004",
        "text": (
            "May malaking butas sa kalsada sa Lipa Public Market area — "
            "yung malapit sa entrance ng palengke. Ilang motor na ang nasira doon. "
            "May natamaan pang pasahero ng tricycle kagabi. Ayusin na po ito!"
        ),
        "category": "public_infrastructure",
        "location_text": "Lipa Public Market, Poblacion, Lipa City",
        "latitude": 13.9420,
        "longitude": 121.1628,
        "urgency_score": 7.4,
        "classifier_confidence": 0.90,
        "status": "reported",
    },
    {
        "post_id": "seed_infra_005",
        "text": (
            "Wala na kaming ilaw sa kalye sa Brgy. Mataas na Lupa mula pa noong isang linggo! "
            "Lahat ng street lights ay patay — mapanganib na lakad ng gabi. "
            "Tumawag na kami sa barangay pero wala pang aksyon."
        ),
        "category": "public_infrastructure",
        "location_text": "Brgy. Mataas na Lupa, Lipa City",
        "latitude": 13.9280,
        "longitude": 121.1590,
        "urgency_score": 6.5,
        "classifier_confidence": 0.88,
        "status": "for_review",
    },
    {
        "post_id": "seed_infra_006",
        "text": (
            "Gulod Labac, Batangas City — bumagsak yung matandang pader ng munisiyo malapit sa barangay hall! "
            "Nakaharang sa daan, hindi makadaan ang mga tao. "
            "Baka may matamaan pa. Paki-report po sa DPWH."
        ),
        "category": "public_infrastructure",
        "location_text": "Brgy. Gulod Labac, Batangas City",
        "latitude": 13.7449,
        "longitude": 121.0565,
        "urgency_score": 7.8,
        "classifier_confidence": 0.91,
        "status": "acknowledged",
    },
    {
        "post_id": "seed_infra_007",
        "text": (
            "Brownout na naman sa Alangilan, Batangas City — ika-tatlong araw na ngayong linggo! "
            "Ilang oras bawat araw. Nasira na ang aming ref at mga gamit. "
            "Meralco hindi sumasagot sa calls. Sana mapansin nila ito."
        ),
        "category": "public_infrastructure",
        "location_text": "Brgy. Alangilan, Batangas City",
        "latitude": 13.7830,
        "longitude": 121.0720,
        "urgency_score": 6.8,
        "classifier_confidence": 0.87,
        "status": "reported",
    },

    # ── public_safety (5) ──────────────────────────────────────────────────

    {
        "post_id": "seed_safety_001",
        "text": (
            "SUNOG SA BRGY. MATAAS NA LUPA!! Tatlong bahay na ang apektado!! "
            "Kumakalat pa ang apoy!! Tumawag na ng BFP at 911!! "
            "Huwag dumaan sa area, delikado!! 🔥🔥🔥"
        ),
        "category": "public_safety",
        "location_text": "Brgy. Mataas na Lupa, Lipa City",
        "latitude": 13.9280,
        "longitude": 121.1590,
        "urgency_score": 9.8,
        "classifier_confidence": 0.98,
        "status": "in_progress",
    },
    {
        "post_id": "seed_safety_002",
        "text": (
            "Aksidente sa intersection ng Brgy. Sabang market kanina ng hapon! "
            "Dalawang motor at isang van, may mga sugatan. "
            "Kailangan ng police at ambulansya agad — may isa na mukhang malubha. "
            "Nandito ako sa tabi, tinawagan ko na ang 911."
        ),
        "category": "public_safety",
        "location_text": "Brgy. Sabang, Lipa City",
        "latitude": 13.9385,
        "longitude": 121.1670,
        "urgency_score": 9.2,
        "classifier_confidence": 0.96,
        "status": "resolved",
    },
    {
        "post_id": "seed_safety_003",
        "text": (
            "Mag-ingat sa Plaridel area!! May holdap na naganap kagabi ng mga 10pm "
            "sa may sari-sari store. Naka-motor ang mga magnanakaw, dalawa sila. "
            "Pakipatrolan na po ng pulis ang lugar. Mababa pa ang ilaw doon."
        ),
        "category": "public_safety",
        "location_text": "Brgy. Plaridel, Lipa City",
        "latitude": 13.9185,
        "longitude": 121.1548,
        "urgency_score": 7.9,
        "classifier_confidence": 0.90,
        "status": "reported",
    },
    {
        "post_id": "seed_safety_004",
        "text": (
            "May natumba na bata sa malalim na kanal sa Brgy. Tambo — "
            "iniligtaas na ng mga kapitbahay pero kailangan pang dalhin sa ospital. "
            "Yung kanal ay walang barikada o cover kahit malapit sa paaralan. "
            "Gawin nang ligtas ito para sa mga bata!!"
        ),
        "category": "public_safety",
        "location_text": "Brgy. Tambo, Lipa City",
        "latitude": 13.9330,
        "longitude": 121.1720,
        "urgency_score": 8.5,
        "classifier_confidence": 0.92,
        "status": "acknowledged",
    },
    {
        "post_id": "seed_safety_005",
        "text": (
            "Batangas Port area — may altercation sa pagitan ng grupo ng mangingisda at cargo workers. "
            "Malapit nang lumaki, kailangan ng police presence dito ngayon. "
            "Maraming tao, baka masama ang mangyari."
        ),
        "category": "public_safety",
        "location_text": "Batangas Port, Batangas City",
        "latitude": 13.7565,
        "longitude": 121.0588,
        "urgency_score": 8.1,
        "classifier_confidence": 0.91,
        "status": "acknowledged",
    },
]

# Verify we have 30 entries
assert len(REPORTS) == 30, f"Expected 30 entries, got {len(REPORTS)}"

# Status transitions to simulate realistic history (for non-reported/for_review statuses)
STATUS_CHAIN = {
    "reported":     [],
    "for_review":   [],
    "acknowledged": [("reported", "acknowledged")],
    "in_progress":  [("reported", "acknowledged"), ("acknowledged", "in_progress")],
    "resolved":     [("reported", "acknowledged"), ("acknowledged", "in_progress"),
                     ("in_progress", "resolved")],
    "dismissed":    [("reported", "dismissed")],
}


class Command(BaseCommand):
    help = "Seed the triage database with 30 high-accuracy mock civic reports."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing seed reports before inserting.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            pids = [r["post_id"] for r in REPORTS]
            raw_deleted, _ = RawPost.objects.filter(facebook_post_id__in=pids).delete()
            self.stdout.write(self.style.WARNING(
                f"Cleared {raw_deleted} existing seed raw-posts (cascades to Reports)."
            ))

        now = timezone.now()
        created = skipped = 0

        with transaction.atomic():
            for idx, entry in enumerate(REPORTS):
                raw_post, is_new = RawPost.objects.get_or_create(
                    facebook_post_id=entry["post_id"],
                    defaults={
                        "post_text": entry["text"],
                        # Spread posts across the past 7 days
                        "received_at": now - timedelta(hours=idx * 5 + random.randint(0, 4)),
                        "processed": True,
                    },
                )

                if not is_new:
                    skipped += 1
                    continue

                # Build routing notes for low-confidence / for_review entries
                if entry["status"] == "for_review":
                    routing_notes = (
                        f"Low confidence: {entry['classifier_confidence'] * 100:.1f}% "
                        f"(threshold 65%). Awaiting human review."
                    )
                    effective_category = "uncertain"
                else:
                    routing_notes = ""
                    effective_category = entry["category"]

                report = Report.objects.create(
                    raw_post=raw_post,
                    category=effective_category,
                    classifier_confidence=entry["classifier_confidence"],
                    urgency_score=entry["urgency_score"],
                    location_text=entry["location_text"],
                    latitude=entry["latitude"],
                    longitude=entry["longitude"],
                    location_confidence="gazetteer",
                    status=entry["status"],
                    routing_notes=routing_notes,
                )

                # Create realistic StatusChange history for advanced statuses
                transitions = STATUS_CHAIN.get(entry["status"], [])
                for offset, (from_s, to_s) in enumerate(transitions):
                    StatusChange.objects.create(
                        report=report,
                        from_status=from_s,
                        to_status=to_s,
                        changed_by="demo",
                        note=None,
                    )

                created += 1
                self.stdout.write(
                    f"  ✓ [{entry['status']:12}] {entry['post_id']:22} "
                    f"→ {entry['category']:30} "
                    f"urgency={entry['urgency_score']:.1f}  "
                    f"conf={entry['classifier_confidence']:.0%}"
                )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. Created {created} reports, skipped {skipped} duplicates."
        ))
        if created:
            self.stdout.write(
                "  Open /dashboard/reports/ to see the populated triage queue."
            )
