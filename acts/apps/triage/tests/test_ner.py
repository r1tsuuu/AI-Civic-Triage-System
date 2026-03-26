"""
Unit tests for apps/triage/ner.py — location extraction, alias map, and geocoding.
Network calls (Nominatim) are mocked throughout.
"""
from unittest.mock import patch, MagicMock
from django.test import SimpleTestCase
from apps.triage.ner import geocode, extract_locations, _ALIAS_MAP


class AliasMapTests(SimpleTestCase):
    """Verify the alias map contains all required entries from CONSTITUTION.md §16."""

    def _assert_alias(self, alias, expected_canonical):
        self.assertIn(alias.lower(), _ALIAS_MAP,
                      msg=f"Alias '{alias}' missing from _ALIAS_MAP")
        self.assertEqual(_ALIAS_MAP[alias.lower()], expected_canonical)

    def test_dlsl(self):
        self._assert_alias('dlsl', 'De La Salle Lipa')

    def test_dls(self):
        self._assert_alias('dls', 'De La Salle Lipa')

    def test_de_la_salle(self):
        self._assert_alias('de la salle', 'De La Salle Lipa')

    def test_cathedral(self):
        self._assert_alias('cathedral', 'Metropolitan Cathedral of San Sebastian')

    def test_san_sebastian(self):
        self._assert_alias('san sebastian', 'Metropolitan Cathedral of San Sebastian')

    def test_sm(self):
        self._assert_alias('sm', 'SM City Lipa')

    def test_sm_lipa(self):
        self._assert_alias('sm lipa', 'SM City Lipa')

    def test_robinsons(self):
        self._assert_alias('robinsons', 'Robinsons Place Lipa')

    def test_robinson(self):
        self._assert_alias('robinson', 'Robinsons Place Lipa')

    def test_bigben(self):
        self._assert_alias('bigben', 'Bigben Commercial Center')

    def test_big_ben(self):
        self._assert_alias('big ben', 'Bigben Commercial Center')

    def test_palengke(self):
        self._assert_alias('palengke', 'Lipa City Public Market')

    def test_merkado(self):
        self._assert_alias('merkado', 'Lipa City Public Market')

    def test_market(self):
        self._assert_alias('market', 'Lipa City Public Market')

    def test_bayan(self):
        self._assert_alias('bayan', 'Lipa City Hall')

    def test_city_hall(self):
        self._assert_alias('city hall', 'Lipa City Hall')

    def test_sports_complex(self):
        self._assert_alias('sports complex', 'Lipa City Sports Complex')

    def test_ospital(self):
        self._assert_alias('ospital', 'Ospital ng Lipa')

    def test_hospital(self):
        self._assert_alias('hospital', 'Ospital ng Lipa')


class GeocodeAliasResolutionTests(SimpleTestCase):
    """Alias resolution fires before gazetteer lookup."""

    def _make_gazetteer(self):
        return {
            'SM City Lipa': (13.9297, 121.1703),
            'Bigben Commercial Center': (13.9411, 121.1624),
            'Lipa City Hall': (13.9420, 121.1628),
            'De La Salle Lipa': (13.9544, 121.1631),
            'Ospital ng Lipa': (13.9359, 121.1692),
        }

    def test_sm_alias_resolves_to_coordinates(self):
        with patch('apps.triage.ner._get_gazetteer', return_value=self._make_gazetteer()):
            lat, lon, conf = geocode('SM')
        self.assertIsNotNone(lat)
        self.assertEqual(conf, 'high')

    def test_bigben_alias_resolves_to_coordinates(self):
        with patch('apps.triage.ner._get_gazetteer', return_value=self._make_gazetteer()):
            lat, lon, conf = geocode('Bigben')
        self.assertIsNotNone(lat)
        self.assertEqual(conf, 'high')

    def test_dlsl_alias_resolves_to_coordinates(self):
        with patch('apps.triage.ner._get_gazetteer', return_value=self._make_gazetteer()):
            lat, lon, conf = geocode('DLSL')
        self.assertIsNotNone(lat)
        self.assertEqual(conf, 'high')

    def test_ospital_alias_resolves_to_coordinates(self):
        with patch('apps.triage.ner._get_gazetteer', return_value=self._make_gazetteer()):
            lat, lon, conf = geocode('Ospital')
        self.assertIsNotNone(lat)
        self.assertEqual(conf, 'high')

    def test_alias_case_insensitive(self):
        with patch('apps.triage.ner._get_gazetteer', return_value=self._make_gazetteer()):
            lat, lon, conf = geocode('SM LIPA')
        self.assertIsNotNone(lat)
        self.assertEqual(conf, 'high')


