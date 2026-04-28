"""Integration tests for ethers5to6 end-to-end pipeline."""

import pytest
from pathlib import Path

from ethers5to6.detector import EthersDetector
from ethers5to6.codemod_engine import CodemodEngine
from ethers5to6.reporter import MigrationReporter
from ethers5to6.verifier import Verifier


class TestEndToEndMigration:
    @pytest.fixture
    def v5_project(self, tmp_path: Path) -> Path:
        project = tmp_path / "v5project"
        project.mkdir()

        (project / "utils.ts").write_text(
            'import { ethers } from "ethers";\n\n'
            'export function setupWallet() {\n'
            '  const provider = new ethers.providers.Web3Provider(window.ethereum);\n'
            '  return provider.getSigner();\n'
            '}\n\n'
            'export function formatValue(val: ethers.BigNumber) {\n'
            '  return ethers.utils.formatEther(val);\n'
            '}\n\n'
            'export function hashData(input: string) {\n'
            '  return ethers.utils.keccak256(ethers.utils.toUtf8Bytes(input));\n'
            '}\n'
        )

        (project / "contract.ts").write_text(
            'import { ethers } from "ethers";\n\n'
            'export async function deployContract(factory: ethers.ContractFactory, args: any[]) {\n'
            '  const contract = await factory.deploy(...args);\n'
            '  await contract.deployed();\n'
            '  return contract;\n'
            '}\n\n'
            'export function getContractSigner(contract: ethers.Contract) {\n'
            '  return contract.signer;\n'
            '}\n\n'
            'export function getContractProvider(contract: ethers.Contract) {\n'
            '  return contract.provider;\n'
            '}\n'
        )

        return project

    def test_full_pipeline(self, v5_project: Path):
        # Stage 1: Detect
        detector = EthersDetector(v5_project)
        detection = detector.detect()

        assert detection.files_with_ethers >= 2
        assert len(detection.provider_usage) >= 1
        assert len(detection.utils_usage) >= 3
        assert len(detection.contract_usage) >= 1

        # Stage 2-3: Migrate
        engine = CodemodEngine(v5_project)
        codemod_stats = engine.apply_all(dry_run=False)

        assert codemod_stats.total_changes >= 5
        assert codemod_stats.files_modified >= 2

        # Verify file contents
        utils = (v5_project / "utils.ts").read_text(encoding="utf-8")
        assert "ethers.BrowserProvider" in utils
        assert "ethers.providers.Web3Provider" not in utils
        assert "ethers.formatEther" in utils
        assert "ethers.utils.formatEther" not in utils
        assert "ethers.keccak256" in utils
        assert "ethers.utils.keccak256" not in utils
        assert "ethers.toUtf8Bytes" in utils
        assert "ethers.utils.toUtf8Bytes" not in utils
        # Type annotations like `ethers.BigNumber` are edge cases
        # not handled by deterministic rules (ast-grep limitation in type position)

        contract = (v5_project / "contract.ts").read_text(encoding="utf-8")
        assert "contract.signer" not in contract
        assert "contract.runner" in contract

        # Stage 5: Verify
        verifier = Verifier(v5_project)
        report = verifier.verify(test_command=None)

        assert report.syntax_valid
        assert report.no_v5_patterns

        # Stage 6: Report
        reporter = MigrationReporter(
            detection_report=detection,
            codemod_stats=codemod_stats,
            verifier_report=report,
        )
        md = reporter.generate_markdown()
        assert "ethers.js v5 -> v6 Migration Report" in md
        assert "Coverage Metrics" in md

        json_report = reporter.generate_json()
        assert '"coverage"' in json_report

    def test_dry_run_leaves_files_intact(self, v5_project: Path):
        original = (v5_project / "utils.ts").read_text(encoding="utf-8")

        engine = CodemodEngine(v5_project)
        engine.apply_all(dry_run=True)

        after = (v5_project / "utils.ts").read_text(encoding="utf-8")
        assert after == original

    def test_idempotency_on_fixture(self, v5_project: Path):
        engine1 = CodemodEngine(v5_project)
        engine1.apply_all(dry_run=False)
        first = (v5_project / "utils.ts").read_text(encoding="utf-8")

        engine2 = CodemodEngine(v5_project)
        stats2 = engine2.apply_all(dry_run=False)
        second = (v5_project / "utils.ts").read_text(encoding="utf-8")

        assert first == second
        assert stats2.total_changes == 0

    def test_reporter_metrics(self, v5_project: Path):
        detector = EthersDetector(v5_project)
        detection = detector.detect()

        engine = CodemodEngine(v5_project)
        stats = engine.apply_all(dry_run=True)

        reporter = MigrationReporter(detection_report=detection, codemod_stats=stats)
        metrics = reporter.generate_metrics()

        assert metrics.total_patterns > 0
        assert metrics.deterministic_transforms > 0
        assert metrics.false_positives == 0
