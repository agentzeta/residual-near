# Release status (14 November 2026)

Canonical repo: https://github.com/agentzeta/residual-near

This repository combines the read-only Python + Lean formal classifier with the browser frontend and RPC sampling demo. It does **not** deploy a smart contract or NEAR Intents and never requires a signing key.

## Verification tasks

1. Confirm GitHub Actions Tests is green (Python and browser tests).
2. Enable GitHub Pages under Settings > Pages > Source: GitHub Actions; confirm Deploy site succeeds.
3. Run Live mainnet scan and inspect the artifact. An unavailable RPC or unresolved sample is **not** evidence of PQ adoption.
4. Run Record demo video and watch the resulting MP4. The script now rejects error-only account checks and samples.
5. Post the verified demo on X; complete the NEAR HACKATHON form before deadline.

Synthetic fixture figures must never be represented as NEAR mainnet observations. PQ-only full-access status is a snapshot classification, not proof of quantum safety or historical key deletion.

The browser reads public RPC endpoints; rate limiting and CORS can affect availability. Pages deployment can succeed even when live scan fails. Do not claim a successful live scan without checking the report.
