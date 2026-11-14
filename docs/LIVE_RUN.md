# Reproducible NEAR mainnet measurement

Residual produces an account-key inventory for a stated block and sampling frame. This document specifies how to reproduce the report and interpret it.

## Requirements

- Python 3.9+ (standard library only)
- An outbound HTTPS connection to a NEAR mainnet RPC endpoint
- Node.js 18+ only for the independent browser parity suite

## Run tests

```bash
python3 -m unittest discover -s tests -v
node --test tests/web/parity.test.mjs
```

The Python and browser implementations are checked against `formal/truth_table.json`. The Lean source of the model is in `formal/Residual.lean`.

## Produce a live sample

```bash
python3 -m residual --sample-signers 200 --window-blocks 60 --output live-output
```

Outputs:

- `live-output/report.json`: block provenance, selection, classification and warnings
- `live-output/observations.json`: observed account access-key data
- `live-output/index.html`: static human-readable dashboard

The scanner attempts to pin observations at one finalized block, walks backward across the requested block window, constructs a frame of observed transaction signers, and draws a hash-seeded sample. Enrollment observations are separately reported when found.

## Interpretation and limitations

- A sample of recent transaction signers is **not a representative sample of all NEAR accounts**.
- Report the actual requested/resolved/unresolved denominators; never interpret missing reads as classical or post-quantum key absence.
- Incomplete block or chunk enumeration makes the signer frame incomplete.
- `COMPLETE` means no classical full-access key was observed alongside a PQ full-access key **at that block**; it is not evidence of historical migration, external recovery security, contract authority or system-wide quantum safety.
- The synthetic six-account fixture in `fixtures/demo.json` is for testing, not mainnet statistics.
- Reports rely on a trusted RPC endpoint; pinned-block reads are not light-client proofs.

## Manual account-list mode

```bash
python3 -m residual --accounts fixtures/accounts-example.txt --output list-output
```

This is a convenience sample with a different selection basis. The report and any publication must describe the sample as such.

## Mainnet endpoint

The default endpoint is a public FastNear mainnet RPC endpoint. Endpoint availability and rate limits vary. Set `FASTNEAR_API_KEY` as an environment variable for compatible authenticated access if needed; credentials must never be committed to source or embedded in browser JavaScript.

## Reproducibility manifest

A reported result should include its chain ID, protocol version, block height/hash, requested frame/window, account selection method and seed, failed RPC reads, unresolved reasons, the observed key-type counts and the report/observation SHA-256 digests. A result of zero observed PQ adopters is a valid observation of its stated sampling frame.
