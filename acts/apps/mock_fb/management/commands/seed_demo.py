"""
python manage.py seed_demo

Pre-populates the Mock FB feed with 14 carefully crafted civic reports
that cover all five categories and exercise the full NLP pipeline.

Each post is designed to produce a correct classification, a resolved
barangay location, and a realistic urgency score — ready for the demo.

Usage:
    python manage.py seed_demo           # add posts (skip duplicates)
    python manage.py seed_demo --clear   # wipe mock posts first, then seed
"""
import uuid

from django.core.management.base import BaseCommand

from apps.webhook.models import RawPost


DEMO_POSTS = [
    # ── disaster_flooding (3) ──────────────────────────────────────────────
    (
        "EMERGENCY sa Brgy. Sabang! Lampas tao na ang baha, hindi na makawala ang "
        "tatlong pamilya sa kanto. Naiipit ang mga matanda at bata. Kailangan ng "
        "rescue ngayon! Tulong po!",
        "demo_flood_001",
    ),
    (
        "Baha na naman sa Marawoy! Hanggang dibdib na ang tubig sa may palengke. "
        "Maraming matanda ang naiipit sa kanilang bahay, hindi makalabas. Saklolo!",
        "demo_flood_002",
    ),
    (
        "Grabe ang ulan kanina, nagbaha agad sa Inosluban. May bata at buntis na "
        "kailangan ma-evacuate. Patuloy pang tumataas ang tubig, wala pang relief.",
        "demo_flood_003",
    ),

    # ── transportation_traffic (3) ─────────────────────────────────────────
    (
        "Sobrang traffic sa Lipa-Batangas highway papunta sa Plaridel. May nabagsak "
        "na malaking puno mula kagabi, nakaharang pa rin sa kalsada. Walang tumitingin "
        "o nag-aalis ng puno. Stranded na ang mga sasakyan.",
        "demo_transport_001",
    ),
    (
        "Traffic na traffic sa Tambois dahil sa construction na walang babala! "
        "Stranded ang mga jeepney at bus, hindi makaalis ang mga pasahero. "
        "Naghihintay na ng dalawang oras, walang alternatibong daan.",
        "demo_transport_002",
    ),
    (
        "Stranded kami sa Lumbang dahil sa sirang tulay. Walang makadaan kahit ang "
        "mga ambulansya at delivery truck. Matagal na itong sira, walang aksyon.",
        "demo_transport_003",
    ),

    # ── public_infrastructure (3) ──────────────────────────────────────────
    (
        "Bagsak ang poste ng kuryente sa Banaybanay kanina ng 5pm! Nakasabit pa ang "
        "live wire sa kalsada, mapanganib sa mga dumadaan. Nag-report na sa Meralco "
        "pero wala pa rin.",
        "demo_infra_001",
    ),
    (
        "Wala na kaming tubig sa Dagatan simula ng Lunes ng gabi. Sira daw ang main "
        "pipeline ng NAWASA. Tatlong araw na kaming walang tubig, kailan ito aayusin?",
        "demo_infra_002",
    ),
    (
        "Sira na ang drainage sa Pinagtongulan. Bumabaha palagi kahit maliit na ulan "
        "dahil sa naharang na kanal. Ilang taon nang ganito, wala pang aksyon mula sa LGU.",
        "demo_infra_003",
    ),

    # ── public_safety (3) ─────────────────────────────────────────────────
    (
        "May sunog sa Mataas na Lupa! Tatlong bahay na ang apektado at kumakalat pa "
        "ang apoy! Tumawag na ng bumbero at 911! Kailangan ng tulong ngayon!",
        "demo_safety_001",
    ),
    (
        "Aksidente sa intersection sa may Sabang market kanina ng tanghali. Nasangkot "
        "ang dalawang motor at isang kotse, may mga sugatan. Kailangan ng police at "
        "ambulansya agad.",
        "demo_safety_002",
    ),
    (
        "Mag-ingat kayong lahat sa Plaridel! May holdap na naganap kanina ng 10pm sa "
        "may sari-sari store. Naka-motor ang magnanakaw, dalawa sila. Pakipatrolan po.",
        "demo_safety_003",
    ),

    # ── other (2) ─────────────────────────────────────────────────────────
    (
        "Kailan po ang susunod na libreng medical mission sa Lipa City? "
        "Gustong mag-check-up ng lola ko pero mahirap na pumunta sa ospital.",
        "demo_other_001",
    ),
    (
        "Kailan po ang schedule ng libreng seminar para sa mga magsasaka sa Sabang? "
        "Gustong dumalo ng aking tatay. Salamat sa LGU sa ganitong programa para sa komunidad.",
        "demo_other_002",
    ),
]


class Command(BaseCommand):
    help = "Seed the Mock FB feed with demo civic reports for the hackathon presentation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing mock posts before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = RawPost.objects.filter(
                facebook_post_id__startswith="demo_"
            ).delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} existing demo posts."))

        created_count = 0
        skipped_count = 0

        for text, post_id in DEMO_POSTS:
            raw_post, created = RawPost.objects.get_or_create(
                facebook_post_id=post_id,
                defaults={"post_text": text},
            )
            if not created:
                skipped_count += 1
                continue

            # Run pipeline synchronously
            try:
                from apps.triage.pipeline import process_post
                report = process_post(raw_post)
                cat = report.category if report else "unknown"
                score = report.urgency_score if report else 0.0
                self.stdout.write(
                    f"  ✓ {post_id:25} → {cat} (urgency={score})"
                )
            except Exception as exc:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {post_id}: pipeline error — {exc}")
                )

            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Created {created_count} posts, skipped {skipped_count} duplicates."
        ))
        self.stdout.write("Open /fb/ to see the populated feed.")
