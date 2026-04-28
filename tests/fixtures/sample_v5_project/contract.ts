import { ethers } from "ethers";

export async function deployContract(
  factory: ethers.ContractFactory,
  args: any[]
) {
  const contract = await factory.deploy(...args);
  await contract.deployed();
  return contract;
}

export function getContractSigner(contract: ethers.Contract) {
  return contract.signer;
}

export function getContractProvider(contract: ethers.Contract) {
  return contract.provider;
}
