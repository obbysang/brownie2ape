"""Tests for ethers5to6 Stage 1 — Detector."""

import pytest
from pathlib import Path

from ethers5to6.detector import EthersDetector, DetectionReport


class TestEthersDetector:
    def test_detects_imports(self, tmp_path: Path):
        file = tmp_path / "utils.ts"
        file.write_text('import { ethers } from "ethers";\n')

        det = EthersDetector(tmp_path)
        report = det.detect()

        assert report.total_files >= 1
        assert len(report.imports) >= 1
        assert any("import" in p.pattern_type for p in report.imports)

    def test_detects_providers(self, tmp_path: Path):
        file = tmp_path / "provider.ts"
        file.write_text(
            'import { ethers } from "ethers";\n'
            'const p = new ethers.providers.Web3Provider(window.ethereum);\n'
        )

        det = EthersDetector(tmp_path)
        report = det.detect()

        assert len(report.provider_usage) >= 1
        assert any("Web3Provider" in p.matched_text for p in report.provider_usage)

    def test_detects_utils(self, tmp_path: Path):
        file = tmp_path / "utils.ts"
        file.write_text(
            'import { ethers } from "ethers";\n'
            'const hash = ethers.utils.keccak256("0x00");\n'
        )

        det = EthersDetector(tmp_path)
        report = det.detect()

        assert len(report.utils_usage) >= 1

    def test_detects_bignum(self, tmp_path: Path):
        file = tmp_path / "math.ts"
        file.write_text(
            'import { ethers } from "ethers";\n'
            'const x = ethers.BigNumber.from(100);\n'
        )

        det = EthersDetector(tmp_path)
        report = det.detect()

        assert len(report.bignum_usage) >= 1

    def test_skips_node_modules(self, tmp_path: Path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "lib.ts").write_text('import { ethers } from "ethers";\n')

        det = EthersDetector(tmp_path)
        report = det.detect()

        assert len(report.imports) == 0

    def test_report_json(self, tmp_path: Path):
        file = tmp_path / "a.ts"
        file.write_text('import { ethers } from "ethers";\n')

        det = EthersDetector(tmp_path)
        report = det.detect()
        json_str = report.to_json()

        assert '"total_files"' in json_str
        assert '"imports"' in json_str

    def test_detects_on_real_fixture(self):
        fixture = Path(__file__).parent / "fixtures" / "sample_v5_project"
        if not fixture.exists():
            pytest.skip("Fixture not found")

        det = EthersDetector(fixture)
        report = det.detect()

        assert report.files_with_ethers >= 1
        assert len(report.provider_usage) >= 1
        assert len(report.utils_usage) >= 1
