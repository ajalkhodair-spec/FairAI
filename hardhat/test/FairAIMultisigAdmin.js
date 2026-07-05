const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("FairAIMultisigAdmin", function () {
  it("executes ledger admin calls after threshold approval", async function () {
    const [owner1, owner2, owner3] = await ethers.getSigners();
    const Multisig = await ethers.getContractFactory("FairAIMultisigAdmin");
    const multisig = await Multisig.deploy([owner1.address, owner2.address, owner3.address], 2);
    await multisig.waitForDeployment();

    const Verifier = await ethers.getContractFactory("FairAIZKVerifierMock");
    const verifier = await Verifier.deploy();
    await verifier.waitForDeployment();

    const Ledger = await ethers.getContractFactory("FairAIEthicalLedger");
    const ledger = await Ledger.deploy();
    await ledger.waitForDeployment();
    const adminRole = await ledger.ADMIN_ROLE();
    await ledger.grantRole(adminRole, await multisig.getAddress());

    const data = ledger.interface.encodeFunctionData("setVerifierContract", [await verifier.getAddress()]);
    const submit = await multisig.submitTransaction(await ledger.getAddress(), 0, data);
    const receipt = await submit.wait();
    const txId = receipt.logs
      .map((log) => {
        try {
          return multisig.interface.parseLog(log);
        } catch {
          return null;
        }
      })
      .find((log) => log && log.name === "TransactionSubmitted").args.txId;

    await multisig.approveTransaction(txId);
    await expect(multisig.executeTransaction(txId))
      .to.be.revertedWithCustomError(multisig, "InsufficientApprovals");
    await multisig.connect(owner2).approveTransaction(txId);
    await multisig.executeTransaction(txId);

    expect(await ledger.verifierContract()).to.equal(await verifier.getAddress());
  });
});
