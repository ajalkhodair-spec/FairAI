const fs = require("fs");
const path = require("path");
const { performance } = require("perf_hooks");
const { ethers } = require("hardhat");

const nodeId = (value) => ethers.keccak256(ethers.toUtf8Bytes(value));

function percentile(values, probability) {
  const sorted = [...values].sort((left, right) => left - right);
  const index = Math.ceil(probability * sorted.length) - 1;
  return sorted[Math.max(0, index)];
}

async function deployFixture() {
  const [owner, verifierSigner] = await ethers.getSigners();
  const MockVerifier = await ethers.getContractFactory("FairAIZKVerifierMock");
  const proofVerifier = await MockVerifier.deploy();
  await proofVerifier.waitForDeployment();
  const Ledger = await ethers.getContractFactory("FairAIEthicalLedger");
  const ledger = await Ledger.deploy();
  await ledger.waitForDeployment();
  await (await ledger.setVerifierContract(await proofVerifier.getAddress())).wait();
  await (
    await ledger.grantRole(
      await ledger.VERIFIER_ROLE(),
      verifierSigner.address
    )
  ).wait();
  return { ledger, verifierSigner };
}

function submissionArguments(roundId, suffix) {
  const proof = ethers.toUtf8Bytes(`proof-${suffix}`);
  const digest = ethers.toBigInt(ethers.sha256(proof)).toString();
  return [
    nodeId(`node-${suffix}`),
    roundId,
    `bafy-model-${suffix}`,
    `bafy-proof-${suffix}`,
    `bafy-public-${suffix}`,
    `bafy-metadata-${suffix}`,
    `bafy-metrics-${suffix}`,
    `bafy-manifest-${suffix}`,
    proof,
    [950, 10, 620, 280, 76, 80, 20, 40, 21, 40, 1, roundId, digest],
  ];
}

async function prepareRound(ledger, roundId, mode, concurrency, repetition) {
  await (await ledger.createRound(roundId)).wait();
  const argumentsByClient = [];
  for (let client = 0; client < concurrency; client += 1) {
    const suffix = `${mode}-${concurrency}-${repetition}-${client}`;
    const args = submissionArguments(roundId, suffix);
    await (await ledger.registerNode(args[0])).wait();
    argumentsByClient.push(args);
  }
  return argumentsByClient;
}

async function runSequential(ledger, signer, argsByClient) {
  const transactionRows = [];
  const started = performance.now();
  for (let client = 0; client < argsByClient.length; client += 1) {
    const transactionStarted = performance.now();
    const transaction = await ledger.connect(signer).submitModel(
      ...argsByClient[client]
    );
    const receipt = await transaction.wait();
    transactionRows.push({
      client,
      latency_ms: performance.now() - transactionStarted,
      gas_used: Number(receipt.gasUsed),
      status: Number(receipt.status),
    });
  }
  return { elapsedMs: performance.now() - started, transactionRows };
}

async function runConcurrent(ledger, signer, argsByClient) {
  const nonceSigner = new ethers.NonceManager(signer);
  const started = performance.now();
  const pending = await Promise.all(
    argsByClient.map((args) => ledger.connect(nonceSigner).submitModel(...args))
  );
  const receipts = await Promise.all(pending.map((transaction) => transaction.wait()));
  const elapsedMs = performance.now() - started;
  return {
    elapsedMs,
    transactionRows: receipts.map((receipt, client) => ({
      client,
      latency_ms: elapsedMs,
      gas_used: Number(receipt.gasUsed),
      status: Number(receipt.status),
    })),
  };
}

async function main() {
  const outputPath = process.env.FAIRAI_THROUGHPUT_OUTPUT;
  if (!outputPath) {
    throw new Error("FAIRAI_THROUGHPUT_OUTPUT is required");
  }
  const repetitions = Number(process.env.FAIRAI_GAS_REPETITIONS || "30");
  const concurrencyLevels = JSON.parse(
    process.env.FAIRAI_GAS_BATCH_SIZES || "[1,5,10,20]"
  );
  const { ledger, verifierSigner } = await deployFixture();
  const scenarios = [];
  const transactions = [];
  let roundId = 900000;

  for (const mode of ["sequential", "concurrent"]) {
    for (const concurrency of concurrencyLevels) {
      for (let repetition = 1; repetition <= repetitions; repetition += 1) {
        roundId += 1;
        const argsByClient = await prepareRound(
          ledger,
          roundId,
          mode,
          concurrency,
          repetition
        );
        const result = mode === "sequential"
          ? await runSequential(ledger, verifierSigner, argsByClient)
          : await runConcurrent(ledger, verifierSigner, argsByClient);
        const failures = result.transactionRows.filter(
          (row) => row.status !== 1
        ).length;
        const latencies = result.transactionRows.map((row) => row.latency_ms);
        scenarios.push({
          evidence_type: "measured_hardhat",
          mode,
          concurrency,
          repetition,
          transaction_count: concurrency,
          elapsed_ms: result.elapsedMs,
          transactions_per_second: concurrency / (result.elapsedMs / 1000),
          median_latency_ms: percentile(latencies, 0.5),
          p95_latency_ms: percentile(latencies, 0.95),
          failure_count: failures,
          failure_rate: failures / concurrency,
          total_gas: result.transactionRows.reduce(
            (sum, row) => sum + row.gas_used,
            0
          ),
        });
        for (const row of result.transactionRows) {
          transactions.push({
            mode,
            concurrency,
            repetition,
            round_id: roundId,
            ...row,
          });
        }
      }
    }
  }

  const result = {
    schema_version: "fairai.transaction_throughput.v1",
    chain_id: Number((await ethers.provider.getNetwork()).chainId),
    hardhat_network: true,
    repetitions,
    concurrency_levels: concurrencyLevels,
    scenarios,
    transactions,
  };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(result, null, 2)}\n`);
  process.stdout.write(
    `${JSON.stringify({ outputPath, scenarios: scenarios.length })}\n`
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
