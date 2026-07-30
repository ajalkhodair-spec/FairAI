const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("FairAISignedVerifierV2", function () {
  const types = {
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

  async function fixture() {
    const [owner, signer, attacker] = await ethers.getSigners();
    const Factory = await ethers.getContractFactory("FairAISignedVerifierV2");
    const verifier = await Factory.deploy(signer.address);
    await verifier.waitForDeployment();
    const network = await ethers.provider.getNetwork();
    const domain = {
      name: "FairAISignedVerifier",
      version: "2",
      chainId: network.chainId,
      verifyingContract: await verifier.getAddress(),
    };
    const block = await ethers.provider.getBlock("latest");
    const decision = {
      nodeId: ethers.id("node-1"),
      roundId: 7,
      policyVersion: (1n << 32n),
      manifestHash: ethers.sha256(ethers.toUtf8Bytes("manifest")),
      metricsHash: ethers.sha256(ethers.toUtf8Bytes("metrics")),
      nonce: 1,
      proofVerified: true,
      policyPassed: true,
      decision: true,
      expiration: block.timestamp + 3600,
    };
    return { owner, signer, attacker, verifier, domain, decision };
  }

  it("accepts and consumes a valid domain-separated decision", async function () {
    const { signer, verifier, domain, decision } = await fixture();
    const signature = await signer.signTypedData(domain, types, decision);
    await expect(verifier.verifyDecision(decision, signature))
      .to.emit(verifier, "DecisionConsumed")
      .withArgs(
        await verifier.decisionDigest(decision),
        signer.address,
        decision.nodeId,
        decision.roundId,
        decision.nonce,
        true
      );
    expect(await verifier.usedNonces(signer.address, decision.nonce)).to.equal(true);
  });

  it("rejects unauthorized signers and changed signed fields", async function () {
    const { signer, attacker, verifier, domain, decision } = await fixture();
    const attackerSignature = await attacker.signTypedData(domain, types, decision);
    await expect(verifier.verifyDecision(decision, attackerSignature))
      .to.be.revertedWithCustomError(verifier, "UnauthorizedSigner");

    const signature = await signer.signTypedData(domain, types, decision);
    const mutations = [
      { nodeId: ethers.id("node-2") },
      { roundId: 8 },
      { policyVersion: (2n << 32n) },
      { manifestHash: ethers.sha256(ethers.toUtf8Bytes("other-manifest")) },
      { metricsHash: ethers.sha256(ethers.toUtf8Bytes("other-metrics")) },
      { decision: false },
    ];
    for (const mutation of mutations) {
      await expect(verifier.verifyDecision({ ...decision, ...mutation }, signature))
        .to.be.revertedWithCustomError(verifier, "UnauthorizedSigner");
    }
  });

  it("binds chain ID and verifying contract", async function () {
    const { signer, verifier, domain, decision } = await fixture();
    const wrongChain = await signer.signTypedData(
      { ...domain, chainId: domain.chainId + 1n },
      types,
      decision
    );
    await expect(verifier.verifyDecision(decision, wrongChain))
      .to.be.revertedWithCustomError(verifier, "UnauthorizedSigner");

    const wrongContract = await signer.signTypedData(
      { ...domain, verifyingContract: ethers.Wallet.createRandom().address },
      types,
      decision
    );
    await expect(verifier.verifyDecision(decision, wrongContract))
      .to.be.revertedWithCustomError(verifier, "UnauthorizedSigner");
  });

  it("rejects expiration, nonce reuse, and exact replay", async function () {
    const { signer, verifier, domain, decision } = await fixture();
    const expired = { ...decision, expiration: 1 };
    const expiredSignature = await signer.signTypedData(domain, types, expired);
    await expect(verifier.verifyDecision(expired, expiredSignature))
      .to.be.revertedWithCustomError(verifier, "DecisionExpired");

    const signature = await signer.signTypedData(domain, types, decision);
    await verifier.verifyDecision(decision, signature);
    await expect(verifier.verifyDecision(decision, signature))
      .to.be.revertedWithCustomError(verifier, "DecisionDigestAlreadyUsed");

    const sameNonce = {
      ...decision,
      roundId: decision.roundId + 1,
      manifestHash: ethers.sha256(ethers.toUtf8Bytes("new-manifest")),
    };
    const sameNonceSignature = await signer.signTypedData(domain, types, sameNonce);
    await expect(verifier.verifyDecision(sameNonce, sameNonceSignature))
      .to.be.revertedWithCustomError(verifier, "NonceAlreadyUsed");
  });

  it("rejects signatures after signer revocation", async function () {
    const { owner, signer, verifier, domain, decision } = await fixture();
    const signature = await signer.signTypedData(domain, types, decision);
    await verifier.connect(owner).setSignerAuthorization(signer.address, false);
    await expect(verifier.verifyDecision(decision, signature))
      .to.be.revertedWithCustomError(verifier, "UnauthorizedSigner");
  });

  it("rejects malformed signatures and public-signal mismatches", async function () {
    const { signer, verifier, domain, decision } = await fixture();
    await expect(verifier.verifyDecision(decision, "0x1234"))
      .to.be.revertedWithCustomError(verifier, "InvalidSignature");

    const signature = await signer.signTypedData(domain, types, decision);
    const encodedProof = ethers.AbiCoder.defaultAbiCoder().encode(
      [
        "tuple(bytes32 nodeId,uint256 roundId,uint64 policyVersion,bytes32 manifestHash,bytes32 metricsHash,uint256 nonce,bool proofVerified,bool policyPassed,bool decision,uint256 expiration)",
        "bytes",
      ],
      [decision, signature]
    );
    await expect(
      verifier.verifyProof(encodedProof, [BigInt(decision.nodeId), decision.roundId + 1])
    ).to.be.revertedWithCustomError(verifier, "PublicSignalMismatch");
  });

  it("demonstrates the authorized-key compromise trust limitation", async function () {
    const { signer, verifier, domain, decision } = await fixture();
    const falseButSignedClaim = {
      ...decision,
      manifestHash: ethers.sha256(ethers.toUtf8Bytes("attacker-controlled-manifest")),
      metricsHash: ethers.sha256(ethers.toUtf8Bytes("fabricated-passing-metrics")),
      nonce: 404,
    };
    const compromisedKeySignature = await signer.signTypedData(
      domain,
      types,
      falseButSignedClaim
    );
    await expect(verifier.verifyDecision(falseButSignedClaim, compromisedKeySignature))
      .to.emit(verifier, "DecisionConsumed");
  });
});
