import unittest

from scripts.analyze_adversarial_results import parse_bool


class AdversarialAnalysisTests(unittest.TestCase):
    def test_parse_bool_accepts_serialized_csv_values(self):
        for value in (True, "True", "true", "1", 1):
            self.assertTrue(parse_bool(value))
        for value in (False, "False", "false", "0", 0):
            self.assertFalse(parse_bool(value))

    def test_parse_bool_rejects_ambiguous_values(self):
        with self.assertRaisesRegex(ValueError, "Invalid boolean"):
            parse_bool("yes")


if __name__ == "__main__":
    unittest.main()
