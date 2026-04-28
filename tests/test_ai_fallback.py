"""Tests for AI fallback pipeline."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from brownie2ape.ai_fallback import (
    AIFallbackPipeline,
    AIResult,
    AIStats
)


class TestAIStats:
    """Test suite for AIStats."""

    def test_stats_initialization(self):
        """Test AIStats initializes with defaults."""
        stats = AIStats()

        assert stats.total_calls == 0
        assert stats.successful == 0
        assert stats.failed == 0
        assert stats.results == []


class TestAIResult:
    """Test suite for AIResult."""

    def test_result_creation_success(self):
        """Test successful AIResult creation."""
        result = AIResult(
            file_path="test.py",
            line_number=10,
            original_code="brownie.eth",
            transformed_code="ape.eth",
            reasoning="Replaced brownie with ape",
            success=True
        )

        assert result.success is True
        assert result.transformed_code == "ape.eth"

    def test_result_creation_failure(self):
        """Test failed AIResult creation."""
        result = AIResult(
            file_path="test.py",
            line_number=10,
            original_code="brownie.eth",
            transformed_code="",
            reasoning="Failed",
            success=False,
            error="No API key"
        )

        assert result.success is False
        assert result.error == "No API key"


class TestAIFallbackPipeline:
    """Test suite for AIFallbackPipeline."""

    def test_pipeline_initialization_without_key(self):
        """Test pipeline initializes without API key."""
        pipeline = AIFallbackPipeline(api_key=None)

        assert pipeline.client is None
        assert pipeline.api_key is None

    def test_pipeline_handles_no_client(self):
        """Test pipeline handles missing client gracefully."""
        pipeline = AIFallbackPipeline(api_key=None)

        result = pipeline.handle_edge_case(
            "test.py",
            10,
            "from brownie import network"
        )

        assert result.success is False
        assert "API key" in result.error or "not configured" in result.error

    @pytest.mark.skipif(not ANTHROPIC_AVAILABLE, reason="anthropic module not installed")
    @patch("anthropic.Anthropic")
    def test_build_prompt_contains_context(self, mock_anthropic):
        """Test prompt includes file context."""
        pipeline = AIFallbackPipeline(api_key="test-key")

        prompt = pipeline._build_prompt("brownie.eth", "test.py", 10)

        assert "test.py" in prompt
        assert "brownie.eth" in prompt
        assert "Ape Framework" in prompt

    def test_log_decision_creates_file(self, tmp_path):
        """Test logging creates log file."""
        pipeline = AIFallbackPipeline(api_key=None)
        original_dir = Path.cwd()

        import os
        os.chdir(tmp_path)

        try:
            pipeline.log_decision("test.py", "transform", "success")

            log_file = Path("ai_fallback_log.json")
            assert log_file.exists()
        finally:
            os.chdir(original_dir)


class TestBatchProcessing:
    """Test suite for batch processing."""

    def test_batch_process_empty_cases(self):
        """Test batch processing with no cases."""
        pipeline = AIFallbackPipeline(api_key=None)

        results = pipeline.batch_process([])

        assert results == []

    def test_batch_process_single_case(self):
        """Test batch processing with single case."""
        pipeline = AIFallbackPipeline(api_key=None)

        cases = [{
            "file_path": "test.py",
            "line_number": 10,
            "context": "from brownie import network"
        }]

        results = pipeline.batch_process(cases)

        assert len(results) == 1
        assert results[0].file_path == "test.py"