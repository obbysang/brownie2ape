"""Stage 2 — Deterministic Codemods.

Applies safe AST-based transformations using ast-grep (jssg).
Each rule is applied sequentially with idempotency checks.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ethers5to6._sg import sg_run_rewrite
from ethers5to6.safety_layer import SafetyLayer


@dataclass
class CodemodResult:
    file_path: str
    rule_id: str
    changes_made: int
    status: str  # "success", "failed", "skipped", "no-op"
    error: Optional[str] = None


@dataclass
class CodemodStats:
    files_scanned: int = 0
    files_modified: int = 0
    total_changes: int = 0
    rule_changes: dict[str, int] = field(default_factory=dict)
    results: list[CodemodResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# Ordered list of deterministic transformations.
# More specific rules run before generic ones to avoid conflicts.
DETERMINISTIC_RULES: list[dict] = [
    # ── Providers ────────────────────────────────────────────
    {
        "id": "provider-web3",
        "pattern": "ethers.providers.Web3Provider",
        "rewrite": "ethers.BrowserProvider",
        "description": "ethers.providers.Web3Provider -> ethers.BrowserProvider",
    },
    {
        "id": "provider-jsonrpc",
        "pattern": "ethers.providers.JsonRpcProvider",
        "rewrite": "ethers.JsonRpcProvider",
        "description": "ethers.providers.JsonRpcProvider stays flat",
    },
    {
        "id": "provider-flatten",
        "pattern": "ethers.providers.$PROV",
        "rewrite": "ethers.$PROV",
        "description": "ethers.providers.* -> ethers.*",
    },
    # ── Utils ────────────────────────────────────────────────
    {
        "id": "utils-parse-ether",
        "pattern": "ethers.utils.parseEther($ARG)",
        "rewrite": "ethers.parseEther($ARG)",
        "description": "Flatten parseEther",
    },
    {
        "id": "utils-format-ether",
        "pattern": "ethers.utils.formatEther($ARG)",
        "rewrite": "ethers.formatEther($ARG)",
        "description": "Flatten formatEther",
    },
    {
        "id": "utils-parse-units",
        "pattern": "ethers.utils.parseUnits($ARG)",
        "rewrite": "ethers.parseUnits($ARG)",
        "description": "Flatten parseUnits",
    },
    {
        "id": "utils-format-units",
        "pattern": "ethers.utils.formatUnits($ARG)",
        "rewrite": "ethers.formatUnits($ARG)",
        "description": "Flatten formatUnits",
    },
    {
        "id": "utils-keccak256",
        "pattern": "ethers.utils.keccak256($ARG)",
        "rewrite": "ethers.keccak256($ARG)",
        "description": "Flatten keccak256",
    },
    {
        "id": "utils-id",
        "pattern": "ethers.utils.id($ARG)",
        "rewrite": "ethers.id($ARG)",
        "description": "Flatten id",
    },
    {
        "id": "utils-solidity-keccak256",
        "pattern": "ethers.utils.solidityKeccak256($ARG)",
        "rewrite": "ethers.solidityPackedKeccak256($ARG)",
        "description": "solidityKeccak256 -> solidityPackedKeccak256",
    },
    {
        "id": "utils-solidity-pack",
        "pattern": "ethers.utils.solidityPack($ARG)",
        "rewrite": "ethers.solidityPacked($ARG)",
        "description": "solidityPack -> solidityPacked",
    },
    {
        "id": "utils-arrayify",
        "pattern": "ethers.utils.arrayify($ARG)",
        "rewrite": "ethers.getBytes($ARG)",
        "description": "arrayify -> getBytes",
    },
    {
        "id": "utils-hexlify",
        "pattern": "ethers.utils.hexlify($ARG)",
        "rewrite": "ethers.hexlify($ARG)",
        "description": "Flatten hexlify",
    },
    {
        "id": "utils-hex-value",
        "pattern": "ethers.utils.hexValue($ARG)",
        "rewrite": "ethers.hexlify($ARG)",
        "description": "hexValue -> hexlify",
    },
    {
        "id": "utils-hex-zero-pad",
        "pattern": "ethers.utils.hexZeroPad($ARG)",
        "rewrite": "ethers.zeroPadValue($ARG)",
        "description": "hexZeroPad -> zeroPadValue",
    },
    {
        "id": "utils-hex-strip-zeros",
        "pattern": "ethers.utils.hexStripZeros($ARG)",
        "rewrite": "ethers.stripZerosLeft($ARG)",
        "description": "hexStripZeros -> stripZerosLeft",
    },
    {
        "id": "utils-hex-data-length",
        "pattern": "ethers.utils.hexDataLength($ARG)",
        "rewrite": "ethers.dataLength($ARG)",
        "description": "hexDataLength -> dataLength",
    },
    {
        "id": "utils-hex-data-slice",
        "pattern": "ethers.utils.hexDataSlice($ARG)",
        "rewrite": "ethers.dataSlice($ARG)",
        "description": "hexDataSlice -> dataSlice",
    },
    {
        "id": "utils-to-utf8-bytes",
        "pattern": "ethers.utils.toUtf8Bytes($ARG)",
        "rewrite": "ethers.toUtf8Bytes($ARG)",
        "description": "Flatten toUtf8Bytes",
    },
    {
        "id": "utils-to-utf8-string",
        "pattern": "ethers.utils.toUtf8String($ARG)",
        "rewrite": "ethers.toUtf8String($ARG)",
        "description": "Flatten toUtf8String",
    },
    {
        "id": "utils-is-address",
        "pattern": "ethers.utils.isAddress($ARG)",
        "rewrite": "ethers.isAddress($ARG)",
        "description": "Flatten isAddress",
    },
    {
        "id": "utils-get-address",
        "pattern": "ethers.utils.getAddress($ARG)",
        "rewrite": "ethers.getAddress($ARG)",
        "description": "Flatten getAddress",
    },
    {
        "id": "utils-compute-address",
        "pattern": "ethers.utils.computeAddress($ARG)",
        "rewrite": "ethers.computeAddress($ARG)",
        "description": "Flatten computeAddress",
    },
    {
        "id": "utils-recover-address",
        "pattern": "ethers.utils.recoverAddress($ARG)",
        "rewrite": "ethers.recoverAddress($ARG)",
        "description": "Flatten recoverAddress",
    },
    {
        "id": "utils-verify-message",
        "pattern": "ethers.utils.verifyMessage($ARG)",
        "rewrite": "ethers.verifyMessage($ARG)",
        "description": "Flatten verifyMessage",
    },
    {
        "id": "utils-verify-typed-data",
        "pattern": "ethers.utils.verifyTypedData($ARG)",
        "rewrite": "ethers.verifyTypedData($ARG)",
        "description": "Flatten verifyTypedData",
    },
    {
        "id": "utils-concat",
        "pattern": "ethers.utils.concat($ARG)",
        "rewrite": "ethers.concat($ARG)",
        "description": "Flatten concat",
    },
    {
        "id": "utils-interface",
        "pattern": "ethers.utils.Interface",
        "rewrite": "ethers.Interface",
        "description": "Flatten Interface",
    },
    {
        "id": "utils-abi-coder",
        "pattern": "ethers.utils.defaultAbiCoder",
        "rewrite": "ethers.AbiCoder.defaultAbiCoder()",
        "description": "defaultAbiCoder -> AbiCoder.defaultAbiCoder()",
    },
    {
        "id": "utils-signing-key",
        "pattern": "ethers.utils.SigningKey",
        "rewrite": "ethers.SigningKey",
        "description": "Flatten SigningKey",
    },
    {
        "id": "utils-get-contract-address",
        "pattern": "ethers.utils.getContractAddress($ARG)",
        "rewrite": "ethers.getContractAddress($ARG)",
        "description": "Flatten getContractAddress",
    },
    {
        "id": "utils-namehash",
        "pattern": "ethers.utils.namehash($ARG)",
        "rewrite": "ethers.namehash($ARG)",
        "description": "Flatten namehash",
    },
    {
        "id": "utils-random-bytes",
        "pattern": "ethers.utils.randomBytes($ARG)",
        "rewrite": "ethers.randomBytes($ARG)",
        "description": "Flatten randomBytes",
    },
    # ── BigNumber ────────────────────────────────────────────
    {
        "id": "bignum-from",
        "pattern": "ethers.BigNumber.from($X)",
        "rewrite": "BigInt($X)",
        "description": "ethers.BigNumber.from -> BigInt",
    },
    # NOTE: Type annotations like `ethers.BigNumber` are not matched by
    # ast-grep in type position and are left for AI/manual handling.
    # ── Contract ─────────────────────────────────────────────
    {
        "id": "contract-signer",
        "pattern": "$CONTRACT.signer",
        "rewrite": "$CONTRACT.runner",
        "description": "contract.signer -> contract.runner",
    },
    {
        "id": "contract-provider",
        "pattern": "$CONTRACT.provider",
        "rewrite": "$CONTRACT.runner?.provider",
        "description": "contract.provider -> contract.runner?.provider",
    },
]


class CodemodEngine:
    """Applies deterministic AST transformations using ast-grep."""

    _GLOBS = ("*.js", "*.ts", "*.jsx", "*.tsx", "*.mjs", "*.cjs")
    _SKIP_DIRS = {
        "node_modules", ".git", "dist", "build", "coverage",
        ".next", ".nuxt", "out", "public", "static",
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.stats = CodemodStats()
        self.safety = SafetyLayer()

    def apply_all(self, dry_run: bool = True) -> CodemodStats:
        """Apply all deterministic codemods to the project."""
        files = self._collect_files()
        self.stats.files_scanned = len(files)

        for file_path in files:
            self._transform_file(file_path, dry_run)

        self.stats.files_modified = len({
            r.file_path for r in self.stats.results
            if r.changes_made > 0 and r.status in ("success", "dry-run")
        })

        return self.stats

    def _collect_files(self) -> list[Path]:
        files: list[Path] = []
        for glob in self._GLOBS:
            for f in self.project_root.rglob(glob):
                if any(part in self._SKIP_DIRS for part in f.parts):
                    continue
                files.append(f)
        return files

    def _transform_file(self, file_path: Path, dry_run: bool) -> None:
        content = file_path.read_text(encoding="utf-8")

        # Fast path
        if "ethers" not in content:
            return

        # Safety check: verify ethers is from the actual package
        if not self.safety.is_ethers_imported(file_path, content):
            return

        original = content
        current = content
        file_changed = False

        for rule in DETERMINISTIC_RULES:
            rewritten, changes = sg_run_rewrite(
                pattern=rule["pattern"],
                rewrite=rule["rewrite"],
                source=current,
            )

            if changes == 0:
                continue

            # Safety: syntax validation
            if not self.safety.is_valid_js_ts(rewritten):
                self.stats.results.append(CodemodResult(
                    file_path=str(file_path),
                    rule_id=rule["id"],
                    changes_made=0,
                    status="failed",
                    error="Syntax validation failed after rewrite",
                ))
                self.stats.errors.append(
                    f"{file_path} [{rule['id']}]: syntax error"
                )
                continue

            if dry_run:
                self.stats.results.append(CodemodResult(
                    file_path=str(file_path),
                    rule_id=rule["id"],
                    changes_made=changes,
                    status="dry-run",
                ))
            else:
                current = rewritten
                file_changed = True
                self.stats.results.append(CodemodResult(
                    file_path=str(file_path),
                    rule_id=rule["id"],
                    changes_made=changes,
                    status="success",
                ))

            self.stats.total_changes += changes
            self.stats.rule_changes[rule["id"]] = (
                self.stats.rule_changes.get(rule["id"], 0) + changes
            )

        if file_changed and not dry_run:
            file_path.write_text(current, encoding="utf-8")

        # Final idempotency check: ensure no v5 patterns remain
        if not dry_run and file_changed:
            self._assert_no_v5_patterns(file_path, current)

    def _assert_no_v5_patterns(self, file_path: Path, content: str) -> None:
        """Log warning if obvious v5 patterns remain (should not happen)."""
        remaining = []
        for rule in DETERMINISTIC_RULES:
            if rule["pattern"] in content:
                remaining.append(rule["id"])
        if remaining:
            self.stats.errors.append(
                f"{file_path}: remaining v5 patterns after migration: {remaining}"
            )
