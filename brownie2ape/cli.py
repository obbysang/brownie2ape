"""CLI interface for Brownie to Ape migration tool."""

import os
import sys
import json
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from brownie2ape.pattern_detector import PatternDetector
from brownie2ape.codemod_engine import CodemodEngine
from brownie2ape.ai_fallback import AIFallbackPipeline
from brownie2ape.reporter import MigrationReporter
from brownie2ape.test_harness import TestHarness


console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Brownie to Ape Framework Migration Tool."""
    pass


@cli.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Save report to file")
def analyze(project_path: str, output: str):
    """Analyze a repository for Brownie patterns."""
    project = Path(project_path)

    console.print(f"[bold cyan]Analyzing:[/bold cyan] {project}")

    detector = PatternDetector(project)
    report = detector.scan_repository()

    table = Table(title="Pattern Analysis Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Python Files", str(report.total_files))
    table.add_row("Files with Brownie", str(report.files_with_brownie))
    table.add_row("Estimated Deterministic Coverage", f"{report.estimated_coverage:.1f}%")

    console.print(table)

    if report.patterns_detected:
        console.print("\n[bold]Patterns Detected:[/bold]")
        for pattern_type, count in report.patterns_detected.items():
            console.print(f"  • {pattern_type}: {count}")

    if output:
        output_path = Path(output)
        output_path.write_text(json.dumps({
            "total_files": report.total_files,
            "files_with_brownie": report.files_with_brownie,
            "patterns": report.patterns_detected,
            "estimated_coverage": report.estimated_coverage,
            "matches": [
                {
                    "file": m.file_path,
                    "line": m.line_number,
                    "type": m.pattern_type,
                    "can_transform": m.can_transform
                }
                for m in report.matches
            ]
        }, indent=2))
        console.print(f"[green]Report saved to:[/green] {output}")


@cli.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
@click.option("--rules-dir", type=click.Path(), help="Custom rules directory")
@click.option("--ai-fallback", is_flag=True, help="Use AI for edge cases")
def migrate(project_path: str, dry_run: bool, rules_dir: str, ai_fallback: bool):
    """Run codemods on the project."""
    project = Path(project_path)
    rules = Path(rules_dir) if rules_dir else Path(__file__).parent / "rules"

    console.print(f"[bold cyan]Migrating:[/bold cyan] {project}")
    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]")

    engine = CodemodEngine(project, rules)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        progress.add_task("Running codemods...", total=None)
        stats = engine.apply_all_codemods(dry_run)

    console.print(f"[green]Files modified:[/green] {stats.files_modified}")
    console.print(f"[green]Total changes:[/green] {stats.total_changes}")

    if ai_fallback:
        console.print("\n[cyan]Running AI fallback for edge cases...[/cyan]")
        ai = AIFallbackPipeline()

        unresolved = [
            {"file_path": m.file_path, "line_number": m.line_number, "context": ""}
            for m in stats.errors
        ]
        results = ai.batch_process(unresolved)
        console.print(f"[green]AI handled {len(results)} edge cases[/green]")


@cli.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.option("--api-key", help="Anthropic API key")
def fix(project_path: str, api_key: str):
    """Trigger AI for unresolved edge cases."""
    project = Path(project_path)

    console.print(f"[bold cyan]Running AI fix:[/bold cyan] {project}")

    ai = AIFallbackPipeline(api_key=api_key)

    fallback_log = Path("ai_fallback_log.json")
    if fallback_log.exists():
        with open(fallback_log) as f:
            cases = json.load(f)
        console.print(f"[cyan]Found {len(cases)} unresolved cases to process[/cyan]")
    else:
        console.print("[yellow]No unresolved cases found. Run 'migrate' first.[/yellow]")


@cli.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.option("--format", type=click.Choice(["json", "markdown", "html"]), default="markdown")
@click.option("--output", "-o", type=click.Path(), help="Save report to file")
def report(project_path: str, format: str, output: str):
    """Generate migration report."""
    project = Path(project_path)

    console.print(f"[bold cyan]Generating Report:[/bold cyan] {project}")

    detector = PatternDetector(project)
    analysis = detector.scan_repository()

    engine = CodemodEngine(project, Path(__file__).parent / "rules")
    migration_stats = engine.apply_all_codemods(dry_run=True)

    reporter = MigrationReporter(analysis, migration_stats)

    if format == "json":
        report_content = reporter.generate_json()
    elif format == "html":
        report_content = reporter.generate_html()
    else:
        report_content = reporter.generate_markdown()

    if output:
        Path(output).write_text(report_content)
        console.print(f"[green]Report saved to:[/green] {output}")
    else:
        console.print(report_content)


@cli.command()
@click.argument("project_path", type=click.Path(exists=True))
@click.option("--test-command", default="pytest", help="Test command to run")
def test(project_path: str, test_command: str):
    """Validate build and tests after migration."""
    project = Path(project_path)

    console.print(f"[bold cyan]Running Tests:[/bold cyan] {project}")

    harness = TestHarness(project)
    result = harness.run_validation(test_command)

    if result["success"]:
        console.print("[bold green]✓ Tests passed![/bold green]")
    else:
        console.print("[bold red]✗ Tests failed![/bold red]")
        console.print(result.get("output", ""))

    console.print(f"\n[cyan]Files changed:[/cyan] {result.get('files_changed', 0)}")
    console.print(f"[cyan]Tests passed:[/cyan] {result.get('tests_passed', 0)}")
    console.print(f"[cyan]Tests failed:[/cyan] {result.get('tests_failed', 0)}")


def main():
    """Entry point for CLI."""
    cli()


if __name__ == "__main__":
    main()