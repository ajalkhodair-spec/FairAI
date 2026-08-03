const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

function requireEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

function numericNodeId(nodeId) {
  return hre.ethers.zeroPadValue(hre.ethers.toBeHex(nodeId), 32);
}

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

async function main() {
  const inputPath = path.resolve(requireEnv("FAIRAI_CONTRACT_INPUT"));
  const outputPath = path.resolve(requireEnv("FAIRAI_CONTRACT_OUTPUT"));
  const input = JSON.parse(fs.readFileSync(inputPath, "utf8"));
  if (input.verifier_mode !== "v2_groth16_eip712") {
    throw new Error("This runner is restricted to the B4/B7 V2 verifier path");
  }
  const [owner, signer, submitter, aggregator] = await hre.ethers.getSigners();
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
  const domain = {
    name: "FairAISignedVerifier",
    version: "2",
    chainId: network.chainId,
    verifyingContract: await signed.getAddress(),
  };
  const allNodeIds = [...new Set(input.rounds.flatMap((round) => round.submissions.map((item) => item.node_id)))];
  for (const nodeId of allNodeIds) await (await ledger.registerNode(numericNodeId(nodeId))).wait();

  const roundResults = [];
  for (const roundInput of input.rounds) {
    await (await ledger.createRound(roundInput.round_id)).wait();
    const block = await hre.ethers.provider.getBlock("latest");
    const records = [];
    for (const submission of roundInput.submissions) {
      const decision = {
        nodeId: numericNodeId(submission.node_id),
        roundId: roundInput.round_id,
        policyVersion: BigInt(submission.policy_version),
        manifestHash: `0x${submission.manifest_hash}`,
        metricsHash: `0x${submission.metrics_hash}`,
        nonce: submission.nonce,
        proofVerified: submission.approved,
        policyPassed: submission.approved,
        decision: submission.approved,
        expiration: block.timestamp + 3600,
      };
      const signature = await signer.signTypedData(domain, decisionTypes, decision);
      const p = submission.groth16_proof;
      const encoded = hre.ethers.AbiCoder.defaultAbiCoder().encode(
        [
          "uint256[2]", "uint256[2][2]", "uint256[2]",
          "tuple(bytes32 nodeId,uint256 roundId,uint64 policyVersion,bytes32 manifestHash,bytes32 metricsHash,uint256 nonce,bool proofVerified,bool policyPassed,bool decision,uint256 expiration)",
          "bytes",
        ],
        [p.pA, p.pB, p.pC, decision, signature],
      );
      const receipt = await (await ledger.connect(submitter).submitModel(
        decision.nodeId,
        roundInput.round_id,
        submission.cids.model,
        submission.cids.proof,
        submission.cids.public,
        submission.cids.metadata,
        submission.cids.metrics,
        submission.cids.manifest,
        encoded,
        submission.public_signals,
      )).wait();
      const record = await ledger.getRecord(decision.nodeId, roundInput.round_id);
      records.push({
        node_id: submission.node_id,
        approval_status: Number(record.approvalStatus) === 1 ? "Approved" : "Rejected",
        model_cid: record.modelCid,
        tx_hash: receipt.hash,
        gas_used: receipt.gasUsed.toString(),
      });
    }
    const eligible = await ledger.getEligibleModelCids(roundInput.round_id);
    const expected = JSON.stringify([...roundInput.global_publication.participant_model_cids].sort());
    if (JSON.stringify([...eligible].sort()) !== expected) {
      throw new Error(`V2 eligible CID mismatch in round ${roundInput.round_id}`);
    }
    await (await ledger.closeSubmissions(roundInput.round_id)).wait();
    let publicationGasUsed = null;
    let finalState;
    if (eligible.length === 0) {
      await (await ledger.cancelRound(roundInput.round_id)).wait();
      finalState = "Cancelled";
    } else {
      await (await ledger.connect(aggregator).startAggregation(roundInput.round_id)).wait();
      const publication = await (await ledger.connect(aggregator).publishGlobalModel(
        roundInput.round_id,
        roundInput.global_publication.global_model_cid,
        roundInput.global_publication.report_cid,
        roundInput.global_publication.participant_model_cids,
      )).wait();
      publicationGasUsed = publication.gasUsed.toString();
      await (await ledger.archiveRound(roundInput.round_id)).wait();
      finalState = "Archived";
    }
    roundResults.push({
      round_id: roundInput.round_id,
      records,
      eligible_model_cids: eligible,
      publication_gas_used: publicationGasUsed,
      final_state: finalState,
    });
  }
  const result = {
    verifier_mode: input.verifier_mode,
    network: hre.network.name,
    contract_address: await ledger.getAddress(),
    groth16_verifier_address: await groth16.getAddress(),
    signed_verifier_address: await signed.getAddress(),
    composite_verifier_address: await composite.getAddress(),
    rounds: roundResults,
  };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
