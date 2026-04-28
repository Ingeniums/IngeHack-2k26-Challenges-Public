// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.14;

import "./IMessenger.sol";
import "./Kou.sol";

contract Futaba {
    address public owner;
    IMessenger public messenger;
    bool public desperate;
    Kou public kou;

    error Heartbreak();

    constructor(address _kou) {
        owner = msg.sender;
        kou = Kou(_kou);
        messenger = kou.messenger();
    }

    function reach(address _feelings, address _messenger) external {
        if (desperate) {
            (bool success, bytes memory ret) = address(kou).delegatecall(
                abi.encodeWithSignature("writeFeelings(address,address)", _feelings, _messenger)
            );
            if (!success) {
                assembly { revert(add(ret, 32), mload(ret)) }
            }
            desperate = false;
        } else {
            try kou.writeFeelings(_feelings, _messenger) {
            } catch (bytes memory reason) {
                if (reason.length == 4 && bytes4(reason) == Heartbreak.selector) {
                    desperate = true;
                } else {
                    assembly { revert(add(reason, 32), mload(reason)) }
                }
            }
        }
    }
}
