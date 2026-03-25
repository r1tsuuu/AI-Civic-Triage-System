from apps.triage.pipeline import process_post
class MockRawPost:
    def __init__(self, content):
        self.content = content
        self.has_image = True
        self.reaction_count = 25
        self.processed = False
    def save(self):
        print(f"-> MockRawPost processed flag is now: {self.processed}")

test_post = MockRawPost("Tulong! Lampas tao na baha dito sa Mataas na Lupa. May mga naiipit na matanda!")
report = process_post(test_post)
print(f"Category: {report.category} (Confidence: {report.classifier_confidence:.2f})")
print(f"Urgency Score: {report.urgency_score} / 10.0")
print(f"Extracted Location: {report.location_text}")
print(f"Coordinates: {report.latitude}, {report.longitude} (Confidence: {report.location_confidence})")
print(f"Initial Status: {report.status}")
