from base.constants import ACTIVE_LANGUAGES
from django.test import SimpleTestCase, tag  # noqa: F401
from panta import constants


class LanguageTests(SimpleTestCase):
    codes = sorted([l[0] for l in ACTIVE_LANGUAGES])

    def test_required_approvals(self):
        self.assertEqual(list(constants.REQUIRED_APPROVALS), self.codes)

    def test_smarty_pants_variables(self):
        self.assertEqual(list(constants.SMARTY_PANTS_ATTRS), self.codes)
        self.assertTrue(set(constants.SMARTY_PANTS_MAPPING) <= set(self.codes))

    def test_language_ratios(self):
        self.assertEqual(set(constants.LANGUAGE_RATIOS), set(self.codes))
