import unittest

from fairai_revision.ipfs import (
    StrictIPFSError,
    deterministic_payload,
    verify_payload,
)


class RevisionIPFSTests(unittest.TestCase):
    def test_payload_generation_is_deterministic_and_exact_size(self):
        first = deterministic_payload(11, 1024, 3)
        second = deterministic_payload(11, 1024, 3)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 1024)
        self.assertNotEqual(first, deterministic_payload(12, 1024, 3))

    def test_retrieval_validation_fails_closed(self):
        payload = deterministic_payload(11, 128, 1)
        verify_payload(payload, payload, "bafy-test")
        altered = payload[:-1] + bytes([payload[-1] ^ 0xFF])
        with self.assertRaisesRegex(StrictIPFSError, "differ"):
            verify_payload(payload, altered, "bafy-test")


if __name__ == "__main__":
    unittest.main()
