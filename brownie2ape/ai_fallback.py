"""AI fallback pipeline for handling edge cases."""

import os
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class AIResult:
    """Result from AI edge case handling."""
    file_path: str
    line_number: int
    original_code: str
    transformed_code: str
    reasoning: str
    success: bool
    error: Optional[str] = None


@dataclass
class AIStats:
    """Statistics for AI fallback."""
    total_calls: int = 0
    successful: int = 0
    failed: int = 0
    results: list[AIResult] = field(default_factory=list)


class AIFallbackPipeline:
    """Handles edge cases using AI when deterministic codemods are insufficient."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.stats = AIStats()
        self.client = None

        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def handle_edge_case(self, file_path: str, line_number: int, context: str) -> AIResult:
        """Handle a single edge case that couldn't be transformed deterministically."""
        if not self.client:
            return AIResult(
                file_path=file_path,
                line_number=line_number,
                original_code=context,
                transformed_code="",
                reasoning="AI client not configured",
                success=False,
                error="No API key configured"
            )

        prompt = self._build_prompt(context, file_path, line_number)

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            transformed = response.content[0].text.strip()

            result = AIResult(
                file_path=file_path,
                line_number=line_number,
                original_code=context,
                transformed_code=transformed,
                reasoning="AI transformation",
                success=True
            )

            self.stats.total_calls += 1
            self.stats.successful += 1
            self.stats.results.append(result)

            return result

        except Exception as e:
            result = AIResult(
                file_path=file_path,
                line_number=line_number,
                original_code=context,
                transformed_code="",
                reasoning="AI transformation failed",
                success=False,
                error=str(e)
            )

            self.stats.total_calls += 1
            self.stats.failed += 1
            self.stats.results.append(result)

            return result

    def _build_prompt(self, context: str, file_path: str, line_number: int) -> str:
        """Build prompt for AI to transform Brownie code to Ape Framework."""
        return f"""You are helping migrate Python code from Brownie to Ape Framework.

File: {file_path}
Line: {line_number}

Code context:
```
{context}
```

Transform this Brownie code to equivalent Ape Framework code. Consider:
1. Brownie uses `brownie.network.account` → Ape uses `ape.account`
2. Brownie uses `network.connect()` → Ape uses `chain.provider.connect()`
3. Brownie uses `project.Contract` → Ape uses `project.containers["Contract"]`
4. Brownie uses `brownie.eth` → Ape uses `ape.eth`

Return ONLY the transformed code, no explanations. If the code cannot be safely transformed, return the original code unchanged."""

    def log_decision(self, file_path: str, decision: str, outcome: str) -> None:
        """Log AI decision for audit trail."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "file": file_path,
            "decision": decision,
            "outcome": outcome
        }

        log_file = Path("ai_fallback_log.json")
        if log_file.exists():
            with open(log_file) as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)
        log_file.write_text(json.dumps(logs, indent=2))

    def batch_process(self, unresolved_cases: list[dict]) -> list[AIResult]:
        """Process multiple edge cases in batch."""
        results = []

        for case in unresolved_cases:
            result = self.handle_edge_case(
                case.get("file_path", ""),
                case.get("line_number", 0),
                case.get("context", "")
            )
            results.append(result)

        return results