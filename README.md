# Residual — NEAR Post-Quantum Migration Observatory

**Adding an ML-DSA-65 key is not the same as retiring classical full-access authority.** Residual is a read-only NEAR access-key scanner (Python standard library only). It reads every sampled account at one pinned block, classifies what it observes, keeps unknowns in the denominator, and writes a reproducible JSON report and a static dashboard.

Built at **NEAR HACKATHON 2026** (1–14 November). Tracks: **AI Security & Defense**, **Open Innovation**.

**Hosted web application:** https://agentzeta.github.io/residual-near/ — check any NEAR account, or run a live sample, straight from NEAR mainnet in your browser. Nothing to install, no wallet.

Demo screenshots: https://x.com/misskhan/status/2121739131005092198

Demo: https://agentzeta.github.io/residual-near

![Residual dashboard on the synthetic demo fixture](docs/screenshots/dashboard-demo.png)

## Check it in two minutes

| Do | See |
| --- | --- |
| Open the [live demo](https://agentzeta.github.io/residual-near/), type a normal account ID under **Check an account**, press **Check** | the account's state ("Classical only" for an account with only classical keys), the pinned block height and hash, and every access key with its type and permission |
| On the same page, press **Run now** under **Live sample** (3 blocks, 5 accounts) | progress through real mainnet blocks, then the headline counts, the state of every sampled account, and any accounts that enrolled an ML-DSA-65 key in that window |
| `python3 -m unittest discover -s tests -v` (Python 3.9+, no network) | Runs the offline Python unit and integration test suite |
| `node --test tests/web/parity.test.mjs` (Node 18+, no network) | Runs browser parity, seeded sampling, mocked RPC and rate-limit failover tests |
| `python3 -m residual --fixture fixtures/demo.json --output demo-output`, then open `demo-output/index.html` | "SYNTHETIC DATA" banner; 4 / 6 accounts with a PQ key, 3 / 6 still holding a classical full-access key, 1 / 6 PQ-only |
| `python3 -m residual --sample-signers 200 --window-blocks 60 --output live-output` (needs internet) | a live mainnet report pinned to one finalized block; see [docs/LIVE_RUN.md](docs/LIVE_RUN.md) |

The headline claim shows in the demo fixture: four of six accounts "have a post-quantum key", but only one exhibits PQ-only full access in the observed fixture. Adoption and observed access-key transition are different measures.

## What's in the repository

| Path | What it is |
| --- | --- |
| `residual/` | Python scanner and classifier (standard library only) and the report dashboard |
| `site/` | The live web app: landing page, account check, live sample, and recorded mainnet evidence. `site/residual.js` is the browser port of the classifier |
| `formal/` | Lean 4 model of the classifier with machine-checked proofs |
| `tests/` | Offline Python tests (including mock-RPC integration) and `tests/web/` for the browser code |
| `.github/workflows/` | `tests.yml` validates the classifier; `live-scan.yml` supports manual mainnet measurements; `demo-video.yml` supports optional recording. The website is published from the `gh-pages` branch |
| `demo/record.cjs` | An optional Playwright demo-recording harness |
| `docs/` | Reproducible live-run guide, product documentation and demonstration screenshots |

## Why this measurement matters

NEAR's ML-DSA-65 keys ([NEP-645](https://github.com/near/NEPs/blob/master/neps/nep-0645.md), protocol version 85 / neard 2.13) were added **alongside** Ed25519 and secp256k1, which are not deprecated, and **without asset migration**. An existing account gets its first ML-DSA key through an `AddKey` signed by one of its own classical full-access keys, so an existing account that adopts post-quantum keys starts out holding both kinds. It reaches PQ-only full access only if the owner later deletes every classical full-access key. (A brand-new account can be created with only an ML-DSA key; Residual classifies it as `COMPLETE`.) Counting "accounts with a PQ key" therefore overstates migration. Residual measures both numbers separately.

## Retirement evidence: post-submission extension

The existing `COMPLETE` state means **PQ full access is observed while classical full access is absent in one pinned snapshot**. That is more meaningful than detecting PQ key presence, but it is **not historical proof of key retirement**. A new comparison tool evaluates two ordered observations for the **same account** and tests whether each specifically identified old classical full-access key has disappeared while PQ full access remains. Its result is explicitly labeled as trusted-RPC observational evidence, not an independently verified cryptographic proof.

See [Classical-key retirement evidence](docs/RETIREMENT_EVIDENCE.md). **This module was added after the 14 November 2026 hackathon submission**, not claimed as part of the original entry.

## Five states (observed access-key layer only)

| State | Definition |
| --- | --- |
| `CLASSICAL_ONLY` | At least one classical full-access key, no PQ full-access key |
| `INCOMPLETE_WEAKEST_LINK` | Classical and PQ full-access keys coexist: the classical key is still an independent way in |
| `COMPLETE` | PQ full-access key(s), no classical full-access key, no unrecognized key |
| `PQ_FUNCTION_ONLY` | PQ function-call key(s) only, no full-access key |
| `UNDETERMINED` | Anything Residual cannot classify, always with a reason code (below) |

`COMPLETE` means only "observed full-access key transition". It is not a claim of quantum safety. If a `COMPLETE` account still has classical function-call keys, the report notes `RESIDUAL_CLASSICAL_FUNCTION_KEYS`.

Reason codes for `UNDETERMINED`: `ACCOUNT_NOT_FOUND`, `RPC_ERROR`, `MALFORMED_RESPONSE`, `NO_ACCESS_KEYS` (locked account), `UNRECOGNIZED_KEY`, `CLASSICAL_FUNCTION_ONLY`.

Key recognition: `ed25519:` (32 bytes), `secp256k1:` (64 bytes) and `ml-dsa-65-hash:` (32-byte SHA3-256 handle, the only ML-DSA form access-key lists return). The base58 payload is decoded and its length checked; a full `ml-dsa-65:` key inside a list is flagged as anomalous.

## Recorded mainnet observation

A timestamped, fully resolved **five-account mainnet scan** is included for reproducibility: [methodology and limitations](docs/MAINNET_OBSERVATION.md). It is not a representative sample of NEAR accounts and is not presented as daily monitoring.

## Demo data

The six demo accounts in `fixtures/demo.json` are **synthetic** and the dashboard says so in a banner. They show every state; they are not NEAR measurements. To serve the dashboard instead of opening the file: `python3 -m http.server 8080 --directory demo-output`, then open http://localhost:8080.

## Live mainnet scan

Default endpoint: `https://rpc.mainnet.fastnear.com`. (`rpc.mainnet.near.org` is deprecated and limited to 30 requests per minute.) Set `FASTNEAR_API_KEY` to send a key; it is never written to the report.

**Reproducible sample (recommended):**

```bash
python3 -m residual --sample-signers 200 --window-blocks 60 --output live-output
```

This pins the latest finalized block, walks back 60 blocks, collects every distinct transaction signer, and draws 200 of them ordered by `sha256(block hash + account)`. Anyone with the report can rebuild the same frame and draw. Accounts that received an ML-DSA-65 `AddKey` inside the window (including inside meta-transactions) are read at the same block as a separate **enrollers cohort**.

**Hand-picked list (convenience sample):**

```bash
python3 -m residual --accounts my-accounts.txt --output live-output
```

Step-by-step instructions and what to record: [docs/LIVE_RUN.md](docs/LIVE_RUN.md).

## Formal model

The classifier's logic is modelled in Lean 4 with machine-checked proofs, including that adding a post-quantum key to a classical-only account can never produce `COMPLETE`. Parity tests compare both the Python and browser classifiers with the model's 128-case truth table. See [formal/README.md](formal/README.md).

## What a report contains

- `report.json`: per-account state, key types, reason codes; denominators; unresolved counts by reason; provenance (chain id, protocol and node version, endpoint, pinned block height and hash, sampling frame, selection method); warnings; SHA-256 digests of the account list, raw observations and the report.
- `observations.json`: the raw access-key lists as returned by RPC.
- `index.html`: self-contained dashboard with drill-down and the full manifest.

Wilson 95% intervals appear only for a seeded random draw. They describe uncertainty within the stated frame (recent active signers), **not** all NEAR accounts.

## Boundaries

- Read-only: no signing keys, wallets, payment logic or transaction submission. The web app never asks for a wallet.
- RPC answers are trusted, not verified with light-client proofs; pinning one block gives consistency, not proof.
- A current snapshot cannot show historical key deletion, contract-based authority, recovery arrangements, validator security or off-chain signers.
- The active-signer frame over-represents bots, relayers and busy accounts. No ecosystem-wide adoption claim is made.

## Hackathon disclosure

- **When the code was written.** Every commit in this repository is dated within the build window; the first is 8 November 2026. An unpublished single-file prototype of the same idea was written in October 2026, after the hackathon was announced; none of its code is reused here.
- **Libraries and templates.** None in the scanner or the web app: Python standard library, plain JavaScript and CSS, no framework. Lean 4 (no Mathlib) for the optional formal model. The demo-video workflow installs Playwright and uses ffmpeg only to record the video. The web page loads Google Fonts.
- **AI-generated code.** AI coding assistants wrote most of the code, tests, web app, workflows and documentation, under the author's direction and review. Every result in this README can be reproduced with the commands above.
- **Other chains and other projects.** Residual is not deployed on, or ported from, another chain. This is the author's only NEAR HACKATHON entry.
- **NEAR features used.** NEP-645 ML-DSA-65 access keys (protocol 85), NEAR JSON-RPC (`view_access_key_list`, `block`, `chunk`, `status`) at a pinned finalized block, and meta-transaction (`Delegate`) parsing for the enrollers cohort.

## Problem Solved
NEAR's introduction of ML-DSA-65 post-quantum signatures creates a critical measurement problem: adding a quantum-resistant key does not automatically retire existing classical full-access keys.

An account may therefore appear to have adopted post-quantum cryptography while still allowing transactions authorized by Ed25519 or secp256k1 keys.

Wallet providers, custodians, account holders and ecosystem researchers need a reliable way to distinguish post-quantum key adoption from the actual retirement of classical full-access authority.

Without that distinction, migration statistics can create a misleading picture of security readiness. Residual addresses this measurement gap using observable onchain evidence, while explicitly preserving uncertainty.

## What we built
Residual is an open-source, read-only post-quantum migration observatory for NEAR.

It examines an account's access keys at a pinned finalized block and classifies the observed state into five categories: classical only, mixed classical/post-quantum authority, post-quantum full access only, post-quantum function-call only, and undetermined.

We built a live browser application, Python command-line scanner, deterministic sampling engine, JSON evidence reports, and a static dashboard. The system records block provenance, distinguishes resolved from unresolved observations, and supports reproducible analysis.

We also developed a Lean 4 formal model and a 128-case truth table to test classification behavior.

A recorded mainnet sample at block 224577581 successfully resolved five accounts. The public demonstration supports live account checks and sampling without connecting a wallet or submitting transactions.

Live demo: https://agentzeta.github.io/residual-near/

## How NEAR fits in 

Residual is built specifically around NEAR's account-access-key model and its introduction of ML-DSA-65 post-quantum signatures through NEP-645.

The application communicates directly with NEAR mainnet using JSON-RPC. It retrieves finalized block information, reads account access keys through view_access_key_list, and examines recent blocks and transactions to construct reproducible samples.

Residual recognizes NEAR's compact ml-dsa-65-hash key representation alongside Ed25519 and secp256k1, while distinguishing full-access permissions from restricted function-call permissions.

NEAR supplies both the post-quantum capability being measured and the onchain observations needed for that measurement.

Because Residual is a read-only security analytics tool, it does not require a smart contract deployment, NEAR Intents, a funded wallet or transaction signing.




## License

MIT, see [LICENSE](LICENSE).
