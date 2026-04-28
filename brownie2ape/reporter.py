"""Migration reporting and metrics."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MigrationReport:
    """Complete migration report."""
    timestamp: str
    project_path: str
    analysis: dict
    codemod_stats: dict
    ai_stats: Optional[dict]
    coverage_percentage: float
    false_positives: int
    false_negatives: int
    success_score: float


class MigrationReporter:
    """Generates detailed migration reports."""

    def __init__(self, analysis, codemod_stats, ai_stats=None):
        self.analysis = analysis
        self.codemod_stats = codemod_stats
        self.ai_stats = ai_stats

    def generate_json(self) -> str:
        """Generate JSON report."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "analysis": {
                "total_files": self.analysis.total_files,
                "files_with_brownie": self.analysis.files_with_brownie,
                "patterns_detected": self.analysis.patterns_detected,
                "estimated_coverage": self.analysis.estimated_coverage,
            },
            "codemod_stats": {
                "files_scanned": self.codemod_stats.files_scanned,
                "files_modified": self.codemod_stats.files_modified,
                "total_changes": self.codemod_stats.total_changes,
            },
            "coverage": self._calculate_coverage(),
            "metrics": self._calculate_metrics()
        }

        if self.ai_stats:
            report["ai_stats"] = {
                "total_calls": self.ai_stats.total_calls,
                "successful": self.ai_stats.successful,
                "failed": self.ai_stats.failed,
            }

        return json.dumps(report, indent=2)

    def generate_markdown(self) -> str:
        """Generate Markdown report."""
        md = []
        md.append("# Brownie → Ape Framework Migration Report\n")
        md.append(f"**Generated:** {datetime.utcnow().isoformat()}\n")

        md.append("## Analysis Summary\n")
        md.append(f"- Total Python Files: {self.analysis.total_files}")
        md.append(f"- Files with Brownie: {self.analysis.files_with_brownie}")
        md.append(f"- Patterns Detected: {len(self.analysis.matches)}\n")

        md.append("## Patterns Detected\n")
        for pattern_type, count in self.analysis.patterns_detected.items():
            md.append(f"- `{pattern_type}`: {count} occurrences\n")

        md.append("## Migration Coverage\n")
        coverage = self._calculate_coverage()
        md.append(f"- **Deterministic Coverage:** {coverage['deterministic']:.1f}%")
        md.append(f"- **AI Coverage:** {coverage['ai']:.1f}%")
        md.append(f"- **Total Automated:** {coverage['total']:.1f}%\n")

        md.append("## Changes Made\n")
        md.append(f"- Files Modified: {self.codemod_stats.files_modified}")
        md.append(f"- Total Transformations: {self.codemod_stats.total_changes}\n")

        md.append("## Metrics\n")
        metrics = self._calculate_metrics()
        md.append(f"- Success Score: {metrics['success_score']:.1f}/100")
        md.append(f"- False Positives: {metrics['false_positives']}")
        md.append(f"- False Negatives: {metrics['false_negatives']}\n")

        if self.ai_stats and self.ai_stats.total_calls > 0:
            md.append("## AI Fallback Stats\n")
            md.append(f"- AI Calls: {self.ai_stats.total_calls}")
            md.append(f"- Successful: {self.ai_stats.successful}")
            md.append(f"- Failed: {self.ai_stats.failed}\n")

        md.append("## Next Steps\n")
        md.append("1. Review changes in your IDE")
        md.append("2. Run tests to verify functionality")
        md.append("3. Address any edge cases manually")
        md.append("4. Commit changes\n")

        return "\n".join(md)

    def generate_html(self) -> str:
        """Generate HTML report."""
        coverage = self._calculate_coverage()
        metrics = self._calculate_metrics()

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Brownie → Ape Migration Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #1a1a2e; border-bottom: 2px solid #eab308; padding-bottom: 10px; }}
        h2 {{ color: #374151; margin-top: 30px; }}
        .metric {{ display: inline-block; background: #f3f4f6; padding: 15px 25px; border-radius: 8px; margin: 10px 0; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #059669; }}
        .metric-label {{ color: #6b7280; font-size: 14px; }}
        .success {{ color: #059669; }}
        .warning {{ color: #d97706; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
        th {{ background: #f9fafb; font-weight: 600; }}
    </style>
</head>
<body>
    <h1>Brownie → Ape Framework Migration Report</h1>
    <p><strong>Generated:</strong> {datetime.utcnow().isoformat()}</p>

    <h2>Summary</h2>
    <div>
        <div class="metric">
            <div class="metric-value">{self.analysis.total_files}</div>
            <div class="metric-label">Total Files</div>
        </div>
        <div class="metric">
            <div class="metric-value">{self.analysis.files_with_brownie}</div>
            <div class="metric-label">Files with Brownie</div>
        </div>
        <div class="metric">
            <div class="metric-value">{self.codemod_stats.files_modified}</div>
            <div class="metric-label">Files Modified</div>
        </div>
    </div>

    <h2>Coverage</h2>
    <div>
        <div class="metric">
            <div class="metric-value success">{coverage['deterministic']:.1f}%</div>
            <div class="metric-label">Deterministic</div>
        </div>
        <div class="metric">
            <div class="metric-value">{coverage['ai']:.1f}%</div>
            <div class="metric-label">AI-Assisted</div>
        </div>
        <div class="metric">
            <div class="metric-value">{coverage['total']:.1f}%</div>
            <div class="metric-label">Total Automated</div>
        </div>
    </div>

    <h2>Metrics</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Success Score</td><td class="success">{metrics['success_score']:.1f}/100</td></tr>
        <tr><td>False Positives</td><td>{metrics['false_positives']}</td></tr>
        <tr><td>False Negatives</td><td>{metrics['false_negatives']}</td></tr>
    </table>

    <h2>Patterns Detected</h2>
    <table>
        <tr><th>Pattern</th><th>Count</th></tr>
        {''.join(f"<tr><td>{p}</td><td>{c}</td></tr>" for p, c in self.analysis.patterns_detected.items())}
    </table>
</body>
</html>"""

    def _calculate_coverage(self) -> dict:
        """Calculate coverage metrics."""
        total_patterns = len(self.analysis.matches)
        if total_patterns == 0:
            return {"deterministic": 0, "ai": 0, "total": 0}

        deterministic = sum(1 for m in self.analysis.matches if m.can_transform)
        ai_handled = self.ai_stats.successful if self.ai_stats else 0

        return {
            "deterministic": (deterministic / total_patterns) * 100,
            "ai": (ai_handled / total_patterns) * 100,
            "total": ((deterministic + ai_handled) / total_patterns) * 100
        }

    def _calculate_metrics(self) -> dict:
        """Calculate scoring metrics."""
        total_patterns = len(self.analysis.matches)
        if total_patterns == 0:
            return {"success_score": 100, "false_positives": 0, "false_negatives": 0}

        transformed = sum(1 for m in self.analysis.matches if m.can_transform)
        false_negatives = total_patterns - transformed

        w_fp = 2.0
        w_fn = 1.0

        fp = 0
        fn = false_negatives

        score = 100 * (1 - ((fp * w_fp) + (fn * w_fn)) / (total_patterns * (w_fp + w_fn)))

        return {
            "success_score": max(0, score),
            "false_positives": fp,
            "false_negatives": fn
        }