class GeocodeGazetteerTests(SimpleTestCase):
    """Direct gazetteer hits (no alias, canonical name)."""

    def _make_gazetteer(self):
        return {'Lipa City Hall': (13.9420, 121.1628)}

    def test_canonical_name_returns_high_confidence(self):
        with patch('apps.triage.ner._get_gazetteer', return_value=self._make_gazetteer()):
            lat, lon, conf = geocode('Lipa City Hall')
        self.assertEqual(conf, 'high')
        self.assertAlmostEqual(lat, 13.9420, places=3)
        self.assertAlmostEqual(lon, 121.1628, places=3)

    def test_no_match_falls_through_to_nominatim(self):
        with patch('apps.triage.ner._get_gazetteer', return_value={}), \
             patch('apps.triage.ner.requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = [{'lat': '13.94', 'lon': '121.16'}]
            mock_get.return_value = mock_resp
            lat, lon, conf = geocode('Some Unknown Place')
        self.assertEqual(conf, 'medium')
        self.assertIsNotNone(lat)


class GeocodeFailureTests(SimpleTestCase):

    def test_nominatim_failure_returns_unresolved(self):
        with patch('apps.triage.ner._get_gazetteer', return_value={}), \
             patch('apps.triage.ner.requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 500
            mock_resp.json.return_value = []
            mock_get.return_value = mock_resp
            lat, lon, conf = geocode('Nowhere')
        self.assertIsNone(lat)
        self.assertIsNone(lon)
        self.assertEqual(conf, 'unresolved')

    def test_nominatim_empty_results_returns_unresolved(self):
        with patch('apps.triage.ner._get_gazetteer', return_value={}), \
             patch('apps.triage.ner.requests.get') as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = []
            mock_get.return_value = mock_resp
            lat, lon, conf = geocode('Nowhere Known')
        self.assertIsNone(lat)
        self.assertEqual(conf, 'unresolved')

    def test_network_exception_returns_unresolved(self):
        with patch('apps.triage.ner._get_gazetteer', return_value={}), \
             patch('apps.triage.ner.requests.get', side_effect=Exception('timeout')):
            lat, lon, conf = geocode('Some Place')
        self.assertIsNone(lat)
        self.assertEqual(conf, 'unresolved')

    def test_geocode_never_raises(self):
        with patch('apps.triage.ner._get_gazetteer', side_effect=Exception('boom')):
            try:
                result = geocode('anywhere')
            except Exception:
                self.fail('geocode() raised an exception to the caller')


class ExtractLocationsTests(SimpleTestCase):

    def test_returns_list(self):
        result = extract_locations('baha sa Lipa City')
        self.assertIsInstance(result, list)

    def test_empty_text_returns_empty_list(self):
        result = extract_locations('')
        self.assertEqual(result, [])

    def test_never_raises_on_bad_input(self):
        with patch('apps.triage.ner._get_nlp', side_effect=Exception('model crash')):
            try:
                result = extract_locations('some text')
                self.assertEqual(result, [])
            except Exception:
                self.fail('extract_locations() raised an exception to the caller')

    def test_deduplicates_locations(self):
        mock_nlp = MagicMock()
        mock_doc = MagicMock()
        ent = MagicMock()
        ent.text = 'Lipa'
        ent.label_ = 'LOC'
        mock_doc.ents = [ent, ent]  # same entity twice
        mock_nlp.return_value = mock_doc
        with patch('apps.triage.ner._get_nlp', return_value=mock_nlp):
            result = extract_locations('Lipa Lipa')
        self.assertEqual(result.count('Lipa'), 1)
