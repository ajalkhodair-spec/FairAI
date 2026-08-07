const fs = require("fs");
const path = require("path");
const { ethers } = require("hardhat");
const v2Proof = require("../test/fixtures/v2_valid_proof.json");
const v2PublicSignals = require("../test/fixtures/v2_valid_public.json");

const nodeId = (value) => ethers.keccak256(ethers.toUtf8Bytes(value));

async function gasOf(transaction) {
  const receipt = await transaction.wait();
  return Number(receipt.gasUsed);
}

async function main() {
  const outputPath = process.env.FAIRAI_GAS_OUTPUT;
  if (!outputPath) {
    throw new Error("FAIRAI_GAS_OUTPUT is required");
  }
  const repetitions = Number(process.env.FAIRAI_GAS_REPETITIONS || "30");
  const batchSizes = JSON.parse(
    process.env.FAIRAI_GAS_BATCH_SIZES || "[1,5,10,20]"
  );
  const [owner, verifierSigner, secondarySigner] = await ethers.getSigners();
  const rows = [];

  const V2Verifier = await ethers.getContractFactory(
    "FairnessEligibilityV2Groth16Verifier"
  );
  const v2Verifier = await V2Verifier.deploy();
  rows.push({
    batch_size: 0,
    repetition: 0,
    operation: "deploy_v2_groth16_verifier",
    gas_used: await gasOf(v2Verifier.deploymentTransaction()),
  });
  const pA = [v2Proof.pi_a[0], v2Proof.pi_a[1]];
  const pB = [
    [v2Proof.pi_b[0][1], v2Proof.pi_b[0][0]],
    [v2Proof.pi_b[1][1], v2Proof.pi_b[1][0]],
  ];
  const pC = [v2Proof.pi_c[0], v2Proof.pi_c[1]];
  if (!(await v2Verifier.verifyProof(pA, pB, pC, v2PublicSignals))) {
    throw new Error("Tracked V2 proof failed before gas measurement");
  }
  const verificationData = v2Verifier.interface.encodeFunctionData(
    "verifyProof",
    [pA, pB, pC, v2PublicSignals]
  );
  for (let repetition = 1; repetition <= repetitions; repetition += 1) {
    rows.push({
      batch_size: 0,
      repetition,
      operation: "verify_v2_groth16",
      gas_used: await gasOf(
        await owner.sendTransaction({
          to: await v2Verifier.getAddress(),
          data: verificationData,
        })
      ),
    });
  }

  const MockVerifier = await ethers.getContractFactory("FairAIZKVerifierMock");
  const proofVerifier = await MockVerifier.deploy();
  rows.push({
    batch_size: 0,
    repetition: 0,
    operation: "deploy_mock_verifier",
    gas_used: await gasOf(proofVerifier.deploymentTransaction()),
  });

  const Ledger = await ethers.getContractFactory("FairAIEthicalLedger");
  const ledger = await Ledger.deploy();
  rows.push({
    batch_size: 0,
    repetition: 0,
    operation: "deploy_ledger",
    gas_used: await gasOf(ledger.deploymentTransaction()),
  });
  rows.push({
    batch_size: 0,
    repetition: 0,
    operation: "set_verifier_contract",
    gas_used: await gasOf(
      await ledger.setVerifierContract(await proofVerifier.getAddress())
    ),
  });
  rows.push({
    batch_size: 0,
    repetition: 0,
    operation: "grant_verifier_role",
    gas_used: await gasOf(
      await ledger.grantRole(
        await ledger.VERIFIER_ROLE(),
        verifierSigner.address
      )
    ),
  });

  const SignedVerifier = await ethers.getContractFactory(
    "FairAISignedVerifierV2"
  );
  const signedVerifier = await SignedVerifier.deploy(verifierSigner.address);
  rows.push({
    batch_size: 0,
    repetition: 0,
    operation: "deploy_signed_verifier_v2",
    gas_used: await gasOf(signedVerifier.deploymentTransaction()),
  });

  for (const batchSize of batchSizes) {
    for (let repetition = 1; repetition <= repetitions; repetition += 1) {
      const roundId = batchSize * 100000 + repetition;
      rows.push({
        batch_size: batchSize,
        repetition,
        operation: "create_round",
        gas_used: await gasOf(await ledger.createRound(roundId)),
      });
      const modelCids = [];
      for (let client = 0; client < batchSize; client += 1) {
        const suffix = `${batchSize}-${repetition}-${client}`;
        const id = nodeId(`node-${suffix}`);
        rows.push({
          batch_size: batchSize,
          repetition,
          operation: "register_node",
          gas_used: await gasOf(await ledger.registerNode(id)),
        });
        const proof = ethers.toUtf8Bytes(`proof-${suffix}`);
        const digest = ethers.toBigInt(ethers.sha256(proof)).toString();
        const publicSignals = [
          950,
          10,
          620,
          280,
          76,
          80,
          20,
          40,
          21,
          40,
          1,
          roundId,
          digest,
        ];
        const modelCid = `bafy-model-${suffix}`;
        rows.push({
          batch_size: batchSize,
          repetition,
          operation: "submit_model",
          gas_used: await gasOf(
            await ledger.connect(verifierSigner).submitModel(
              id,
              roundId,
              modelCid,
              `bafy-proof-${suffix}`,
              `bafy-public-${suffix}`,
              `bafy-metadata-${suffix}`,
              `bafy-metrics-${suffix}`,
              `bafy-manifest-${suffix}`,
              proof,
              publicSignals
            )
          ),
        });
        modelCids.push(modelCid);
      }
      rows.push({
        batch_size: batchSize,
        repetition,
        operation: "close_submissions",
        gas_used: await gasOf(await ledger.closeSubmissions(roundId)),
      });
      rows.push({
        batch_size: batchSize,
        repetition,
        operation: "start_aggregation",
        gas_used: await gasOf(await ledger.startAggregation(roundId)),
      });
      rows.push({
        batch_size: batchSize,
        repetition,
        operation: "publish_global_model",
        gas_used: await gasOf(
          await ledger.publishGlobalModel(
            roundId,
            `bafy-global-${batchSize}-${repetition}`,
            `bafy-report-${batchSize}-${repetition}`,
            modelCids
          )
        ),
      });
      rows.push({
        batch_size: batchSize,
        repetition,
        operation: "archive_round",
        gas_used: await gasOf(await ledger.archiveRound(roundId)),
      });
    }
  }

  for (let repetition = 1; repetition <= repetitions; repetition += 1) {
    rows.push({
      batch_size: 0,
      repetition,
      operation: "authorize_signer",
      gas_used: await gasOf(
        await signedVerifier.setSignerAuthorization(
          secondarySigner.address,
          true
        )
      ),
    });
    rows.push({
      batch_size: 0,
      repetition,
      operation: "revoke_signer",
      gas_used: await gasOf(
        await signedVerifier.setSignerAuthorization(
          secondarySigner.address,
          false
        )
      ),
    });
  }

  const result = {
    schema_version: "fairai.gas_benchmark.v1",
    chain_id: Number((await ethers.provider.getNetwork()).chainId),
    hardhat_network: true,
    repetitions,
    batch_sizes: batchSizes,
    rows,
  };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify({ outputPath, rows: rows.length })}\n`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
