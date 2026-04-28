"""Real Brownie code patterns for testing migration."""

from brownie import network
from brownie.network import account
from brownie.network.account import accounts
from brownie import project
import brownie

brownie.eth.connect("mainnet")

network.connect("localhost")

accounts = network.eth.accounts

token = project.Token.deploy({"from": accounts[0]})

from brownie.network.eth import ChainAPI

config = brownie._config

web3.eth.accounts

def deploy_contract():
    from brownie import network
    network.connect("mainnet")
    accounts = network.eth.accounts
    return project.MyContract.deploy({"from": accounts[0]})


class BrownieIntegration:
    def __init__(self):
        self.network = network
        self.accounts = network.eth.accounts

    def get_balance(self, address):
        return web3.eth.get_balance(address)


from brownie.network.transaction import Transaction
from brownie.convert import to_address