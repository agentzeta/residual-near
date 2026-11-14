# NEAR HACKATHON — form answers

Copy each field into the official submission form. You can submit only once; corrections go through the organizers' "Request changes" form. Deadline: 14 November 2026, 23:59 UTC (15 November, 05:29 IST).

| Field | Answer |
| --- | --- |
| Project name | Residual — NEAR Post-Quantum Migration Observatory |
| Team lead | [your name] |
| Email | [your email] |
| Team size | 1 |
| Tracks | AI Security & Defense; Open Innovation |
| NEAR account for prizes | [an account you created and control, e.g. yourname.near] |
| Repository | https://github.com/agentzeta/residual-near |
| Demo post (X) | [link to your post] |

## Project description (about 1,750 characters; the form allows 20 to 2,000)

Paste everything between the lines. If you ran the live scan, replace the last paragraph's bracketed sentence with your numbers; otherwise delete that sentence.

---

Residual measures whether NEAR accounts have actually migrated to post-quantum keys, not just added one.

NEAR added ML-DSA-65 access keys (NEP-645, protocol 85) alongside Ed25519 and secp256k1. An existing account adds its first ML-DSA key with a transaction signed by one of its classical full-access keys, so it starts out holding both. Until the owner deletes every classical full-access key, that old key is still a complete, independent way to control the account. Counting "accounts with a PQ key" therefore overstates migration.

Residual is a read-only scanner (Python standard library, no dependencies). It pins one finalized block, reads every sampled account's access keys at that block, and classifies each into five states: classical only, mixed PQ + classical, PQ-only full access, PQ function-call only, or undetermined with a reason code. Unknowns stay in the denominator. The sample is drawn from the chain itself: every distinct transaction signer in a recent block window, drawn by a seed equal to the pinned block hash, so anyone can rebuild it. Accounts that enrolled an ML-DSA key inside the window are read as a separate cohort. Output is a JSON report with provenance and SHA-256 digests, the raw RPC observations, and a static dashboard.

The classifier is modelled in Lean 4 with machine-checked proofs, including that adding a PQ key to a classical-only account can never count as migrated; a test checks the Python code against the model on all 128 input combinations. 40 tests, including an end-to-end run against a mock NEAR RPC.

[At mainnet block HEIGHT, a seeded draw of N active signers found X with a PQ key, Y still holding classical full access, and Z PQ-only.] Residual is a measurement, not a safety certificate.

---

## Disclosure (if the form asks)

All code was written during the build window (first commit 8 November 2026). An unpublished October prototype of the same idea is not reused. No third-party libraries or templates. AI coding assistants were used for code, tests and documentation.
