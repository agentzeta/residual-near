# NEAR HACKATHON — form answers

The form is the **Submit** section of https://nearhackathon.com. You submit once; mistakes are fixed through https://nearhackathon.com/request-changes. Deadline: 14 November 2026, 23:59 UTC (15 November, 05:29 IST).

| Field | Answer |
| --- | --- |
| Project name | Residual |
| Team lead | [your full name] |
| Email address | [the email you want the organizers to use] |
| Team size | Solo builder |
| Tracks | AI Security & Defense, Open Innovation |
| NEAR wallet address | [your own NEAR account, for example yourname.near. Prizes are paid here] |
| Repository link | https://github.com/agentzeta/residual-near |
| Demo post link | [the URL of your X post] |
| What did you build? | The text below |
| Website | **Leave empty.** The rules file says a filled-in website field is treated as spam and rejects the submission. The live demo link is already in the description and the README |
| Consent | Read the notice on the form and tick it yourself |

## What did you build? (about 1,850 characters; the limit is 2,000)

Paste everything between the lines. If the daily snapshot has run, you may replace the bracketed sentence with its numbers (from the run page or the live site); otherwise delete it.

---

Residual checks whether NEAR accounts have actually moved to post-quantum keys, or only added one.

NEAR now supports ML-DSA-65 access keys (NEP-645, protocol 85). An existing account adds its first ML-DSA key with a transaction signed by its classical key, so it starts out holding both. Until the owner deletes every classical full-access key, that old key can still do anything the account can. Counting "accounts with a PQ key" overstates migration.

Live demo: https://agentzeta.github.io/residual-near/ — no wallet, nothing to install. Type any account and see its state, read live from NEAR mainnet at one pinned finalized block, with every key and its permission. Or run a live sample: the page walks back through recent blocks, collects every transaction signer, draws a sample seeded by the block hash (so anyone can rebuild it), and classifies each account. Accounts that added an ML-DSA key inside the window, including through meta-transactions, are shown as their own group. A daily 200-account snapshot is published by GitHub Actions with the raw RPC data and SHA-256 digests.

Five states: classical only; mixed PQ + classical; PQ full access only; PQ function-call only; undetermined, always with a reason code. Failed reads and unknown keys stay in the totals.

NEAR's role: the whole product reads NEAR's own data — access-key lists, blocks, chunks and delegate actions over NEAR RPC — to measure a property NEP-645 introduced.

Read-only and open source (MIT). Python standard library and plain JavaScript. The classifier is modelled in Lean 4 with machine-checked proofs, and tests check both the Python and browser code against the model on all 128 input combinations.

[Latest mainnet snapshot: block HEIGHT, X of N sampled accounts with a PQ key, Y still holding classical full access.] It measures the access-key layer only; it is not a safety certificate.

---
