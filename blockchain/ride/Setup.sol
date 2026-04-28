// SPDX-License-Identifier: UNLICENSED
pragma solidity 0.8.14;

import "./Futaba.sol";
import "./Kou.sol";

contract Setup {
    address public immutable PLAYER_ADR;

    Futaba public futaba;
    Kou public kou;

    constructor(address playerAddr) {
        PLAYER_ADR = playerAddr;

        kou = new Kou(); 
        futaba = new Futaba(address(kou));
    }

    function isSolved() external view returns (bool) {
        return futaba.owner() == PLAYER_ADR;
    }
}
