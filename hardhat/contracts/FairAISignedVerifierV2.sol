// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract FairAISignedVerifierV2 {
    struct Decision {
        bytes32 nodeId;
        uint256 roundId;
        uint64 policyVersion;
        bytes32 manifestHash;
        bytes32 metricsHash;
        uint256 nonce;
        bool proofVerified;
        bool policyPassed;
        bool decision;
        uint256 expiration;
    }

    bytes32 public constant DECISION_TYPEHASH = keccak256(
        "Decision(bytes32 nodeId,uint256 roundId,uint64 policyVersion,bytes32 manifestHash,bytes32 metricsHash,uint256 nonce,bool proofVerified,bool policyPassed,bool decision,uint256 expiration)"
    );
    bytes32 private constant DOMAIN_TYPEHASH = keccak256(
        "EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
    );
    bytes32 private constant NAME_HASH = keccak256("FairAISignedVerifier");
    bytes32 private constant VERSION_HASH = keccak256("2");
    uint256 private constant SECP256K1_HALF_ORDER =
        0x7fffffffffffffffffffffffffffffff5d576e7357a4501ddfe92f46681b20a0;

    address public owner;
    mapping(address => bool) public authorizedSigners;
    mapping(address => mapping(uint256 => bool)) public usedNonces;
    mapping(bytes32 => bool) public usedDecisionDigests;

    event SignerAuthorizationChanged(address indexed signer, bool authorized);
    event DecisionConsumed(
        bytes32 indexed digest,
        address indexed signer,
        bytes32 indexed nodeId,
        uint256 roundId,
        uint256 nonce,
        bool approved
    );

    error OnlyOwner();
    error ZeroAddress();
    error DecisionExpired(uint256 expiration, uint256 currentTimestamp);
    error UnauthorizedSigner(address signer);
    error NonceAlreadyUsed(address signer, uint256 nonce);
    error DecisionDigestAlreadyUsed(bytes32 digest);
    error InvalidSignature();
    error PublicSignalMismatch();

    constructor(address initialSigner) {
        if (initialSigner == address(0)) revert ZeroAddress();
        owner = msg.sender;
        authorizedSigners[initialSigner] = true;
        emit SignerAuthorizationChanged(initialSigner, true);
    }

    modifier onlyOwner() {
        if (msg.sender != owner) revert OnlyOwner();
        _;
    }

    function setSignerAuthorization(
        address signer,
        bool authorized
    ) external onlyOwner {
        if (signer == address(0)) revert ZeroAddress();
        authorizedSigners[signer] = authorized;
        emit SignerAuthorizationChanged(signer, authorized);
    }

    function domainSeparator() public view returns (bytes32) {
        return keccak256(
            abi.encode(
                DOMAIN_TYPEHASH,
                NAME_HASH,
                VERSION_HASH,
                block.chainid,
                address(this)
            )
        );
    }

    function decisionStructHash(
        Decision calldata decisionData
    ) public pure returns (bytes32) {
        return keccak256(
            abi.encode(
                DECISION_TYPEHASH,
                decisionData.nodeId,
                decisionData.roundId,
                decisionData.policyVersion,
                decisionData.manifestHash,
                decisionData.metricsHash,
                decisionData.nonce,
                decisionData.proofVerified,
                decisionData.policyPassed,
                decisionData.decision,
                decisionData.expiration
            )
        );
    }

    function decisionDigest(
        Decision calldata decisionData
    ) public view returns (bytes32) {
        return keccak256(
            abi.encodePacked(
                "\x19\x01",
                domainSeparator(),
                decisionStructHash(decisionData)
            )
        );
    }

    function verifyDecision(
        Decision calldata decisionData,
        bytes calldata signature
    ) public returns (bool approved) {
        if (block.timestamp > decisionData.expiration) {
            revert DecisionExpired(decisionData.expiration, block.timestamp);
        }
        bytes32 digest = decisionDigest(decisionData);
        if (usedDecisionDigests[digest]) {
            revert DecisionDigestAlreadyUsed(digest);
        }
        address signer = _recover(digest, signature);
        if (!authorizedSigners[signer]) revert UnauthorizedSigner(signer);
        if (usedNonces[signer][decisionData.nonce]) {
            revert NonceAlreadyUsed(signer, decisionData.nonce);
        }

        usedDecisionDigests[digest] = true;
        usedNonces[signer][decisionData.nonce] = true;
        approved =
            decisionData.proofVerified &&
            decisionData.policyPassed &&
            decisionData.decision;
        emit DecisionConsumed(
            digest,
            signer,
            decisionData.nodeId,
            decisionData.roundId,
            decisionData.nonce,
            approved
        );
    }

    function verifyProof(
        bytes calldata proof,
        uint256[] calldata publicSignals
    ) external returns (bool) {
        (Decision memory decisionData, bytes memory signature) = abi.decode(
            proof,
            (Decision, bytes)
        );
        if (
            publicSignals.length < 2 ||
            publicSignals[0] != uint256(decisionData.nodeId) ||
            publicSignals[1] != decisionData.roundId
        ) revert PublicSignalMismatch();
        return this.verifyDecision(decisionData, signature);
    }

    function _recover(
        bytes32 digest,
        bytes memory signature
    ) private pure returns (address) {
        if (signature.length != 65) revert InvalidSignature();
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := mload(add(signature, 32))
            s := mload(add(signature, 64))
            v := byte(0, mload(add(signature, 96)))
        }
        if (uint256(s) > SECP256K1_HALF_ORDER || (v != 27 && v != 28)) {
            revert InvalidSignature();
        }
        address recovered = ecrecover(digest, v, r, s);
        if (recovered == address(0)) revert InvalidSignature();
        return recovered;
    }
}
