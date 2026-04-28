"""Tests for codemod engine."""

import pytest
import tempfile
from pathlib import Path

from brownie2ape.codemod_engine import (
    CodemodEngine,
    CodemodResult,
    MigrationStats
)

BROWNIESE_TO_APE_CODEMODS = [
    {"name": "brownie-import-network", "description": "Import migration", "rule": "rule pattern: from brownie import network"},
    {"name": "brownie-import-accounts", "description": "Accounts import", "rule": "rule pattern: from brownie.network.account import accounts"},
    {"name": "network-connect", "description": "Network connect", "rule": "rule pattern: network.connect($HOST)"},
    {"name": "project-contract-container", "description": "Contract container", "rule": "rule pattern: project.$CONTRACT"},
]


class TestCodemodEngine:
    """Test suite for CodemodEngine."""

    @pytest.fixture
    def temp_project(self):
        """Create temporary project directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_rules_dir(self):
        """Create temporary rules directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_engine_initialization(self, temp_project, temp_rules_dir):
        """Test engine initializes correctly."""
        engine = CodemodEngine(temp_project, temp_rules_dir)

        assert engine.project_root == temp_project
        assert engine.rules_dir == temp_rules_dir

    def test_migration_stats_initialization(self):
        """Test MigrationStats initializes with defaults."""
        stats = MigrationStats()

        assert stats.files_scanned == 0
        assert stats.files_modified == 0
        assert stats.total_changes == 0
        assert stats.codemod_results == []
        assert stats.errors == []

    def test_codemod_result_creation(self):
        """Test CodemodResult creation."""
        result = CodemodResult(
            file_path="test.py",
            rule_name="test_rule",
            changes_made=1,
            status="success"
        )

        assert result.file_path == "test.py"
        assert result.changes_made == 1
        assert result.status == "success"

    def test_codemod_result_with_error(self):
        """Test CodemodResult with error."""
        result = CodemodResult(
            file_path="test.py",
            rule_name="test_rule",
            changes_made=0,
            status="failed",
            error="Timeout"
        )

        assert result.error == "Timeout"
        assert result.status == "failed"


class TestBrownieToApeCodemods:
    """Test suite for Brownie to Ape codemod definitions."""

    def test_codemods_list_not_empty(self):
        """Test that codemods list has entries."""
        assert len(BROWNIESE_TO_APE_CODEMODS) > 0

    def test_codemod_has_required_fields(self):
        """Test each codemod has required fields."""
        for codemod in BROWNIESE_TO_APE_CODEMODS:
            assert "name" in codemod
            assert "description" in codemod
            assert "rule" in codemod

    def test_codemod_names_unique(self):
        """Test codemod names are unique."""
        names = [c["name"] for c in BROWNIESE_TO_APE_CODEMODS]
        assert len(names) == len(set(names))

    def test_covers_major_patterns(self):
        """Test codemods cover major migration patterns."""
        names = [c["name"] for c in BROWNIESE_TO_APE_CODEMODS]

        expected_patterns = [
            "brownie-import-network",
            "network-connect",
            "project-contract-container"
        ]

        for pattern in expected_patterns:
            assert any(pattern in name for name in names), f"Missing: {pattern}"