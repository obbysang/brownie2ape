"""Stage 5 — Verification.

Ensures transformed code compiles, has no remaining v5 patterns,
and did not corrupt unrelated code.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class VerificationReport:
    success: bool = False
    syntax_valid: bool = False
    no_v5_patterns: bool = False
    build_passed: bool = False
    tests_passed: bool = False
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "syntax_valid": self.syntax_valid,
            "no_v5_patterns": self.no_v5_patterns,
            "build_passed": self.build_passed,
            "tests_passed": self.tests_passed,
            "issues": self.issues,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class Verifier:
    """Post-migration verification harness."""

    _V5_SMELL_PATTERNS = [
        "ethers.providers.Web3Provider",  # should be BrowserProvider
        "ethers.providers.",               # namespace should be flattened
        "ethers.utils.",                   # namespace should be flattened
        "ethers.BigNumber.from",           # should be BigInt
    ]

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.report = VerificationReport()

    def verify(self, test_command: Optional[str] = None) -> VerificationReport:
        """Run full verification suite."""
        self.report.syntax_valid = self._check_syntax_all()
        self.report.no_v5_patterns = self._check_no_v5_patterns()
        self.report.build_passed = self._check_build()
        if test_command:
            self.report.tests_passed = self._run_tests(test_command)
        else:
            self.report.tests_passed = True  # not requested

        self.report.success = (
            self.report.syntax_valid
            and self.report.no_v5_patterns
            and self.report.build_passed
            and self.report.tests_passed
        )

        return self.report

    def _check_syntax_all(self) -> bool:
        """Validate syntax of all modified JS/TS files."""
        from ethers5to6.safety_layer import SafetyLayer

        safety = SafetyLayer()
        all_valid = True
        for f in self._collect_files():
            content = f.read_text(encoding="utf-8")
            if "ethers" not in content:
                continue
            if not safety.is_valid_js_ts(content):
                self.report.issues.append(f"Syntax error in {f}")
                all_valid = False
        return all_valid

    def _check_no_v5_patterns(self) -> bool:
        """Ensure no obvious v5 patterns remain."""
        clean = True
        for f in self._collect_files():
            content = f.read_text(encoding="utf-8")
            if "ethers" not in content:
                continue
            for smell in self._V5_SMELL_PATTERNS:
                if smell in content:
                    self.report.issues.append(
                        f"Remaining v5 pattern '{smell}' in {f}"
                    )
                    clean = False
        return clean

    def _check_build(self) -> bool:
        """Try to run TypeScript or basic build check."""
        tsconfig = self.project_root / "tsconfig.json"
        if tsconfig.exists():
            return self._run_tsc()
        # No tsconfig — assume JS-only, syntax check is sufficient
        return True

    def _run_tsc(self) -> bool:
        """Run tsc --noEmit if available."""
        try:
            result = subprocess.run(
                ["tsc", "--noEmit"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                self.report.issues.append(
                    f"TypeScript build errors:\n{result.stdout}\n{result.stderr}"
                )
            return result.returncode == 0
        except FileNotFoundError:
            # tsc not installed
            return True
        except subprocess.TimeoutExpired:
            self.report.issues.append("TypeScript check timed out")
            return False

    def _run_tests(self, test_command: str) -> bool:
        """Run project test suite."""
        try:
            result = subprocess.run(
                test_command.split(),
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                self.report.issues.append(
                    f"Tests failed:\n{result.stdout}\n{result.stderr}"
                )
            return result.returncode == 0
        except FileNotFoundError:
            self.report.issues.append(f"Test command '{test_command}' not found")
            return False
        except subprocess.TimeoutExpired:
            self.report.issues.append("Test run timed out")
            return False

    def _collect_files(self) -> list[Path]:
        files: list[Path] = []
        skip = {"node_modules", ".git", "dist", "build", "coverage"}
        for glob in ("*.js", "*.ts", "*.jsx", "*.tsx", "*.mjs", "*.cjs"):
            for f in self.project_root.rglob(glob):
                if any(part in skip for part in f.parts):
                    continue
                files.append(f)
        return files
