// SPDX-License-Identifier: GPL-3.0
/*
    Copyright 2021 0KIMS association.

    This file is generated with [snarkJS](https://github.com/iden3/snarkjs).

    snarkJS is a free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    snarkJS is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
    or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public
    License for more details.

    You should have received a copy of the GNU General Public License
    along with snarkJS. If not, see <https://www.gnu.org/licenses/>.
*/

pragma solidity >=0.7.0 <0.9.0;

contract FairnessEligibilityV2Groth16Verifier {
    // Scalar field size
    uint256 constant r    = 21888242871839275222246405745257275088548364400416034343698204186575808495617;
    // Base field size
    uint256 constant q   = 21888242871839275222246405745257275088696311157297823662689037894645226208583;

    // Verification Key data
    uint256 constant alphax  = 1203298258470160694405800514545591754869090292775755168475285677808812747142;
    uint256 constant alphay  = 6179859288715301532505230075191077782467128524403580361985797145808716143707;
    uint256 constant betax1  = 11779053541352740609186924076905516483721340213269792892876526174723616428801;
    uint256 constant betax2  = 17548517439021853164843609674742436386771973520281114666548701960053851617185;
    uint256 constant betay1  = 14094452064388581745138494198948125276181409060638500899262213241671855031740;
    uint256 constant betay2  = 18537454149102506696720048567777181333590726617979727933444065375748167765755;
    uint256 constant gammax1 = 11559732032986387107991004021392285783925812861821192530917403151452391805634;
    uint256 constant gammax2 = 10857046999023057135944570762232829481370756359578518086990519993285655852781;
    uint256 constant gammay1 = 4082367875863433681332203403145435568316851327593401208105741076214120093531;
    uint256 constant gammay2 = 8495653923123431417604973247489272438418190587263600148770280649306958101930;
    uint256 constant deltax1 = 7087850823788322880375814707169157411514972301746968056820342519579185476618;
    uint256 constant deltax2 = 1215868398562589416285131524849603124935281823726336478988350055864690942126;
    uint256 constant deltay1 = 10744698322597632094493075391918047476650963682885059004353371146564217782461;
    uint256 constant deltay2 = 17062271371199588740269214524556412032395322474979067339884463050958410016008;

    
    uint256 constant IC0x = 17339546862955925669017843225749727769290088032838834874391304072208815587842;
    uint256 constant IC0y = 509460203158754600520826261194837767349238356661724150934166276622434364894;
    
    uint256 constant IC1x = 7877394220568048048190101413535904591744578932927735261455368606347565975511;
    uint256 constant IC1y = 9471774192267939238128411926033830742725535870602541369153156511329047327383;
    
    uint256 constant IC2x = 9398730152112838085363806639386561547366639085527314485682243915129642852174;
    uint256 constant IC2y = 13461813395943891898827600113416826222316213067305837402717526098807801930339;
    
    uint256 constant IC3x = 20660908203310110679779137753113924842304012529090472396823764913180711519983;
    uint256 constant IC3y = 5131140681831623091902568135215060997328212472363774769352871402722961075091;
    
    uint256 constant IC4x = 9621457594115051899326923231830143144854321503277584594444845190323263886716;
    uint256 constant IC4y = 9418927128730144867562120957946166232243382177267646814445492396892499972923;
    
    uint256 constant IC5x = 21442090660957798744069830851795993459072401923693029514389810926788986987890;
    uint256 constant IC5y = 7932781577814213463866598304996209861824475997915869698619238375418397145624;
    
    uint256 constant IC6x = 12125677161651630857255901859203884716019277193951909600345520502824786382955;
    uint256 constant IC6y = 21545513376278364561144717464748412200898951315432940967443066782809779453020;
    
    uint256 constant IC7x = 8383500502382217353462650295261510246300748778556440800518432102833767089119;
    uint256 constant IC7y = 13046749633633988712896366284961999523291033111726064826492501483675870175965;
    
    uint256 constant IC8x = 12322848595838002161492885771097718806865463899633129664806847823661430141371;
    uint256 constant IC8y = 10109421224497274781726891781097362187104853601419490358773736229976637846529;
    
    uint256 constant IC9x = 19917740514440928230030319617025811930814927075145446810463855480374800066664;
    uint256 constant IC9y = 5014563299263812011442062035710678653299330063328557838096296413379404923693;
    
    uint256 constant IC10x = 186164227714908796665842383176209497718451932580541039951456773871484168247;
    uint256 constant IC10y = 2244426595883982589332604921707372278488444676805745740189044876691094694343;
    
    uint256 constant IC11x = 8094502833951840205238371212402532195703759444218958743699727525030258854614;
    uint256 constant IC11y = 6296367470155085367783771284216993786351132019003401115535421369713774293479;
    
    uint256 constant IC12x = 5709467832673270610012371644231614400108358176335704502937787224459719046453;
    uint256 constant IC12y = 4312121239622672931381356770465532751787972468346813395129261440384952007324;
    
    uint256 constant IC13x = 7149262113500314329628476831448655123240116849412730619148538046818068209456;
    uint256 constant IC13y = 3964150904368939338791961676617167647539305330789749817603047587638513835653;
    
    uint256 constant IC14x = 8661420093544485003054079159258937205128909570551344221952668786509391833916;
    uint256 constant IC14y = 14513724584028571415240021858408076239460285886501516549177708002128611328761;
    
    uint256 constant IC15x = 1363687413830448107737717358485902139404377025742583215010473768603916106230;
    uint256 constant IC15y = 15918702619933384212307060219204175999524706377007271164499930312237909199837;
    
    uint256 constant IC16x = 18862259118897554860219823612790003703228652638144987353245304435476564069658;
    uint256 constant IC16y = 12169802945391879626654286601831916465551244696174798418669573683146567066604;
    
    uint256 constant IC17x = 14337699292513739075473677603064086137009339823244195567305564824739261680991;
    uint256 constant IC17y = 283754758200833346668866012533099908906605612740435534625362203550142762720;
    
    uint256 constant IC18x = 5235212340300276798340156462441268947625939192810916200885369720661552644873;
    uint256 constant IC18y = 2370991412263120621347899550533330888811755112556900387690655176962127011294;
    
    uint256 constant IC19x = 18630217020561905932262619072964369668492643068546457605482956284947603686013;
    uint256 constant IC19y = 2335780875176007198416011484916421264331279053524425030264904738524721292546;
    
    uint256 constant IC20x = 6081899522124323139437949709718277223966312030845630283800022744185978650060;
    uint256 constant IC20y = 21459896046095405939089686735960502770182018911085722875269969917660642381663;
    
    uint256 constant IC21x = 3689407157844654680953688448752002282215336725121917485594449185713648876401;
    uint256 constant IC21y = 2988055027980737491007639373209430909657758722280175670108834859312033774284;
    
 
    // Memory data
    uint16 constant pVk = 0;
    uint16 constant pPairing = 128;

    uint16 constant pLastMem = 896;

    function verifyProof(uint[2] calldata _pA, uint[2][2] calldata _pB, uint[2] calldata _pC, uint[21] calldata _pubSignals) public view returns (bool) {
        assembly {
            function checkField(v) {
                if iszero(lt(v, r)) {
                    mstore(0, 0)
                    return(0, 0x20)
                }
            }
            
            // G1 function to multiply a G1 value(x,y) to value in an address
            function g1_mulAccC(pR, x, y, s) {
                let success
                let mIn := mload(0x40)
                mstore(mIn, x)
                mstore(add(mIn, 32), y)
                mstore(add(mIn, 64), s)

                success := staticcall(sub(gas(), 2000), 7, mIn, 96, mIn, 64)

                if iszero(success) {
                    mstore(0, 0)
                    return(0, 0x20)
                }

                mstore(add(mIn, 64), mload(pR))
                mstore(add(mIn, 96), mload(add(pR, 32)))

                success := staticcall(sub(gas(), 2000), 6, mIn, 128, pR, 64)

                if iszero(success) {
                    mstore(0, 0)
                    return(0, 0x20)
                }
            }

            function checkPairing(pA, pB, pC, pubSignals, pMem) -> isOk {
                let _pPairing := add(pMem, pPairing)
                let _pVk := add(pMem, pVk)

                mstore(_pVk, IC0x)
                mstore(add(_pVk, 32), IC0y)

                // Compute the linear combination vk_x
                
                g1_mulAccC(_pVk, IC1x, IC1y, calldataload(add(pubSignals, 0)))
                
                g1_mulAccC(_pVk, IC2x, IC2y, calldataload(add(pubSignals, 32)))
                
                g1_mulAccC(_pVk, IC3x, IC3y, calldataload(add(pubSignals, 64)))
                
                g1_mulAccC(_pVk, IC4x, IC4y, calldataload(add(pubSignals, 96)))
                
                g1_mulAccC(_pVk, IC5x, IC5y, calldataload(add(pubSignals, 128)))
                
                g1_mulAccC(_pVk, IC6x, IC6y, calldataload(add(pubSignals, 160)))
                
                g1_mulAccC(_pVk, IC7x, IC7y, calldataload(add(pubSignals, 192)))
                
                g1_mulAccC(_pVk, IC8x, IC8y, calldataload(add(pubSignals, 224)))
                
                g1_mulAccC(_pVk, IC9x, IC9y, calldataload(add(pubSignals, 256)))
                
                g1_mulAccC(_pVk, IC10x, IC10y, calldataload(add(pubSignals, 288)))
                
                g1_mulAccC(_pVk, IC11x, IC11y, calldataload(add(pubSignals, 320)))
                
                g1_mulAccC(_pVk, IC12x, IC12y, calldataload(add(pubSignals, 352)))
                
                g1_mulAccC(_pVk, IC13x, IC13y, calldataload(add(pubSignals, 384)))
                
                g1_mulAccC(_pVk, IC14x, IC14y, calldataload(add(pubSignals, 416)))
                
                g1_mulAccC(_pVk, IC15x, IC15y, calldataload(add(pubSignals, 448)))
                
                g1_mulAccC(_pVk, IC16x, IC16y, calldataload(add(pubSignals, 480)))
                
                g1_mulAccC(_pVk, IC17x, IC17y, calldataload(add(pubSignals, 512)))
                
                g1_mulAccC(_pVk, IC18x, IC18y, calldataload(add(pubSignals, 544)))
                
                g1_mulAccC(_pVk, IC19x, IC19y, calldataload(add(pubSignals, 576)))
                
                g1_mulAccC(_pVk, IC20x, IC20y, calldataload(add(pubSignals, 608)))
                
                g1_mulAccC(_pVk, IC21x, IC21y, calldataload(add(pubSignals, 640)))
                

                // -A
                mstore(_pPairing, calldataload(pA))
                mstore(add(_pPairing, 32), mod(sub(q, calldataload(add(pA, 32))), q))

                // B
                mstore(add(_pPairing, 64), calldataload(pB))
                mstore(add(_pPairing, 96), calldataload(add(pB, 32)))
                mstore(add(_pPairing, 128), calldataload(add(pB, 64)))
                mstore(add(_pPairing, 160), calldataload(add(pB, 96)))

                // alpha1
                mstore(add(_pPairing, 192), alphax)
                mstore(add(_pPairing, 224), alphay)

                // beta2
                mstore(add(_pPairing, 256), betax1)
                mstore(add(_pPairing, 288), betax2)
                mstore(add(_pPairing, 320), betay1)
                mstore(add(_pPairing, 352), betay2)

                // vk_x
                mstore(add(_pPairing, 384), mload(add(pMem, pVk)))
                mstore(add(_pPairing, 416), mload(add(pMem, add(pVk, 32))))


                // gamma2
                mstore(add(_pPairing, 448), gammax1)
                mstore(add(_pPairing, 480), gammax2)
                mstore(add(_pPairing, 512), gammay1)
                mstore(add(_pPairing, 544), gammay2)

                // C
                mstore(add(_pPairing, 576), calldataload(pC))
                mstore(add(_pPairing, 608), calldataload(add(pC, 32)))

                // delta2
                mstore(add(_pPairing, 640), deltax1)
                mstore(add(_pPairing, 672), deltax2)
                mstore(add(_pPairing, 704), deltay1)
                mstore(add(_pPairing, 736), deltay2)


                let success := staticcall(sub(gas(), 2000), 8, _pPairing, 768, _pPairing, 0x20)

                isOk := and(success, mload(_pPairing))
            }

            let pMem := mload(0x40)
            mstore(0x40, add(pMem, pLastMem))

            // Validate that all evaluations ∈ F
            
            checkField(calldataload(add(_pubSignals, 0)))
            
            checkField(calldataload(add(_pubSignals, 32)))
            
            checkField(calldataload(add(_pubSignals, 64)))
            
            checkField(calldataload(add(_pubSignals, 96)))
            
            checkField(calldataload(add(_pubSignals, 128)))
            
            checkField(calldataload(add(_pubSignals, 160)))
            
            checkField(calldataload(add(_pubSignals, 192)))
            
            checkField(calldataload(add(_pubSignals, 224)))
            
            checkField(calldataload(add(_pubSignals, 256)))
            
            checkField(calldataload(add(_pubSignals, 288)))
            
            checkField(calldataload(add(_pubSignals, 320)))
            
            checkField(calldataload(add(_pubSignals, 352)))
            
            checkField(calldataload(add(_pubSignals, 384)))
            
            checkField(calldataload(add(_pubSignals, 416)))
            
            checkField(calldataload(add(_pubSignals, 448)))
            
            checkField(calldataload(add(_pubSignals, 480)))
            
            checkField(calldataload(add(_pubSignals, 512)))
            
            checkField(calldataload(add(_pubSignals, 544)))
            
            checkField(calldataload(add(_pubSignals, 576)))
            
            checkField(calldataload(add(_pubSignals, 608)))
            
            checkField(calldataload(add(_pubSignals, 640)))
            

            // Validate all evaluations
            let isValid := checkPairing(_pA, _pB, _pC, _pubSignals, pMem)

            mstore(0, isValid)
             return(0, 0x20)
         }
     }
 }
