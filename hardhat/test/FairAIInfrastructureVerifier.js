const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("FairAIInfrastructureVerifier", function () {
  it("supports the explicitly ungated B2 ledger lifecycle", async function () {
    const [owner, submitter] = await ethers.getSigners();
    const Verifier = await ethers.getContractFactory("FairAIInfrastructureVerifier");
    const verifier = await Verifier.deploy();
    await verifier.waitForDeployment();
    expect(await verifier.verifyProof("0x", [])).to.equal(true);

    const Ledger = await ethers.getContractFactory("FairAIEthicalLedger");
    const ledger = await Ledger.deploy();
    await ledger.waitForDeployment();
    await ledger.setVerifierContract(await verifier.getAddress());
    await ledger.grantRole(await ledger.VERIFIER_ROLE(), submitter.address);
    await ledger.createRound(1);
    const node = ethers.encodeBytes32String("node-0");
    await ledger.registerNode(node);
    await ledger.connect(submitter).submitModel(
      node,
      1,
      "bafy-b2-model",
      "bafy-b2-proof-na",
      "bafy-b2-public-na",
      "bafy-b2-metadata",
      "bafy-b2-metrics",
      "bafy-b2-manifest",
      "0x",
      [],
    );
    expect(await ledger.getEligibleModelCids(1)).to.deep.equal(["bafy-b2-model"]);
    const record = await ledger.getRecord(node, 1);
    expect(record.submitter).to.equal(submitter.address);
    expect(record.approvalStatus).to.equal(1);
    expect(await ledger.owner()).to.equal(owner.address);
  });
});
