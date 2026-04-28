# ethers.js v5 -> v6 Migration Report

**Generated:** 2026-04-28T23:29:58.804052+00:00 UTC

## Coverage Metrics

| Metric | Value |
|--------|-------|
| Total Automated | **72.7%** |
| Deterministic | 72.7% |
| AI-Assisted | 0.0% |
| Skipped Edge Cases | 3 |
| False Positives | 0 |

## Detection Summary

- Total JS/TS Files: 3
- Files with ethers.js: 3
- Imports detected: 3
- Utils usage detected: 3
- Provider usage detected: 1
- Contract usage detected: 2
- BigNumber usage detected: 2

## Codemod Results

- Files Scanned: 3
- Files Modified: 3
- Total Transformations: 8

### Rule Breakdown

| Rule | Changes |
|------|---------|
| bignum-from | 1 |
| contract-signer | 1 |
| contract-provider | 1 |
| provider-web3 | 1 |
| provider-flatten | 1 |
| utils-format-ether | 1 |
| utils-keccak256 | 1 |
| utils-to-utf8-bytes | 1 |

## Next Steps

1. Review the diff in your version control system.
2. Run the project's test suite.
3. Check AI fallback log for any manual fixes needed.
4. Commit the migration.
