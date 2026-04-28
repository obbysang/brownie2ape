"""Internal helper for locating and running ast-grep (sg)."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def find_sg_binary() -> Optional[str]:
    """Find the ast-grep (sg) binary path cross-platform."""
    system = platform.system()

    # Try PATH first
    sg_cmd = shutil.which("sg")
    if sg_cmd:
        return sg_cmd

    # Windows: look in npm global bin
    if system == "Windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidate = Path(appdata) / "npm" / "sg.cmd"
            if candidate.exists():
                return str(candidate)

        # Also check Program Files nodejs
        pf = os.environ.get("ProgramFiles", "C:\\Program Files")
        candidate = Path(pf) / "nodejs" / "sg.cmd"
        if candidate.exists():
            return str(candidate)

    # macOS / Linux
    home = Path.home()
    candidates = [
        home / ".cargo" / "bin" / "sg",
        home / ".npm-global" / "bin" / "sg",
        Path("/usr/local/bin/sg"),
        Path("/usr/bin/sg"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


SG_BINARY: Optional[str] = find_sg_binary()


def run_sg(
    args: list[str],
    input_text: Optional[str] = None,
    cwd: Optional[Path] = None,
    timeout: int = 60,
) -> subprocess.CompletedProcess:
    """Run ast-grep with the given arguments."""
    if SG_BINARY is None:
        raise RuntimeError(
            "ast-grep (sg) binary not found. "
            "Please install it: npm install -g @ast-grep/cli"
        )

    cmd = [SG_BINARY] + args
    return subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
        shell=(platform.system() == "Windows" and SG_BINARY.endswith(".cmd")),
    )


def sg_run_rewrite(
    pattern: str,
    rewrite: str,
    source: str,
    language: str = "ts",
) -> tuple[str, int]:
    """Run a single sg run --rewrite on source code.

    Returns (rewritten_source, change_count).
    """
    result = run_sg(
        [
            "run",
            "--pattern", pattern,
            "--rewrite", rewrite,
            "--stdin",
            "--lang", language,
            "--update-all",
        ],
        input_text=source,
    )

    if result.returncode not in (0, 1):
        # Error case: return original source
        return source, 0

    stdout = result.stdout
    stderr = result.stderr

    # Count changes from stderr
    changes = 0
    if "Applied" in stderr:
        try:
            changes = int(stderr.split("Applied ")[1].split()[0])
        except (IndexError, ValueError):
            pass

    # If no output on stdout, source might be unchanged
    if not stdout.strip():
        return source, changes

    return stdout, changes


def sg_scan_json(rule_yaml: str, file_path: Path) -> list[dict]:
    """Run sg scan --json with a temporary rule file."""
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as tf:
            tf.write(rule_yaml)
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


def _parse_sg_json_lines(stdout: str) -> list[dict]:
    """Parse ast-grep JSON output.

    ast-grep --json outputs a pretty-printed JSON array.
    We attempt full-array parse first, then line-by-line fallback.
    """
    text = stdout.strip()
    if not text:
        return []

    # Try parsing the entire output as a JSON array first
    try:
        obj = json.loads(text)
        if isinstance(obj, list):
            return [item for item in obj if isinstance(item, dict)]
        if isinstance(obj, dict):
            return [obj]
    except Exception:
        pass

    # Fallback: line-by-line (for streaming or partial output)
    matches: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                matches.append(obj)
            elif isinstance(obj, list):
                matches.extend(obj)
        except Exception:
            continue
    return matches
