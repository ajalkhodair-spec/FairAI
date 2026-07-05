// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract FairAISignedVerifier {
    address public immutable signer;

    error InvalidSignatureLength();

    constructor(address signer_) {
        require(signer_ != address(0), "signer required");
        signer = signer_;
    }

    function verifyProof(
        bytes calldata proof,
        uint256[] calldata publicSignals
    ) external view returns (bool) {
        if (proof.length == 0) {
            return false;
        }
        (bytes memory signature, bool approved) = abi.decode(proof, (bytes, bool));
        bytes32 publicSignalsHash = keccak256(abi.encode(publicSignals));
        bytes32 decisionHash = keccak256(abi.encode(address(this), publicSignalsHash, approved));
        bytes32 ethHash = keccak256(abi.encodePacked("\x19Ethereum Signed Message:\n32", decisionHash));
        return approved && _recover(ethHash, signature) == signer;
    }

    function _recover(bytes32 digest, bytes memory signature) private pure returns (address) {
        if (signature.length != 65) revert InvalidSignatureLength();
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        if (v < 27) {
            v += 27;
        }
        return ecrecover(digest, v, r, s);
    }
}
