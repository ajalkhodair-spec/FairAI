const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

const statusNames = {
  verification: ["Submitted", "Valid", "Invalid"],
  approval: ["Pending", "Approved", "Rejected"],
  round: ["Uncreated", "Open", "SubmissionClosed", "AggregationStarted", "Published", "Archived"],
};

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function nodeIdBytes(nodeId) {
  return hre.ethers.encodeBytes32String(`node-${nodeId}`);
}

async function proofCalldata(submission, verifierMode, proofVerifier, submitter) {
  if (verifierMode === "signed") {
    const approved = Boolean(submission.proof_verified);
    const publicSignalsHash = hre.ethers.keccak256(
      hre.ethers.AbiCoder.defaultAbiCoder().encode(["uint256[]"], [submission.contract_public_signals])
    );
    const decisionHash = hre.ethers.keccak256(
      hre.ethers.AbiCoder.defaultAbiCoder().encode(
        ["address", "bytes32", "bool"],
        [await proofVerifier.getAddress(), publicSignalsHash, approved]
      )
    );
    const signature = await submitter.signMessage(hre.ethers.getBytes(decisionHash));
    return hre.ethers.AbiCoder.defaultAbiCoder().encode(["bytes", "bool"], [signature, approved]);
  }
  if (!submission.groth16_proof) {
    if (verifierMode === "mock" && submission.contract_proof) {
      return `0x${submission.contract_proof}`;
    }
    return "0x";
  }
  const proof = submission.groth16_proof;
  return hre.ethers.AbiCoder.defaultAbiCoder().encode(
    ["uint256[2]", "uint256[2][2]", "uint256[2]"],
    [proof.pA, proof.pB, proof.pC],
  );
}

