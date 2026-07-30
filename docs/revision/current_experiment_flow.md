# Current Experiment Flow

For each of three clients, the runner generates deterministic synthetic records,
trains a three-parameter logistic model, evaluates it on the same local
partition, creates a threshold proof, writes artifacts, uploads them through the
storage adapter, and validates the manifest.

The runner then identifies locally verified submissions, retrieves their model
artifacts, performs weighted FedAvg, evaluates on a deterministic global
validation set, uploads the global model and report, and invokes a fresh local
Hardhat deployment. The contract registers nodes, records signed decisions,
returns eligible CIDs, publishes the global model, and archives the round.

`scripts/run_experiments.py` repeats the same deterministic scenario three
times. The data and seeds do not vary by trial, so the repetitions primarily
measure runtime variation rather than independent statistical trials.

