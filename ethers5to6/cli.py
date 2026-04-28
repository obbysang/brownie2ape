"""CLI interface for ethers.js v5 -> v6 migration tool."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from ethers5to6.detector import EthersDetector
from ethers5to6.codemod_engine import CodemodEngine
from ethers5to6.safety_layer import SafetyLayer
from ethers5to6.ai_fallback import AIFallbackPipeline
from ethers5to6.verifier import Verifier
from ethers5to6.reporter import MigrationReporter

console = Console()


@click.group()
@click.version_option(version="1.0.0", prog_name="ethers5to6")
def cli():
    """ethers.js v5 -> v6 Production-Grade Migration Tool."""
    pass


@cli.command()
@click.argument("project_path", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Save JSON report")
def analyze(project_path: Path, output: Path | None):
    """Stage 1 — Analyze a project for ethers.js v5 patterns."""
    console.print(f"[bold cyan]Analyzing:[/bold cyan] {project_path}")

    detector = EthersDetector(project_path)
    report = detector.detect()

    table = Table(title="Detection Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total JS/TS Files", str(report.total_files))
    table.add_row("Files with ethers.js", str(report.files_with_ethers))
    table.add_row("Imports", str(len(report.imports)))
    table.add_row("Utils Usage", str(len(report.utils_usage)))
    table.add_row("Provider Usage", str(len(report.provider_usage)))
    table.add_row("Contract Usage", str(len(report.contract_usage)))
    table.add_row("BigNumber Usage", str(len(report.bignum_usage)))

    console.print(table)

    if output:
        output.write_text(report.to_json(), encoding="utf-8")
        console.print(f"[green]Report saved to:[/green] {output}")


@cli.command()
@click.argument("project_path", type=click.Path(exists=True, path_type=Path))
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--ai-fallback", is_flag=True, help="Run AI edge-case layer after codemods")
@click.option("--api-key", help="Anthropic API key for AI fallback")
def migrate(project_path: Path, dry_run: bool, ai_fallback: bool, api_key: str | None):
    """Stages 1-3 — Detect and apply deterministic codemods."""
    console.print(f"[bold cyan]Migrating:[/bold cyan] {project_path}")
    if dry_run:
        console.print("[yellow]DRY RUN — no files will be modified[/yellow]")

    # Stage 1: Detection
    console.print("[dim]Stage 1: Detecting patterns...[/dim]")
    detector = EthersDetector(project_path)
    detection_report = detector.detect()

    # Stage 2-3: Codemods + Safety
    console.print("[dim]Stage 2-3: Applying deterministic codemods...[/dim]")
    engine = CodemodEngine(project_path)
    codemod_stats = engine.apply_all(dry_run=dry_run)

    console.print(f"[green]Files scanned:[/green] {codemod_stats.files_scanned}")
    console.print(f"[green]Files modified:[/green] {codemod_stats.files_modified}")
    console.print(f"[green]Total changes:[/green] {codemod_stats.total_changes}")

    # Stage 4: AI Fallback (optional)
    ai_stats = None
    if ai_fallback and not dry_run:
        console.print("[dim]Stage 4: Running AI edge-case layer...[/dim]")
        ai = AIFallbackPipeline(api_key=api_key)

        # Collect unresolved cases (e.g., BigNumber arithmetic chains)
        unresolved = _collect_unresolved(detection_report, codemod_stats)
        if unresolved:
            ai_results = ai.process_edge_cases(unresolved, dry_run=False)
            ai.save_log(project_path / "ai_fallback_log.json")
            ai_stats = ai.stats
            console.print(f"[green]AI handled {len(ai_results)} edge cases[/green]")
        else:
            console.print("[dim]No unresolved edge cases found.[/dim]")

    # Report
    reporter = MigrationReporter(
        detection_report=detection_report,
        codemod_stats=codemod_stats,
        ai_stats=ai_stats,
    )
    report_path = project_path / "migration-report.md"
    reporter.save(report_path, fmt="markdown")
    console.print(f"[green]Report saved to:[/green] {report_path}")


@cli.command()
@click.argument("project_path", type=click.Path(exists=True, path_type=Path))
@click.option("--api-key", help="Anthropic API key")
@click.option("--dry-run", is_flag=True, help="Preview AI changes without applying")
def fix(project_path: Path, api_key: str | None, dry_run: bool):
    """Stage 4 — Run AI fallback for unresolved edge cases."""
    console.print(f"[bold cyan]AI Fix:[/bold cyan] {project_path}")

    ai = AIFallbackPipeline(api_key=api_key)

    # Load detection data
    det_file = project_path / "detection-report.json"
    if det_file.exists():
        data = json.loads(det_file.read_text(encoding="utf-8"))
        unresolved = _extract_edge_cases(data)
    else:
        console.print("[yellow]No detection report found. Run 'analyze' first.[/yellow]")
        return

    if not unresolved:
        console.print("[dim]No edge cases to process.[/dim]")
        return

    results = ai.process_edge_cases(unresolved, dry_run=dry_run)
    console.print(f"[green]Processed {len(results)} cases[/green]")

    if not dry_run:
        ai.save_log(project_path / "ai_fallback_log.json")


@cli.command()
@click.argument("project_path", type=click.Path(exists=True, path_type=Path))
@click.option("--test-command", default="npm test", help="Test command to run")
@click.option("--json", "output_json", is_flag=True, help="Output JSON")
def verify(project_path: Path, test_command: str, output_json: bool):
    """Stage 5 — Verify migrated code compiles and passes tests."""
    console.print(f"[bold cyan]Verifying:[/bold cyan] {project_path}")

    verifier = Verifier(project_path)
    report = verifier.verify(test_command=test_command)

    if output_json:
        console.print(report.to_json())
    else:
        table = Table(title="Verification Results")
        table.add_column("Check", style="cyan")
        table.add_column("Status", style="green")

        table.add_row("Syntax Valid", "✅" if report.syntax_valid else "❌")
        table.add_row("No v5 Patterns", "✅" if report.no_v5_patterns else "❌")
        table.add_row("Build Passed", "✅" if report.build_passed else "❌")
        table.add_row("Tests Passed", "✅" if report.tests_passed else "❌")

        console.print(table)

        if report.issues:
            console.print("[bold red]Issues:[/bold red]")
            for issue in report.issues:
                console.print(f"  - {issue}")

    sys.exit(0 if report.success else 1)


@cli.command()
@click.argument("project_path", type=click.Path(exists=True, path_type=Path))
@click.option("--format", "fmt", type=click.Choice(["json", "markdown", "html"]), default="markdown")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Save report to file")
def report(project_path: Path, fmt: str, output: Path | None):
    """Stage 6 — Generate migration coverage report."""
    console.print(f"[bold cyan]Generating Report:[/bold cyan] {project_path}")

    detector = EthersDetector(project_path)
    detection = detector.detect()

    engine = CodemodEngine(project_path)
    codemod_stats = engine.apply_all(dry_run=True)

    reporter = MigrationReporter(
        detection_report=detection,
        codemod_stats=codemod_stats,
    )

    if fmt == "json":
        content = reporter.generate_json()
    elif fmt == "html":
        content = reporter.generate_html()
    else:
        content = reporter.generate_markdown()

    if output:
        output.write_text(content, encoding="utf-8")
        console.print(f"[green]Report saved to:[/green] {output}")
    else:
        console.print(content)


def _collect_unresolved(detection_report, codemod_stats) -> list[dict]:
    """Collect patterns that deterministic codemods likely missed."""
    unresolved: list[dict] = []

    # BigNumber arithmetic chains are the primary edge case
    for p in detection_report.bignum_usage:
        if p.rule_id in ("bignum-arith-add", "bignum-arith-mul"):
            unresolved.append({
                "file_path": p.file_path,
                "line_number": p.line_number,
                "context": p.matched_text,
                "pattern_type": "bignum-arith-chain",
            })

    return unresolved


def _extract_edge_cases(data: dict) -> list[dict]:
    """Extract edge cases from detection JSON."""
    cases: list[dict] = []
    for p in data.get("bignum_usage", []):
        cases.append({
            "file_path": p.get("file_path", ""),
            "line_number": p.get("line_number", 0),
            "context": p.get("matched_text", ""),
            "pattern_type": "bignum",
        })
    return cases


def main():
    cli()


if __name__ == "__main__":
    main()
