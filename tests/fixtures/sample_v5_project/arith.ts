import { ethers } from "ethers";

export function calculateFee(amount: ethers.BigNumber) {
  // Edge case: BigNumber arithmetic chain
  const fee = amount.mul(ethers.BigNumber.from(3)).div(100);
  return fee;
}
