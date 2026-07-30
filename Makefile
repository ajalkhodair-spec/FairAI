.PHONY: test revision-smoke revision-baseline revision-core revision-scaling \
	revision-fairness revision-security revision-ipfs revision-report revision-all

test:
	python3 -m unittest discover -s tests -v
	cd hardhat && npm test

revision-smoke:
	python3 -m fairai_revision.run \
		--config configs/revision/smoke.yaml \
		--run-id revision-smoke \
		--resume

revision-baseline:
	python3 -m fairai_revision.run \
		--config configs/revision/legacy_mvp.yaml \
		--run-id legacy_mvp

revision-core:
	python3 -m fairai_revision.run --config configs/revision/adult_core.yaml
	python3 -m fairai_revision.run --config configs/revision/compas_core.yaml

revision-scaling:
	python3 -m fairai_revision.run --config configs/revision/scaling.yaml

revision-fairness:
	python3 -m fairai_revision.run --config configs/revision/threshold_sensitivity.yaml

revision-security:
	python3 -m fairai_revision.run --config configs/revision/verifier_security.yaml
	python3 -m fairai_revision.run --config configs/revision/adversarial.yaml

revision-ipfs:
	python3 -m fairai_revision.run --config configs/revision/ipfs_benchmark.yaml

revision-report:
	python3 -m fairai_revision.run --config configs/revision/full_revision_matrix.yaml

revision-all: test revision-smoke revision-baseline revision-core revision-scaling \
	revision-fairness revision-security revision-ipfs revision-report
