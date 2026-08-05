import unittest

from fairai_revision.ipfs import (
    StrictIPFSError,
    concurrency_payload_seed,
    connect_two_peers,
    deterministic_payload,
    verify_payload,
)


class RevisionIPFSTests(unittest.TestCase):
    def test_concurrency_payload_seeds_do_not_overlap(self):
        sequential_seed = 11201
        observed = {
            concurrency_payload_seed(sequential_seed, concurrency, worker)
            for concurrency in (1, 5, 10, 20)
            for worker in range(concurrency)
        }
        self.assertEqual(len(observed), 36)
        self.assertNotIn(sequential_seed, observed)
        with self.assertRaises(ValueError):
            concurrency_payload_seed(sequential_seed, 5, 5)

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

    def test_peer_connection_supports_compose_dns_and_private_ip(self):
        publisher = Peer("publisher")
        consumer = Peer("consumer")
        connect_two_peers(publisher, consumer, "10.42.0.5")
        self.assertEqual(
            consumer.connected,
            "/ip4/10.42.0.5/tcp/4001/p2p/publisher",
        )
        connect_two_peers(publisher, consumer, "ipfs-publisher")
        self.assertEqual(
            consumer.connected,
            "/dns4/ipfs-publisher/tcp/4001/p2p/publisher",
        )


class Peer:
    def __init__(self, peer_id):
        self.peer_id = peer_id
        self.connected = None

    def identity(self):
        return {"ID": self.peer_id}

    def connect(self, address):
        self.connected = address


if __name__ == "__main__":
    unittest.main()
