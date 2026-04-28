"""Tests for ethers5to6 Stage 3 — Safety Layer."""

import pytest
from pathlib import Path

from ethers5to6.safety_layer import SafetyLayer


class TestSafetyLayer:
    def test_detects_ethers_import(self):
        safety = SafetyLayer()
        content = 'import { ethers } from "ethers";\n'
        assert safety.is_ethers_imported(Path("a.ts"), content)

    def test_detects_require_ethers(self):
        safety = SafetyLayer()
        content = 'const ethers = require("ethers");\n'
        assert safety.is_ethers_imported(Path("a.ts"), content)

    def test_rejects_no_import(self):
        safety = SafetyLayer()
        content = 'const x = 1;\n'
        assert not safety.is_ethers_imported(Path("a.ts"), content)

    def test_rejects_shadowed_ethers(self):
        safety = SafetyLayer()
        content = 'const ethers = { fake: true };\n'
        assert safety.is_shadowed(content)

    def test_not_shadowed_for_import(self):
        safety = SafetyLayer()
        content = 'import { ethers } from "ethers";\n'
        assert not safety.is_shadowed(content)

    def test_valid_js_braces_balanced(self):
        safety = SafetyLayer()
        assert safety._braces_balanced("function f() { return 1; }")

    def test_invalid_js_unbalanced_braces(self):
        safety = SafetyLayer()
        assert not safety._braces_balanced("function f() { return 1; ")

    def test_should_skip_non_ethers_file(self):
        safety = SafetyLayer()
        content = 'const x = 1;\n'
        assert safety.should_skip_file(Path("a.ts"), content)

    def test_should_skip_already_v6(self):
        safety = SafetyLayer()
        content = (
            'import { ethers } from "ethers";\n'
            'const p = new ethers.BrowserProvider(window.ethereum);\n'
        )
        assert safety.should_skip_file(Path("a.ts"), content)

    def test_should_not_skip_v5_file(self):
        safety = SafetyLayer()
        content = (
            'import { ethers } from "ethers";\n'
            'const p = new ethers.providers.Web3Provider(window.ethereum);\n'
        )
        assert not safety.should_skip_file(Path("a.ts"), content)
