"""Core codemod engine using ast-grep (jssg) for deterministic transformations."""

import os
import subprocess
import json
import re
from pathlib import Path
from typing import Optional
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
    """AST-based codemod engine using ast-grep (jssg)."""

    def __init__(self, project_root: Path, rules_dir: Path):
        self.project_root = project_root
        self.rules_dir = rules_dir
        self.stats = MigrationStats()

    def run_codemod(self, rule_id: str, dry_run: bool = True) -> list[CodemodResult]:
        """Run a single codemod rule on the project using ast-grep."""
        results = []

        config_file = self.rules_dir / "rules.yaml"
        if not config_file.exists():
            results.append(CodemodResult(
                file_path="",
                rule_name=rule_id,
                changes_made=0,
                status="failed",
                error="Rules file not found"
            ))
            return results

        try:
            if dry_run:
                cmd = ["sg", "scan", "--config", str(config_file), "--json", "-r", rule_id]
            else:
                cmd = ["sg", "apply", "--config", str(config_file), "-r", rule_id]

            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0 and "no matches found" not in result.stderr.lower():
                results.append(CodemodResult(
                    file_path="",
                    rule_name=rule_id,
                    changes_made=0,
                    status="failed",
                    error=result.stderr[:200] if result.stderr else "Unknown error"
                ))
                return results

            matches = self._parse_output(result.stdout + result.stderr)
            for match in matches:
                results.append(CodemodResult(
                    file_path=match.get("file", ""),
                    rule_name=rule_id,
                    changes_made=match.get("count", 1),
                    status="success"
                ))

            if not matches:
                results.append(CodemodResult(
                    file_path="",
                    rule_name=rule_id,
                    changes_made=0,
                    status="skipped",
                    error="No matches found"
                ))

        except FileNotFoundError:
            results.append(CodemodResult(
                file_path="",
                rule_name=rule_id,
                changes_made=0,
                status="failed",
                error="ast-grep (sg) not installed. Run: cargo install ast-grep"
            ))
        except subprocess.TimeoutExpired:
            results.append(CodemodResult(
                file_path="",
                rule_name=rule_id,
                changes_made=0,
                status="failed",
                error="Timeout"
            ))
        except Exception as e:
            results.append(CodemodResult(
                file_path="",
                rule_name=rule_id,
                changes_made=0,
                status="failed",
                error=str(e)
            ))

        return results

    def _parse_output(self, output: str) -> list[dict]:
        """Parse ast-grep output to extract matches."""
        matches = []

        try:
            if output.strip().startswith("["):
                data = json.loads(output)
                if isinstance(data, list):
                    for item in data:
                        matches.append({
                            "file": item.get("file_path", item.get("path", "")),
                            "count": 1
                        })
        except json.JSONDecodeError:
            pass

        file_pattern = re.compile(r"(\S+\.py):(\d+):(\d+):")
        for line in output.split("\n"):
            match = file_pattern.search(line)
            if match:
                matches.append({"file": match.group(1), "count": 1})

        return matches

    def apply_all_codemods(self, dry_run: bool = True) -> MigrationStats:
        """Apply all registered codemods to the project."""
        rule_ids = self.get_rule_id_list()

        for rule_id in rule_ids:
            console.print(f"[cyan]Running:[/cyan] {rule_id}")
            results = self.run_codemod(rule_id, dry_run)
            self.stats.codemod_results.extend(results)
            self.stats.total_changes += sum(r.changes_made for r in results)

        self.stats.files_modified = len(set(
            r.file_path for r in self.stats.codemod_results
            if r.file_path and r.status == "success"
        ))

        return self.stats

    def get_rule_id_list(self) -> list[str]:
        """Get list of rule IDs to run."""
        return [
            "brownie-import-network",
            "brownie-import-accounts",
            "brownie-import-project",
            "brownie-eth-usage",
            "network-connect",
            "network-eth-accounts",
            "project-contract-container",
            "brownie-chain-api",
            "web3-eth-replace",
            "brownie-config-replace",
        ]

    def get_codemod_list(self) -> list[dict]:
        """Get list of available codemods from YAML rules."""
        config_file = self.rules_dir / "rules.yaml"
        if not config_file.exists():
            return []

        try:
            import yaml
            with open(config_file) as f:
                data = yaml.safe_load(f)

            rules = data.get("rules", [])
            return [{"name": r["id"], "description": r.get("message", "")} for r in rules]
        except Exception:
            return []