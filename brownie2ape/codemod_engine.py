"""Core codemod engine using AST-based transformations for Brownie to Ape migration."""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass, field
from rich.console import Console
from rich.table import Table

console = Console()


@dataclass
class CodemodResult:
    """Result of a single codemod transformation."""
    file_path: str
    rule_name: str
    changes_made: int
    status: str  # "success", "failed", "skipped"
    error: Optional[str] = None


@dataclass
class MigrationStats:
    """Statistics for a migration run."""
    files_scanned: int = 0
    files_modified: int = 0
    total_changes: int = 0
    codemod_results: list = field(default_factory=list)
    errors: list = field(default_factory=list)


class CodemodEngine:
    """Python AST-based codemod engine for deterministic transformations."""

    TRANSFORMATIONS = [
        {
            "id": "brownie-import-network",
            "pattern": re.compile(r"from\s+brownie\s+import\s+([^#\n]+)"),
            "replacement": lambda m: "from brownie import " + m.group(1).replace("network", "account"),
            "description": "Migrate 'from brownie import network'"
        },
        {
            "id": "brownie-import-accounts",
            "pattern": re.compile(r"from\s+brownie\.network\.account\s+import\s+accounts\b"),
            "replacement": "from ape import accounts",
            "description": "Migrate 'from brownie.network.account import accounts'"
        },
        {
            "id": "brownie-network-account-import",
            "pattern": re.compile(r"from\s+brownie\.network\.account\s+import\s+(\w+)"),
            "replacement": "from ape import account",
            "description": "Migrate 'from brownie.network.account import X'"
        },
        {
            "id": "brownie-network-eth-import",
            "pattern": re.compile(r"from\s+brownie\.network\.eth\s+import\s+(\w+)"),
            "replacement": "from ape import eth",
            "description": "Migrate 'from brownie.network.eth import X'"
        },
        {
            "id": "brownie-import-project",
            "pattern": re.compile(r"import\s+brownie\.project\b"),
            "replacement": "import ape.project",
            "description": "Migrate 'import brownie.project'"
        },
        {
            "id": "brownie-eth-usage",
            "pattern": re.compile(r"\bbrownie\.eth\b"),
            "replacement": "ape.eth",
            "description": "Migrate 'brownie.eth'"
        },
        {
            "id": "network-connect",
            "pattern": re.compile(r"\bnetwork\.connect\(([^)]+)\)"),
            "replacement": r"chain.provider.connect(\1)",
            "description": "Migrate 'network.connect(...)'"
        },
        {
            "id": "network-eth-accounts",
            "pattern": re.compile(r"\bnetwork\.eth\.accounts\b"),
            "replacement": "account.accounts",
            "description": "Migrate 'network.eth.accounts'"
        },
        {
            "id": "brownie-chain-api",
            "pattern": re.compile(r"from\s+brownie\.network\.eth\s+import\s+ChainAPI\b"),
            "replacement": "from ape import api",
            "description": "Migrate 'from brownie.network.eth import ChainAPI'"
        },
        {
            "id": "web3-eth-replace",
            "pattern": re.compile(r"\bweb3\.eth\b"),
            "replacement": "chain",
            "description": "Migrate 'web3.eth'"
        },
        {
            "id": "brownie-config-replace",
            "pattern": re.compile(r"\bbrownie\._config\b"),
            "replacement": "ape.config",
            "description": "Migrate 'brownie._config'"
        },
        {
            "id": "brownie-network-transaction",
            "pattern": re.compile(r"from\s+brownie\.network\.transaction\s+import\s+(\w+)"),
            "replacement": "from ape import transactions",
            "description": "Migrate transaction imports"
        },
        {
            "id": "brownie-convert-import",
            "pattern": re.compile(r"from\s+brownie\.convert\s+import\s+(\w+)"),
            "replacement": "from ape import convert",
            "description": "Migrate convert imports"
        },
        {
            "id": "network-show-active",
            "pattern": re.compile(r"\bnetwork\.show_active\(\)"),
            "replacement": "chain.provider.network",
            "description": "Migrate 'network.show_active()'"
        },
        {
            "id": "config-networks",
            "pattern": re.compile(r"\bconfig\[.networks.\]\[network\.show_active\(\)\]"),
            "replacement": "chain.provider.network_config",
            "description": "Migrate config access"
        },
    ]

    def __init__(self, project_root: Path, rules_dir: Path):
        self.project_root = project_root
        self.rules_dir = rules_dir
        self.stats = MigrationStats()

    def run_codemod(self, transform: dict, dry_run: bool = True) -> list[CodemodResult]:
        """Run a single codemod transformation on the project."""
        results = []
        pattern = transform["pattern"]
        replacement = transform["replacement"]
        rule_id = transform["id"]

        py_files = list(self.project_root.rglob("*.py"))
        self.stats.files_scanned = len(py_files)

        for py_file in py_files:
            if any(part in {"__pycache__", ".git", "tests", "node_modules", "venv"} for part in py_file.parts):
                continue

            try:
                content = py_file.read_text(encoding="utf-8")
                new_content = content

                if callable(replacement):
                    new_content = pattern.sub(replacement, content)
                else:
                    new_content = pattern.sub(replacement, content)

                count = len(pattern.findall(content))

                if count > 0:
                    if dry_run:
                        results.append(CodemodResult(
                            file_path=str(py_file),
                            rule_name=rule_id,
                            changes_made=count,
                            status="dry-run"
                        ))
                    else:
                        py_file.write_text(new_content, encoding="utf-8")
                        results.append(CodemodResult(
                            file_path=str(py_file),
                            rule_name=rule_id,
                            changes_made=count,
                            status="success"
                        ))
            except Exception as e:
                results.append(CodemodResult(
                    file_path=str(py_file),
                    rule_name=rule_id,
                    changes_made=0,
                    status="failed",
                    error=str(e)
                ))

        return results

    def apply_all_codemods(self, dry_run: bool = True) -> MigrationStats:
        """Apply all registered codemods to the project."""
        for transform in self.TRANSFORMATIONS:
            console.print(f"[cyan]Running:[/cyan] {transform['description']}")
            results = self.run_codemod(transform, dry_run)
            self.stats.codemod_results.extend(results)
            self.stats.total_changes += sum(r.changes_made for r in results if r.status in ["success", "dry-run"])

        self.stats.files_modified = len(set(
            r.file_path for r in self.stats.codemod_results
            if r.file_path and r.status in ["success", "dry-run"] and r.changes_made > 0
        ))

        return self.stats

    def get_rule_id_list(self) -> list[str]:
        """Get list of rule IDs to run."""
        return [t["id"] for t in self.TRANSFORMATIONS]

    def get_codemod_list(self) -> list[dict]:
        """Get list of available codemods."""
        return [{"name": t["id"], "description": t["description"]} for t in self.TRANSFORMATIONS]