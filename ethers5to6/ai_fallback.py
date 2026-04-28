"""Stage 4 — AI Edge Case Layer.

Handles rare, complex patterns that deterministic codemods cannot safely
resolve. AI is ONLY invoked after the deterministic pass and is strictly
forbidden from modifying imports or core API structure.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class AIResult:
    file_path: str
    line_number: int
    original_code: str
    transformed_code: str
    reasoning: str
    success: bool
    error: Optional[str] = None


@dataclass
class AIStats:
    total_calls: int = 0
    successful: int = 0
    failed: int = 0
    results: list[AIResult] = field(default_factory=list)


class AIFallbackPipeline:
    """AI pipeline for edge cases only."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.stats = AIStats()
        self.client: Optional[object] = None

        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def process_edge_cases(
        self, cases: list[dict], dry_run: bool = True
    ) -> list[AIResult]:
        """Process unresolved edge cases.

        Each case dict should contain:
        - file_path
        - line_number
        - context (surrounding code block)
        - pattern_type (e.g., 'bignum-arith-chain', 'dynamic-provider')
        """
        results: list[AIResult] = []

        for case in cases:
            if dry_run:
                results.append(AIResult(
                    file_path=case.get("file_path", ""),
                    line_number=case.get("line_number", 0),
                    original_code=case.get("context", ""),
                    transformed_code="",
                    reasoning="AI dry-run (no API call)",
                    success=True,
                ))
                continue

            result = self._call_ai(case)
            results.append(result)

        return results

    def _call_ai(self, case: dict) -> AIResult:
        if not self.client:
            return AIResult(
                file_path=case.get("file_path", ""),
                line_number=case.get("line_number", 0),
                original_code=case.get("context", ""),
                transformed_code="",
                reasoning="AI client not available (no API key)",
                success=False,
                error="No API key configured",
            )

        prompt = self._build_prompt(case)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            transformed = response.content[0].text.strip()

            result = AIResult(
                file_path=case.get("file_path", ""),
                line_number=case.get("line_number", 0),
                original_code=case.get("context", ""),
                transformed_code=transformed,
                reasoning="AI edge-case transformation",
                success=True,
            )

            self.stats.total_calls += 1
            self.stats.successful += 1
            self.stats.results.append(result)

            return result

        except Exception as e:
            result = AIResult(
                file_path=case.get("file_path", ""),
                line_number=case.get("line_number", 0),
                original_code=case.get("context", ""),
                transformed_code="",
                reasoning="AI transformation failed",
                success=False,
                error=str(e),
            )

            self.stats.total_calls += 1
            self.stats.failed += 1
            self.stats.results.append(result)

            return result

    def _build_prompt(self, case: dict) -> str:
        context = case.get("context", "")
        pattern_type = case.get("pattern_type", "unknown")
        file_path = case.get("file_path", "unknown")
        line_number = case.get("line_number", 0)

        return f"""You are an expert in ethers.js migrations.

Task: Migrate the following edge-case pattern from ethers.js v5 to v6.

File: {file_path}
Line: {line_number}
Pattern type: {pattern_type}

Code context:
```typescript
{context}
```

IMPORTANT RULES:
1. ONLY transform the specific edge case shown. Do NOT modify imports.
2. Do NOT change core API structure (e.g., do not rewrite class definitions).
3. For BigNumber arithmetic chains, convert to native bigint operators (+, -, *, /).
4. Return ONLY the transformed code block, no explanations.
5. If you cannot safely transform it, return the original code unchanged.

Transformed code:"""

    def save_log(self, path: Path = Path("ai_fallback_log.json")) -> None:
        """Persist AI decisions for audit."""
        entries = []
        for r in self.stats.results:
            entries.append({
                "file_path": r.file_path,
                "line_number": r.line_number,
                "original": r.original_code,
                "transformed": r.transformed_code,
                "success": r.success,
                "error": r.error,
            })
        path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
