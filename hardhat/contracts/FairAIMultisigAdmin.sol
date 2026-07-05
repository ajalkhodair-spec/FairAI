// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract FairAIMultisigAdmin {
    struct Transaction {
        address target;
        uint256 value;
        bytes data;
        bool executed;
        uint256 approvals;
    }

    mapping(address => bool) public isOwner;
    address[] public owners;
    uint256 public immutable threshold;
    Transaction[] private transactions;
    mapping(uint256 => mapping(address => bool)) public approvedBy;

    event TransactionSubmitted(uint256 indexed txId, address indexed submitter, address indexed target, uint256 value);
    event TransactionApproved(uint256 indexed txId, address indexed owner);
    event TransactionExecuted(uint256 indexed txId, address indexed executor);

    error NotOwner();
    error InvalidThreshold();
    error AlreadyApproved();
    error AlreadyExecuted();
    error InsufficientApprovals(uint256 approvals, uint256 threshold);
    error ExecutionFailed();

    constructor(address[] memory owners_, uint256 threshold_) {
        if (threshold_ == 0 || threshold_ > owners_.length) revert InvalidThreshold();
        for (uint256 i = 0; i < owners_.length; i++) {
            address owner = owners_[i];
            if (owner == address(0) || isOwner[owner]) revert InvalidThreshold();
            isOwner[owner] = true;
            owners.push(owner);
        }
        threshold = threshold_;
    }

    modifier onlyOwner() {
        if (!isOwner[msg.sender]) revert NotOwner();
        _;
    }

    function submitTransaction(address target, uint256 value, bytes calldata data) external onlyOwner returns (uint256 txId) {
        txId = transactions.length;
        transactions.push(Transaction({
            target: target,
            value: value,
            data: data,
            executed: false,
            approvals: 0
        }));
        emit TransactionSubmitted(txId, msg.sender, target, value);
    }

    function approveTransaction(uint256 txId) external onlyOwner {
        Transaction storage transaction = transactions[txId];
        if (transaction.executed) revert AlreadyExecuted();
        if (approvedBy[txId][msg.sender]) revert AlreadyApproved();
        approvedBy[txId][msg.sender] = true;
        transaction.approvals++;
        emit TransactionApproved(txId, msg.sender);
    }

    function executeTransaction(uint256 txId) external onlyOwner {
        Transaction storage transaction = transactions[txId];
        if (transaction.executed) revert AlreadyExecuted();
        if (transaction.approvals < threshold) revert InsufficientApprovals(transaction.approvals, threshold);
        transaction.executed = true;
        (bool ok,) = transaction.target.call{value: transaction.value}(transaction.data);
        if (!ok) revert ExecutionFailed();
        emit TransactionExecuted(txId, msg.sender);
    }

    function getTransaction(uint256 txId) external view returns (Transaction memory) {
        return transactions[txId];
    }

    function transactionCount() external view returns (uint256) {
        return transactions.length;
    }

    receive() external payable {}
}
