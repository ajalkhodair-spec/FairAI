require("@nomicfoundation/hardhat-toolbox");

const accounts = process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [];

module.exports = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
      viaIR: true,
    },
  },
  overrides: {
    "contracts/FairnessEligibilityGroth16Verifier.sol": {
      version: "0.8.20",
      settings: {
        optimizer: {
          enabled: true,
          runs: 200,
        },
        viaIR: false,
      },
    },
  },
  networks: {
    hardhat: {},
    localhost: {
      url: process.env.LOCAL_RPC_URL || "http://127.0.0.1:8545",
    },
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "",
      accounts,
    },
  },
};
