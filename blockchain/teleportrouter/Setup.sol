// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.16;
import "./TeleportRouter.sol";

contract Setup {
    address public immutable PLAYER_ADR;
    TeleportRouter public router;

    constructor(address playerAddr) payable {
        PLAYER_ADR = playerAddr;
        router = new TeleportRouter{value: msg.value}();
    }

    function isSolved() external view returns (bool) {
        return address(router).balance == 0;
    }
}

