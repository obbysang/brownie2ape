"""Pattern detection and analysis module."""

import ast
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class PatternMatch:
    """A detected pattern in the codebase."""
    file_path: str
    line_number: int
    pattern_type: str
    matched_text: str
    confidence: float  # 0.0 to 1.0
    can_transform: bool  # True if deterministic transform available


@dataclass
class AnalysisReport:
    """Full analysis of a repository."""
    total_files: int
    files_with_brownie: int
    patterns_detected: dict[str, int]  # pattern_type -> count
    estimated_coverage: float  # percentage of patterns with deterministic transforms
    matches: list[PatternMatch]


class PatternDetector:
    """Detects Brownie patterns in Python code."""

    BROWNIE_PATTERNS = {
        "imports": [
            "brownie",
            "brownie.network",
            "brownie.project",
            "brownie.network.account",
            "brownie.network.eth",
            "brownie._config",
        ],
        "usages": [
            "brownie.eth",
            "network.connect",
            "network.eth",
            "accounts",
            "ChainAPI",
            "BrownieProject",
            "ContractContainer",
            "web3.eth",
        ],
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.matches: list[PatternMatch] = []

    def scan_repository(self) -> AnalysisReport:
        """Scan entire repository for Brownie patterns."""
        py_files = list(self.project_root.rglob("*.py"))
        patterns_found: dict[str, int] = defaultdict(int)

        for py_file in py_files:
            if self._should_skip(py_file):
                continue

            file_matches = self._scan_file(py_file)
            self.matches.extend(file_matches)

            for match in file_matches:
                patterns_found[match.pattern_type] += 1

        files_with_brownie = len(set(m.file_path for m in self.matches))

        deterministic_patterns = sum(1 for m in self.matches if m.can_transform)
        total_patterns = len(self.matches)
        estimated_coverage = (deterministic_patterns / total_patterns * 100) if total_patterns > 0 else 0

        return AnalysisReport(
            total_files=len(py_files),
            files_with_brownie=files_with_brownie,
            patterns_detected=dict(patterns_found),
            estimated_coverage=estimated_coverage,
            matches=self.matches
        )

    def _should_skip(self, path: Path) -> bool:
        """Check if file should be skipped."""
        skip_dirs = {".git", "__pycache__", ".pytest_cache", "node_modules", "venv", ".venv", "tests"}

        if any(part in skip_dirs for part in path.parts):
            return True
        return False

    def _scan_file(self, path: Path) -> list[PatternMatch]:
        """Scan a single file for Brownie patterns."""
        matches = []

        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (SyntaxError, UnicodeDecodeError):
            return matches

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for pattern in self.BROWNIE_PATTERNS["imports"]:
                        if alias.name.startswith(pattern):
                            matches.append(PatternMatch(
                                file_path=str(path),
                                line_number=node.lineno or 0,
                                pattern_type="import",
                                matched_text=alias.name,
                                confidence=1.0,
                                can_transform=True
                            ))

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for pattern in self.BROWNIE_PATTERNS["imports"]:
                        if node.module.startswith(pattern):
                            matches.append(PatternMatch(
                                file_path=str(path),
                                line_number=node.lineno or 0,
                                pattern_type="import",
                                matched_text=node.module,
                                confidence=1.0,
                                can_transform=True
                            ))

        content_matches = self._scan_content_strings(content, str(path))
        matches.extend(content_matches)

        return matches

    def _scan_content_strings(self, content: str, file_path: str) -> list[PatternMatch]:
        """Scan for Brownie patterns in string content."""
        matches = []

        usage_patterns = [
            ("brownie.eth", "brownie_eth_address"),
            ("network.connect", "network_connect"),
            ("network.eth.accounts", "network_eth_account"),
            ("ChainAPI", "brownie_chain_api"),
            ("web3.eth", "web3_eth_import"),
            ("project.", "project_contract_container"),
        ]

        for line_num, line in enumerate(content.split("\n"), 1):
            for pattern, pattern_type in usage_patterns:
                if pattern in line:
                    matches.append(PatternMatch(
                        file_path=file_path,
                        line_number=line_num,
                        pattern_type=pattern_type,
                        matched_text=pattern,
                        confidence=0.9,
                        can_transform=pattern_type in self._get_transformable_patterns()
                    ))

        return matches

    def _get_transformable_patterns(self) -> set[str]:
        """Get set of patterns that have deterministic transforms."""
        return {
            "brownie_eth_address",
            "network_connect",
            "network_eth_account",
            "brownie_chain_api",
            "web3_eth_import",
            "project_contract_container",
        }