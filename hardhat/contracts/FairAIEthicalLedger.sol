// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IFairAIVerifier {
    function verifyProof(
        bytes calldata proof,
        uint256[] calldata publicSignals
    ) external returns (bool);
}

contract FairAIEthicalLedger {
    enum VerificationStatus {
        Submitted,
        Valid,
        Invalid
    }

    enum ApprovalStatus {
        Pending,
        Approved,
        Rejected
    }

    enum RoundState {
        Uncreated,
        Open,
        SubmissionClosed,
        AggregationStarted,
        Published,
        Archived,
        Cancelled
    }

    struct ModelRecord {
        bytes32 nodeId;
        uint256 roundId;
        string modelCid;
        string proofCid;
        string publicCid;
        string metadataCid;
        string metricsCid;
        string manifestCid;
        VerificationStatus verificationStatus;
        ApprovalStatus approvalStatus;
        address submitter;
        uint256 timestamp;
    }

    struct GlobalModelRecord {
        uint256 roundId;
        string globalModelCid;
        string reportCid;
        string[] participantModelCids;
        address publisher;
        uint256 timestamp;
    }

    bytes32 public constant ADMIN_ROLE = keccak256("ADMIN_ROLE");
    bytes32 public constant NODE_OPERATOR_ROLE = keccak256("NODE_OPERATOR_ROLE");
    bytes32 public constant VERIFIER_ROLE = keccak256("VERIFIER_ROLE");
    bytes32 public constant AGGREGATOR_ROLE = keccak256("AGGREGATOR_ROLE");

    address public owner;
    IFairAIVerifier public verifierContract;
    mapping(bytes32 => mapping(address => bool)) private roles;
    uint256 private adminCount;
    mapping(bytes32 => bool) public registeredNodes;
    mapping(uint256 => RoundState) public roundStates;
    mapping(bytes32 => ModelRecord) private records;
    mapping(uint256 => bytes32[]) private roundRecordKeys;
    mapping(uint256 => GlobalModelRecord) private globalModels;
    mapping(uint256 => mapping(string => bool)) private approvedModelCidsByRound;
    mapping(string => bool) private usedCids;

    event NodeRegistered(bytes32 indexed nodeId, address indexed registrar);
    event RoleGranted(bytes32 indexed role, address indexed account, address indexed sender);
    event RoleRevoked(bytes32 indexed role, address indexed account, address indexed sender);
    event VerifierContractUpdated(address indexed verifierContract);
    event RoundStateChanged(uint256 indexed roundId, RoundState state);
    event ModelSubmitted(
        bytes32 indexed nodeId,
        uint256 indexed roundId,
        string modelCid,
        string proofCid,
        string publicCid,
        string metadataCid,
        string metricsCid,
        string manifestCid,
        VerificationStatus verificationStatus,
        ApprovalStatus approvalStatus
    );
    event AuditLogged(
        bytes32 indexed nodeId,
        uint256 indexed roundId,
        VerificationStatus verificationStatus,
        ApprovalStatus approvalStatus,
        string modelCid,
        string proofCid
    );
    event GlobalModelPublished(
        uint256 indexed roundId,
        string globalModelCid,
        string reportCid,
        address indexed publisher,
        uint256 participantCount
    );

    error OnlyOwner();
    error MissingRole(bytes32 role, address account);
    error NodeNotRegistered(bytes32 nodeId);
    error DuplicateSubmission(bytes32 nodeId, uint256 roundId);
    error GlobalModelAlreadyPublished(uint256 roundId);
    error InvalidRoundState(uint256 roundId, RoundState expected, RoundState actual);
    error NoParticipants();
    error ParticipantNotApproved(string modelCid);
    error EmptyCid();
    error DuplicateCid(string cid);
    error InvalidProof();
    error VerifierContractNotSet();
    error ZeroAddress();
    error NoAdminRemaining();
    error ContractAddressRequired(address account);
    error PublicSignalContextMismatch();

    constructor() {
        owner = msg.sender;
        roles[ADMIN_ROLE][msg.sender] = true;
        roles[NODE_OPERATOR_ROLE][msg.sender] = true;
        roles[VERIFIER_ROLE][msg.sender] = true;
        roles[AGGREGATOR_ROLE][msg.sender] = true;
        adminCount = 1;
    }

    modifier onlyRole(bytes32 role) {
        if (!roles[role][msg.sender]) revert MissingRole(role, msg.sender);
        _;
    }

    modifier inRoundState(uint256 roundId, RoundState expected) {
        RoundState actual = roundStates[roundId];
        if (actual != expected) revert InvalidRoundState(roundId, expected, actual);
        _;
    }

    function hasRole(bytes32 role, address account) external view returns (bool) {
        return roles[role][account];
    }

    function grantRole(bytes32 role, address account) external onlyRole(ADMIN_ROLE) {
        if (account == address(0)) revert ZeroAddress();
        if (!roles[role][account] && role == ADMIN_ROLE) {
            adminCount++;
        }
        roles[role][account] = true;
        emit RoleGranted(role, account, msg.sender);
    }

    function revokeRole(bytes32 role, address account) external onlyRole(ADMIN_ROLE) {
        if (account == address(0)) revert ZeroAddress();
        if (role == ADMIN_ROLE && roles[role][account]) {
            if (adminCount <= 1) revert NoAdminRemaining();
            adminCount--;
        }
        roles[role][account] = false;
        emit RoleRevoked(role, account, msg.sender);
    }

    function setVerifierContract(address verifierContract_) external onlyRole(ADMIN_ROLE) {
        if (verifierContract_ == address(0)) revert ZeroAddress();
        if (verifierContract_.code.length == 0) revert ContractAddressRequired(verifierContract_);
        verifierContract = IFairAIVerifier(verifierContract_);
        emit VerifierContractUpdated(verifierContract_);
    }

    function createRound(uint256 roundId) external onlyRole(ADMIN_ROLE) inRoundState(roundId, RoundState.Uncreated) {
        roundStates[roundId] = RoundState.Open;
        emit RoundStateChanged(roundId, RoundState.Open);
    }

    function closeSubmissions(uint256 roundId) external onlyRole(ADMIN_ROLE) inRoundState(roundId, RoundState.Open) {
        roundStates[roundId] = RoundState.SubmissionClosed;
        emit RoundStateChanged(roundId, RoundState.SubmissionClosed);
    }

    function startAggregation(uint256 roundId) external onlyRole(AGGREGATOR_ROLE) inRoundState(roundId, RoundState.SubmissionClosed) {
        roundStates[roundId] = RoundState.AggregationStarted;
        emit RoundStateChanged(roundId, RoundState.AggregationStarted);
    }

    function cancelRound(uint256 roundId) external onlyRole(ADMIN_ROLE) inRoundState(roundId, RoundState.SubmissionClosed) {
        roundStates[roundId] = RoundState.Cancelled;
        emit RoundStateChanged(roundId, RoundState.Cancelled);
    }

    function archiveRound(uint256 roundId) external onlyRole(ADMIN_ROLE) inRoundState(roundId, RoundState.Published) {
        roundStates[roundId] = RoundState.Archived;
        emit RoundStateChanged(roundId, RoundState.Archived);
    }

    function registerNode(bytes32 nodeId) external onlyRole(NODE_OPERATOR_ROLE) {
        registeredNodes[nodeId] = true;
        emit NodeRegistered(nodeId, msg.sender);
    }

    function submitModel(
        bytes32 nodeId,
        uint256 roundId,
        string calldata modelCid,
        string calldata proofCid,
        string calldata publicCid,
        string calldata metadataCid,
        string calldata metricsCid,
        string calldata manifestCid,
        bytes calldata proof,
        uint256[] calldata publicSignals
    ) external onlyRole(VERIFIER_ROLE) inRoundState(roundId, RoundState.Open) {
        if (!registeredNodes[nodeId]) revert NodeNotRegistered(nodeId);
        if (address(verifierContract) == address(0)) revert VerifierContractNotSet();
        if (
            _isEmpty(modelCid) ||
            _isEmpty(proofCid) ||
            _isEmpty(publicCid) ||
            _isEmpty(metadataCid) ||
            _isEmpty(metricsCid) ||
            _isEmpty(manifestCid)
        ) revert EmptyCid();
        if (
            publicSignals.length == 21 &&
            (nodeId != bytes32(publicSignals[17]) || roundId != publicSignals[18])
        ) revert PublicSignalContextMismatch();

        bytes32 key = getRecordKey(nodeId, roundId);
        if (records[key].timestamp != 0) revert DuplicateSubmission(nodeId, roundId);
        _markCidUnused(modelCid);
        _markCidUnused(proofCid);
        _markCidUnused(publicCid);
        _markCidUnused(metadataCid);
        _markCidUnused(metricsCid);
        _markCidUnused(manifestCid);

        bool proofVerified = verifierContract.verifyProof(proof, publicSignals);
        VerificationStatus verificationStatus = proofVerified ? VerificationStatus.Valid : VerificationStatus.Invalid;
        ApprovalStatus approvalStatus = proofVerified ? ApprovalStatus.Approved : ApprovalStatus.Rejected;

        records[key] = ModelRecord({
            nodeId: nodeId,
            roundId: roundId,
            modelCid: modelCid,
            proofCid: proofCid,
            publicCid: publicCid,
            metadataCid: metadataCid,
            metricsCid: metricsCid,
            manifestCid: manifestCid,
            verificationStatus: verificationStatus,
            approvalStatus: approvalStatus,
            submitter: msg.sender,
            timestamp: block.timestamp
        });
        roundRecordKeys[roundId].push(key);
        if (approvalStatus == ApprovalStatus.Approved) {
            approvedModelCidsByRound[roundId][modelCid] = true;
        }

        emit ModelSubmitted(
            nodeId,
            roundId,
            modelCid,
            proofCid,
            publicCid,
            metadataCid,
            metricsCid,
            manifestCid,
            verificationStatus,
            approvalStatus
        );
        emit AuditLogged(nodeId, roundId, verificationStatus, approvalStatus, modelCid, proofCid);
    }

    function getRecord(bytes32 nodeId, uint256 roundId) external view returns (ModelRecord memory) {
        return records[getRecordKey(nodeId, roundId)];
    }

    function getRoundRecordKeys(uint256 roundId) external view returns (bytes32[] memory) {
        return roundRecordKeys[roundId];
    }

    function getEligibleModelCids(uint256 roundId) external view returns (string[] memory) {
        bytes32[] storage keys = roundRecordKeys[roundId];
        uint256 count = 0;
        for (uint256 i = 0; i < keys.length; i++) {
            if (records[keys[i]].approvalStatus == ApprovalStatus.Approved) {
                count++;
            }
        }

        string[] memory cids = new string[](count);
        uint256 cursor = 0;
        for (uint256 i = 0; i < keys.length; i++) {
            if (records[keys[i]].approvalStatus == ApprovalStatus.Approved) {
                cids[cursor] = records[keys[i]].modelCid;
                cursor++;
            }
        }
        return cids;
    }

    function publishGlobalModel(
        uint256 roundId,
        string calldata globalModelCid,
        string calldata reportCid,
        string[] calldata participantModelCids
    ) external onlyRole(AGGREGATOR_ROLE) inRoundState(roundId, RoundState.AggregationStarted) {
        if (globalModels[roundId].timestamp != 0) revert GlobalModelAlreadyPublished(roundId);
        if (_isEmpty(globalModelCid) || _isEmpty(reportCid)) revert EmptyCid();
        if (participantModelCids.length == 0) revert NoParticipants();

        _markCidUnused(globalModelCid);
        _markCidUnused(reportCid);
        for (uint256 i = 0; i < participantModelCids.length; i++) {
            if (!approvedModelCidsByRound[roundId][participantModelCids[i]]) {
                revert ParticipantNotApproved(participantModelCids[i]);
            }
        }

        globalModels[roundId] = GlobalModelRecord({
            roundId: roundId,
            globalModelCid: globalModelCid,
            reportCid: reportCid,
            participantModelCids: participantModelCids,
            publisher: msg.sender,
            timestamp: block.timestamp
        });
        roundStates[roundId] = RoundState.Published;

        emit GlobalModelPublished(roundId, globalModelCid, reportCid, msg.sender, participantModelCids.length);
        emit RoundStateChanged(roundId, RoundState.Published);
    }

    function getGlobalModel(uint256 roundId) external view returns (GlobalModelRecord memory) {
        return globalModels[roundId];
    }

    function getRecordKey(bytes32 nodeId, uint256 roundId) public pure returns (bytes32) {
        return keccak256(abi.encodePacked(nodeId, roundId));
    }

    function _markCidUnused(string calldata cid) private {
        if (usedCids[cid]) revert DuplicateCid(cid);
        usedCids[cid] = true;
    }

    function _isEmpty(string calldata value) private pure returns (bool) {
        return bytes(value).length == 0;
    }
}
