const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const signers = await hre.ethers.getSigners();
  const [deployer, verifierSigner, owner2, owner3] = signers;

  const SignedVerifier = await hre.ethers.getContractFactory("FairAISignedVerifier");
  const signedVerifier = await SignedVerifier.deploy(verifierSigner.address);
  await signedVerifier.waitForDeployment();

  const Groth16Verifier = await hre.ethers.getContractFactory("Groth16Verifier");
  const groth16Verifier = await Groth16Verifier.deploy();
  await groth16Verifier.waitForDeployment();

  const Adapter = await hre.ethers.getContractFactory("FairAIGroth16VerifierAdapter");
  const groth16Adapter = await Adapter.deploy(await groth16Verifier.getAddress());
  await groth16Adapter.waitForDeployment();

  const multisigOwners = [deployer.address, owner2.address, owner3.address];
  const Multisig = await hre.ethers.getContractFactory("FairAIMultisigAdmin");
  const multisig = await Multisig.deploy(multisigOwners, 2);
  await multisig.waitForDeployment();

  const Ledger = await hre.ethers.getContractFactory("FairAIEthicalLedger");
  const ledger = await Ledger.deploy();
  await ledger.waitForDeployment();
  await (await ledger.setVerifierContract(await signedVerifier.getAddress())).wait();
  await (await ledger.grantRole(await ledger.ADMIN_ROLE(), await multisig.getAddress())).wait();

  const deployment = {
    network: hre.network.name,
    chain_id: Number((await hre.ethers.provider.getNetwork()).chainId),
    deployer: deployer.address,
    ledger: await ledger.getAddress(),
    signed_verifier: await signedVerifier.getAddress(),
    signed_verifier_signer: verifierSigner.address,
    groth16_verifier: await groth16Verifier.getAddress(),
    groth16_adapter: await groth16Adapter.getAddress(),
    multisig_admin: await multisig.getAddress(),
    multisig_owners: multisigOwners,
    multisig_threshold: 2,
    roles: {
      admin: await ledger.ADMIN_ROLE(),
      node_operator: await ledger.NODE_OPERATOR_ROLE(),
      verifier: await ledger.VERIFIER_ROLE(),
      aggregator: await ledger.AGGREGATOR_ROLE(),
    },
  };

  const outputDir = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(outputDir, { recursive: true });
  fs.writeFileSync(
    path.join(outputDir, `${hre.network.name}.json`),
    JSON.stringify(deployment, null, 2)
  );
  console.log(JSON.stringify(deployment, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
