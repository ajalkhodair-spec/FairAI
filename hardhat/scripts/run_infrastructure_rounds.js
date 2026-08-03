const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

function requireEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

function nodeIdBytes(nodeId) {
  return hre.ethers.encodeBytes32String(`node-${nodeId}`);
}

async function main() {
  const inputPath = path.resolve(requireEnv("FAIRAI_CONTRACT_INPUT"));
  const outputPath = path.resolve(requireEnv("FAIRAI_CONTRACT_OUTPUT"));
  const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
  if (input.verifier_mode !== "infrastructure_passthrough") {
    throw new Error("This runner is restricted to the B2 infrastructure baseline");
  }

  const [owner, submitter, aggregator] = await hre.ethers.getSigners();
  const Verifier = await hre.ethers.getContractFactory("FairAIInfrastructureVerifier");
  const verifier = await Verifier.deploy();
  await verifier.waitForDeployment();
  const Ledger = await hre.ethers.getContractFactory("FairAIEthicalLedger");
  const ledger = await Ledger.deploy();
  await ledger.waitForDeployment();
  await (await ledger.setVerifierContract(await verifier.getAddress())).wait();
  await (await ledger.grantRole(await ledger.VERIFIER_ROLE(), submitter.address)).wait();
  await (await ledger.grantRole(await ledger.AGGREGATOR_ROLE(), aggregator.address)).wait();

  const allNodeIds = [...new Set(input.rounds.flatMap((round) => round.submissions.map((item) => item.node_id)))];
  const registrations = [];
  for (const nodeId of allNodeIds) {
    const receipt = await (await ledger.registerNode(nodeIdBytes(nodeId))).wait();
    registrations.push({ node_id: nodeId, tx_hash: receipt.hash, gas_used: receipt.gasUsed.toString() });
  }

  const rounds = [];
  for (const roundInput of input.rounds) {
    const roundId = roundInput.round_id;
    await (await ledger.createRound(roundId)).wait();
    const records = [];
    for (const submission of roundInput.submissions) {
      const receipt = await (await ledger.connect(submitter).submitModel(
        nodeIdBytes(submission.node_id),
        roundId,
        submission.cids.model,
        submission.cids.proof,
        submission.cids.public,
        submission.cids.metadata,
        submission.cids.metrics,
        submission.cids.manifest,
        "0x",
        [],
      )).wait();
      const record = await ledger.getRecord(nodeIdBytes(submission.node_id), roundId);
      records.push({
        node_id: submission.node_id,
        model_cid: record.modelCid,
        approval_status: Number(record.approvalStatus) === 1 ? "Approved" : "Rejected",
        tx_hash: receipt.hash,
        block_number: Number(receipt.blockNumber),
        gas_used: receipt.gasUsed.toString(),
      });
    }
    const eligible = await ledger.getEligibleModelCids(roundId);
    const expected = JSON.stringify([...roundInput.global_publication.participant_model_cids].sort());
    const observed = JSON.stringify([...eligible].sort());
    if (expected !== observed) {
      throw new Error(`Eligible CID mismatch for round ${roundId}: expected=${expected} observed=${observed}`);
    }
    await (await ledger.closeSubmissions(roundId)).wait();
    await (await ledger.connect(aggregator).startAggregation(roundId)).wait();
    const publicationReceipt = await (await ledger.connect(aggregator).publishGlobalModel(
      roundId,
      roundInput.global_publication.global_model_cid,
      roundInput.global_publication.report_cid,
      roundInput.global_publication.participant_model_cids,
    )).wait();
    await (await ledger.archiveRound(roundId)).wait();
    rounds.push({
      round_id: roundId,
      records,
      eligible_model_cids: eligible,
      publication: {
        tx_hash: publicationReceipt.hash,
        block_number: Number(publicationReceipt.blockNumber),
        gas_used: publicationReceipt.gasUsed.toString(),
      },
      final_state: Number(await ledger.roundStates(roundId)) === 5 ? "Archived" : "Unexpected",
    });
  }

  const result = {
    verifier_mode: input.verifier_mode,
    network: hre.network.name,
    contract_address: await ledger.getAddress(),
    verifier_contract_address: await verifier.getAddress(),
    owner: owner.address,
    submitter: submitter.address,
    aggregator: aggregator.address,
    registrations,
    rounds,
  };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
