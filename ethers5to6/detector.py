"""Stage 1 — Static Detection (no transforms).

Traverses JS/TS files to collect all ethers.js v5 usage patterns
without modifying any code.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ethers5to6._sg import run_sg, _parse_sg_json_lines


@dataclass
class DetectedPattern:
    file_path: str
    line_number: int
    column: int
    pattern_type: str
    matched_text: str
    rule_id: Optional[str] = None


@dataclass
class DetectionReport:
    total_files: int = 0
    files_with_ethers: int = 0
    imports: list[DetectedPattern] = field(default_factory=list)
    utils_usage: list[DetectedPattern] = field(default_factory=list)
    provider_usage: list[DetectedPattern] = field(default_factory=list)
    contract_usage: list[DetectedPattern] = field(default_factory=list)
    bignum_usage: list[DetectedPattern] = field(default_factory=list)
    other_patterns: list[DetectedPattern] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_files": self.total_files,
            "files_with_ethers": self.files_with_ethers,
            "imports": [self._pattern_to_dict(p) for p in self.imports],
            "utils_usage": [self._pattern_to_dict(p) for p in self.utils_usage],
            "provider_usage": [self._pattern_to_dict(p) for p in self.provider_usage],
            "contract_usage": [self._pattern_to_dict(p) for p in self.contract_usage],
            "bignum_usage": [self._pattern_to_dict(p) for p in self.bignum_usage],
            "other_patterns": [self._pattern_to_dict(p) for p in self.other_patterns],
        }

    @staticmethod
    def _pattern_to_dict(p: DetectedPattern) -> dict:
        return {
            "file_path": p.file_path,
            "line_number": p.line_number,
            "column": p.column,
            "pattern_type": p.pattern_type,
            "matched_text": p.matched_text,
            "rule_id": p.rule_id,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class EthersDetector:
    """Detects ethers.js v5 patterns in JavaScript/TypeScript code."""

    _GLOBS = ("*.js", "*.ts", "*.jsx", "*.tsx", "*.mjs", "*.cjs")
    _SKIP_DIRS = {
        "node_modules", ".git", "dist", "build", "coverage",
        ".next", ".nuxt", "out", "public", "static",
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.report = DetectionReport()

    def detect(self) -> DetectionReport:
        """Run full detection scan."""
        files = self._collect_files()
        self.report.total_files = len(files)

        for file_path in files:
            self._scan_file(file_path)

        self.report.files_with_ethers = len({
            p.file_path for group in (
                self.report.imports,
                self.report.utils_usage,
                self.report.provider_usage,
                self.report.contract_usage,
                self.report.bignum_usage,
                self.report.other_patterns,
            )
            for p in group
        })

        return self.report

    def _collect_files(self) -> list[Path]:
        files: list[Path] = []
        for glob in self._GLOBS:
            for f in self.project_root.rglob(glob):
                if any(part in self._SKIP_DIRS for part in f.parts):
                    continue
                files.append(f)
        return files

    def _scan_file(self, file_path: Path) -> None:
        content = file_path.read_text(encoding="utf-8")

        # Fast path: skip files that don't mention "ethers" at all
        if "ethers" not in content:
            return

        rules = _get_detection_rules()
        for rule in rules:
            matches = self._run_sg_rule(file_path, rule)
            for match in matches:
                pattern = DetectedPattern(
                    file_path=str(file_path),
                    line_number=match.get("line", 0),
                    column=match.get("column", 0),
                    pattern_type=rule["category"],
                    matched_text=match.get("text", ""),
                    rule_id=rule["id"],
                )
                self._categorize_pattern(pattern)

    def _categorize_pattern(self, pattern: DetectedPattern) -> None:
        cat = pattern.pattern_type
        if cat == "import":
            self.report.imports.append(pattern)
        elif cat == "utils":
            self.report.utils_usage.append(pattern)
        elif cat == "provider":
            self.report.provider_usage.append(pattern)
        elif cat == "contract":
            self.report.contract_usage.append(pattern)
        elif cat == "bignum":
            self.report.bignum_usage.append(pattern)
        else:
            self.report.other_patterns.append(pattern)

    def _run_sg_rule(self, file_path: Path, rule: dict) -> list[dict]:
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yml", delete=False
            ) as tf:
                tf.write(_build_sg_rule_yaml(rule))
                tf.flush()
                rule_path = Path(tf.name)

            result = run_sg(
                ["scan", "--rule", str(rule_path), "--json", str(file_path)]
            )
            rule_path.unlink(missing_ok=True)

            if result.returncode not in (0, 1):
                return []

            return _parse_sg_json_lines(result.stdout)
        except Exception:
            return []


def _get_detection_rules() -> list[dict]:
    """Return detection-only ast-grep rules."""
    return [
        # Imports
        {"id": "import-ethers-esm", "category": "import", "language": "ts",
         "pattern": 'import { ethers } from "ethers"'},
        {"id": "import-ethers-cjs", "category": "import", "language": "ts",
         "pattern": 'const ethers = require("ethers")'},
        {"id": "import-providers-deep", "category": "import", "language": "ts",
         "pattern": 'import { $ARG } from "ethers/lib/utils"'},
        {"id": "import-providers-old", "category": "import", "language": "ts",
         "pattern": 'import { providers } from "ethers"'},
        # Utils namespace
        {"id": "utils-namespace", "category": "utils", "language": "ts",
         "pattern": "ethers.utils.$FUNC"},
        # Providers namespace
        {"id": "providers-namespace", "category": "provider", "language": "ts",
         "pattern": "ethers.providers.$PROV"},
        # BigNumber
        {"id": "bignum-from", "category": "bignum", "language": "ts",
         "pattern": "ethers.BigNumber.from($ARG)"},
        {"id": "bignum-arith-add", "category": "bignum", "language": "ts",
         "pattern": "$X.add($ARG)"},
        {"id": "bignum-arith-mul", "category": "bignum", "language": "ts",
         "pattern": "$X.mul($ARG)"},
        # Contract
        {"id": "contract-new", "category": "contract", "language": "ts",
         "pattern": "new ethers.Contract($ARG)"},
        {"id": "contract-signer", "category": "contract", "language": "ts",
         "pattern": "$CONTRACT.signer"},
        {"id": "contract-provider", "category": "contract", "language": "ts",
         "pattern": "$CONTRACT.provider"},
    ]


def _build_sg_rule_yaml(rule: dict) -> str:
    lines = [
        f"id: {rule['id']}",
        f"language: {rule['language']}",
        "rule:",
        f"  pattern: {rule['pattern']}",
    ]
    return "\n".join(lines) + "\n"
