const readline = require("readline");
const hre = require("hardhat");

const PREFIX = "FAIRAI_JSON:";
const decisionTypes = {
  Decision: [
    { name: "nodeId", type: "bytes32" },
    { name: "roundId", type: "uint256" },
    { name: "policyVersion", type: "uint64" },
    { name: "manifestHash", type: "bytes32" },
    { name: "metricsHash", type: "bytes32" },
    { name: "nonce", type: "uint256" },
    { name: "proofVerified", type: "bool" },
    { name: "policyPassed", type: "bool" },
    { name: "decision", type: "bool" },
    { name: "expiration", type: "uint256" },
  ],
};

function respond(value) {
  process.stdout.write(`${PREFIX}${JSON.stringify(value)}\n`);
}

function numericNodeId(nodeId) {
  return hre.ethers.zeroPadValue(hre.ethers.toBeHex(nodeId), 32);
}

async function deploy() {
  const [, signer, submitter, aggregator] = await hre.ethers.getSigners();
  const Groth16 = await hre.ethers.getContractFactory("FairnessEligibilityV2Groth16Verifier");
  const groth16 = await Groth16.deploy();
  await groth16.waitForDeployment();
  const Signed = await hre.ethers.getContractFactory("FairAISignedVerifierV2");
  const signed = await Signed.deploy(signer.address);
  await signed.waitForDeployment();
  const Composite = await hre.ethers.getContractFactory("FairAIV2CompositeVerifier");
  const composite = await Composite.deploy(await groth16.getAddress(), await signed.getAddress());
  await composite.waitForDeployment();
  const Ledger = await hre.ethers.getContractFactory("FairAIEthicalLedger");
  const ledger = await Ledger.deploy();
  await ledger.waitForDeployment();
  await (await ledger.setVerifierContract(await composite.getAddress())).wait();
  await (await ledger.grantRole(await ledger.VERIFIER_ROLE(), submitter.address)).wait();
  await (await ledger.grantRole(await ledger.AGGREGATOR_ROLE(), aggregator.address)).wait();
  const network = await hre.ethers.provider.getNetwork();
  return {
    signer,
    submitter,
    aggregator,
    groth16,
    signed,
    composite,
    ledger,
    registered: new Set(),
    domain: {
      name: "FairAISignedVerifier",
      version: "2",
      chainId: network.chainId,
      verifyingContract: await signed.getAddress(),
    },
  };
}

async function submitRound(state, command) {
  const roundId = command.round_id;
  await (await state.ledger.createRound(roundId)).wait();
  const block = await hre.ethers.provider.getBlock("latest");
  const records = [];
  for (const submission of command.submissions) {
    if (!state.registered.has(submission.node_id)) {
      await (await state.ledger.registerNode(numericNodeId(submission.node_id))).wait();
      state.registered.add(submission.node_id);
    }
    const decision = {
      nodeId: numericNodeId(submission.node_id),
      roundId,
      policyVersion: BigInt(submission.policy_version),
      manifestHash: `0x${submission.manifest_hash}`,
      metricsHash: `0x${submission.metrics_hash}`,
      nonce: submission.nonce,
      proofVerified: submission.approved,
      policyPassed: submission.approved,
      decision: submission.approved,
      expiration: block.timestamp + 3600,
    };
    const signature = await state.signer.signTypedData(state.domain, decisionTypes, decision);
    const p = submission.groth16_proof;
    const encoded = hre.ethers.AbiCoder.defaultAbiCoder().encode(
      [
        "uint256[2]", "uint256[2][2]", "uint256[2]",
        "tuple(bytes32 nodeId,uint256 roundId,uint64 policyVersion,bytes32 manifestHash,bytes32 metricsHash,uint256 nonce,bool proofVerified,bool policyPassed,bool decision,uint256 expiration)",
        "bytes",
      ],
      [p.pA, p.pB, p.pC, decision, signature],
    );
    const receipt = await (await state.ledger.connect(state.submitter).submitModel(
      decision.nodeId,
      roundId,
      submission.cids.model,
      submission.cids.proof,
      submission.cids.public,
      submission.cids.metadata,
      submission.cids.metrics,
      submission.cids.manifest,
      encoded,
      submission.public_signals,
    )).wait();
    const record = await state.ledger.getRecord(decision.nodeId, roundId);
    records.push({
      node_id: submission.node_id,
      approval_status: Number(record.approvalStatus) === 1 ? "Approved" : "Rejected",
      verification_status: Number(record.verificationStatus) === 1 ? "Valid" : "Invalid",
      model_cid: record.modelCid,
      tx_hash: receipt.hash,
      gas_used: receipt.gasUsed.toString(),
    });
  }
  await (await state.ledger.closeSubmissions(roundId)).wait();
  const eligible = await state.ledger.getEligibleModelCids(roundId);
  return {
    round_id: roundId,
    records,
    eligible_model_cids: [...eligible],
    state: "SubmissionClosed",
  };
}

async function publishRound(state, command) {
  const roundId = command.round_id;
  await (await state.ledger.connect(state.aggregator).startAggregation(roundId)).wait();
  const receipt = await (await state.ledger.connect(state.aggregator).publishGlobalModel(
    roundId,
    command.global_model_cid,
    command.report_cid,
    command.participant_model_cids,
  )).wait();
  await (await state.ledger.archiveRound(roundId)).wait();
  return {
    round_id: roundId,
    publication_gas_used: receipt.gasUsed.toString(),
    final_state: "Archived",
  };
}

async function cancelRound(state, command) {
  const reasonCode = hre.ethers.id(command.reason).slice(0, 66);
  const receipt = await (await state.ledger.cancelRoundWithReason(command.round_id, reasonCode)).wait();
  return {
    round_id: command.round_id,
    reason: command.reason,
    reason_code: reasonCode,
    cancellation_tx_hash: receipt.hash,
    cancellation_gas_used: receipt.gasUsed.toString(),
    final_state: "Cancelled",
  };
}

async function main() {
  const state = await deploy();
  respond({
    status: "ready",
    network: hre.network.name,
    chain_id: Number(state.domain.chainId),
    contract_address: await state.ledger.getAddress(),
    groth16_verifier_address: await state.groth16.getAddress(),
    signed_verifier_address: await state.signed.getAddress(),
    composite_verifier_address: await state.composite.getAddress(),
  });
  const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of input) {
    if (!line.trim()) continue;
    try {
      const command = JSON.parse(line);
      if (command.action === "submit_round") respond({ status: "ok", result: await submitRound(state, command) });
      else if (command.action === "publish_round") respond({ status: "ok", result: await publishRound(state, command) });
      else if (command.action === "cancel_round") respond({ status: "ok", result: await cancelRound(state, command) });
      else if (command.action === "close") {
        respond({ status: "closed" });
        input.close();
        break;
      } else throw new Error(`Unsupported action: ${command.action}`);
    } catch (error) {
      respond({ status: "error", error: error.stack || String(error) });
    }
  }
}

main().catch((error) => {
  respond({ status: "fatal", error: error.stack || String(error) });
  process.exitCode = 1;
});
