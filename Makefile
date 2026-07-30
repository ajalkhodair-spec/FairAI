.PHONY: test revision-smoke revision-baseline revision-core revision-scaling \
	revision-fairness revision-security revision-ipfs revision-report revision-all

PYTHON ?= python3

test:
	$(PYTHON) -m unittest discover -s tests -v
	cd hardhat && npm test

revision-smoke:
	$(PYTHON) -m fairai_revision.run \
		--config configs/revision/smoke.yaml \
		--run-id revision-smoke \
		--resume

revision-baseline:
	$(PYTHON) -m fairai_revision.run \
		--config configs/revision/legacy_mvp.yaml \
		--run-id legacy_mvp

revision-core:
	$(PYTHON) -m fairai_revision.run --config configs/revision/adult_core.yaml
	$(PYTHON) -m fairai_revision.run --config configs/revision/compas_core.yaml

revision-scaling:
	$(PYTHON) -m fairai_revision.run --config configs/revision/scaling.yaml

revision-fairness:
	$(PYTHON) -m fairai_revision.run --config configs/revision/threshold_sensitivity.yaml

revision-security:
	$(PYTHON) -m fairai_revision.run --config configs/revision/verifier_security.yaml
	$(PYTHON) -m fairai_revision.run --config configs/revision/adversarial.yaml

revision-ipfs:
	$(PYTHON) -m fairai_revision.run --config configs/revision/ipfs_benchmark.yaml

revision-report:
	$(PYTHON) -m fairai_revision.run --config configs/revision/full_revision_matrix.yaml

revision-all: test revision-smoke revision-baseline revision-core revision-scaling \
	revision-fairness revision-security revision-ipfs revision-report
