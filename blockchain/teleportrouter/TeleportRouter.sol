// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.16;
contract TeleportRouter {

    event StepExecuted(address indexed sender, uint256 ptr);
    event StrategyExecutionRequested();

    struct Strategy {
        function() internal fn;
    }

    uint public timelock;
    bool entered;

    constructor() payable {
        require(msg.value > 0, "Invalid deployment, contract must be funded");
        timelock = block.timestamp + 365 days;
    }

    modifier nonReentrant() {
        if (entered) {revert();}
        entered = true;
        _;
        entered = false;
    }


    modifier validateTarget(address _target) {
        uint256 size;
        assembly { size := extcodesize(_target) }
        bytes memory code = address(_target).code;
        require (size == 9, "You gotta be carefuly mate!");
        for (uint i = 0; i < code.length; i++) {
            require(bytes1(code[i]) != 0x55, "Huh? I know what you are trying to do");
        }
        _;
        
    }

    function execute(
        address _target,
        bool isDelegate
    )
        external
        validateTarget(_target)
    {   
        uint decodedret = _executeCall(_target, isDelegate);

        emit StepExecuted(msg.sender, decodedret);

        Strategy memory p;
        p.fn = _base;
        assembly {
            mstore(p, add(mload(p), decodedret))
        }

        p.fn(); 
    }

    function _executeCall(address _target, bool isDelegate) internal returns (uint) {
    if (isDelegate) {
        (bool ok, bytes memory ret) = _target.delegatecall(abi.encodeWithSignature("step()"));
        require(ok, "fallback can not fail");
        return abi.decode(ret, (uint)); 
    } else {
        (bool ok, bytes memory ret) = _target.call(abi.encodeWithSignature("stepFallback()"));
        require(ok, "fallback can not fail");
        return abi.decode(ret, (uint));   
    }
}

    function _base() public {
        // TODO implement the function
        emit StrategyExecutionRequested();
    }

    function borrow(address _recipient, uint _amount) external nonReentrant {
        uint available = address(this).balance;
        require(available >= _amount, "Not enough balance to borrow");
        (bool success, ) = payable(_recipient).call{value:  _amount}("");
        require(success);
        uint remaining = address(this).balance;
        require(remaining == available);
    }

    function rescueAllFunds() public {
        require(block.timestamp >= timelock);
        (bool success, ) = payable(msg.sender).call{value: address(this).balance}("");
        require(success);
    }

}

