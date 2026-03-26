"""
Unit tests for apps/triage/scorer.py — urgency scoring rule engine.
No Django DB required; pure unit tests.
"""
from django.test import SimpleTestCase
from apps.triage.scorer import compute_score, compute_score_with_breakdown


class ComputeScoreBasicTests(SimpleTestCase):

    def test_empty_text_returns_zero(self):
        self.assertEqual(compute_score(''), 0.0)

    def test_none_like_empty_returns_zero(self):
        self.assertEqual(compute_score(''), 0.0)

    def test_no_signals_returns_zero(self):
        self.assertEqual(compute_score('Magandang umaga po sa lahat.'), 0.0)

    def test_returns_float(self):
        self.assertIsInstance(compute_score('walang laman'), float)

    def test_score_capped_at_ten(self):
        # Text with all signals present
        text = 'tulong! lampas tao na! may matanda! di makalabas!'
        score = compute_score(text)
        self.assertLessEqual(score, 10.0)

    def test_score_non_negative(self):
        score = compute_score('tulong po kami')
        self.assertGreaterEqual(score, 0.0)


class DistressSignalTests(SimpleTestCase):

    def test_tulong_adds_three_points(self):
        score = compute_score('tulong po kami dito sa bahay')
        self.assertEqual(score, 3.0)

    def test_rescue_adds_three_points(self):
        score = compute_score('please rescue us here')
        self.assertEqual(score, 3.0)

    def test_saklolo_adds_three_points(self):
        score = compute_score('saklolo na po kami')
        self.assertEqual(score, 3.0)

    def test_hindi_na_kaya_adds_three_points(self):
        score = compute_score('hindi na kaya namin ito')
        self.assertEqual(score, 3.0)

    def test_naiipit_adds_three_points(self):
        score = compute_score('naiipit kami sa loob')
        self.assertEqual(score, 3.0)

    def test_distress_only_adds_once(self):
        # Multiple distress keywords should still only add 3.0 once
        score = compute_score('tulong tulong rescue saklolo')
        self.assertEqual(score, 3.0)


class FloodDepthSignalTests(SimpleTestCase):

    def test_lampas_tao_adds_two_points(self):
        score = compute_score('lampas tao na ang baha dito')
        self.assertEqual(score, 2.0)

    def test_hanggang_dibdib_adds_two_points(self):
        score = compute_score('hanggang dibdib na ang tubig')
        self.assertEqual(score, 2.0)

    def test_lampas_tuhod_adds_two_points(self):
        score = compute_score('lampas tuhod na ang baha')
        self.assertEqual(score, 2.0)

    def test_flood_depth_only_adds_once(self):
        score = compute_score('lampas tao hanggang dibdib')
        self.assertEqual(score, 2.0)


class VulnerablePersonsSignalTests(SimpleTestCase):

    def test_may_matanda_adds_two_points(self):
        # Avoid "di makalabas" substring match inside "hindi makalabas"
        score = compute_score('may matanda kami dito na nagtatago sa sulok')
        self.assertEqual(score, 2.0)

    def test_may_bata_adds_two_points(self):
        score = compute_score('may bata kami dito')
        self.assertEqual(score, 2.0)

    def test_may_buntis_adds_two_points(self):
        score = compute_score('may buntis sa loob ng bahay')
        self.assertEqual(score, 2.0)

    def test_vulnerable_only_adds_once(self):
        score = compute_score('may matanda may bata may buntis')
        self.assertEqual(score, 2.0)


class StrandedSignalTests(SimpleTestCase):

    def test_di_makalabas_adds_two_points(self):
        score = compute_score('di makalabas ang mga tao')
        self.assertEqual(score, 2.0)

    def test_may_stranded_adds_two_points(self):
        score = compute_score('may stranded na pasyente dito')
        self.assertEqual(score, 2.0)

    def test_stranded_only_adds_once(self):
        score = compute_score('di makalabas may stranded')
        self.assertEqual(score, 2.0)


class ImageAndReactionTests(SimpleTestCase):

    def test_has_image_adds_half_point(self):
        score = compute_score('baha dito', has_image=True)
        self.assertEqual(score, 0.5)

    def test_no_image_adds_nothing(self):
        score = compute_score('baha dito', has_image=False)
        self.assertEqual(score, 0.0)

    def test_over_twenty_reactions_adds_half_point(self):
        score = compute_score('baha dito', reaction_count=21)
        self.assertEqual(score, 0.5)

    def test_exactly_twenty_reactions_adds_nothing(self):
        score = compute_score('baha dito', reaction_count=20)
        self.assertEqual(score, 0.0)


class CombinedSignalTests(SimpleTestCase):

    def test_full_emergency_post(self):
        text = 'tulong po may baha sa Bigben area, lampas tuhod na, may matanda kami dito di makalabas'
        score = compute_score(text)
        # distress(3) + flood_depth(2) + vulnerable(2) + stranded(2) = 9.0
        self.assertEqual(score, 9.0)

    def test_distress_plus_flood_depth(self):
        score = compute_score('tulong lampas tuhod na ang tubig')
        self.assertEqual(score, 5.0)


class ComputeScoreWithBreakdownTests(SimpleTestCase):

    def test_returns_tuple(self):
        result = compute_score_with_breakdown('tulong po')
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def test_score_matches_compute_score(self):
        text = 'tulong po may baha lampas tuhod may matanda di makalabas'
        score_simple = compute_score(text)
        score_breakdown, _ = compute_score_with_breakdown(text)
        self.assertEqual(score_simple, score_breakdown)

    def test_breakdown_has_all_keys(self):
        _, breakdown = compute_score_with_breakdown('test')
        for key in ('distress', 'flood_depth', 'vulnerable', 'stranded', 'image', 'reactions'):
            self.assertIn(key, breakdown)

    def test_breakdown_distress_fired(self):
        _, breakdown = compute_score_with_breakdown('tulong po kami')
        self.assertEqual(breakdown['distress'], 3.0)

    def test_breakdown_distress_not_fired(self):
        _, breakdown = compute_score_with_breakdown('magandang araw po')
        self.assertEqual(breakdown['distress'], 0.0)

    def test_breakdown_flood_depth_fired(self):
        _, breakdown = compute_score_with_breakdown('lampas tuhod na ang baha')
        self.assertEqual(breakdown['flood_depth'], 2.0)

    def test_breakdown_vulnerable_fired(self):
        _, breakdown = compute_score_with_breakdown('may matanda kami dito')
        self.assertEqual(breakdown['vulnerable'], 2.0)

    def test_breakdown_stranded_fired(self):
        _, breakdown = compute_score_with_breakdown('di makalabas ang mga tao')
        self.assertEqual(breakdown['stranded'], 2.0)

    def test_breakdown_image_fired(self):
        _, breakdown = compute_score_with_breakdown('test', has_image=True)
        self.assertEqual(breakdown['image'], 0.5)

    def test_breakdown_reactions_fired(self):
        _, breakdown = compute_score_with_breakdown('test', reaction_count=25)
        self.assertEqual(breakdown['reactions'], 0.5)

    def test_empty_text_breakdown_all_zeros(self):
        _, breakdown = compute_score_with_breakdown('')
        for v in breakdown.values():
            self.assertEqual(v, 0.0)
