Intro
Building software is exciting. Keeping it up to date is what slows everything down.

Every upgrade, refactor, and migration turns into weeks of work, coordination, and risk.

This hackathon is about changing that.

👉 Use AI + codemods to automate software maintenance 👉 Turn complex migrations into fast, reliable workflows 👉 Build tools that real teams can use in production

By the end, you won't just ship a project. You'll learn Codemod's open-source toolkit — adopted by Node.js, React, Express, React Router, Nuxt.js, pnpm, Webpack, MSW, i18next, and more, and make it your superpower for the rest of your career.

⚡ What You'll Do
Pick a real world upgrade or migration
Build codemods to automate it
Use AI to handle edge cases
Prove it works on a real repo
That’s it.

You’ll end up with a production-grade migration workflow: deterministic codemods handle most changes fast and reliably, AI steps cover edge cases, and it works across real-world repositories.

Goal: 👉 Automate 80%+ of the migration 👉 Minimize manual work 👉 Make it reliable enough for real teams

🧰 Quickstart
Learn the Codemod toolkit
Pick a migration from the pre-approved list below (or propose a new one)
Check the registry — make sure it doesn't already exist
Build your codemod workflow in your own repository
Test it on a real open-source project
When you're done, publish your codemod to the registry — guide here
💡 Starter Ideas (Pre-approved Migrations)
Don't overthink it. Pick a migration from the following pre-approved ecosystems. If you want to propose something not listed, reach out to us before starting work.

TypeScript / JavaScript

@solana/web3.js v1 → @solana/kit — Docs · Announcement
ethers.js v5 → v6 (full recipe) — Migration Guide
wagmi v1 → v2 — Migration Guide
Python

Brownie → Ape Framework — Ape Docs
web3.py v6 → v7 — Migration Guide
Rust / Config

Anchor IDL v0 → v1 (JSON schema migration)
Anchor v0.29 → v0.30 Rust API changes — Changelog
🚫 NOTE

If official codemods already exist for it (e.g. React v18 → v19), pick something else.

You should NEVER use jscodeshift to make your codemod. We use jssg in order to detect and do the migration.

💰 Prizes
🥇 Top Codemod Prize — Up to $3,000 total
The strongest submission can earn up to $3,000 in total by combining rewards across the three categories below.

📦 1. Production-grade Migration Recipes
Build codemods that automate 80%+ of a migration deterministically, with clear AI instructions for the remaining edge cases.

Pre-approved ecosystems only — see the list below. Contributions must be submitted as pull requests and accepted after review.

S ⇒ up to 2 days ⇒ $100
M ⇒ ~1 week ⇒ $200
L ⇒ ~2 weeks ⇒ $400
XL ⇒ 2+ weeks ⇒ $800
📝 2. Public Case Studies
Publish a write-up showing how a migration was handled with Codemod on a meaningful open-source project.

$200 per published case study.

Cover: migration approach, automation coverage %, AI vs manual effort, and real-world impact.

🚀 3. Official Framework Adoption
Get a framework maintainer to host your codemod in their org or reference it in their official upgrade guide.

Up to $2,000 per successful adoption.

🔧 How Submissions Are Evaluated
We evaluate submissions based on how much of the migration you automate, how accurate it is, and how well it works on real codebases.

Core Criteria
Accuracy: zero incorrect changes (no false positives)
Coverage: how much of the migration is automated
Reliability: works across real repos, not just a single test case
Evaluation Process
Your codemod is tested on a real repository:

Codemod runs and commits changes
AI agent handles remaining edge cases
Manual fixes (if needed) until build and tests pass
Scoring
Score = 100 × (1 − ((FP × wFP) + (FN × wFN)) ÷ (N × (wFP + wFN)))
FP (False Positives): incorrect changes, heavily penalized
FN (False Negatives): missed patterns, penalized less
N: total patterns in the repo
w_fp / w_fn: penalty weights
Checklist
Runs successfully on real repos
Includes tests (full credit)
All tests pass
Deterministic changes have zero false positives
Covers as many patterns as possible, leaving edge cases to AI
What Great Looks Like
80–95% of the migration automated
Zero false positives
Works across real-world repos
Minimal AI and manual cleanup
Clear tests and documentation
🎯 Why This Matters
Every company struggles with maintenance — dependency upgrades, API changes, large refactors. It is a massive, mostly unsolved problem.

If you get this right, you are not just building a hackathon project. You are building infrastructure that every engineering team needs.

Your codemod could become the default migration path used by thousands of developers.

Pick something real. Ship something useful. Make maintenance invisible.