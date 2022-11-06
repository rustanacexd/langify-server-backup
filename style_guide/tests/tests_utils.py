from django.test import SimpleTestCase
from style_guide.utils import DiffConflictException, DiffParser, calculate_diff


class DiffParserTests(SimpleTestCase):
    def setUp(self) -> None:
        # all text has to be ended with new line (otherwise diff wouldn't work)
        self.original_text = '1\n2\n3\n4\n5\n6\n7\n8\n9\n'
        self.modified_text = '11\n22\n3\n4\n4\n4\n6\n9\n10\n11\n12\n'
        self.conflicted_text = '1\n3\n3\n4\n5\n6\n7\n8\n9\n'
        self.test_cases = (
            (self.original_text, '11\n22\n3\n4\n4\n4\n6\n9\n10\n11\n12\n'),
            (self.original_text, '11\n22\n3\n4\n4\n4\n9\n10\n11\n12\n'),
            (self.original_text, '3\n4\n5\n6\n7\n8\n9\n10\n11\n12\n'),
            ('1\n', '2\n'),
        )
        diff_text = calculate_diff(self.original_text, self.modified_text)
        self.diff = DiffParser(diff_text)

    def test_conflict_not_exists(self):
        self.assertFalse(self.diff.has_conflict(self.original_text))

    def test_conflict_exists(self):
        self.assertTrue(self.diff.has_conflict(self.conflicted_text))

    def test_conflict_raised(self):
        with self.assertRaises(DiffConflictException):
            self.diff.apply(self.conflicted_text)

    def test_diff_applied(self):
        self.assertEqual(
            self.diff.apply(self.original_text), self.modified_text
        )
        for original, modified in self.test_cases[1:]:
            diff_text = calculate_diff(original, modified)
            diff = DiffParser(diff_text)
            self.assertEqual(diff.apply(original), modified)
