# Two-minute video walkthrough

A video is optional: the rules accept screenshots. If time is short, post `docs/screenshots/dashboard-demo.png` instead.

Record your own voice; keep the synthetic banner visible whenever the demo fixture is on screen.

**0:00–0:15 — Problem.** "NEAR now supports post-quantum ML-DSA-65 keys. But an existing account adds one using its old classical key, and the old key stays. Adding a post-quantum key is not the same as retiring classical authority."

**0:15–0:35 — Run it.** Show `python3 -m residual --fixture fixtures/demo.json --output demo-output`. "This fixture is synthetic, so you can see every case without me inventing mainnet numbers."

**0:35–1:00 — Dashboard.** Point to the three headline cards: "Four of six accounts have a PQ key. Three still hold a classical full-access key. Only one is PQ-only. A naive adoption count would say four; the honest migration count is one."

**1:00–1:30 — Live mainnet.** If you committed a live run, open `evidence/.../index.html`: "Block <height>, a seeded draw of <n> active signers: <x> with a PQ key, <y> still holding classical full access." Show the window, frame size and block hash. If the sample has no PQ adopters, say so: "Adoption is weeks old; this is the baseline." If you did not run it, show the command and say it is not yet run.

**1:30–1:50 — Reproducibility.** Show the provenance block and manifest: chain, protocol version, pinned block hash, seed, digests. "Anyone can rerun this and get the same sample."

**1:50–2:00 — Close.** "Residual is a read-only measurement, not a safety certificate. It reports what the access-key layer shows, and how much it can't see."
