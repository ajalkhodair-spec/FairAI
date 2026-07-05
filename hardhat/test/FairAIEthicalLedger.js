const { expect } = require("chai");
const { ethers } = require("hardhat");

const nodeId = (name) => ethers.encodeBytes32String(name);

async function submitModel(ledger, signer, node, round, suffix, proofVerified) {
  const proof = ethers.toUtf8Bytes(`proof-${suffix}`);
  const digest = ethers.toBigInt(ethers.sha256(proof)).toString();
  const publicSignals = proofVerified
    ? [950, 10, 620, 280, 76, 80, 20, 40, 21, 40, 1, round, digest]
    : [950, 290, 620, 280, 76, 80, 20, 40, 31, 40, 1, round, digest];
  return ledger.connect(signer).submitModel(
    nodeId(node),
    round,
    `bafy-model-${suffix}`,
    `bafy-proof-${suffix}`,
    `bafy-public-${suffix}`,
    `bafy-metadata-${suffix}`,
    `bafy-metrics-${suffix}`,
    `bafy-manifest-${suffix}`,
    proof,
    publicSignals
  );
}

describe("FairAIEthicalLedger", function () {
  async function deployFixture() {
    const [owner, verifier, otherAccount] = await ethers.getSigners();
    const Verifier = await ethers.getContractFactory("FairAIZKVerifierMock");
    const proofVerifier = await Verifier.deploy();
    await proofVerifier.waitForDeployment();
    const Ledger = await ethers.getContractFactory("FairAIEthicalLedger");
    const ledger = await Ledger.deploy();
    await ledger.waitForDeployment();
    await ledger.setVerifierContract(await proofVerifier.getAddress());
    await ledger.grantRole(await ledger.VERIFIER_ROLE(), verifier.address);
    return { ledger, owner, verifier, otherAccount, proofVerifier };
  }

  it("registers nodes by node-operator role only", async function () {
    const { ledger, verifier } = await deployFixture();
    await expect(ledger.registerNode(nodeId("node-1")))
      .to.emit(ledger, "NodeRegistered")
      .withArgs(nodeId("node-1"), await ledger.owner());

    await expect(ledger.connect(verifier).registerNode(nodeId("node-2")))
      .to.be.revertedWithCustomError(ledger, "MissingRole");
  });

  it("approves verified model CIDs and exposes eligible models", async function () {
    const { ledger, verifier } = await deployFixture();
    await ledger.createRound(1);
    await ledger.registerNode(nodeId("node-1"));

    await expect(submitModel(ledger, verifier, "node-1", 1, "1", true))
      .to.emit(ledger, "AuditLogged");

    const record = await ledger.getRecord(nodeId("node-1"), 1);
    expect(record.verificationStatus).to.equal(1);
    expect(record.approvalStatus).to.equal(1);
    expect(record.modelCid).to.equal("bafy-model-1");
    expect(record.manifestCid).to.equal("bafy-manifest-1");

    expect(await ledger.getEligibleModelCids(1)).to.deep.equal(["bafy-model-1"]);
  });

  it("rejects unverified proofs and excludes them from eligible models", async function () {
    const { ledger, verifier } = await deployFixture();
    await ledger.createRound(1);
    await ledger.registerNode(nodeId("node-2"));

    await submitModel(ledger, verifier, "node-2", 1, "2", false);

    const record = await ledger.getRecord(nodeId("node-2"), 1);
    expect(record.verificationStatus).to.equal(2);
    expect(record.approvalStatus).to.equal(2);
    expect(await ledger.getEligibleModelCids(1)).to.deep.equal([]);
  });

  it("rejects unregistered nodes, duplicate submissions, empty CIDs, and reused CIDs", async function () {
    const { ledger, verifier } = await deployFixture();
    await ledger.createRound(1);

    await expect(ledger.connect(verifier).submitModel(
      nodeId("missing"),
      1,
      "bafy-model-x",
      "bafy-proof-x",
      "bafy-public-x",
      "bafy-metadata-x",
      "bafy-metrics-x",
      "bafy-manifest-x",
      "0x01",
      [950, 10, 620, 280, 76, 80, 20, 40, 21, 40, 1, 1, "1"]
    )).to.be.revertedWithCustomError(ledger, "NodeNotRegistered");

    await ledger.registerNode(nodeId("node-1"));
    await expect(ledger.connect(verifier).submitModel(
      nodeId("node-1"),
      1,
      "",
      "bafy-proof-1",
      "bafy-public-1",
      "bafy-metadata-1",
      "bafy-metrics-1",
      "bafy-manifest-1",
      "0x01",
      [950, 10, 620, 280, 76, 80, 20, 40, 21, 40, 1, 1, "1"]
    )).to.be.revertedWithCustomError(ledger, "EmptyCid");

    await submitModel(ledger, verifier, "node-1", 1, "1", true);

    await expect(submitModel(ledger, verifier, "node-1", 1, "1b", true))
      .to.be.revertedWithCustomError(ledger, "DuplicateSubmission");

    await ledger.registerNode(nodeId("node-2"));
    await expect(ledger.connect(verifier).submitModel(
      nodeId("node-2"),
      1,
      "bafy-model-1",
      "bafy-proof-2",
      "bafy-public-2",
      "bafy-metadata-2",
      "bafy-metrics-2",
      "bafy-manifest-2",
      "0x01",
      [950, 10, 620, 280, 76, 80, 20, 40, 21, 40, 1, 1, "1"]
    )).to.be.revertedWithCustomError(ledger, "DuplicateCid");
  });

  it("publishes a global model only with approved participant models", async function () {
    const { ledger, verifier } = await deployFixture();
    await ledger.createRound(1);
    await ledger.registerNode(nodeId("node-1"));
    await ledger.registerNode(nodeId("node-2"));
    await submitModel(ledger, verifier, "node-1", 1, "1", true);
    await submitModel(ledger, verifier, "node-2", 1, "2", false);

    await expect(ledger.publishGlobalModel(1, "bafy-global-1", "bafy-report-1", ["bafy-model-2"]))
      .to.be.revertedWithCustomError(ledger, "InvalidRoundState");

    await ledger.closeSubmissions(1);
    await ledger.startAggregation(1);

    await expect(ledger.publishGlobalModel(1, "bafy-global-1", "bafy-report-1", ["bafy-model-2"]))
      .to.be.revertedWithCustomError(ledger, "ParticipantNotApproved");

    await expect(ledger.publishGlobalModel(1, "bafy-global-1", "bafy-report-1", ["bafy-model-1"]))
      .to.emit(ledger, "GlobalModelPublished")
      .withArgs(1, "bafy-global-1", "bafy-report-1", await ledger.owner(), 1);

    const globalRecord = await ledger.getGlobalModel(1);
    expect(globalRecord.globalModelCid).to.equal("bafy-global-1");
    expect(globalRecord.reportCid).to.equal("bafy-report-1");
    expect(globalRecord.participantModelCids).to.deep.equal(["bafy-model-1"]);

    await expect(ledger.publishGlobalModel(1, "bafy-global-2", "bafy-report-2", ["bafy-model-1"]))
      .to.be.revertedWithCustomError(ledger, "InvalidRoundState");
  });

  it("enforces verifier authorization and round lifecycle", async function () {
    const { ledger, verifier, otherAccount } = await deployFixture();
    await ledger.registerNode(nodeId("node-1"));

    await expect(submitModel(ledger, verifier, "node-1", 1, "1", true))
      .to.be.revertedWithCustomError(ledger, "InvalidRoundState");

    await ledger.createRound(1);
    await expect(submitModel(ledger, otherAccount, "node-1", 1, "1", true))
      .to.be.revertedWithCustomError(ledger, "MissingRole");

    await submitModel(ledger, verifier, "node-1", 1, "1", true);
    await ledger.closeSubmissions(1);

    await expect(submitModel(ledger, verifier, "node-1", 1, "1b", true))
      .to.be.revertedWithCustomError(ledger, "InvalidRoundState");

    await ledger.startAggregation(1);
    await ledger.publishGlobalModel(1, "bafy-global-1", "bafy-report-1", ["bafy-model-1"]);
    await ledger.archiveRound(1);
    expect(await ledger.roundStates(1)).to.equal(5);
  });

  it("hardens role and verifier administration", async function () {
    const { ledger, owner, verifier, otherAccount } = await deployFixture();
    const adminRole = await ledger.ADMIN_ROLE();
    const verifierRole = await ledger.VERIFIER_ROLE();

    await expect(ledger.grantRole(verifierRole, ethers.ZeroAddress))
      .to.be.revertedWithCustomError(ledger, "ZeroAddress");

    await expect(ledger.setVerifierContract(ethers.ZeroAddress))
      .to.be.revertedWithCustomError(ledger, "ZeroAddress");

    await expect(ledger.setVerifierContract(otherAccount.address))
      .to.be.revertedWithCustomError(ledger, "ContractAddressRequired");

    await expect(ledger.revokeRole(adminRole, owner.address))
      .to.be.revertedWithCustomError(ledger, "NoAdminRemaining");

    await ledger.grantRole(adminRole, verifier.address);
    await ledger.revokeRole(adminRole, owner.address);
    expect(await ledger.hasRole(adminRole, verifier.address)).to.equal(true);
    expect(await ledger.hasRole(adminRole, owner.address)).to.equal(false);
  });
});
