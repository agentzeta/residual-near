# Evidence and test interpretation

## What is measured

- **PQ-key presence:** An account has at least one recognized ML-DSA-65 hash-handle key, whether full-access or function-call.
- **Mixed full-access authority:** Both a classical full-access key and a PQ full-access key exist at the observed block.
- **Observed PQ-only full access:** A recognized PQ full-access key exists and no classical full-access key or unrecognized key is observed. This is labeled `COMPLETE` in the classifier but is **not** a quantum-safety certificate.
- **Undetermined:** Any failure or unsupported authority configuration that does not support a definitive classification; it remains in denominators.

## Provenance and uncertainty

- Live reads use NEAR JSON-RPC at a pinned finalized block hash.
- Signer samples are deterministic given an observed block window and its signer frame.
- Block or chunk failures mark the frame incomplete.
- Wilson confidence intervals refer only to the specified sampled signer frame, not the population of all accounts.
- RPC replies are not independently verified with a light client.
- The recorded five-account sample is an illustrative historical mainnet observation, not a population migration statistic.

## Validation boundaries

The repository includes Python unit/integration tests and Node browser tests. The browser classification rules were separately checked against all 128 entries of `formal/truth_table.json` with zero mismatches during review, **without running the full Node test suite** in that verification. The browser RPC provider fallback was checked with simulated HTTP 429 responses. GitHub Actions runs may fail before a test runner is assigned; such runs are **not** evidence that the code tests passed. Run the local commands in [Judge's quick evaluation](README.md) to verify independently.

The synthetic six-account fixture exercises states not necessarily represented in a small recent-signer mainnet sample; it must not be described as a live mainnet measurement.
