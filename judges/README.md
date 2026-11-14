# Residual — Judge's quick evaluation

**Problem:** Adding an ML-DSA-65 post-quantum access key to a NEAR account does not automatically revoke existing Ed25519/secp256k1 full-access keys. Counting post-quantum key presence alone can overstate *observed full-access-key transition*.

**Build:** A read-only NEAR account-access-key scanner and public browser application. It pins one finalized block, enumerates account keys, distinguishes five access-key states, preserves undetermined cases and reports reproducible signer-window samples. Python CLI and browser implementations use the same classification rules, checked against a 128-row formal truth table.

**NEAR integration:** Direct NEAR mainnet JSON-RPC (`status`, `block`, `chunk`, `query/view_access_key_list`); explicit recognition of `ml-dsa-65-hash:` per [NEP-645](https://github.com/near/NEPs/blob/master/neps/nep-0645.md). No smart-contract deployment, account connection, tokens or NEAR Intents are used or required.

## Try the live app

1. Visit **https://agentzeta.github.io/residual-near/**.
2. Select **Check an account**, enter `hashkeympc.near` or `u-cexdex.near` on Mainnet, and press **Check**.
3. Select **Live sample**, choose **3 blocks / 5 accounts**, and run it. Public RPC rate limits may affect results; unresolved states are never silently omitted.
4. Review the **Recorded evidence** section for a successful dated observation, rather than assuming every live run succeeds.

## Run the offline verification

```bash
python3 -m unittest discover -s tests -v
node --test tests/web/parity.test.mjs
python3 -m residual --fixture fixtures/demo.json --output demo-output
```

The fixture is **synthetic**; its results are labeled as such. The Lean 4 model is in `formal/Residual.lean`, with the truth table in `formal/truth_table.json`.

## Recorded mainnet observation

The [14 November 2026 sample](../docs/MAINNET_OBSERVATION.md) was obtained at finalized block **224577581**, selecting 5 from a frame of 14 recently active signers across 3 blocks. All five access-key reads resolved; 5 had classical full-access keys; none had PQ keys observed. The frame was fully read. **This is not a claim that NEAR overall has zero PQ adoption.**

- [Recorded JSON with raw account responses](../site/data/latest/report.json)
- [Source and technical limits](../README.md)
- [Reproducible measurement method](../docs/LIVE_RUN.md)

**Limits:** This analyzes the observed access-key layer only. It does not infer past key deletion, contract authority, validators, recovery, light-client-verified RPC state or whole-account quantum safety. Samples of active signers are not representative of every NEAR account.

**Development disclosure:** See [README — Hackathon disclosure](../README.md#hackathon-disclosure) for pre-existing work, AI coding assistance and dependencies.
