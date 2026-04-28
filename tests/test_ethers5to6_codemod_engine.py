"""Tests for ethers5to6 Stage 2 — Codemod Engine."""

import pytest
from pathlib import Path

from ethers5to6.codemod_engine import CodemodEngine, DETERMINISTIC_RULES


class TestCodemodEngine:
    def test_provider_web3_rewrite(self, tmp_path: Path):
        file = tmp_path / "provider.ts"
        original = 'import { ethers } from "ethers";\nconst p = new ethers.providers.Web3Provider(window.ethereum);\n'
        file.write_text(original)

        engine = CodemodEngine(tmp_path)
        stats = engine.apply_all(dry_run=False)

        result = file.read_text(encoding="utf-8")
        assert "ethers.BrowserProvider" in result
        assert "ethers.providers.Web3Provider" not in result
        assert stats.total_changes >= 1

    def test_utils_flatten(self, tmp_path: Path):
        file = tmp_path / "utils.ts"
        original = (
            'import { ethers } from "ethers";\n'
            'const h = ethers.utils.keccak256("0x00");\n'
            'const f = ethers.utils.formatEther("1000");\n'
        )
        file.write_text(original)

        engine = CodemodEngine(tmp_path)
        stats = engine.apply_all(dry_run=False)

        result = file.read_text(encoding="utf-8")
        assert "ethers.keccak256" in result
        assert "ethers.formatEther" in result
        assert "ethers.utils.keccak256" not in result
        assert "ethers.utils.formatEther" not in result
        assert stats.total_changes >= 2

    def test_bignum_from_rewrite(self, tmp_path: Path):
        file = tmp_path / "math.ts"
        original = (
            'import { ethers } from "ethers";\n'
            'const x = ethers.BigNumber.from(100);\n'
        )
        file.write_text(original)

        engine = CodemodEngine(tmp_path)
        stats = engine.apply_all(dry_run=False)

        result = file.read_text(encoding="utf-8")
        assert "BigInt(100)" in result
        assert "ethers.BigNumber.from" not in result
        assert stats.total_changes >= 1

    def test_dry_run_does_not_modify(self, tmp_path: Path):
        file = tmp_path / "utils.ts"
        original = 'import { ethers } from "ethers";\nconst h = ethers.utils.keccak256("0x00");\n'
        file.write_text(original)

        engine = CodemodEngine(tmp_path)
        stats = engine.apply_all(dry_run=True)

        result = file.read_text(encoding="utf-8")
        assert result == original
        assert stats.total_changes >= 1  # changes are counted even in dry-run

    def test_idempotency(self, tmp_path: Path):
        file = tmp_path / "utils.ts"
        original = 'import { ethers } from "ethers";\nconst h = ethers.utils.keccak256("0x00");\n'
        file.write_text(original)

        engine = CodemodEngine(tmp_path)
        engine.apply_all(dry_run=False)
        first = file.read_text(encoding="utf-8")

        engine2 = CodemodEngine(tmp_path)
        stats2 = engine2.apply_all(dry_run=False)
        second = file.read_text(encoding="utf-8")

        assert first == second
        assert stats2.total_changes == 0

    def test_skips_non_ethers_files(self, tmp_path: Path):
        file = tmp_path / "plain.ts"
        original = 'const x = 1;\n'
        file.write_text(original)

        engine = CodemodEngine(tmp_path)
        stats = engine.apply_all(dry_run=False)

        result = file.read_text(encoding="utf-8")
        assert result == original
        assert stats.total_changes == 0

    def test_contract_signer_provider(self, tmp_path: Path):
        file = tmp_path / "contract.ts"
        original = (
            'import { ethers } from "ethers";\n'
            'function getSigner(c: ethers.Contract) { return c.signer; }\n'
            'function getProvider(c: ethers.Contract) { return c.provider; }\n'
        )
        file.write_text(original)

        engine = CodemodEngine(tmp_path)
        stats = engine.apply_all(dry_run=False)

        result = file.read_text(encoding="utf-8")
        assert "c.runner" in result
        assert "c.signer" not in result
        assert "c.provider" not in result
        assert stats.total_changes >= 2

    def test_rules_have_unique_ids(self):
        ids = [r["id"] for r in DETERMINISTIC_RULES]
        assert len(ids) == len(set(ids))

    def test_rules_have_required_fields(self):
        for rule in DETERMINISTIC_RULES:
            assert "id" in rule
            assert "pattern" in rule
            assert "rewrite" in rule
            assert "description" in rule
