"""Pytest configuration and fixtures."""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_brownie_file(temp_dir):
    """Create a sample Brownie file."""
    file_path = temp_dir / "sample.py"
    file_path.write_text("""
from brownie import network
from brownie.network.account import accounts

def main():
    network.connect("mainnet")
    return accounts[0]
""")
    return file_path


@pytest.fixture
def sample_ape_file(temp_dir):
    """Create a sample Ape file."""
    file_path = temp_dir / "sample_ape.py"
    file_path.write_text("""
from ape import chain, accounts

def main():
    chain.provider.connect("mainnet")
    return accounts[0]
""")
    return file_path


@pytest.fixture
def mock_brownie_project(temp_dir):
    """Create a mock Brownie project."""
    project_path = temp_dir / "project"
    project_path.mkdir()

    (project_path / "scripts").mkdir()
    (project_path / "tests").mkdir()
    (project_path / "contracts").mkdir()

    (project_path / "scripts" / "deploy.py").write_text("""
from brownie import network, project
from brownie.network.account import accounts

def main():
    network.connect("mainnet")
    token = project.Token.deploy({"from": accounts[0]})
    return token
""")

    (project_path / "tests" / "test_token.py").write_text("""
import pytest
from brownie import network

def test_deploy():
    network.connect("localhost")
    assert True
""")

    (project_path / "brownie-config.yaml").write_text("""
network:
  default: mainnet
""")

    return project_path