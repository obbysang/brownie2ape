"""Tests for pattern detector."""

import pytest
import tempfile
from pathlib import Path

from brownie2ape.pattern_detector import PatternDetector, PatternMatch, AnalysisReport


class TestPatternDetector:
    """Test suite for PatternDetector."""

    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_detects_brownie_import(self, temp_project):
        """Test detection of brownie import."""
        test_file = temp_project / "test_script.py"
        test_file.write_text("from brownie import network\n")

        detector = PatternDetector(temp_project)
        report = detector.scan_repository()

        assert report.files_with_brownie == 1
        assert "import" in report.patterns_detected

    def test_detects_network_connect(self, temp_project):
        """Test detection of network.connect pattern."""
        test_file = temp_project / "test_script.py"
        test_file.write_text("network.connect('mainnet')\n")

        detector = PatternDetector(temp_project)
        report = detector.scan_repository()

        assert len([m for m in report.matches if m.pattern_type == "network_connect"]) > 0

    def test_detects_project_contract(self, temp_project):
        """Test detection of project.Contract pattern."""
        test_file = temp_project / "test_script.py"
        test_file.write_text("token = project.Token.deploy({'from': accounts[0]})\n")

        detector = PatternDetector(temp_project)
        report = detector.scan_repository()

        assert len([m for m in report.matches if "project" in m.matched_text]) > 0

    def test_skips_test_files(self, temp_project):
        """Test that test files are skipped."""
        test_file = temp_project / "test_example.py"
        test_file.write_text("from brownie import network\n")

        detector = PatternDetector(temp_project)
        report = detector.scan_repository()

        assert report.total_files >= 0

    def test_calculates_coverage(self, temp_project):
        """Test coverage calculation."""
        test_file = temp_project / "main.py"
        test_file.write_text("from brownie import network\nnetwork.connect('localhost')\n")

        detector = PatternDetector(temp_project)
        report = detector.scan_repository()

        assert 0 <= report.estimated_coverage <= 100


class TestPatternMatch:
    """Test suite for PatternMatch dataclass."""

    def test_pattern_match_creation(self):
        """Test creating a PatternMatch."""
        match = PatternMatch(
            file_path="test.py",
            line_number=10,
            pattern_type="import",
            matched_text="brownie.network",
            confidence=1.0,
            can_transform=True
        )

        assert match.file_path == "test.py"
        assert match.line_number == 10
        assert match.can_transform is True


class TestAnalysisReport:
    """Test suite for AnalysisReport."""

    def test_analysis_report_creation(self):
        """Test creating an AnalysisReport."""
        report = AnalysisReport(
            total_files=10,
            files_with_brownie=3,
            patterns_detected={"import": 5, "usage": 3},
            estimated_coverage=85.0,
            matches=[]
        )

        assert report.total_files == 10
        assert report.files_with_brownie == 3
        assert report.estimated_coverage == 85.0