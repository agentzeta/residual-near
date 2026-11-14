# Formal model (Lean 4)

`Residual.lean` models the five-state classifier in `residual/core.py` and proves, with Lean 4.24 and no Mathlib:

| Theorem | Says |
| --- | --- |
| `adding_pq_key_is_not_migration` | Adding an ML-DSA full-access key to a classical-only account gives the mixed state, never `COMPLETE` |
| `retiring_classical_keys_completes` | Removing every classical full-access key from a mixed account is what makes it `COMPLETE` |
| `classical_full_never_complete` | No account holding a classical full-access key is ever `COMPLETE` |
| `unknown_never_complete` | An unrecognized key always blocks `COMPLETE` |
| `complete_iff` | `COMPLETE` exactly when the read succeeded, a PQ full-access key is present, and no classical full-access or unknown key is |
| `failed_read_undetermined` | A failed or malformed read is always `UNDETERMINED` |
| `membership_only` | The result depends only on which key types are present, not their order or repeats |

The theorems use no `sorry` and rely only on Lean's standard axioms (`propext`, `Quot.sound`, `Classical.choice`).

**What this does and doesn't prove.** The theorems are about the model. `tests/test_formal_model.py` ties the model to the code: it checks the Python classifier against the model's full truth table (`truth_table.json`, 32 key-type combinations × 4 read statuses). Nothing here proves anything about NEAR, RPC answers, key parsing, or account security.

Check it yourself:

```bash
lean formal/Residual.lean > formal/truth_table.json   # compiles every proof, prints the table
python3 -m unittest tests.test_formal_model -v
```
