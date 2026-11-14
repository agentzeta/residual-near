# Recorded NEAR mainnet observation — 14 November 2026

A live browser scan of the NEAR mainnet access-key layer produced this pinned-block report. This is a **recorded observation, not a live-updating snapshot**. It was supplied by the project maintainer and has not been independently verified through a light client.

- Source: NEAR mainnet via `rpc.mainnet.fastnear.com`
- Pinned finalized block: **224577581**
- Block hash: `GCgeDTJpSUBDJrDCMK6p1Gjv5d31jCHK6rTyvtsCY5uk`
- Window: 3 blocks, heights 224577579–224577581
- Sampling frame: 14 distinct transaction signers; deterministic hash-seeded draw of 5
- Frame completeness: 3/3 blocks, 30 chunks, 0 missing reads; 21 transactions observed
- Account classifications: **5/5 resolved**, all five with observed classical full-access keys
- PQ keys observed: **0 of 5**; PQ-only full access: **0 of 5**

These are observations for a five-account draw from a recent-signer frame. They do **not** estimate all of NEAR, establish overall migration adoption, or certify quantum safety. The 95% Wilson interval for PQ presence in this narrow frame is **0–43.4%**. The downloadable JSON preserves the selected accounts and raw access-key responses.

**Evidence:** [Full JSON report](../site/data/latest/report.json) · [Run the scanner](LIVE_RUN.md)

The application provides live, separately sampled account checks when public RPC providers are available. Transient rate limiting may cause unresolved reads.
