"""Test harness for validating migrations on real repositories."""

import subprocess
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class ValidationResult:
    """Result of validation run."""
    success: bool
    output: str
    files_changed: int
    tests_passed: int
    tests_failed: int
    build_success: bool
    errors: list[str]


class TestHarness:
    """Validates migration results against real test suites."""

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run_validation(self, test_command: str = "pytest") -> dict:
        """Run validation tests on migrated code."""
        results = {
            "success": False,
            "output": "",
            "files_changed": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "build_success": False,
            "errors": []
        }

        results["build_success"] = self._check_build()
        if not results["build_success"]:
            results["errors"].append("Build failed")

        test_result = self._run_tests(test_command)
        results["tests_passed"] = test_result.get("passed", 0)
        results["tests_failed"] = test_result.get("failed", 0)
        results["output"] = test_result.get("output", "")

        results["files_changed"] = self._count_changed_files()

        results["success"] = results["build_success"] and results["tests_failed"] == 0

        return results

    def _check_build(self) -> bool:
        """Check if project builds successfully."""
        build_commands = ["python -m py_compile .", "python setup.py check"]

        for cmd in build_commands:
            try:
                result = subprocess.run(
                    cmd.split(),
                    cwd=self.project_root,
                    capture_output=True,
                    timeout=60
                )
                if result.returncode != 0:
                    return False
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue

        return True

    def _run_tests(self, test_command: str) -> dict:
        """Run test suite and parse results."""
        try:
            result = subprocess.run(
                test_command.split(),
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            output = result.stdout + result.stderr

            passed = output.count(" PASSED")
            failed = output.count(" FAILED")

            if "passed" in output.lower():
                import re
                match = re.search(r"(\d+) passed", output)
                if match:
                    passed = int(match.group(1))

            return {
                "passed": passed,
                "failed": failed,
                "output": output,
                "returncode": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {"passed": 0, "failed": 0, "output": "Test timeout", "returncode": -1}
        except FileNotFoundError:
            return {"passed": 0, "failed": 0, "output": "Test command not found", "returncode": -1}

    def _count_changed_files(self) -> int:
        """Count files that were modified by migration."""
        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            return 0

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            return len([l for l in result.stdout.strip().split("\n") if l])
        except FileNotFoundError:
            return 0

    def validate_syntax(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """Validate Python syntax of a single file."""
        try:
            compile(file_path.read_text(), str(file_path), "exec")
            return True, None
        except SyntaxError as e:
            return False, str(e)

    def rollback_last_change(self) -> bool:
        """Rollback the last migration change."""
        try:
            subprocess.run(
                ["git", "checkout", "--", "."],
                cwd=self.project_root,
                capture_output=True
            )
            return True
        except FileNotFoundError:
            return False


class DryRunValidator:
    """Validates changes without applying them."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.issues: list[dict] = []

    def validate_codemod(self, codemod_result: dict) -> bool:
        """Validate a single codemod change."""
        file_path = self.project_root / codemod_result.get("file", "")

        if not file_path.exists():
            self.issues.append({
                "type": "missing_file",
                "file": str(file_path)
            })
            return False

        is_valid, error = self._validate_syntax(file_path)
        if not is_valid:
            self.issues.append({
                "type": "syntax_error",
                "file": str(file_path),
                "error": error
            })
            return False

        return True

    def _validate_syntax(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """Validate file syntax."""
        try:
            compile(file_path.read_text(), str(file_path), "exec")
            return True, None
        except SyntaxError as e:
            return False, str(e)

    def get_report(self) -> dict:
        """Get validation report."""
        return {
            "total_issues": len(self.issues),
            "issues": self.issues,
            "valid": len(self.issues) == 0
        }