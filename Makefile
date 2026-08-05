.PHONY: test revision-smoke revision-baseline revision-partitions revision-core revision-scaling \
	revision-algorithmic-scaling revision-fairfed revision-fairness revision-security revision-ipfs \
	revision-ipfs-native revision-ipfs-recovery revision-kubo-v2 revision-kubo-v2-adversarial \
	revision-proof azure-validate revision-report revision-all

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

revision-partitions:
	$(PYTHON) -m fairai_revision.run \
		--config configs/revision/heterogeneity.yaml \
		--run-id heterogeneity-partitions

revision-core:
	$(PYTHON) -m fairai_revision.run --config configs/revision/adult_core.yaml
	$(PYTHON) -m fairai_revision.run --config configs/revision/compas_core.yaml

revision-scaling:
	$(PYTHON) -m fairai_revision.run --config configs/revision/scaling.yaml

revision-algorithmic-scaling:
	$(PYTHON) -m fairai_revision.run --config configs/revision/scaling_algorithmic.yaml

revision-fairfed:
	$(PYTHON) -m fairai_revision.run --config configs/revision/adult_fairfed.yaml
	$(PYTHON) -m fairai_revision.run --config configs/revision/compas_fairfed.yaml

revision-fairness:
	$(PYTHON) -m fairai_revision.run --config configs/revision/threshold_sensitivity.yaml

revision-security:
	$(PYTHON) -m fairai_revision.run --config configs/revision/verifier_security.yaml
	$(PYTHON) -m fairai_revision.run --config configs/revision/adversarial.yaml

revision-ipfs:
	$(PYTHON) -m fairai_revision.run --config configs/revision/ipfs_benchmark.yaml

revision-ipfs-native:
	$(PYTHON) -m fairai_revision.run --config configs/revision/ipfs_benchmark_native.yaml

revision-ipfs-recovery:
	$(PYTHON) -m fairai_revision.run --config configs/revision/ipfs_recovery_native.yaml

revision-kubo-v2:
	$(PYTHON) -m fairai_revision.run --config configs/revision/kubo_v2_bounded.yaml

revision-kubo-v2-adversarial:
	$(PYTHON) -m fairai_revision.run --config configs/revision/kubo_v2_adversarial.yaml

revision-proof:
	$(PYTHON) -m fairai_revision.run --config configs/revision/proof_binding.yaml

BICEP ?= bicep
azure-validate:
	DOTNET_BUNDLE_EXTRACT_BASE_DIR=$${DOTNET_BUNDLE_EXTRACT_BASE_DIR:-/tmp/bicep-cache} \
		$(BICEP) build azure/main.bicep --outfile /tmp/fairai-azure-template.json

revision-report:
	$(PYTHON) -m fairai_revision.run --config configs/revision/full_revision_matrix.yaml

revision-all: test revision-smoke revision-baseline revision-partitions revision-core revision-scaling \
	revision-fairness revision-security revision-ipfs revision-report
