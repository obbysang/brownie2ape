# Agent Instructions

## Setup

```powershell
# Install dependencies
cd "C:\Users\Dravel\Videos\April\Brownie → Ape Framework"
pip install -e .

# Install ast-grep (required for jssg codemods)
# Option 1: via cargo
cargo install ast-grep

# Option 2: via npm
npm install -g @ast-grep/cli
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=brownie2ape --cov-report=html
```

## CLI Commands

```bash
# Analyze a Brownie project
brownie2ape analyze C:\path\to\brownie\project

# Dry-run migration
brownie2ape migrate C:\path\to\brownie\project --dry-run

# Apply migration
brownie2ape migrate C:\path\to\brownie\project

# Handle edge cases with AI
brownie2ape fix C:\path\to\brownie\project --api-key YOUR_KEY

# Generate report
brownie2ape report C:\path\to\brownie\project --format markdown --output report.md

# Validate tests
brownie2ape test C:\path\to\brownie\project
```

## Lint & Typecheck

```bash
# Run ruff linter
ruff check brownie2ape/

# Format code
ruff format brownie2ape/
```

## Notes

- Uses ast-grep (jssg) as required by hackathon rules
- AI fallback requires ANTHROPIC_API_KEY environment variable
- Zero false positives is the accuracy target
- 85%+ deterministic coverage is the automation target