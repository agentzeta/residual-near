# Post-submission extension: Evidence of classical-key retirement

**Added after the 14 November 2026 hackathon submission. This is not represented as part of the original submitted build.**

> A migration check should establish that old authority is absent—not merely that a new cryptographic key exists.

## Two distinct claims

1. **Present-state absence:** at pinned finalized block B, the complete observed access-key list contains a PQ full-access key but no classical full-access key. The existing `COMPLETE` classifier addresses this narrow property. It does **not** establish that a particular old key existed previously.
2. **Observed retirement between snapshots:** at earlier block A an identified Ed25519 or secp256k1 full-access key was present; at later block B the account has PQ full access, no classical full-access keys remain, and each previously named classical full-access key is absent. The new `residual.retirement` comparison implements this *additional* test.

Both observations must have trusted block height and hash, the same NEAR chain, one successful complete key-list read for the same account, and recognized key formats. Missing or malformed evidence fails closed.

## Run locally

With two browser-downloaded Residual reports for the SAME account at distinct blocks:

```bash
python3 -m residual.retirement \
  --before earlier.json --after later.json --account example.near \
  --output comparison.json
```

With Python CLI `report.json` files, which store raw observations in separate files:

```bash
python3 -m residual.retirement \
  --before before/report.json --before-observations before/observations.json \
  --after after/report.json --after-observations after/observations.json \
  --account example.near --output comparison.json
```

The output includes the paired block hashes and one of:

- `RETIREMENT_OBSERVED_BETWEEN_SNAPSHOTS`: identified old classical full-access key(s) were present earlier, absent later; PQ full access was present later; no classical full-access path was observed later.
- `NOT_RETIRED`: a classical full-access key still remains at the later observation.
- `CURRENT_ABSENCE_ONLY`: PQ-only full access is observed, but historical retirement of an old key was not demonstrated.
- `NOT_ESTABLISHED`: no PQ full-access authority at the later observation.
- `INSUFFICIENT_EVIDENCE`: observations are missing, invalid, contradictory or not ordered.

```bash
python3 -m unittest tests.test_retirement -v
```

## Evidentiary limitations

This is **a temporal comparison of trusted RPC snapshots, not a cryptographic proof**. It does not show a particular DeleteKey receipt, guarantee continuous absence between sampled blocks, rule out a deleted-and-readded key between observations, verify RPC state using light-client proofs, or assess contract, recovery, validator and off-chain signing authority. Archival state availability varies by provider. RPC results are not a substitute for a verified state commitment.

For a stronger independently verifiable proof, future work would bind (a) before and after state commitments, (b) membership and non-membership proofs for each former classical full-access key, (c) a verified sequence or authenticated trace of `DeleteKey` effects and intervening key additions, and (d) a declared scope covering recovery and alternate authorization paths. That capability is **not implemented** here.

The original hackathon five-state classifier and demo remain unchanged. No new claims of network-wide adoption, quantum safety or historical key deletion are made.