async function main() {
  const inputPath = path.resolve(requireEnv("FAIRAI_CONTRACT_INPUT"));
  const outputPath = path.resolve(requireEnv("FAIRAI_CONTRACT_OUTPUT"));
  const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));

  const [owner, submitter, aggregator] = await hre.ethers.getSigners();
  let proofVerifier;
  let verifierMode = input.verifier_mode || "signed";
  if (verifierMode === "mock") {
    const MockVerifier = await hre.ethers.getContractFactory("FairAIZKVerifierMock");
    proofVerifier = await MockVerifier.deploy();
    await proofVerifier.waitForDeployment();
  } else if (verifierMode === "groth16") {
    const Groth16Verifier = await hre.ethers.getContractFactory("Groth16Verifier");
    const generatedVerifier = await Groth16Verifier.deploy();
    await generatedVerifier.waitForDeployment();
    const Adapter = await hre.ethers.getContractFactory("FairAIGroth16VerifierAdapter");
    proofVerifier = await Adapter.deploy(await generatedVerifier.getAddress());
    await proofVerifier.waitForDeployment();
  } else if (verifierMode === "signed") {
    const SignedVerifier = await hre.ethers.getContractFactory("FairAISignedVerifier");
    proofVerifier = await SignedVerifier.deploy(submitter.address);
    await proofVerifier.waitForDeployment();
  } else {
    throw new Error(`Unsupported verifier_mode: ${verifierMode}`);
  }

  const Ledger = await hre.ethers.getContractFactory("FairAIEthicalLedger");
  const ledger = await Ledger.deploy();
  await ledger.waitForDeployment();
  await (await ledger.setVerifierContract(await proofVerifier.getAddress())).wait();
  await (await ledger.grantRole(await ledger.VERIFIER_ROLE(), submitter.address)).wait();
  await (await ledger.grantRole(await ledger.AGGREGATOR_ROLE(), aggregator.address)).wait();
  const createRoundTx = await ledger.createRound(input.round_id);
  await createRoundTx.wait();

  const nodeIds = [...new Set(input.submissions.map((submission) => submission.node_id))];
  const registeredNodes = [];
  for (const nodeId of nodeIds) {
    const tx = await ledger.registerNode(nodeIdBytes(nodeId));
    const receipt = await tx.wait();
    registeredNodes.push({
      node_id: nodeId,
      tx_hash: receipt.hash,
      block_number: Number(receipt.blockNumber),
    });
  }

  const records = [];
  for (const submission of input.submissions) {
    const tx = await ledger.connect(submitter).submitModel(
      nodeIdBytes(submission.node_id),
      submission.round_id,
      submission.cids.model,
      submission.cids.proof,
      submission.cids.public,
      submission.cids.metadata,
      submission.cids.metrics,
      submission.cids.manifest,
      await proofCalldata(submission, verifierMode, proofVerifier, submitter),
      submission.contract_public_signals,
    );
    const receipt = await tx.wait();
    const record = await ledger.getRecord(nodeIdBytes(submission.node_id), submission.round_id);
    records.push({
      node_id: submission.node_id,
      round_id: submission.round_id,
      model_cid: record.modelCid,
      proof_cid: record.proofCid,
      public_cid: record.publicCid,
      metadata_cid: record.metadataCid,
      metrics_cid: record.metricsCid,
      manifest_cid: record.manifestCid,
      verification_status: statusNames.verification[Number(record.verificationStatus)],
      approval_status: statusNames.approval[Number(record.approvalStatus)],
      submitter: record.submitter,
      timestamp: Number(record.timestamp),
      tx_hash: receipt.hash,
      block_number: Number(receipt.blockNumber),
      gas_used: receipt.gasUsed.toString(),
    });
  }

  const eligibleModelCids = await ledger.getEligibleModelCids(input.round_id);
  let globalPublication = null;
  if (input.global_publication) {
    await (await ledger.closeSubmissions(input.round_id)).wait();
    await (await ledger.connect(aggregator).startAggregation(input.round_id)).wait();
    const expected = JSON.stringify([...eligibleModelCids].sort());
    const submitted = JSON.stringify([...input.global_publication.participant_model_cids].sort());
    if (expected !== submitted) {
      throw new Error(`Global participant CIDs do not match contract eligible CIDs. expected=${expected} submitted=${submitted}`);
    }
    const tx = await ledger.connect(aggregator).publishGlobalModel(
      input.round_id,
      input.global_publication.global_model_cid,
      input.global_publication.report_cid,
      input.global_publication.participant_model_cids,
    );
    const receipt = await tx.wait();
    const record = await ledger.getGlobalModel(input.round_id);
    await (await ledger.archiveRound(input.round_id)).wait();
    globalPublication = {
      round_id: Number(record.roundId),
      global_model_cid: record.globalModelCid,
      report_cid: record.reportCid,
      participant_model_cids: record.participantModelCids,
      publisher: record.publisher,
      timestamp: Number(record.timestamp),
      tx_hash: receipt.hash,
      block_number: Number(receipt.blockNumber),
      gas_used: receipt.gasUsed.toString(),
    };
  }

  const auditEvents = (await ledger.queryFilter(ledger.filters.AuditLogged())).map((event) => ({
    node_id: hre.ethers.decodeBytes32String(event.args.nodeId),
    round_id: Number(event.args.roundId),
    verification_status: statusNames.verification[Number(event.args.verificationStatus)],
    approval_status: statusNames.approval[Number(event.args.approvalStatus)],
    model_cid: event.args.modelCid,
    proof_cid: event.args.proofCid,
    tx_hash: event.transactionHash,
    block_number: Number(event.blockNumber),
  }));
  const roundEvents = (await ledger.queryFilter(ledger.filters.RoundStateChanged())).map((event) => ({
    round_id: Number(event.args.roundId),
    state: statusNames.round[Number(event.args.state)],
    tx_hash: event.transactionHash,
    block_number: Number(event.blockNumber),
  }));

  const result = {
    contract_address: await ledger.getAddress(),
    verifier_contract_address: await proofVerifier.getAddress(),
    verifier_mode: verifierMode,
    network: hre.network.name,
    owner: owner.address,
    submitter: submitter.address,
    aggregator: aggregator.address,
    round_id: input.round_id,
    registered_nodes: registeredNodes,
    records,
    eligible_model_cids: eligibleModelCids,
    global_publication: globalPublication,
    audit_events: auditEvents,
    round_events: roundEvents,
    final_round_state: statusNames.round[Number(await ledger.roundStates(input.round_id))],
  };

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
