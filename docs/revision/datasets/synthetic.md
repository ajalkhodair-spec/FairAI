# Synthetic Legacy Dataset

The legacy generator creates 80 binary-classification examples per client with
two numeric features and one binary protected-group value. Client-specific fixed
seeds are derived as `1000 + node_id`; the global validation seed is `4242`.

Client 3 receives a stronger group-dependent feature shift to exercise the
submitted demographic-parity threshold. This scenario is retained only for
regression and targeted attack tests. It is not evidence of real-world
generalization.

