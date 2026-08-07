import unittest

from fairai_revision.run import parse_mocha_passes


class RevisionRunHelperTests(unittest.TestCase):
    def test_parse_mocha_passes_ignores_suite_and_summary_lines(self):
        output = """
FairAIV2CompositeVerifier
  ✔ accepts a real proof (48ms)
  ✔ rejects replay

2 passing (91ms)
"""
        self.assertEqual(
            parse_mocha_passes(output),
            ["accepts a real proof (48ms)", "rejects replay"],
        )


if __name__ == "__main__":
    unittest.main()
