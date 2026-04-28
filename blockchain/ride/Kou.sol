// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.14;

import "./IMessenger.sol";

contract Kou {
    address public feelings;
    IMessenger public messenger;

    function writeFeelings(address _feelings, address _messenger) external {
        feelings = _feelings;

        messenger = IMessenger(_messenger); 
        messenger.notify();
    }
}
