const { expect } = require("chai");
const { ethers } = require("hardhat");
const proof = require("./fixtures/v2_valid_proof.json");
const publicSignals = require("./fixtures/v2_valid_public.json");

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

describe("FairAIV2CompositeVerifier", function () {
  async function fixture() {
    const [owner, signer, submitter] = await ethers.getSigners();
    const Groth16 = await ethers.getContractFactory("FairnessEligibilityV2Groth16Verifier");
    const groth16 = await Groth16.deploy();
    await groth16.waitForDeployment();
    const Signed = await ethers.getContractFactory("FairAISignedVerifierV2");
    const signed = await Signed.deploy(signer.address);
    await signed.waitForDeployment();
    const Composite = await ethers.getContractFactory("FairAIV2CompositeVerifier");
    const composite = await Composite.deploy(await groth16.getAddress(), await signed.getAddress());
    await composite.waitForDeployment();
    const Ledger = await ethers.getContractFactory("FairAIEthicalLedger");
    const ledger = await Ledger.deploy();
    await ledger.waitForDeployment();
    await ledger.setVerifierContract(await composite.getAddress());
    await ledger.grantRole(await ledger.VERIFIER_ROLE(), submitter.address);
    const block = await ethers.provider.getBlock("latest");
    const decision = {
      nodeId: ethers.zeroPadValue(ethers.toBeHex(1), 32),
      roundId: 1,
      policyVersion: 4294967296n,
      manifestHash: ethers.zeroPadValue(ethers.toBeHex(123), 32),
      metricsHash: ethers.zeroPadValue(ethers.toBeHex(456), 32),
      nonce: 1,
      proofVerified: true,
      policyPassed: true,
      decision: true,
      expiration: block.timestamp + 3600,
    };
    const network = await ethers.provider.getNetwork();
    const domain = {
      name: "FairAISignedVerifier",
      version: "2",
      chainId: network.chainId,
      verifyingContract: await signed.getAddress(),
    };
    const signature = await signer.signTypedData(domain, decisionTypes, decision);
    const pA = [proof.pi_a[0], proof.pi_a[1]];
    const pB = [
      [proof.pi_b[0][1], proof.pi_b[0][0]],
      [proof.pi_b[1][1], proof.pi_b[1][0]],
    ];
    const pC = [proof.pi_c[0], proof.pi_c[1]];
    const encoded = ethers.AbiCoder.defaultAbiCoder().encode(
      [
        "uint256[2]",
        "uint256[2][2]",
        "uint256[2]",
        "tuple(bytes32 nodeId,uint256 roundId,uint64 policyVersion,bytes32 manifestHash,bytes32 metricsHash,uint256 nonce,bool proofVerified,bool policyPassed,bool decision,uint256 expiration)",
        "bytes",
      ],
      [pA, pB, pC, decision, signature],
    );
    return { owner, signer, submitter, composite, signed, ledger, domain, decision, encoded };
  }

  it("accepts a real V2 proof only with its bound signed decision", async function () {
    const { signer, submitter, signed, ledger, decision, encoded } = await fixture();
    await ledger.createRound(1);
    await ledger.registerNode(decision.nodeId);
    await ledger.connect(submitter).submitModel(
      decision.nodeId,
      1,
      "bafy-v2-model",
      "bafy-v2-proof",
      "bafy-v2-public",
      "bafy-v2-metadata",
      "bafy-v2-metrics",
      "bafy-v2-manifest",
      encoded,
      publicSignals,
    );
    const record = await ledger.getRecord(decision.nodeId, 1);
    expect(record.approvalStatus).to.equal(1);
    expect(await signed.usedNonces(signer.address, 1)).to.equal(true);
  });

  it("rejects ledger context changes and signed-decision replay", async function () {
    const { submitter, composite, signed, ledger, decision, encoded } = await fixture();
    await ledger.createRound(1);
    const wrongNode = ethers.zeroPadValue(ethers.toBeHex(2), 32);
    await ledger.registerNode(wrongNode);
    await expect(ledger.connect(submitter).submitModel(
      wrongNode,
      1,
      "bafy-wrong-model",
      "bafy-wrong-proof",
      "bafy-wrong-public",
      "bafy-wrong-metadata",
      "bafy-wrong-metrics",
      "bafy-wrong-manifest",
      encoded,
      publicSignals,
    )).to.be.revertedWithCustomError(ledger, "PublicSignalContextMismatch");

    await ledger.registerNode(decision.nodeId);
    await ledger.connect(submitter).submitModel(
      decision.nodeId, 1,
      "bafy-ok-model", "bafy-ok-proof", "bafy-ok-public",
      "bafy-ok-metadata", "bafy-ok-metrics", "bafy-ok-manifest",
      encoded, publicSignals,
    );
    await expect(composite.verifyProof(encoded, publicSignals))
      .to.be.revertedWithCustomError(signed, "DecisionDigestAlreadyUsed");
  });

  it("records a signed failed-proof decision as rejected", async function () {
    const { signer, submitter, signed, ledger, domain, decision } = await fixture();
    const rejectedDecision = {
      ...decision,
      proofVerified: false,
      policyPassed: false,
      decision: false,
    };
    const signature = await signer.signTypedData(domain, decisionTypes, rejectedDecision);
    const encoded = ethers.AbiCoder.defaultAbiCoder().encode(
      [
        "uint256[2]",
        "uint256[2][2]",
        "uint256[2]",
        "tuple(bytes32 nodeId,uint256 roundId,uint64 policyVersion,bytes32 manifestHash,bytes32 metricsHash,uint256 nonce,bool proofVerified,bool policyPassed,bool decision,uint256 expiration)",
        "bytes",
      ],
      [[0, 0], [[0, 0], [0, 0]], [0, 0], rejectedDecision, signature],
    );
    await ledger.createRound(1);
    await ledger.registerNode(decision.nodeId);
    await ledger.connect(submitter).submitModel(
      decision.nodeId, 1,
      "bafy-rejected-model", "bafy-rejected-proof", "bafy-rejected-public",
      "bafy-rejected-metadata", "bafy-rejected-metrics", "bafy-rejected-manifest",
      encoded, publicSignals,
    );
    const record = await ledger.getRecord(decision.nodeId, 1);
    expect(record.approvalStatus).to.equal(2);
    expect(record.verificationStatus).to.equal(2);
    expect(await signed.usedNonces(signer.address, 1)).to.equal(true);
  });

  it("rejects a malformed proof that is signed as verified", async function () {
    const { submitter, composite, ledger, decision, encoded } = await fixture();
    const types = [
      "uint256[2]",
      "uint256[2][2]",
      "uint256[2]",
      "tuple(bytes32 nodeId,uint256 roundId,uint64 policyVersion,bytes32 manifestHash,bytes32 metricsHash,uint256 nonce,bool proofVerified,bool policyPassed,bool decision,uint256 expiration)",
      "bytes",
    ];
    const decoded = ethers.AbiCoder.defaultAbiCoder().decode(types, encoded);
    const malformed = ethers.AbiCoder.defaultAbiCoder().encode(
      types,
      [[0, 0], [[0, 0], [0, 0]], [0, 0], decoded[3], decoded[4]],
    );
    await ledger.createRound(1);
    await ledger.registerNode(decision.nodeId);
    await expect(ledger.connect(submitter).submitModel(
      decision.nodeId, 1,
      "bafy-malformed-model", "bafy-malformed-proof", "bafy-malformed-public",
      "bafy-malformed-metadata", "bafy-malformed-metrics", "bafy-malformed-manifest",
      malformed, publicSignals,
    )).to.be.revertedWithCustomError(composite, "DecisionBindingMismatch");
    const record = await ledger.getRecord(decision.nodeId, 1);
    expect(record.timestamp).to.equal(0);
    expect(await ledger.getEligibleModelCids(1)).to.deep.equal([]);
  });
});
