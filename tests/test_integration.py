"""Integration tests for end-to-end migration."""

import pytest
import subprocess
import tempfile
from pathlib import Path

from brownie2ape.pattern_detector import PatternDetector
from brownie2ape.codemod_engine import CodemodEngine
from brownie2ape.reporter import MigrationReporter


class TestEndToEndMigration:
    """End-to-end integration tests."""

    @pytest.fixture
    def mock_brownie_project(self):
        """Create a mock Brownie project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)

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

            yield project_path

    def test_full_migration_workflow(self, mock_brownie_project):
        """Test complete migration workflow."""
        detector = PatternDetector(mock_brownie_project)
        report = detector.scan_repository()

        assert report.total_files >= 2
        assert "import" in report.patterns_detected

    def test_pattern_detection_on_real_code(self, mock_brownie_project):
        """Test pattern detection on realistic code."""
        detector = PatternDetector(mock_brownie_project)
        report = detector.scan_repository()

        assert report.files_with_brownie >= 1
        assert len(report.matches) >= 3

    def test_coverage_calculation(self, mock_brownie_project):
        """Test coverage calculation accuracy."""
        detector = PatternDetector(mock_brownie_project)
        report = detector.scan_repository()

        assert 0 <= report.estimated_coverage <= 100
        assert isinstance(report.estimated_coverage, float)


class TestReporterIntegration:
    """Test reporter with real data."""

    def test_generate_json_report(self, mock_brownie_project):
        """Test JSON report generation."""
        from brownie2ape.codemod_engine import MigrationStats

        detector = PatternDetector(mock_brownie_project)
        analysis = detector.scan_repository()
        stats = MigrationStats(files_modified=1, total_changes=2)

        reporter = MigrationReporter(analysis, stats)
        json_report = reporter.generate_json()

        assert "analysis" in json_report
        assert "coverage" in json_report

    def test_generate_markdown_report(self, mock_brownie_project):
        """Test Markdown report generation."""
        from brownie2ape.codemod_engine import MigrationStats

        detector = PatternDetector(mock_brownie_project)
        analysis = detector.scan_repository()
        stats = MigrationStats(files_modified=1, total_changes=2)

        reporter = MigrationReporter(analysis, stats)
        md_report = reporter.generate_markdown()

        assert "## Analysis Summary" in md_report
        assert "Brownie → Ape Framework Migration Report" in md_report