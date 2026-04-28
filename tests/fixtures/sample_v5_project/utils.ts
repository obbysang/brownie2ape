import { ethers } from "ethers";

export function setupWallet() {
  const provider = new ethers.providers.Web3Provider(window.ethereum);
  const signer = provider.getSigner();
  return signer;
}

export function formatValue(val: ethers.BigNumber) {
  return ethers.utils.formatEther(val);
}

export function hashData(input: string) {
  return ethers.utils.keccak256(ethers.utils.toUtf8Bytes(input));
}
